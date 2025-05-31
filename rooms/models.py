from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from common.models import TimeStampedModel
import uuid
import string
import random

class Room(TimeStampedModel):
    """Chat room that multiple users can join"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_private = models.BooleanField(default=False)
    code = models.CharField(max_length=8, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_rooms')
    
    def save(self, *args, **kwargs):
        """Generate unique code if not provided"""
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)
        
        # Auto-create admin membership for room creator
        if self._state.adding:  # Only when creating new room
            RoomMember.objects.create(
                room=self,
                user=self.created_by,
                is_admin=True
            )
    
    @staticmethod
    def generate_unique_code():
        """Generate a unique 8-character room code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Room.objects.filter(code=code).exists():
                return code
    
    def get_members(self):
        """Get all members of this room"""
        return self.members.all()
    
    def get_admins(self):
        """Get all admin members of this room"""
        return self.members.filter(is_admin=True)
    
    def is_member(self, user):
        """Check if user is a member of this room"""
        return self.members.filter(user=user).exists()
    
    def is_admin(self, user):
        """Check if user is an admin of this room"""
        return self.members.filter(user=user, is_admin=True).exists()
    
    def add_member(self, user, added_by=None):
        """Add a user to the room"""
        if self.is_member(user):
            raise ValidationError("User is already a member of this room")
        
        return RoomMember.objects.create(room=self, user=user)
    
    def remove_member(self, user, removed_by):
        """Remove a user from the room (only admins can remove)"""
        if not self.is_admin(removed_by):
            raise ValidationError("Only admins can remove members")
        
        if user == self.created_by:
            raise ValidationError("Cannot remove the room creator")
        
        membership = self.members.filter(user=user).first()
        if not membership:
            raise ValidationError("User is not a member of this room")
        
        membership.delete()
        return True
    
    def make_admin(self, user, promoted_by):
        """Make a user an admin (only existing admins can do this)"""
        if not self.is_admin(promoted_by):
            raise ValidationError("Only admins can promote other members")
        
        membership = self.members.filter(user=user).first()
        if not membership:
            raise ValidationError("User is not a member of this room")
        
        membership.is_admin = True
        membership.save()
        return membership
    
    def remove_admin(self, user, demoted_by):
        """Remove admin privileges (only admins can do this)"""
        if not self.is_admin(demoted_by):
            raise ValidationError("Only admins can demote other admins")
        
        if user == self.created_by:
            raise ValidationError("Cannot demote the room creator")
        
        membership = self.members.filter(user=user, is_admin=True).first()
        if not membership:
            raise ValidationError("User is not an admin of this room")
        
        membership.is_admin = False
        membership.save()
        return membership
        
    def __str__(self):
        return f"{self.name} ({'Private' if self.is_private else 'Public'})"


class RoomMember(TimeStampedModel):
    """Represents a user's membership in a room"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_memberships')
    is_admin = models.BooleanField(default=False)
    
    
    class Meta:
        unique_together = ('room', 'user')
    
    def __str__(self):
        admin_text = " (Admin)" if self.is_admin else ""
        return f"{self.user.username} in {self.room.name}{admin_text}"


class RoomMessage(TimeStampedModel):
    """Message sent in a room"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_room_messages')
    content = models.TextField()
    
    class Meta:
        ordering = ['created_at']
    
    def clean(self):
        """Validate that sender is a member of the room"""
        if not self.room.is_member(self.sender):
            raise ValidationError("Only room members can send messages")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def get_read_by(self):
        """Get list of users who have read this message"""
        return [read.user for read in self.read_receipts.all()]
    
    def get_unread_by(self):
        """Get list of room members who haven't read this message"""
        read_users = self.get_read_by()
        room_members = [member.user for member in self.room.get_members()]
        return [user for user in room_members if user not in read_users and user != self.sender]
    
    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        if user == self.sender:
            return  # Sender doesn't need to mark their own message as read
        
        if not self.room.is_member(user):
            raise ValidationError("Only room members can mark messages as read")
        
        read_receipt, created = RoomMessageRead.objects.get_or_create(
            message=self,
            user=user,
            defaults={'read_at': timezone.now()}
        )
        return read_receipt
    
    def is_read_by(self, user):
        """Check if message has been read by a specific user"""
        return self.read_receipts.filter(user=user).exists()
        
    def __str__(self):
        return f"{self.sender.username} in {self.room.name}: {self.content[:20]}..."


class RoomMessageRead(TimeStampedModel):
    """Tracks which users have read which room messages"""
    message = models.ForeignKey(RoomMessage, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_message_reads')
    read_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('message', 'user')
    
    def __str__(self):
        return f"{self.user.username} read message {self.message.id} at {self.read_at}"