from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from common.models import TimeStampedModel

class FriendRequestManager(models.Manager):
    """Custom manager for FriendRequest with common queries"""
    
    def pending_for_user(self, user):
        """Get all pending requests received by a user"""
        return self.filter(receiver=user, status='pending')
    
    def sent_by_user(self, user):
        """Get all requests sent by a user"""
        return self.filter(sender=user)
    
    def pending_sent_by_user(self, user):
        """Get pending requests sent by a user"""
        return self.filter(sender=user, status='pending')

class FriendRequest(TimeStampedModel):
    """Manages friend requests between users"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Add the custom manager
    objects = FriendRequestManager()
    
    class Meta:
        unique_together = ('sender', 'receiver')
        # Add indexes for better performance
        indexes = [
            models.Index(fields=['receiver', 'status']),  # For "pending requests for user" queries
            models.Index(fields=['sender', 'status']),    # For "requests sent by user" queries
            models.Index(fields=['status']),              # For filtering by status
        ]
    
    def clean(self):
        """Enhanced validation for friend requests"""
        # Prevent self-requests
        if self.sender == self.receiver:
            raise ValidationError("You cannot send a friend request to yourself.")
        
        # Check if they're already friends
        already_friends = Friendship.objects.filter(
            (Q(user1=self.sender, user2=self.receiver) | 
             Q(user1=self.receiver, user2=self.sender))
        ).exists()
        
        if already_friends:
            raise ValidationError("You are already friends with this user.")
        
        # Check existing requests in BOTH directions
        existing_request = FriendRequest.objects.filter(
            (Q(sender=self.sender, receiver=self.receiver) | 
             Q(sender=self.receiver, receiver=self.sender))
        ).exclude(id=self.id).first()  # Exclude self when updating
        
        if existing_request:
            if existing_request.sender == self.sender:
                # User already sent a request
                raise ValidationError("You have already sent a request to this user.")
            else:
                # Received a request from the other user
                if existing_request.status == 'pending':
                    raise ValidationError(
                        f"{self.receiver.username} has already sent you a friend request. "
                        "Please respond to their request first."
                    )
                elif existing_request.status == 'rejected':
                    # Allow sending if previous request was rejected
                    pass
                elif existing_request.status == 'accepted':
                    raise ValidationError("You are already friends with this user.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def accept(self):
        """Accept this friend request and create friendship"""
        if self.status != 'pending':
            raise ValidationError("This request is not pending.")
            
        self.status = 'accepted'
        self.save()
        
        # Create friendship (with ordering to prevent duplicates)
        user1, user2 = (self.sender, self.receiver) if self.sender.id < self.receiver.id else (self.receiver, self.sender)
        Friendship.objects.create(user1=user1, user2=user2)
        
        return True
    
    def reject(self):
        """Reject this friend request"""
        if self.status != 'pending':
            raise ValidationError("This request is not pending.")
            
        self.status = 'rejected'
        self.save()
        return True
        
    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.status}"


class Friendship(TimeStampedModel):
    """Represents an active friendship between two users"""
    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships_as_user1')
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='friendships_as_user2')
    
    class Meta:
        unique_together = ('user1', 'user2')
        # Add index for friend lookups
        indexes = [
            models.Index(fields=['user1']),
            models.Index(fields=['user2']),
        ]
    
    def clean(self):
        """Prevent duplicate friendships by enforcing order"""
        # Ensure user1.id is always less than user2.id
        if self.user1.id > self.user2.id:
            self.user1, self.user2 = self.user2, self.user1
        
        # Prevent self-friendship
        if self.user1 == self.user2:
            raise ValidationError("Users cannot be friends with themselves.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def are_friends(cls, user1, user2):
        """Check if two users are friends"""
        if user1.id > user2.id:
            user1, user2 = user2, user1
        return cls.objects.filter(user1=user1, user2=user2).exists()
    
    @classmethod
    def get_friends(cls, user):
        """Get all friends of a user"""
        friendships = cls.objects.filter(Q(user1=user) | Q(user2=user))
        return [
            friendship.user2 if friendship.user1 == user else friendship.user1
            for friendship in friendships
        ]
    
    @classmethod
    def get_friend_count(cls, user):
        """Get total number of friends for a user (performance optimized)"""
        return cls.objects.filter(Q(user1=user) | Q(user2=user)).count()
        
    def __str__(self):
        return f"{self.user1.username} ↔ {self.user2.username}"