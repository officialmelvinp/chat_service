from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Q, Count, Exists, OuterRef
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator

from .models import FriendRequest, Friendship
from .serializers import (
    FriendRequestSerializer, 
    FriendRequestResponseSerializer,
    FriendListSerializer,
    PendingRequestsSerializer,
    FriendSearchSerializer,
    FriendStatsSerializer,
    UserBasicSerializer
)
from .pagination import FriendsPagination, SearchPagination, RequestsPagination

User = get_user_model()

class FriendRequestView(generics.CreateAPIView):
    """
    Send a friend request to another user.
    
    Requires the receiver's username in the request body.
    """
    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save()
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({
            'message': f"Friend request sent to {serializer.validated_data['receiver_username'].username}",
            'request': serializer.data
        }, status=status.HTTP_201_CREATED)


class FriendRequestResponseView(generics.GenericAPIView):
    """
    Accept or reject a friend request.
    
    Requires the request_id and action ('accept' or 'reject') in the request body.
    """
    serializer_class = FriendRequestResponseSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response({
            'message': result['message'],
            'status': result['status']
        }, status=status.HTTP_200_OK)


class FriendListView(generics.ListAPIView):
    """
    Get the current user's friends list with pagination.
    
    Supports large friend lists (celebrities, influencers).
    Query params: ?page=1&page_size=20
    """
    serializer_class = UserBasicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FriendsPagination
    
    def get_queryset(self):
        """Get paginated friends list"""
        return Friendship.get_friends(self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data)
            
            # Add additional stats to the response data
            response_data.data['total_friends'] = len(queryset)
            response_data.data['online_friends'] = 0  # We'll implement this later
            
            return response_data
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': len(queryset),
            'total_friends': len(queryset),
            'online_friends': 0
        })
        
        


class PendingRequestsView(generics.GenericAPIView):
    """
    Get all pending friend requests for the current user with pagination.
    
    Handles celebrities with hundreds of pending requests.
    Query params: ?page=1&page_size=15
    """
    serializer_class = PendingRequestsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = RequestsPagination
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # Get received requests
        received_requests = FriendRequest.objects.filter(
            receiver=user,
            status='pending'
        ).select_related('sender').order_by('-created_at')
        
        # Get sent requests
        sent_requests = FriendRequest.objects.filter(
            sender=user,
            status='pending'
        ).select_related('receiver').order_by('-created_at')
        
        # Paginate received requests
        received_page = self.paginate_queryset(received_requests)
        if received_page is not None:
            received_serializer = FriendRequestSerializer(received_page, many=True)
            received_data = {
                'results': received_serializer.data,
                'count': self.paginator.page.paginator.count,
                'total_pages': self.paginator.page.paginator.num_pages,
                'current_page': self.paginator.page.number,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
            }
        else:
            received_serializer = FriendRequestSerializer(received_requests, many=True)
            received_data = {
                'results': received_serializer.data,
                'count': len(received_requests),
                'total_pages': 1,
                'current_page': 1,
                'next': None,
                'previous': None,
            }
        
        # For sent requests, we'll include them but not paginate separately for now
        sent_serializer = FriendRequestSerializer(sent_requests[:10], many=True)  # Limit to 10 recent
        
        return Response({
            'received_requests': received_data,
            'sent_requests': {
                'results': sent_serializer.data,
                'count': sent_requests.count()
            },
            'total_pending_received': received_requests.count(),
            'total_pending_sent': sent_requests.count()
        })

class FriendStatsView(generics.RetrieveAPIView):
    """
    Get friendship statistics for the current user.
    
    Returns counts of total friends, online friends, and pending requests.
    """
    serializer_class = FriendStatsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class FriendSearchView(generics.GenericAPIView):
    """
    Search for users to add as friends with pagination.
    
    Handles large search results (thousands of users named 'John').
    Query params: ?page=1&page_size=25&query=john
    """
    serializer_class = FriendSearchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SearchPagination
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        current_user = request.user
        
        # Get IDs of current friends
        friend_ids = Friendship.objects.filter(
            Q(user1=current_user) | Q(user2=current_user)
        ).values_list('user1', 'user2').distinct()
        
        # Flatten the list of friend IDs
        flat_friend_ids = []
        for user1_id, user2_id in friend_ids:
            flat_friend_ids.extend([user1_id, user2_id])
        
        # Remove current user from exclusion list
        if current_user.id in flat_friend_ids:
            flat_friend_ids.remove(current_user.id)
        
        # Get IDs of users with pending requests (in either direction)
        pending_request_user_ids = FriendRequest.objects.filter(
            (Q(sender=current_user) | Q(receiver=current_user)) & 
            Q(status='pending')
        ).values_list('sender', 'receiver').distinct()
        
        # Flatten pending request user IDs
        flat_pending_ids = []
        for sender_id, receiver_id in pending_request_user_ids:
            flat_pending_ids.extend([sender_id, receiver_id])
        
        # Remove current user from exclusion list
        if current_user.id in flat_pending_ids:
            flat_pending_ids.remove(current_user.id)
        
        # Combine all IDs to exclude
        exclude_ids = list(set(flat_friend_ids + flat_pending_ids))
        
        # Search for users (REMOVED the [:20] limit!)
        users = User.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query)
        ).exclude(
            id__in=exclude_ids
        ).exclude(
            id=current_user.id
        ).order_by('username')  # Add ordering for consistent pagination
        
        # Paginate the results
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = UserBasicSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Fallback if pagination fails
        serializer = UserBasicSerializer(users, many=True)
        return Response({
            'results': serializer.data,
            'count': users.count()
        })


class FriendshipManagementView(generics.GenericAPIView):
    """
    Remove an existing friendship.
    
    Requires the friend's username in the request body.
    """
    serializer_class = UserBasicSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        friend_username = request.data.get('username')
        if not friend_username:
            return Response({
                'error': 'Friend username is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            friend = User.objects.get(username=friend_username)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if they are friends
        if not Friendship.are_friends(request.user, friend):
            return Response({
                'error': 'You are not friends with this user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find and delete the friendship
        if request.user.id < friend.id:
            friendship = Friendship.objects.get(user1=request.user, user2=friend)
        else:
            friendship = Friendship.objects.get(user1=friend, user2=request.user)
        
        friendship.delete()
        
        return Response({
            'message': f'Friendship with {friend.username} has been removed'
        }, status=status.HTTP_200_OK)


class CancelFriendRequestView(generics.GenericAPIView):
    """
    Cancel a pending friend request sent by the current user.
    
    Requires the request_id in the URL.
    """
    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, request_id, *args, **kwargs):
        try:
            friend_request = FriendRequest.objects.get(
                id=request_id,
                sender=request.user,
                status='pending'
            )
        except FriendRequest.DoesNotExist:
            return Response({
                'error': 'Friend request not found or cannot be canceled'
            }, status=status.HTTP_404_NOT_FOUND)
        
        receiver_username = friend_request.receiver.username
        friend_request.delete()
        
        return Response({
            'message': f'Friend request to {receiver_username} has been canceled'
        }, status=status.HTTP_200_OK)


class MutualFriendsView(generics.GenericAPIView):
    """
    Get mutual friends between the current user and another user with pagination.
    
    Handles users with thousands of mutual friends.
    """
    serializer_class = UserBasicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FriendsPagination
    
    def get(self, request, username, *args, **kwargs):
        try:
            other_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get current user's friends
        current_user_friends = set(Friendship.get_friends(request.user))
        
        # Get other user's friends
        other_user_friends = set(Friendship.get_friends(other_user))
        
        # Find mutual friends
        mutual_friends = list(current_user_friends.intersection(other_user_friends))
        
        # Paginate mutual friends
        page = self.paginate_queryset(mutual_friends)
        if page is not None:
            serializer = UserBasicSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        return Response({
            'results': UserBasicSerializer(mutual_friends, many=True).data,
            'count': len(mutual_friends)
        })