from django.core.cache import cache
from django.conf import settings

def get_user_conversations_cached(user):
    """Cache user conversations for 5 minutes"""
    from .models import Conversation
    
    cache_key = f"user_conversations_{user.id}"
    conversations = cache.get(cache_key)
    
    if not conversations:
        conversations = Conversation.get_user_conversations(user)
        cache.set(cache_key, conversations, getattr(settings, 'CACHE_TTL', 300))  # 5 minutes
    
    return conversations

def get_conversation_messages_cached(conversation_id, limit=50):
    """Cache conversation messages for 1 minute"""
    from .models import Message
    
    cache_key = f"conversation_messages_{conversation_id}_{limit}"
    messages = cache.get(cache_key)
    
    if not messages:
        messages = Message.objects.filter(
            conversation_id=conversation_id,
            is_deleted=False
        ).order_by('-created_at')[:limit]
        
        cache.set(cache_key, messages, 60)  # 1 minute
    
    return messages

def invalidate_conversation_cache(conversation_id):
    """Invalidate conversation cache when new messages are added"""
    # Clear all possible cache keys for this conversation
    for limit in [20, 50, 100]:
        cache_key = f"conversation_messages_{conversation_id}_{limit}"
        cache.delete(cache_key)

def invalidate_user_cache(user_id):
    """Invalidate user cache when conversations change"""
    cache_key = f"user_conversations_{user_id}"
    cache.delete(cache_key)