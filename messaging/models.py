from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from common.models import TimeStampedModel

class Conversation(TimeStampedModel):
    """Represents a conversation between two users"""
    participant1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_as_p1')
    participant2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations_as_p2')
    
    class Meta:
        unique_together = ('participant1', 'participant2')
    
    def clean(self):
        """Prevent duplicate conversations by enforcing order"""
        # Ensure participant1.id is always less than participant2.id
        if self.participant1.id > self.participant2.id:
            self.participant1, self.participant2 = self.participant2, self.participant1
        
        # Prevent self-conversations
        if self.participant1 == self.participant2:
            raise ValidationError("Users cannot have conversations with themselves.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get existing conversation or create new one"""
        if user1 == user2:
            raise ValidationError("Users cannot have conversations with themselves.")
            
        if user1.id > user2.id:
            user1, user2 = user2, user1
        
        conversation, created = cls.objects.get_or_create(
            participant1=user1,
            participant2=user2
        )
        return conversation, created
    
    @classmethod
    def get_user_conversations(cls, user):
        """Get all conversations for a user, ordered by latest activity"""
        return cls.objects.filter(
            Q(participant1=user) | Q(participant2=user)
        ).order_by('-updated_at')
    
    def get_other_participant(self, user):
        """Get the other participant in this conversation"""
        if self.participant1 == user:
            return self.participant2
        elif self.participant2 == user:
            return self.participant1
        else:
            raise ValueError("User is not a participant in this conversation")
    
    def get_latest_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.last()
    
    def get_unread_count(self, user):
        """Get count of unread messages for a specific user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
        
    def __str__(self):
        return f"Conversation: {self.participant1.username} & {self.participant2.username}"


class Message(TimeStampedModel):
    """Individual message in a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']  # Messages in chronological order
    
    def clean(self):
        """Validate that sender is a participant in the conversation"""
        if (self.sender != self.conversation.participant1 and 
            self.sender != self.conversation.participant2):
            raise ValidationError("Sender must be a participant in the conversation.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation and update conversation timestamp"""
        self.clean()
        super().save(*args, **kwargs)
        
        # Update conversation's updated_at to show latest activity
        self.conversation.save(update_fields=['updated_at'])
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def receiver(self):
        """Get the receiver of this message"""
        if self.sender == self.conversation.participant1:
            return self.conversation.participant2
        return self.conversation.participant1
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:20]}..."