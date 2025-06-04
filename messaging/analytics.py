from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta, datetime
from typing import Dict, List
import json


class AnalyticsEngine:
    """Generate analytics and insights"""
    
    @classmethod
    def get_user_engagement_summary(cls, user) -> Dict:
        """Get comprehensive user engagement summary"""
        from .models import Message, MessageReaction, Conversation, UserEngagementAnalytics
        
        # Get or create analytics record
        analytics, created = UserEngagementAnalytics.objects.get_or_create(user=user)
        
        # Update statistics
        analytics.total_messages_sent = Message.objects.filter(sender=user, is_deleted=False).count()
        analytics.total_messages_received = Message.objects.filter(
            conversation__in=Conversation.get_user_conversations(user)
        ).exclude(sender=user).filter(is_deleted=False).count()
        
        analytics.total_reactions_given = MessageReaction.objects.filter(user=user).count()
        analytics.total_reactions_received = MessageReaction.objects.filter(
            message__sender=user
        ).count()
        
        user_conversations = Conversation.get_user_conversations(user)
        analytics.total_conversations = user_conversations.count()
        analytics.active_conversations = user_conversations.filter(
            last_message_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Calculate engagement score
        analytics.calculate_engagement_score()
        
        return {
            'user_id': user.id,
            'username': user.username,
            'messages_sent': analytics.total_messages_sent,
            'messages_received': analytics.total_messages_received,
            'reactions_given': analytics.total_reactions_given,
            'reactions_received': analytics.total_reactions_received,
            'total_conversations': analytics.total_conversations,
            'active_conversations': analytics.active_conversations,
            'engagement_score': analytics.engagement_score,
            'most_active_hour': analytics.most_active_hour,
            'most_active_day': analytics.most_active_day,
        }
    
    @classmethod
    def get_conversation_analytics(cls, conversation) -> Dict:
        """Get analytics for a specific conversation"""
        from .models import Message, MessageReaction
        
        messages = Message.objects.filter(conversation=conversation, is_deleted=False)
        
        # Basic stats
        total_messages = messages.count()
        total_reactions = MessageReaction.objects.filter(message__conversation=conversation).count()
        
        # Participant stats
        participant_stats = messages.values('sender__username').annotate(
            message_count=Count('id'),
            reaction_count=Count('reactions')
        ).order_by('-message_count')
        
        # Time-based analytics
        messages_by_hour = messages.extra(
            select={'hour': 'EXTRACT(hour FROM created_at)'}
        ).values('hour').annotate(count=Count('id')).order_by('hour')
        
        messages_by_day = messages.extra(
            select={'day': 'EXTRACT(dow FROM created_at)'}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        # Response time analytics
        response_times = []
        previous_message = None
        for message in messages.order_by('created_at'):
            if previous_message and previous_message.sender != message.sender:
                response_time = message.created_at - previous_message.created_at
                response_times.append(response_time.total_seconds())
            previous_message = message
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'conversation_id': conversation.id,
            'total_messages': total_messages,
            'total_reactions': total_reactions,
            'participant_count': len(conversation.get_participants()),
            'participant_stats': list(participant_stats),
            'messages_by_hour': list(messages_by_hour),
            'messages_by_day': list(messages_by_day),
            'average_response_time_seconds': avg_response_time,
            'created_at': conversation.created_at,
            'last_activity': conversation.last_message_at,
        }
    
    @classmethod
    def get_platform_analytics(cls) -> Dict:
        """Get platform-wide analytics"""
        from django.contrib.auth import get_user_model
        from .models import Message, Conversation, MessageReaction
        
        User = get_user_model()
        
        # User statistics
        total_users = User.objects.count()
        active_users_today = User.objects.filter(
            last_active__gte=timezone.now() - timedelta(days=1)
        ).count()
        active_users_week = User.objects.filter(
            last_active__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Message statistics
        total_messages = Message.objects.filter(is_deleted=False).count()
        messages_today = Message.objects.filter(
            created_at__gte=timezone.now().replace(hour=0, minute=0, second=0)
        ).count()
        
        # Conversation statistics
        total_conversations = Conversation.objects.filter(is_active=True).count()
        active_conversations = Conversation.objects.filter(
            last_message_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Engagement statistics
        total_reactions = MessageReaction.objects.count()
        
        # Growth analytics (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        new_conversations_30d = Conversation.objects.filter(created_at__gte=thirty_days_ago).count()
        
        return {
            'users': {
                'total': total_users,
                'active_today': active_users_today,
                'active_week': active_users_week,
                'new_30_days': new_users_30d,
            },
            'messages': {
                'total': total_messages,
                'today': messages_today,
                'average_per_user': total_messages / total_users if total_users > 0 else 0,
            },
            'conversations': {
                'total': total_conversations,
                'active': active_conversations,
                'new_30_days': new_conversations_30d,
            },
            'engagement': {
                'total_reactions': total_reactions,
                'reactions_per_message': total_reactions / total_messages if total_messages > 0 else 0,
            },
            'generated_at': timezone.now().isoformat(),
        }
    
    @classmethod
    def get_trending_content(cls, days=7) -> Dict:
        """Get trending content and popular users"""
        from .models import Message, MessageReaction
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Most reacted messages
        trending_messages = Message.objects.filter(
            created_at__gte=cutoff_date,
            is_deleted=False
        ).annotate(
            reaction_count=Count('reactions')
        ).filter(reaction_count__gt=0).order_by('-reaction_count')[:10]
        
        # Most active users
        active_users = User.objects.filter(
            sent_messages__created_at__gte=cutoff_date
        ).annotate(
            message_count=Count('sent_messages'),
            reaction_count=Count('message_reactions')
        ).order_by('-message_count')[:10]
        
        # Popular emojis
        popular_emojis = MessageReaction.objects.filter(
            created_at__gte=cutoff_date
        ).values('emoji').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'period_days': days,
            'trending_messages': [
                {
                    'id': msg.id,
                    'content': msg.content[:100] if msg.content else None,
                    'sender': msg.sender.username,
                    'reaction_count': msg.reaction_count,
                    'created_at': msg.created_at,
                }
                for msg in trending_messages
            ],
            'active_users': [
                {
                    'username': user.username,
                    'message_count': user.message_count,
                    'reaction_count': user.reaction_count,
                }
                for user in active_users
            ],
            'popular_emojis': list(popular_emojis),
        }


# Add this function that's being imported by the tests
def calculate_message_analytics(start_date=None, end_date=None):
    """
    Calculate message analytics for the platform
    This function is used by the Celery task
    """
    from .models import Message, Conversation
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Apply date filters if provided
    messages = Message.objects.filter(is_deleted=False)
    if start_date:
        messages = messages.filter(created_at__gte=start_date)
    if end_date:
        messages = messages.filter(created_at__lte=end_date)
    
    # Basic counts
    total_messages = messages.count()
    total_conversations = Conversation.objects.filter(is_active=True).count()
    
    # User activity
    active_users = User.objects.filter(
        sent_messages__in=messages
    ).distinct().count()
    
    # Message types
    messages_by_type = messages.values('message_type').annotate(
        count=Count('id')
    ).order_by('message_type')
    
    # Convert to dictionary for easier access
    message_types_dict = {
        item['message_type']: item['count'] 
        for item in messages_by_type
    }
    
    # Time-based analytics
    messages_by_hour = list(messages.extra(
        select={'hour': 'EXTRACT(hour FROM created_at)'}
    ).values('hour').annotate(count=Count('id')).order_by('hour'))
    
    messages_by_day = list(messages.extra(
        select={'day': 'EXTRACT(dow FROM created_at)'}
    ).values('day').annotate(count=Count('id')).order_by('day'))
    
    # Conversation activity
    active_conversations = Conversation.objects.filter(
        messages__in=messages
    ).distinct().count()
    
    return {
        'total_messages': total_messages,
        'total_conversations': total_conversations,
        'active_users': active_users,
        'messages_by_type': message_types_dict,
        'messages_by_hour': messages_by_hour,
        'messages_by_day': messages_by_day,
        'active_conversations': active_conversations,
        'period_start': start_date.isoformat() if start_date else None,
        'period_end': end_date.isoformat() if end_date else None,
        'generated_at': timezone.now().isoformat()
    }
