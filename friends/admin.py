from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import FriendRequest, Friendship


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    """
    Admin interface for Friend Requests
    Optimized for managing celebrity-level friend request volumes
    """
    list_display = [
        'id', 
        'sender_link', 
        'receiver_link', 
        'status', 
        'created_at', 
        'updated_at',
        'days_pending'
    ]
    list_filter = [
        'status', 
        'created_at', 
        'updated_at'
    ]
    search_fields = [
        'sender__username', 
        'sender__first_name', 
        'sender__last_name',
        'receiver__username', 
        'receiver__first_name', 
        'receiver__last_name'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'days_pending'
    ]
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('sender', 'receiver', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'days_pending'),
            'classes': ('collapse',)
        }),
    )
    
    def sender_link(self, obj):
        """Create clickable link to sender's profile"""
        url = reverse('admin:authentication_user_change', args=[obj.sender.pk])
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)
    sender_link.short_description = 'Sender'
    sender_link.admin_order_field = 'sender__username'
    
    def receiver_link(self, obj):
        """Create clickable link to receiver's profile"""
        url = reverse('admin:authentication_user_change', args=[obj.receiver.pk])
        return format_html('<a href="{}">{}</a>', url, obj.receiver.username)
    receiver_link.short_description = 'Receiver'
    receiver_link.admin_order_field = 'receiver__username'
    
    def days_pending(self, obj):
        """Show how many days the request has been pending"""
        # Check if the object has been saved
        if not obj.created_at or obj.status != 'pending':
            return '-'
        
        from django.utils import timezone
        days = (timezone.now() - obj.created_at).days
        if days > 30:
            return format_html('<span style="color: red;">{} days</span>', days)
        elif days > 7:
            return format_html('<span style="color: orange;">{} days</span>', days)
        else:
            return f'{days} days'
    days_pending.short_description = 'Days Pending'
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        return super().get_queryset(request).select_related('sender', 'receiver')
    
    actions = ['accept_requests', 'reject_requests', 'delete_old_requests']
    
    def accept_requests(self, request, queryset):
        """Bulk accept friend requests"""
        count = 0
        for friend_request in queryset.filter(status='pending'):
            # Create friendship
            if friend_request.sender.id < friend_request.receiver.id:
                friendship, created = Friendship.objects.get_or_create(
                    user1=friend_request.sender,
                    user2=friend_request.receiver
                )
            else:
                friendship, created = Friendship.objects.get_or_create(
                    user1=friend_request.receiver,
                    user2=friend_request.sender
                )
            
            if created:
                friend_request.status = 'accepted'
                friend_request.save()
                count += 1
        
        self.message_user(request, f'Successfully accepted {count} friend requests.')
    accept_requests.short_description = 'Accept selected friend requests'
    
    def reject_requests(self, request, queryset):
        """Bulk reject friend requests"""
        count = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'Successfully rejected {count} friend requests.')
    reject_requests.short_description = 'Reject selected friend requests'
    
    def delete_old_requests(self, request, queryset):
        """Delete requests older than 90 days"""
        from django.utils import timezone
        from datetime import timedelta
        
        old_date = timezone.now() - timedelta(days=90)
        count = queryset.filter(created_at__lt=old_date).delete()[0]
        self.message_user(request, f'Deleted {count} old friend requests.')
    delete_old_requests.short_description = 'Delete requests older than 90 days'


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    """
    Admin interface for Friendships
    Optimized for managing large friendship networks
    """
    list_display = [
        'id',
        'user1_link',
        'user2_link', 
        'created_at',
        'friendship_duration'
    ]
    list_filter = [
        'created_at',
    ]
    search_fields = [
        'user1__username',
        'user1__first_name', 
        'user1__last_name',
        'user2__username',
        'user2__first_name',
        'user2__last_name'
    ]
    readonly_fields = [
        'created_at',
        'friendship_duration'
    ]
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Friendship Details', {
            'fields': ('user1', 'user2')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'friendship_duration'),
            'classes': ('collapse',)
        }),
    )
    
    def user1_link(self, obj):
        """Create clickable link to user1's profile"""
        url = reverse('admin:authentication_user_change', args=[obj.user1.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user1.username)
    user1_link.short_description = 'User 1'
    user1_link.admin_order_field = 'user1__username'
    
    def user2_link(self, obj):
        """Create clickable link to user2's profile"""
        url = reverse('admin:authentication_user_change', args=[obj.user2.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user2.username)
    user2_link.short_description = 'User 2'
    user2_link.admin_order_field = 'user2__username'
    
    def friendship_duration(self, obj):
        """Show how long they've been friends"""
        # Check if the object has been saved (has created_at)
        if not obj.created_at:
            return '-'  # Return dash for unsaved objects
        
        from django.utils import timezone
        duration = timezone.now() - obj.created_at
        days = duration.days
        
        if days < 1:
            return 'Today'
        elif days < 30:
            return f'{days} days'
        elif days < 365:
            months = days // 30
            return f'{months} month{"s" if months > 1 else ""}'
        else:
            years = days // 365
            return f'{years} year{"s" if years > 1 else ""}'
    friendship_duration.short_description = 'Duration'  
  
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        return super().get_queryset(request).select_related('user1', 'user2')
    
    actions = ['delete_friendships']
    
    def delete_friendships(self, request, queryset):
        """Bulk delete friendships"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Successfully deleted {count} friendships.')
    delete_friendships.short_description = 'Delete selected friendships'


# Optional: Custom admin site configuration
admin.site.site_header = "Chat Service Administration"
admin.site.site_title = "Chat Service Admin"
admin.site.index_title = "Welcome to Chat Service Administration"