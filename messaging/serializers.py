from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Conversation, ConversationType, Message, MessageType,
    MessageStatus, MessageReaction, ConversationParticipant
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class MessageReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'emoji', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    reply_to_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'file', 'file_name', 'file_size', 'status', 'created_at',
            'delivered_at', 'read_at', 'is_edited', 'edited_at',
            'is_deleted', 'reply_to', 'reply_to_preview', 'reactions',
            'latitude', 'longitude', 'location_name'
        ]
        read_only_fields = [
            'id', 'sender', 'created_at', 'delivered_at', 'read_at',
            'is_edited', 'edited_at', 'is_deleted'
        ]
    
    def get_reply_to_preview(self, obj):
        """Get a preview of the message being replied to"""
        if not obj.reply_to:
            return None
        
        reply = obj.reply_to
        return {
            'id': reply.id,
            'sender_name': reply.sender.username,
            'content_preview': reply.content[:50] if reply.content else None,
            'message_type': reply.message_type
        }


# OPTIMIZATION: Add optimized serializer for list views
class MessageListSerializer(serializers.ModelSerializer):
    """Optimized serializer for message lists - excludes heavy fields"""
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    reaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender_name', 'message_type', 'content',
            'file_name', 'status', 'created_at', 'is_edited', 'is_deleted',
            'reply_to', 'reaction_count'
        ]
    
    def get_reaction_count(self, obj):
        """Get total reaction count without loading all reactions"""
        return getattr(obj, 'reaction_count', 0)


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'role', 'joined_at', 'left_at',
            'is_active', 'is_muted', 'muted_until'
        ]


class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'title', 'description',
            'avatar', 'created_at', 'updated_at', 'last_message_at',
            'participants', 'last_message', 'unread_count',
            'is_active', 'is_public', 'join_by_link'
        ]
    
    def get_participants(self, obj):
        """Get conversation participants based on type"""
        request = self.context.get('request')
        
        if obj.conversation_type == ConversationType.DIRECT:
            # For direct messages, just return the two participants
            return [
                UserSerializer(obj.participant1).data,
                UserSerializer(obj.participant2).data
            ]
        else:
            # For groups, return active participants
            participants = obj.participants.filter(is_active=True)
            return ConversationParticipantSerializer(participants, many=True).data
    
    def get_last_message(self, obj):
        """Get the most recent message in the conversation"""
        last_message = obj.get_latest_message()
        if last_message:
            return {
                'id': last_message.id,
                'sender_name': last_message.sender.username,
                'content': last_message.content if not last_message.is_deleted else None,
                'is_deleted': last_message.is_deleted,
                'message_type': last_message.message_type,
                'created_at': last_message.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        """Get count of unread messages for the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0


# OPTIMIZATION: Add lightweight serializer for conversation lists
class ConversationListSerializer(serializers.ModelSerializer):
    """Optimized serializer for conversation lists - minimal data"""
    other_participant = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'title', 'avatar',
            'last_message_at', 'other_participant', 'last_message_preview',
            'unread_count', 'is_active'
        ]
    
    def get_other_participant(self, obj):
        """Get the other participant for direct messages"""
        request = self.context.get('request')
        if obj.conversation_type == ConversationType.DIRECT and request:
            other = obj.get_other_participant(request.user)
            return {
                'id': other.id,
                'username': other.username,
                'first_name': other.first_name,
                'last_name': other.last_name
            }
        return None
    
    def get_last_message_preview(self, obj):
        """Get minimal last message info"""
        # Use prefetched last message if available
        if hasattr(obj, 'prefetched_last_message'):
            last_message = obj.prefetched_last_message
        else:
            last_message = obj.get_latest_message()
        
        if last_message:
            return {
                'content': last_message.content[:50] if last_message.content else None,
                'message_type': last_message.message_type,
                'created_at': last_message.created_at,
                'is_deleted': last_message.is_deleted
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread count from prefetched data if available"""
        if hasattr(obj, 'prefetched_unread_count'):
            return obj.prefetched_unread_count
        
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0


class CreateDirectMessageSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField()
    message = serializers.CharField(required=False)
    message_type = serializers.ChoiceField(choices=MessageType.choices, default=MessageType.TEXT)
    file = serializers.FileField(required=False)
    
    def validate_recipient_id(self, value):
        """Validate recipient exists and is not the current user"""
        User = get_user_model()
        request = self.context.get('request')
        
        try:
            recipient = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found")
        
        if request and request.user.id == value:
            raise serializers.ValidationError("Cannot send message to yourself")
        
        return value


class SendMessageSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    message = serializers.CharField(required=False)
    message_type = serializers.ChoiceField(choices=MessageType.choices, default=MessageType.TEXT)
    file = serializers.FileField(required=False)
    reply_to = serializers.IntegerField(required=False)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
    location_name = serializers.CharField(required=False)
    
    def validate(self, data):
        """Validate message data based on message type"""
        message_type = data.get('message_type')
        
        if message_type == MessageType.TEXT and not data.get('message'):
            raise serializers.ValidationError({"message": "Text message cannot be empty"})
        
        if message_type in [MessageType.IMAGE, MessageType.FILE, MessageType.VOICE, MessageType.VIDEO]:
            if not data.get('file'):
                raise serializers.ValidationError({"file": f"{message_type} message requires a file"})
        
        if message_type == MessageType.LOCATION:
            if not data.get('latitude') or not data.get('longitude'):
                raise serializers.ValidationError(
                    {"location": "Location message requires latitude and longitude"}
                )
        
        return data


class CreateGroupConversationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    
    def validate_participant_ids(self, value):
        """Validate all participants exist"""
        User = get_user_model()
        existing_ids = set(User.objects.filter(id__in=value).values_list('id', flat=True))
        
        if len(existing_ids) != len(value):
            missing_ids = set(value) - existing_ids
            raise serializers.ValidationError(f"Users not found: {missing_ids}")
        
        return value


class ReactionSerializer(serializers.Serializer):
    message_id = serializers.IntegerField()
    emoji = serializers.CharField(max_length=10)


# OPTIMIZATION: Add bulk operations serializers
class BulkMessageStatusSerializer(serializers.Serializer):
    """Serializer for bulk message status updates"""
    message_ids = serializers.ListField(
        child=serializers.IntegerField(),
        max_length=100  # Limit bulk operations
    )
    status = serializers.ChoiceField(choices=MessageStatus.choices)


class MessageSearchSerializer(serializers.Serializer):
    """Serializer for message search parameters"""
    query = serializers.CharField(max_length=255, required=False)
    conversation_id = serializers.IntegerField(required=False)
    message_type = serializers.ChoiceField(choices=MessageType.choices, required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    sender_id = serializers.IntegerField(required=False)


# OPTIMIZATION: Add analytics serializers
class ConversationAnalyticsSerializer(serializers.Serializer):
    """Serializer for conversation analytics"""
    conversation_id = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    total_participants = serializers.IntegerField()
    messages_today = serializers.IntegerField()
    most_active_user = serializers.CharField()
    average_response_time = serializers.DurationField()


class UserEngagementSerializer(serializers.Serializer):
    """Serializer for user engagement data"""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_messages_sent = serializers.IntegerField()
    total_conversations = serializers.IntegerField()
    engagement_score = serializers.FloatField()
    last_active = serializers.DateTimeField()
