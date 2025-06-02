from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db.models import Q
from friends.models import FriendRequest, Friendship

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for friend-related responses"""
    full_name = serializers.CharField(read_only=True)
    avatar = serializers.ImageField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'avatar', 'is_online']
        read_only_fields = ['id', 'username']

class FriendRequestSerializer(serializers.ModelSerializer):
    """Serializer for friend requests"""
    sender = UserBasicSerializer(read_only=True)
    receiver = UserBasicSerializer(read_only=True)
    receiver_username = serializers.CharField(write_only=True, required=False)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = FriendRequest
        fields = [
            'id', 'sender', 'receiver', 'receiver_username', 
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'receiver', 'status', 'created_at', 'updated_at']
    
    def validate_receiver_username(self, value):
        """Validate that the receiver username exists"""
        try:
            user = User.objects.get(username=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this username does not exist.")
    
    def validate(self, attrs):
        """Custom validation for friend requests"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")
        
        sender = request.user
        receiver = attrs.get('receiver_username')
        
        # Prevent self-requests
        if sender == receiver:
            raise serializers.ValidationError("You cannot send a friend request to yourself.")
        
        # Check if they're already friends
        if Friendship.are_friends(sender, receiver):
            raise serializers.ValidationError("You are already friends with this user.")
        
        # Check for existing pending requests
        existing_request = FriendRequest.objects.filter(
            sender=sender, receiver=receiver, status='pending'
        ).first()
        
        if existing_request:
            raise serializers.ValidationError("You have already sent a friend request to this user.")
        
        # Check if receiver has sent a request to sender
        reverse_request = FriendRequest.objects.filter(
            sender=receiver, receiver=sender, status='pending'
        ).first()
        
        if reverse_request:
            raise serializers.ValidationError(
                f"{receiver.username} has already sent you a friend request. "
                "Please respond to their request first."
            )
        
        attrs['receiver'] = receiver
        return attrs
    
    def create(self, validated_data):
        """Create a new friend request"""
        request = self.context.get('request')
        validated_data['sender'] = request.user
        validated_data['receiver'] = validated_data.pop('receiver_username')
        
        try:
            return super().create(validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))

class FriendRequestResponseSerializer(serializers.Serializer):
    """Serializer for responding to friend requests (accept/reject)"""
    ACTION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    request_id = serializers.IntegerField()
    
    def validate_request_id(self, value):
        """Validate that the friend request exists and belongs to current user"""
        request_user = self.context.get('request').user
        
        try:
            friend_request = FriendRequest.objects.get(
                id=value, 
                receiver=request_user,
                status='pending'
            )
            return friend_request
        except FriendRequest.DoesNotExist:
            raise serializers.ValidationError(
                "Friend request not found or you don't have permission to respond to it."
            )
    
    def validate(self, attrs):
        """Additional validation"""
        friend_request = attrs['request_id']
        action = attrs['action']
        
        if friend_request.status != 'pending':
            raise serializers.ValidationError("This friend request is no longer pending.")
        
        attrs['friend_request'] = friend_request
        return attrs
    
    def save(self):
        """Process the friend request response"""
        friend_request = self.validated_data['friend_request']
        action = self.validated_data['action']
        
        try:
            if action == 'accept':
                friend_request.accept()
                return {
                    'message': f'Friend request from {friend_request.sender.username} accepted.',
                    'status': 'accepted',
                    'friend_request': friend_request
                }
            elif action == 'reject':
                friend_request.reject()
                return {
                    'message': f'Friend request from {friend_request.sender.username} rejected.',
                    'status': 'rejected',
                    'friend_request': friend_request
                }
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))

class FriendshipSerializer(serializers.ModelSerializer):
    """Serializer for friendships"""
    friend = serializers.SerializerMethodField()
    friendship_date = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = Friendship
        fields = ['id', 'friend', 'friendship_date']
        read_only_fields = ['id', 'friendship_date']
    
    def get_friend(self, obj):
        """Get the friend user (not the current user)"""
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        current_user = request.user
        friend_user = obj.user2 if obj.user1 == current_user else obj.user1
        return UserBasicSerializer(friend_user, context=self.context).data

class FriendListSerializer(serializers.Serializer):
    """Serializer for listing friends with additional info"""
    friends = FriendshipSerializer(many=True, read_only=True)
    total_friends = serializers.IntegerField(read_only=True)
    online_friends = serializers.IntegerField(read_only=True)
    
    def to_representation(self, instance):
        """Custom representation for friend list"""
        user = instance
        friendships = Friendship.objects.filter(
            models.Q(user1=user) | models.Q(user2=user)
        ).select_related('user1', 'user2')
        
        # Get friend count
        total_friends = friendships.count()
        
        # Count online friends
        online_friends = 0
        friends_data = []
        
        for friendship in friendships:
            friend_user = friendship.user2 if friendship.user1 == user else friendship.user1
            if friend_user.is_online:
                online_friends += 1
            
            friends_data.append({
                'id': friendship.id,
                'friend': UserBasicSerializer(friend_user, context=self.context).data,
                'friendship_date': friendship.created_at
            })
        
        return {
            'friends': friends_data,
            'total_friends': total_friends,
            'online_friends': online_friends
        }

class PendingRequestsSerializer(serializers.Serializer):
    """Serializer for pending friend requests (received and sent)"""
    received_requests = FriendRequestSerializer(many=True, read_only=True)
    sent_requests = FriendRequestSerializer(many=True, read_only=True)
    total_received = serializers.IntegerField(read_only=True)
    total_sent = serializers.IntegerField(read_only=True)
    
    def to_representation(self, instance):
        """Custom representation for pending requests"""
        user = instance
        
        # Get received requests
        received_requests = FriendRequest.objects.pending_for_user(user).select_related(
            'sender', 'receiver'
        )
        
        # Get sent requests
        sent_requests = FriendRequest.objects.pending_sent_by_user(user).select_related(
            'sender', 'receiver'
        )
        
        return {
            'received_requests': FriendRequestSerializer(
                received_requests, many=True, context=self.context
            ).data,
            'sent_requests': FriendRequestSerializer(
                sent_requests, many=True, context=self.context
            ).data,
            'total_received': received_requests.count(),
            'total_sent': sent_requests.count()
        }

# Additional utility serializers
class FriendSearchSerializer(serializers.Serializer):
    """Serializer for searching potential friends"""
    query = serializers.CharField(max_length=100, required=True)
    
    def validate_query(self, value):
        """Validate search query"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Search query must be at least 2 characters long.")
        return value.strip()

class FriendStatsSerializer(serializers.Serializer):
    """Serializer for friend statistics"""
    total_friends = serializers.IntegerField(read_only=True)
    online_friends = serializers.IntegerField(read_only=True)
    pending_received = serializers.IntegerField(read_only=True)
    pending_sent = serializers.IntegerField(read_only=True)
    mutual_friends = serializers.IntegerField(read_only=True, required=False)
    
    def to_representation(self, instance):
        """Generate friend statistics for a user"""
        user = instance
        
        # Get friend count
        total_friends = Friendship.get_friend_count(user)
        
        # Count online friends
        online_friends = User.objects.filter(
            models.Q(friendships_as_user1__user2=user, is_online=True) |
            models.Q(friendships_as_user2__user1=user, is_online=True)
        ).distinct().count()
        
        # Count pending requests
        pending_received = FriendRequest.objects.pending_for_user(user).count()
        pending_sent = FriendRequest.objects.pending_sent_by_user(user).count()
        
        return {
            'total_friends': total_friends,
            'online_friends': online_friends,
            'pending_received': pending_received,
            'pending_sent': pending_sent
        }