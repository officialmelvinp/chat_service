from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer, UserSerializer, ProfileUpdateSerializer, UserListSerializer
)
from .permissions import IsOwnerOrReadOnly
from .throttling import LoginRateThrottle, MessageSendRateThrottle
from .pagination import UserListPagination  # Import the new pagination

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [LoginRateThrottle]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully. You can now login.'
        }, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with throttling"""
    throttle_classes = [LoginRateThrottle]

class UserDetailView(generics.RetrieveUpdateAPIView):
    """Get and update current user's profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProfileUpdateSerializer
        return UserSerializer

class UserListView(generics.ListAPIView):
    """
    List all users (for finding people to chat with)
    
    Supports pagination for large user bases.
    Query params: ?page=1&page_size=25
    """
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserListPagination  # Use the new pagination class
    
    def get_queryset(self):
        """Get all active users except current user"""
        return User.objects.filter(
            is_active=True
        ).exclude(
            id=self.request.user.id
        ).order_by('username')
    
    def list(self, request, *args, **kwargs):
        """Override to add additional metadata"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data)
            
            # Add additional stats
            response_data.data['total_users'] = queryset.count()
            response_data.data['online_users'] = queryset.filter(is_online=True).count()
            
            return response_data
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': queryset.count(),
            'total_users': queryset.count(),
            'online_users': queryset.filter(is_online=True).count()
        })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_online_status(request):
    """Update user's online status"""
    user = request.user
    is_online = request.data.get('is_online', False)
    
    user.is_online = is_online
    if is_online:
        user.update_last_active()
    else:
        user.save(update_fields=['is_online'])
    
    return Response({
        'message': f'Status updated to {"online" if is_online else "offline"}',
        'is_online': user.is_online,
        'last_active': user.last_active
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deactivate_account(request):
    """Temporarily deactivate account (can be reactivated later)"""
    user = request.user
    user.is_active = False
    user.is_online = False
    user.save()
    return Response({'message': 'Account deactivated successfully. You can reactivate by logging in again.'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def delete_account(request):
    """Permanently delete account and all associated data"""
    user = request.user
    # Optional: Add password confirmation for security
    password = request.data.get('password')
    if not user.check_password(password):
        return Response({'error': 'Password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Delete the user (this will cascade to related models)
    user.delete()
    return Response({'message': 'Account permanently deleted'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Secure logout with token blacklisting"""
    try:
        refresh_token = request.data.get("refresh_token")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Update user status
        user = request.user
        user.is_online = False
        user.save(update_fields=['is_online'])
        
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
        
    except TokenError:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)