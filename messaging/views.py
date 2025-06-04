from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

# Import your tasks
from .tasks import moderate_content, send_webhook, process_message_encryption
from .models import Message, Conversation
from .serializers import MessageSerializer
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

from .models import (
    Conversation, Message, MessageType, MessageStatus,
    MessageReaction, ConversationType, ConversationParticipant
)
from .serializers import (
    ConversationSerializer, MessageSerializer, CreateDirectMessageSerializer,
    SendMessageSerializer, CreateGroupConversationSerializer, ReactionSerializer,
    # OPTIMIZATION: Import new optimized serializers
    ConversationListSerializer, MessageListSerializer, BulkMessageStatusSerializer,
    MessageSearchSerializer
)

# OPTIMIZATION: Import caching utilities
from .utils import (
    get_user_conversations_cached, get_conversation_messages_cached,
    invalidate_conversation_cache, invalidate_user_cache
)

User = get_user_model()

# OPTIMIZATION: Custom pagination classes
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class MessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ConversationViewSet(viewsets.ModelViewSet):
    """API endpoint for conversations"""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination  # OPTIMIZATION: Add pagination
    
    def get_queryset(self):
        """Get conversations for the current user with optimizations"""
        # Fix for Swagger schema generation - handle AnonymousUser
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        
        # Handle case where user is not authenticated
        if not self.request.user.is_authenticated:
            return Conversation.objects.none()
        
        # OPTIMIZATION: Use cached conversations for list view
        if self.action == 'list':
            return self.get_optimized_conversations()
        
        return Conversation.get_user_conversations(self.request.user)
    
    def get_optimized_conversations(self):
        """Get optimized conversation list with prefetching"""
        # OPTIMIZATION: Use cached data
        conversations = get_user_conversations_cached(self.request.user)
        
        # OPTIMIZATION: Prefetch related data to reduce queries
        conversations = conversations.select_related(
            'participant1', 'participant2', 'created_by'
        ).prefetch_related(
            Prefetch(
                'participants',
                queryset=ConversationParticipant.objects.select_related('user').filter(is_active=True)
            ),
            Prefetch(
                'messages',
                queryset=Message.objects.select_related('sender').filter(is_deleted=False).order_by('-created_at')[:1],
                to_attr='prefetched_last_message'
            )
        )
        
        # OPTIMIZATION: Annotate with unread counts
        conversations = conversations.annotate(
            prefetched_unread_count=Count(
                'messages',
                filter=Q(
                    messages__status__in=[MessageStatus.SENT, MessageStatus.DELIVERED]
                ) & ~Q(messages__sender=self.request.user)
            )
        )
        
        return conversations
    
    def get_serializer_class(self):
        """OPTIMIZATION: Use different serializers for different actions"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def list(self, request, *args, **kwargs):
        """OPTIMIZATION: Optimized list view with caching"""
        cache_key = f"user_conversations_list_{request.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        # Get optimized queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            
            # Cache for 2 minutes
            cache.set(cache_key, result.data, 120)
            return result
        
        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 120)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def direct(self, request):
        """Create or get direct conversation with another user"""
        serializer = CreateDirectMessageSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            recipient_id = serializer.validated_data['recipient_id']
            recipient = get_object_or_404(User, id=recipient_id)
            
            # Get or create conversation
            conversation, created = Conversation.get_or_create_direct_conversation(
                request.user, recipient
            )
            
            # OPTIMIZATION: Invalidate cache when new conversation is created
            if created:
                invalidate_user_cache(request.user.id)
                invalidate_user_cache(recipient.id)
            
            # If message content provided, create message
            if 'message' in serializer.validated_data:
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    message_type=serializer.validated_data.get('message_type', MessageType.TEXT),
                    content=serializer.validated_data.get('message'),
                    status=MessageStatus.SENT
                )
                
                # OPTIMIZATION: Queue background tasks
                moderate_content.delay(message.id, message.content)
                process_message_encryption.delay(message.id)
            
            # Return conversation data
            return Response(
                ConversationSerializer(conversation, context={'request': request}).data,
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def group(self, request):
        """Create a new group conversation"""
        serializer = CreateGroupConversationSerializer(data=request.data)
        
        if serializer.is_valid():
            title = serializer.validated_data['title']
            description = serializer.validated_data.get('description', '')
            
            # Get participant users
            participant_ids = serializer.validated_data.get('participant_ids', [])
            participants = list(User.objects.filter(id__in=participant_ids))
            
            # Create group conversation
            conversation = Conversation.create_group_conversation(
                creator=request.user,
                title=title,
                description=description,
                participants=participants
            )
            
            # OPTIMIZATION: Invalidate cache for all participants
            for participant in participants + [request.user]:
                invalidate_user_cache(participant.id)
            
            return Response(
                ConversationSerializer(conversation, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add participant to group conversation"""
        conversation = self.get_object()
        
        if conversation.conversation_type == ConversationType.DIRECT:
            return Response(
                {"detail": "Cannot add participants to direct conversations"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"detail": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            participant = conversation.add_participant(user, added_by=request.user)
            
            # OPTIMIZATION: Invalidate cache for new participant
            invalidate_user_cache(user.id)
            
            return Response(status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Remove participant from group conversation"""
        conversation = self.get_object()
        
        if conversation.conversation_type == ConversationType.DIRECT:
            return Response(
                {"detail": "Cannot remove participants from direct conversations"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"detail": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            conversation.remove_participant(user, removed_by=request.user)
            
            # OPTIMIZATION: Invalidate cache for removed participant
            invalidate_user_cache(user.id)
            
            return Response(status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class MessageViewSet(viewsets.ModelViewSet):
    """API endpoint for messages"""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination  # OPTIMIZATION: Add pagination
    
    def get_queryset(self):
        """Get messages for a specific conversation with optimizations"""
        # Fix for Swagger schema generation - handle AnonymousUser
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()
        
        # Handle case where user is not authenticated
        if not self.request.user.is_authenticated:
            return Message.objects.none()
            
        conversation_id = self.request.query_params.get('conversation_id')
        if not conversation_id:
            return Message.objects.none()
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            if not conversation.is_participant(self.request.user):
                return Message.objects.none()
            
            # OPTIMIZATION: Use cached messages for list view
            if self.action == 'list':
                return self.get_optimized_messages(conversation_id)
            
            return Message.objects.filter(
                conversation=conversation,
                is_deleted=False
            ).order_by('created_at')
        except Conversation.DoesNotExist:
            return Message.objects.none()
    
    def get_optimized_messages(self, conversation_id):
        """Get optimized message list with prefetching"""
        # OPTIMIZATION: Use cached messages
        messages = get_conversation_messages_cached(conversation_id)
        
        # OPTIMIZATION: Prefetch related data
        messages = messages.select_related('sender', 'reply_to__sender').prefetch_related(
            Prefetch(
                'reactions',
                queryset=MessageReaction.objects.select_related('user')
            )
        ).annotate(
            reaction_count=Count('reactions')
        )
        
        return messages
    
    def get_serializer_class(self):
        """OPTIMIZATION: Use different serializers for different actions"""
        if self.action == 'list':
            return MessageListSerializer
        return MessageSerializer
    
    def list(self, request, *args, **kwargs):
        """OPTIMIZATION: Optimized list view with caching"""
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response({"detail": "conversation_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        cache_key = f"conversation_messages_{conversation_id}_{request.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            
            # Cache for 1 minute
            cache.set(cache_key, result.data, 60)
            return result
        
        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 60)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send a new message with optimizations"""
        serializer = SendMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            conversation_id = serializer.validated_data['conversation_id']
            
            try:
                conversation = Conversation.objects.get(id=conversation_id)
                
                # Check if user is participant
                if not conversation.is_participant(request.user):
                    return Response(
                        {"detail": "You are not a participant in this conversation"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Get reply_to message if provided
                reply_to = None
                if 'reply_to' in serializer.validated_data:
                    try:
                        reply_to = Message.objects.get(id=serializer.validated_data['reply_to'])
                    except Message.DoesNotExist:
                        return Response(
                            {"detail": "Reply message not found"},
                            status=status.HTTP_404_NOT_FOUND
                        )
                
                # Create message
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    message_type=serializer.validated_data.get('message_type', MessageType.TEXT),
                    content=serializer.validated_data.get('message'),
                    file=serializer.validated_data.get('file'),
                    reply_to=reply_to,
                    latitude=serializer.validated_data.get('latitude'),
                    longitude=serializer.validated_data.get('longitude'),
                    location_name=serializer.validated_data.get('location_name'),
                    status=MessageStatus.SENT
                )
                
                # OPTIMIZATION: Invalidate caches
                invalidate_conversation_cache(conversation_id)
                for participant in conversation.get_participants():
                    invalidate_user_cache(participant.id)
                
                # OPTIMIZATION: Queue background tasks
                if message.content:
                    moderate_content.delay(message.id, message.content)
                process_message_encryption.delay(message.id)
                
                # Send webhook notification
                webhook_payload = {
                    'event': 'message_created',
                    'message_id': str(message.id),
                    'conversation_id': str(conversation.id),
                    'sender': request.user.username,
                    'timestamp': message.created_at.isoformat()
                }
                send_webhook.delay('https://your-webhook-url.com/messages', webhook_payload)
                
                return Response(
                    MessageSerializer(message).data,
                    status=status.HTTP_201_CREATED
                )
            except Conversation.DoesNotExist:
                return Response(
                    {"detail": "Conversation not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # OPTIMIZATION: Add bulk operations
    @action(detail=False, methods=['post'])
    def bulk_mark_read(self, request):
        """Mark multiple messages as read"""
        serializer = BulkMessageStatusSerializer(data=request.data)
        
        if serializer.is_valid():
            message_ids = serializer.validated_data['message_ids']
            
            # Update messages in bulk
            updated_count = Message.objects.filter(
                id__in=message_ids,
                conversation__in=Conversation.get_user_conversations(request.user)
            ).exclude(sender=request.user).update(
                status=MessageStatus.READ,
                read_at=timezone.now()
            )
            
            return Response({
                'updated_count': updated_count,
                'message': f'Marked {updated_count} messages as read'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """OPTIMIZATION: Search messages with caching"""
        serializer = MessageSearchSerializer(data=request.query_params)
        
        if serializer.is_valid():
            # Create cache key based on search parameters
            cache_key = f"message_search_{request.user.id}_{hash(str(sorted(serializer.validated_data.items())))}"
            cached_results = cache.get(cache_key)
            
            if cached_results:
                return Response(cached_results)
            
            # Build query
            queryset = Message.objects.filter(
                conversation__in=Conversation.get_user_conversations(request.user),
                is_deleted=False
            ).select_related('sender', 'conversation').order_by('-created_at')
            
            # Apply filters
            if serializer.validated_data.get('query'):
                queryset = queryset.filter(content__icontains=serializer.validated_data['query'])
            
            if serializer.validated_data.get('conversation_id'):
                queryset = queryset.filter(conversation_id=serializer.validated_data['conversation_id'])
            
            if serializer.validated_data.get('message_type'):
                queryset = queryset.filter(message_type=serializer.validated_data['message_type'])
            
            if serializer.validated_data.get('sender_id'):
                queryset = queryset.filter(sender_id=serializer.validated_data['sender_id'])
            
            if serializer.validated_data.get('date_from'):
                queryset = queryset.filter(created_at__gte=serializer.validated_data['date_from'])
            
            if serializer.validated_data.get('date_to'):
                queryset = queryset.filter(created_at__lte=serializer.validated_data['date_to'])
            
            # Paginate results
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = MessageListSerializer(page, many=True)
                result = self.get_paginated_response(serializer.data)
                
                # Cache for 5 minutes
                cache.set(cache_key, result.data, 300)
                return result
            
            serializer = MessageListSerializer(queryset[:50], many=True)  # Limit to 50 results
            cache.set(cache_key, serializer.data, 300)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        
        # Only mark as read if user is recipient
        if message.sender != request.user and message.conversation.is_participant(request.user):
            message.mark_as_read()
            
            # OPTIMIZATION: Invalidate relevant caches
            invalidate_conversation_cache(message.conversation.id)
            
            return Response(status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "Cannot mark this message as read"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        """Edit message content"""
        message = self.get_object()
        
        # Only sender can edit
        if message.sender != request.user:
            return Response(
                {"detail": "You can only edit your own messages"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only text messages can be edited
        if message.message_type != MessageType.TEXT:
            return Response(
                {"detail": "Only text messages can be edited"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get new content
        new_content = request.data.get('content')
        if not new_content:
            return Response(
                {"detail": "Content is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.edit_content(new_content)
        
        # OPTIMIZATION: Invalidate caches and queue moderation
        invalidate_conversation_cache(message.conversation.id)
        moderate_content.delay(message.id, new_content)
        
        return Response(MessageSerializer(message).data)
    
    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        """Soft delete message"""
        message = self.get_object()
        
        # Only sender can delete
        if message.sender != request.user:
            return Response(
                {"detail": "You can only delete your own messages"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.soft_delete()
        
        # OPTIMIZATION: Invalidate caches
        invalidate_conversation_cache(message.conversation.id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Add reaction to message"""
        message = self.get_object()
        serializer = ReactionSerializer(data=request.data)
        
        if serializer.is_valid():
            emoji = serializer.validated_data['emoji']
            
            # Check if user is participant
            if not message.conversation.is_participant(request.user):
                return Response(
                    {"detail": "You are not a participant in this conversation"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Add reaction
            try:
                reaction = MessageReaction.objects.create(
                    message=message,
                    user=request.user,
                    emoji=emoji
                )
                
                # OPTIMIZATION: Invalidate message cache
                invalidate_conversation_cache(message.conversation.id)
                
                return Response(status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def remove_reaction(self, request, pk=None):
        """Remove reaction from message"""
        message = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {"detail": "Emoji is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove reaction
        MessageReaction.objects.filter(
            message=message,
            user=request.user,
            emoji=emoji
        ).delete()
        
        # OPTIMIZATION: Invalidate message cache
        invalidate_conversation_cache(message.conversation.id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


# OPTIMIZATION: Keep your existing function-based views but add optimizations
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_message(request):
    """Create a new message with background processing"""
    try:
        data = request.data
        conversation_id = data.get('conversation_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        
        # Get conversation
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Create the message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=message_type
        )
        
        # OPTIMIZATION: Invalidate caches
        invalidate_conversation_cache(conversation_id)
        for participant in conversation.get_participants():
            invalidate_user_cache(participant.id)
        
        # Queue background tasks (non-blocking)
        moderate_content.delay(message.id, content)  # Content moderation
        process_message_encryption.delay(message.id)  # Encryption
        
        # Send webhook notification
        webhook_payload = {
            'event': 'message_created',
            'message_id': str(message.id),  # Convert UUID to string
            'conversation_id': str(conversation.id),
            'sender': request.user.username,
            'timestamp': message.created_at.isoformat()
        }
        send_webhook.delay('https://your-webhook-url.com/messages', webhook_payload)
        
        # Return immediate response (don't wait for background tasks)
        serializer = MessageSerializer(message)
        return Response({
            'status': 'success',
            'message': serializer.data,
            'background_tasks_queued': True
        }, status=status.HTTP_201_CREATED)
        
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_message_cleanup(request):
    """Trigger bulk message cleanup"""
    from .tasks import cleanup_expired_messages
    
    # Queue the cleanup task
    task = cleanup_expired_messages.delay()
    
    return Response({
        'status': 'cleanup_queued',
        'task_id': task.id,
        'message': 'Cleanup task has been queued and will run in the background'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_analytics(request):
    """Generate analytics report"""
    from .tasks import calculate_analytics
    
    # Queue analytics calculation
    task = calculate_analytics.delay()
    
    return Response({
        'status': 'analytics_queued',
        'task_id': task.id,
        'message': 'Analytics calculation has been queued'
    })

@api_view(['GET'])
def task_status(request, task_id):
    """Check the status of a background task"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id)
    
    return Response({
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None
    })

# OPTIMIZATION: Add new analytics endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_analytics(request, conversation_id):
    """Get analytics for a specific conversation"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        if not conversation.is_participant(request.user):
            return Response(
                {"detail": "You are not a participant in this conversation"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cache analytics for 10 minutes
        cache_key = f"conversation_analytics_{conversation_id}"
        analytics = cache.get(cache_key)
        
        if not analytics:
            from .analytics import AnalyticsEngine
            analytics = AnalyticsEngine.get_conversation_analytics(conversation)
            cache.set(cache_key, analytics, 600)
        
        return Response(analytics)
        
    except Conversation.DoesNotExist:
        return Response(
            {"detail": "Conversation not found"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_engagement(request):
    """Get user engagement analytics"""
    cache_key = f"user_engagement_{request.user.id}"
    engagement = cache.get(cache_key)
    
    if not engagement:
        from .analytics import AnalyticsEngine
        engagement = AnalyticsEngine.get_user_engagement_summary(request.user)
        cache.set(cache_key, engagement, 300)  # Cache for 5 minutes
    
    return Response(engagement)
