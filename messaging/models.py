from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from datetime import timedelta
from common.models import TimeStampedModel
import uuid
import os


class ConversationType(models.TextChoices):
    """Types of conversations"""
    DIRECT = 'direct', 'Direct Message'
    GROUP = 'group', 'Group Chat'
    CHANNEL = 'channel', 'Channel'


class MessageType(models.TextChoices):
    """Types of messages"""
    TEXT = 'text', 'Text Message'
    IMAGE = 'image', 'Image'
    FILE = 'file', 'File'
    VOICE = 'voice', 'Voice Message'
    VIDEO = 'video', 'Video'
    LOCATION = 'location', 'Location'
    SYSTEM = 'system', 'System Message'


class MessageStatus(models.TextChoices):
    """Message delivery status"""
    SENT = 'sent', 'Sent'
    DELIVERED = 'delivered', 'Delivered'
    READ = 'read', 'Read'
    FAILED = 'failed', 'Failed'


def conversation_avatar_path(instance, filename):
    """Generate path for conversation avatar uploads"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f"conversations/avatars/{filename}"


def message_file_path(instance, filename):
    """Generate path for message file uploads"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f"messages/files/{instance.conversation.id}/{filename}"


class Conversation(TimeStampedModel):
    """Enhanced conversation model supporting both direct and group chats"""
    # Basic conversation info
    conversation_type = models.CharField(
        max_length=20, 
        choices=ConversationType.choices, 
        default=ConversationType.DIRECT
    )
    title = models.CharField(max_length=255, blank=True, null=True)  # For group chats
    description = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to=conversation_avatar_path, blank=True, null=True)
    
    # Direct message participants (for backward compatibility)
    participant1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='conversations_as_p1',
        blank=True, null=True
    )
    participant2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='conversations_as_p2',
        blank=True, null=True
    )
    
    # Group chat settings
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='created_conversations',
        blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    max_participants = models.PositiveIntegerField(default=256)  # WhatsApp limit
    
    # Privacy settings
    is_public = models.BooleanField(default=False)
    join_by_link = models.BooleanField(default=False)
    invite_link = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Last activity tracking
    last_message_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['conversation_type', 'is_active']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['participant1', 'is_active']),  # For finding user's direct conversations
            models.Index(fields=['participant2', 'is_active']),  # For finding user's direct conversations
            models.Index(fields=['created_by']),  # For finding conversations created by a user
        ]
        
    
    def clean(self):
        """Enhanced validation for different conversation types"""
        if self.conversation_type == ConversationType.DIRECT:
            # Direct message validation
            if not self.participant1 or not self.participant2:
                raise ValidationError("Direct conversations must have exactly 2 participants.")
            
            if self.participant1 == self.participant2:
                raise ValidationError("Users cannot have conversations with themselves.")
            
            # Ensure participant1.id is always less than participant2.id for consistency
            if self.participant1.id > self.participant2.id:
                self.participant1, self.participant2 = self.participant2, self.participant1
                
        elif self.conversation_type in [ConversationType.GROUP, ConversationType.CHANNEL]:
            # Group/Channel validation
            if not self.title:
                raise ValidationError(f"{self.conversation_type} conversations must have a title.")
            
            if not self.created_by:
                raise ValidationError(f"{self.conversation_type} conversations must have a creator.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_direct_conversation(cls, user1, user2):
        """Get existing direct conversation or create new one"""
        if user1 == user2:
            raise ValidationError("Users cannot have conversations with themselves.")
            
        if user1.id > user2.id:
            user1, user2 = user2, user1
        
        conversation, created = cls.objects.get_or_create(
            conversation_type=ConversationType.DIRECT,
            participant1=user1,
            participant2=user2
        )
        return conversation, created
    
    @classmethod
    def create_group_conversation(cls, creator, title, description=None, participants=None):
        """Create a new group conversation"""
        conversation = cls.objects.create(
            conversation_type=ConversationType.GROUP,
            title=title,
            description=description,
            created_by=creator
        )
        
        # Add creator as admin
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=creator,
            role=ParticipantRole.ADMIN,
            joined_at=timezone.now()
        )
        
        # Add other participants
        if participants:
            for user in participants:
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=user,
                    role=ParticipantRole.MEMBER,
                    joined_at=timezone.now()
                )
        
        return conversation
    
    @classmethod
    def get_user_conversations(cls, user):
        """Get all conversations for a user, ordered by latest activity"""
        # Direct conversations
        direct_conversations = cls.objects.filter(
            Q(participant1=user) | Q(participant2=user),
            conversation_type=ConversationType.DIRECT,
            is_active=True
        )
        
        # Group conversations
        group_conversations = cls.objects.filter(
            participants__user=user,
            conversation_type__in=[ConversationType.GROUP, ConversationType.CHANNEL],
            is_active=True
        )
        
        return (direct_conversations | group_conversations).distinct().order_by('-last_message_at')
    
    def get_participants(self):
        """Get all participants in this conversation"""
        if self.conversation_type == ConversationType.DIRECT:
            return [self.participant1, self.participant2]
        else:
            return [p.user for p in self.participants.filter(is_active=True)]
    
    def get_participant_count(self):
        """Get total number of active participants"""
        if self.conversation_type == ConversationType.DIRECT:
            return 2
        else:
            return self.participants.filter(is_active=True).count()
    
    def get_other_participant(self, user):
        """Get the other participant in direct conversation"""
        if self.conversation_type != ConversationType.DIRECT:
            raise ValueError("This method only works for direct conversations")
            
        if self.participant1 == user:
            return self.participant2
        elif self.participant2 == user:
            return self.participant1
        else:
            raise ValueError("User is not a participant in this conversation")
    
    def get_latest_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.filter(is_deleted=False).last()
    
    def get_unread_count(self, user):
        """Get count of unread messages for a specific user"""
        return self.messages.filter(
            status__in=[MessageStatus.SENT, MessageStatus.DELIVERED]
        ).exclude(sender=user).count()
    
    def is_participant(self, user):
        """Check if user is a participant in this conversation"""
        if self.conversation_type == ConversationType.DIRECT:
            return user in [self.participant1, self.participant2]
        else:
            return self.participants.filter(user=user, is_active=True).exists()
    
    def add_participant(self, user, added_by=None, role=None):
        """Add a participant to group conversation"""
        if self.conversation_type == ConversationType.DIRECT:
            raise ValueError("Cannot add participants to direct conversations")
        
        if self.get_participant_count() >= self.max_participants:
            raise ValidationError(f"Conversation has reached maximum participants limit ({self.max_participants})")
        
        participant, created = ConversationParticipant.objects.get_or_create(
            conversation=self,
            user=user,
            defaults={
                'role': role or ParticipantRole.MEMBER,
                'added_by': added_by,
                'joined_at': timezone.now()
            }
        )
        
        if not created and not participant.is_active:
            participant.is_active = True
            participant.joined_at = timezone.now()
            participant.save()
        
        return participant
    
    def remove_participant(self, user, removed_by=None):
        """Remove a participant from group conversation"""
        if self.conversation_type == ConversationType.DIRECT:
            raise ValueError("Cannot remove participants from direct conversations")
        
        try:
            participant = self.participants.get(user=user)
            participant.is_active = False
            participant.left_at = timezone.now()
            participant.removed_by = removed_by
            participant.save()
        except ConversationParticipant.DoesNotExist:
            raise ValueError("User is not a participant in this conversation")
    
    def update_last_message_time(self):
        """Update the last message timestamp"""
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])
    
    def __str__(self):
        if self.conversation_type == ConversationType.DIRECT:
            return f"Direct: {self.participant1.username} & {self.participant2.username}"
        else:
            return f"{self.get_conversation_type_display()}: {self.title}"


class ParticipantRole(models.TextChoices):
    """Roles for group conversation participants"""
    ADMIN = 'admin', 'Admin'
    MODERATOR = 'moderator', 'Moderator'
    MEMBER = 'member', 'Member'


class ConversationParticipant(TimeStampedModel):
    """Participants in group conversations with roles and permissions"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_memberships')
    role = models.CharField(max_length=20, choices=ParticipantRole.choices, default=ParticipantRole.MEMBER)
    
    # Participation tracking
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    # Who added/removed this participant
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='added_participants',
        blank=True, null=True
    )
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        related_name='removed_participants',
        blank=True, null=True
    )
    
    # Participant settings
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['conversation', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def can_send_messages(self):
        """Check if participant can send messages"""
        return self.is_active and self.conversation.is_active
    
    def can_add_participants(self):
        """Check if participant can add new members"""
        return self.role in [ParticipantRole.ADMIN, ParticipantRole.MODERATOR]
    
    def can_remove_participants(self):
        """Check if participant can remove members"""
        return self.role == ParticipantRole.ADMIN
    
    def __str__(self):
        return f"{self.user.username} in {self.conversation}"


class Message(TimeStampedModel):
    """Enhanced message model with multiple types and statuses"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    
    # Message content
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    content = models.TextField(blank=True, null=True)  # Text content
    
    # File attachments
    file = models.FileField(
        upload_to=message_file_path, 
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpg', 'jpeg', 'png', 'gif', 'webp',  # Images
            'mp4', 'avi', 'mov', 'webm',  # Videos
            'mp3', 'wav', 'ogg', 'm4a',  # Audio
            'pdf', 'doc', 'docx', 'txt', 'rtf',  # Documents
            'zip', 'rar', '7z'  # Archives
        ])]
    )
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)  # Size in bytes
    
    # Message status and delivery
    status = models.CharField(max_length=20, choices=MessageStatus.choices, default=MessageStatus.SENT)
    delivered_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    # Message features
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    # Reply/Thread support
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    
    # Location data (for location messages)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['conversation', 'is_deleted']),  # For filtering non-deleted messages in a conversation
            models.Index(fields=['message_type']),  # For filtering by message type
            models.Index(fields=['conversation', 'message_type']),  # For filtering message types in a conversation
            models.Index(fields=['reply_to']),  # For finding replies to messages
        ]
    
    def clean(self):
        """Enhanced validation for different message types"""
        # Validate sender is participant
        if not self.conversation.is_participant(self.sender):
            raise ValidationError("Sender must be a participant in the conversation.")
        
        # Validate content based on message type
        if self.message_type == MessageType.TEXT and not self.content:
            raise ValidationError("Text messages must have content.")
        
        if self.message_type in [MessageType.IMAGE, MessageType.FILE, MessageType.VOICE, MessageType.VIDEO]:
            if not self.file:
                raise ValidationError(f"{self.message_type} messages must have a file attachment.")
        
        if self.message_type == MessageType.LOCATION:
            if self.latitude is None or self.longitude is None:
                raise ValidationError("Location messages must have latitude and longitude.")
    
    def save(self, *args, **kwargs):
        """Enhanced save with file handling"""
        self.clean()
        
        # Set file metadata
        if self.file:
            self.file_name = self.file.name
            if hasattr(self.file, 'size'):
                self.file_size = self.file.size
        
        super().save(*args, **kwargs)
        
        # Update conversation's last message time
        self.conversation.update_last_message_time()
    
    def mark_as_delivered(self):
        """Mark message as delivered"""
        if self.status == MessageStatus.SENT:
            self.status = MessageStatus.DELIVERED
            self.delivered_at = timezone.now()
            self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self):
        """Mark message as read"""
        if self.status in [MessageStatus.SENT, MessageStatus.DELIVERED]:
            self.status = MessageStatus.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def edit_content(self, new_content):
        """Edit message content"""
        if self.message_type != MessageType.TEXT:
            raise ValidationError("Only text messages can be edited.")
        
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'is_edited', 'edited_at'])
    
    def soft_delete(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    @property
    def receivers(self):
        """Get all receivers of this message"""
        participants = self.conversation.get_participants()
        return [p for p in participants if p != self.sender]
    
    @property
    def file_url(self):
        """Get file URL if file exists"""
        return self.file.url if self.file else None
    
    @property
    def is_reply(self):
        """Check if this message is a reply"""
        return self.reply_to is not None
    
    def get_replies(self):
        """Get all replies to this message"""
        return self.replies.filter(is_deleted=False).order_by('created_at')
    
    def __str__(self):
        if self.is_deleted:
            return f"[Deleted Message] - {self.sender.username}"
        
        if self.message_type == MessageType.TEXT:
            content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
            return f"{self.sender.username}: {content_preview}"
        else:
            return f"{self.sender.username}: [{self.get_message_type_display()}]"


class MessageReaction(TimeStampedModel):
    """Reactions/emojis on messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=10)  # Unicode emoji
    
    class Meta:
        unique_together = ('message', 'user', 'emoji')
        indexes = [
            models.Index(fields=['message', 'emoji']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def clean(self):
        """Validate user can react to message"""
        if not self.message.conversation.is_participant(self.user):
            raise ValidationError("User must be a participant to react to messages.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message"


class TypingIndicator(models.Model):
    """Track who is currently typing in conversations"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='typing_indicators')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='typing_in')
    started_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['conversation', 'started_at']),
        ]
    
    @classmethod
    def start_typing(cls, conversation, user):
        """Start typing indicator"""
        if not conversation.is_participant(user):
            raise ValidationError("User must be a participant to type in conversation.")
        
        indicator, created = cls.objects.get_or_create(
            conversation=conversation,
            user=user
        )
        return indicator
    
    @classmethod
    def stop_typing(cls, conversation, user):
        """Stop typing indicator"""
        cls.objects.filter(conversation=conversation, user=user).delete()
    
    @classmethod
    def get_typing_users(cls, conversation):
        """Get users currently typing in conversation"""
        # Remove stale typing indicators (older than 10 seconds)
        stale_time = timezone.now() - timezone.timedelta(seconds=10)
        cls.objects.filter(started_at__lt=stale_time).delete()
        
        return cls.objects.filter(conversation=conversation).select_related('user')
    
    def __str__(self):
        return f"{self.user.username} typing in {self.conversation}"


class UserOnlineStatus(models.Model):
    """Track user online/offline status"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='online_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    status_message = models.CharField(max_length=100, blank=True, null=True)  # "Available", "Busy", etc.
    
    class Meta:
        indexes = [
            models.Index(fields=['is_online', 'last_seen']),
        ]
    
    @classmethod
    def set_online(cls, user):
        """Set user as online"""
        status, created = cls.objects.get_or_create(user=user)
        status.is_online = True
        status.last_seen = timezone.now()
        status.save()
        return status
    
    @classmethod
    def set_offline(cls, user):
        """Set user as offline"""
        try:
            status = cls.objects.get(user=user)
            status.is_online = False
            status.last_seen = timezone.now()
            status.save()
        except cls.DoesNotExist:
            pass
    
    @classmethod
    def get_online_users(cls):
        """Get all currently online users"""
        return cls.objects.filter(is_online=True).select_related('user')
    
    def __str__(self):
        status = "Online" if self.is_online else f"Last seen {self.last_seen}"
        return f"{self.user.username} - {status}"
    
class UserEncryptionKey(TimeStampedModel):
    """Store user encryption keys"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='encryption_key'
    )
    private_key = models.BinaryField()  # Store encrypted private key
    public_key = models.BinaryField()   # Store public key
    key_version = models.PositiveIntegerField(default=1)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Encryption keys for {self.user.username}"


class MessageExpiration(models.Model):
    """Handle message expiration settings"""
    EXPIRATION_CHOICES = [
        ('1h', '1 Hour'),
        ('24h', '24 Hours'),
        ('7d', '7 Days'),
        ('30d', '30 Days'),
        ('read_once', 'Disappear after reading'),
        ('never', 'Never expire'),
    ]
    
    message = models.OneToOneField(
        'Message', 
        on_delete=models.CASCADE, 
        related_name='expiration'
    )
    expiration_type = models.CharField(max_length=20, choices=EXPIRATION_CHOICES)
    expires_at = models.DateTimeField(null=True, blank=True)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True, 
        related_name='read_expiring_messages'
    )
    is_expired = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        """Set expiration time based on type"""
        if not self.expires_at and self.expiration_type != 'read_once':
            now = timezone.now()
            if self.expiration_type == '1h':
                self.expires_at = now + timedelta(hours=1)
            elif self.expiration_type == '24h':
                self.expires_at = now + timedelta(days=1)
            elif self.expiration_type == '7d':
                self.expires_at = now + timedelta(days=7)
            elif self.expiration_type == '30d':
                self.expires_at = now + timedelta(days=30)
        
        super().save(*args, **kwargs)
    
    def check_expiration(self, user=None):
        """Check if message should expire"""
        if self.is_expired:
            return True
        
        if self.expiration_type == 'read_once' and user:
            # Mark as read by this user
            self.read_by.add(user)
            
            # Check if all participants have read it
            participants = self.message.conversation.get_participants()
            if all(p in self.read_by.all() for p in participants if p != self.message.sender):
                self.is_expired = True
                self.save()
                return True
        
        elif self.expires_at and timezone.now() >= self.expires_at:
            self.is_expired = True
            self.save()
            return True
        
        return False


class MessageAnalytics(TimeStampedModel):
    """Track message analytics"""
    message = models.OneToOneField(
        'Message', 
        on_delete=models.CASCADE, 
        related_name='analytics'
    )
    delivered_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)
    reaction_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    
    # Timing analytics
    first_delivered_at = models.DateTimeField(null=True, blank=True)
    first_read_at = models.DateTimeField(null=True, blank=True)
    average_read_time = models.DurationField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['read_count']),  # For finding popular messages
        ]
    
    def update_delivery(self):
        """Update delivery analytics"""
        self.delivered_count += 1
        if not self.first_delivered_at:
            self.first_delivered_at = timezone.now()
        self.save()
    
    def update_read(self):
        """Update read analytics"""
        self.read_count += 1
        if not self.first_read_at:
            self.first_read_at = timezone.now()
            
            # Calculate time to first read
            if self.message.created_at:
                self.average_read_time = self.first_read_at - self.message.created_at
        
        self.save()


class UserEngagementAnalytics(TimeStampedModel):
    """Track user engagement patterns"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='engagement_analytics'
    )
    
    # Message statistics
    total_messages_sent = models.PositiveIntegerField(default=0)
    total_messages_received = models.PositiveIntegerField(default=0)
    total_reactions_given = models.PositiveIntegerField(default=0)
    total_reactions_received = models.PositiveIntegerField(default=0)
    
    # Conversation statistics
    total_conversations = models.PositiveIntegerField(default=0)
    active_conversations = models.PositiveIntegerField(default=0)
    
    # Time-based analytics
    most_active_hour = models.PositiveIntegerField(null=True, blank=True)  # 0-23
    most_active_day = models.PositiveIntegerField(null=True, blank=True)   # 0-6 (Monday=0)
    average_response_time = models.DurationField(null=True, blank=True)
    
    # Engagement scores
    engagement_score = models.FloatField(default=0.0)  # 0-100
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['engagement_score']),  # For sorting users by engagement
        ]
    
    def calculate_engagement_score(self):
        """Calculate user engagement score"""
        # Simple engagement calculation
        messages_weight = min(self.total_messages_sent * 0.1, 30)
        reactions_weight = min(self.total_reactions_given * 0.2, 20)
        conversations_weight = min(self.active_conversations * 2, 30)
        response_time_weight = 20  # Base score for responsiveness
        
        if self.average_response_time:
            # Lower response time = higher score
            response_minutes = self.average_response_time.total_seconds() / 60
            if response_minutes < 5:
                response_time_weight = 20
            elif response_minutes < 30:
                response_time_weight = 15
            elif response_minutes < 60:
                response_time_weight = 10
            else:
                response_time_weight = 5
        
        self.engagement_score = messages_weight + reactions_weight + conversations_weight + response_time_weight
        self.save()
        
        return self.engagement_score


class RateLimitTracker(models.Model):
    """Track rate limiting for users"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50)  # 'message', 'reaction', 'friend_request'
    count = models.PositiveIntegerField(default=1)
    window_start = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'action_type', 'window_start')
        indexes = [
            models.Index(fields=['user', 'action_type', 'window_start']),
        ]
    
    @classmethod
    def check_rate_limit(cls, user, action_type, limit_per_minute=10):
        """Check if user has exceeded rate limit"""
        now = timezone.now()
        window_start = now.replace(second=0, microsecond=0)  # Start of current minute
        
        # Get or create tracker for this minute
        tracker, created = cls.objects.get_or_create(
            user=user,
            action_type=action_type,
            window_start=window_start,
            defaults={'count': 0}
        )
        
        if tracker.count >= limit_per_minute:
            return False, f"Rate limit exceeded. Max {limit_per_minute} {action_type}s per minute."
        
        # Increment counter
        tracker.count += 1
        tracker.save()
        
        return True, None
    
    @classmethod
    def cleanup_old_trackers(cls):
        """Clean up old rate limit trackers"""
        cutoff = timezone.now() - timedelta(hours=1)
        cls.objects.filter(window_start__lt=cutoff).delete()


class ContentModerationLog(TimeStampedModel):
    """Log content moderation actions"""
    MODERATION_ACTIONS = [
        ('flagged', 'Flagged for Review'),
        ('blocked', 'Blocked/Censored'),
        ('warning', 'Warning Issued'),
        ('approved', 'Approved'),
    ]
    
    CONTENT_TYPES = [
        ('message', 'Message'),
        ('profile', 'Profile'),
        ('image', 'Image'),
    ]
    
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    content_id = models.PositiveIntegerField()  # ID of the content being moderated
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=MODERATION_ACTIONS)
    reason = models.CharField(max_length=200)
    confidence_score = models.FloatField(default=0.0)  # AI confidence 0-1
    is_automated = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='moderation_reviews'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['user', 'action']),
            models.Index(fields=['is_automated', 'action']),
        ]


class WebhookEndpoint(TimeStampedModel):
    """Store webhook endpoints for external integrations"""
    name = models.CharField(max_length=100)
    url = models.URLField()
    secret_key = models.CharField(max_length=255)  # For webhook verification
    is_active = models.BooleanField(default=True)
    events = models.JSONField(default=list)  # List of events to send
    
    # Statistics
    total_sent = models.PositiveIntegerField(default=0)
    total_failed = models.PositiveIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.url}"


class WebhookDelivery(TimeStampedModel):
    """Track webhook delivery attempts"""
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    delivery_attempts = models.PositiveIntegerField(default=0)
    is_delivered = models.BooleanField(default=False)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['endpoint', 'is_delivered']),
            models.Index(fields=['next_retry_at']),
        ]

