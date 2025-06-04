import requests
import logging
from django.conf import settings
from celery import shared_task
import re
from typing import Dict, List, Tuple
import json

logger = logging.getLogger(__name__)


class ContentModerator:
    """Handle content moderation for messages and profiles"""
    
    # Predefined inappropriate content patterns
    INAPPROPRIATE_PATTERNS = [
        # Profanity (basic examples - you'd want a more comprehensive list)
        r'\b(fuck|shit|damn|bitch|asshole)\b',
        # Spam patterns
        r'(click here|buy now|limited time|act now)',
        # Personal info patterns
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone numbers
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email addresses
    ]
    
    SEVERITY_SCORES = {
        'profanity': 0.7,
        'spam': 0.5,
        'personal_info': 0.8,
        'harassment': 0.9,
        'explicit': 0.95,
    }
    
    @classmethod
    def moderate_text(cls, content: str, user=None) -> Dict:
        """Moderate text content"""
        results = {
            'is_appropriate': True,
            'confidence_score': 0.0,
            'issues_found': [],
            'action_required': 'none',  # none, flag, block
            'filtered_content': content
        }
        
        # Check against predefined patterns
        issues = cls._check_patterns(content)
        
        # Calculate overall severity
        max_severity = 0.0
        for issue in issues:
            max_severity = max(max_severity, issue['severity'])
            results['issues_found'].append(issue)
        
        results['confidence_score'] = max_severity
        
        # Determine action based on severity
        if max_severity >= 0.9:
            results['is_appropriate'] = False
            results['action_required'] = 'block'
            results['filtered_content'] = cls._censor_content(content)
        elif max_severity >= 0.7:
            results['is_appropriate'] = False
            results['action_required'] = 'flag'
            results['filtered_content'] = cls._censor_content(content)
        elif max_severity >= 0.5:
            results['action_required'] = 'flag'
        
        # Log moderation action
        if user and results['action_required'] != 'none':
            cls._log_moderation(user, 'message', content, results)
        
        return results
    
    @classmethod
    def _check_patterns(cls, content: str) -> List[Dict]:
        """Check content against predefined patterns"""
        issues = []
        content_lower = content.lower()
        
        for pattern in cls.INAPPROPRIATE_PATTERNS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                if 'fuck|shit|damn' in pattern:
                    issue_type = 'profanity'
                elif 'click here|buy now' in pattern:
                    issue_type = 'spam'
                elif r'\d{3}-\d{3}-\d{4}' in pattern or '@' in pattern:
                    issue_type = 'personal_info'
                else:
                    issue_type = 'other'
                
                issues.append({
                    'type': issue_type,
                    'severity': cls.SEVERITY_SCORES.get(issue_type, 0.5),
                    'matches': matches,
                    'pattern': pattern
                })
        
        return issues
    
    @classmethod
    def _censor_content(cls, content: str) -> str:
        """Censor inappropriate content"""
        censored = content
        
        for pattern in cls.INAPPROPRIATE_PATTERNS:
            censored = re.sub(pattern, '***', censored, flags=re.IGNORECASE)
        
        return censored
    
    @classmethod
    def _log_moderation(cls, user, content_type: str, content: str, results: Dict):
        """Log moderation action"""
        from .models import ContentModerationLog
        
        action_map = {
            'block': 'blocked',
            'flag': 'flagged',
            'none': 'approved'
        }
        
        ContentModerationLog.objects.create(
            content_type=content_type,
            content_id=0,  # You'd set this to the actual content ID
            user=user,
            action=action_map[results['action_required']],
            reason=', '.join([issue['type'] for issue in results['issues_found']]),
            confidence_score=results['confidence_score'],
            is_automated=True
        )
    
    @classmethod
    def moderate_image(cls, image_path: str, user=None) -> Dict:
        """Moderate image content (placeholder for AI service integration)"""
        # This would integrate with services like Google Vision API, AWS Rekognition, etc.
        results = {
            'is_appropriate': True,
            'confidence_score': 0.0,
            'issues_found': [],
            'action_required': 'none'
        }
        
        # Placeholder for actual image moderation
        # You would integrate with external AI services here
        
        return results


class RateLimiter:
    """Handle rate limiting for various actions"""
    
    LIMITS = {
        'message': {'per_minute': 10, 'per_hour': 100},
        'reaction': {'per_minute': 20, 'per_hour': 200},
        'friend_request': {'per_minute': 5, 'per_hour': 20},
        'profile_update': {'per_minute': 2, 'per_hour': 10},
    }
    
    @classmethod
    def check_limit(cls, user, action_type: str) -> Tuple[bool, str]:
        """Check if user has exceeded rate limit"""
        from .models import RateLimitTracker
        
        if action_type not in cls.LIMITS:
            return True, None
        
        limits = cls.LIMITS[action_type]
        
        # Check per-minute limit
        allowed, message = RateLimitTracker.check_rate_limit(
            user, action_type, limits['per_minute']
        )
        
        if not allowed:
            return False, message
        
        # You could add per-hour checking here as well
        
        return True, None
    
    @classmethod
    def is_user_rate_limited(cls, user, action_type: str) -> bool:
        """Quick check if user is rate limited"""
        allowed, _ = cls.check_limit(user, action_type)
        return not allowed


class AdvancedSearch:
    """Handle advanced search functionality"""
    
    @classmethod
    def search_messages(cls, user, query: str, conversation_id=None, 
                       date_from=None, date_to=None, message_type=None) -> Dict:
        """Search through user's messages"""
        from django.db.models import Q
        from .models import Message, Conversation
        
        # Base query - only messages user can access
        user_conversations = Conversation.get_user_conversations(user)
        messages = Message.objects.filter(
            conversation__in=user_conversations,
            is_deleted=False
        )
        
        # Apply filters
        if conversation_id:
            messages = messages.filter(conversation_id=conversation_id)
        
        if date_from:
            messages = messages.filter(created_at__gte=date_from)
        
        if date_to:
            messages = messages.filter(created_at__lte=date_to)
        
        if message_type:
            messages = messages.filter(message_type=message_type)
        
        # Text search
        if query:
            messages = messages.filter(
                Q(content__icontains=query) |
                Q(sender__username__icontains=query) |
                Q(sender__first_name__icontains=query) |
                Q(sender__last_name__icontains=query)
            )
        
        # Order by relevance (most recent first for now)
        messages = messages.order_by('-created_at')
        
        return {
            'messages': messages[:50],  # Limit results
            'total_count': messages.count(),
            'query': query,
            'filters_applied': {
                'conversation_id': conversation_id,
                'date_from': date_from,
                'date_to': date_to,
                'message_type': message_type
            }
        }
    
    @classmethod
    def search_conversations(cls, user, query: str) -> Dict:
        """Search through user's conversations"""
        from django.db.models import Q
        from .models import Conversation
        
        conversations = Conversation.get_user_conversations(user)
        
        if query:
            conversations = conversations.filter(
                Q(title__icontains=query) |
                Q(participant1__username__icontains=query) |
                Q(participant2__username__icontains=query) |
                Q(participants__user__username__icontains=query)
            ).distinct()
        
        return {
            'conversations': conversations[:20],
            'total_count': conversations.count(),
            'query': query
        }


# ADD THIS FUNCTION - This is what was missing!
def moderate_message_content(content: str, user=None) -> Dict:
    """
    Standalone function to moderate message content
    This is the function that tasks.py is trying to import
    """
    # Use the ContentModerator class to do the actual moderation
    result = ContentModerator.moderate_text(content, user)
    
    # Convert the result format to match what tasks.py expects
    return {
        'flagged': not result['is_appropriate'],
        'reason': ', '.join([issue['type'] for issue in result['issues_found']]) if result['issues_found'] else None,
        'confidence': result['confidence_score'],
        'action': result['action_required'],
        'filtered_content': result['filtered_content'],
        'issues': result['issues_found']
    }

@shared_task(bind=True, max_retries=3)
def moderate_content_async(self, message_id, content):
    """
    Asynchronous content moderation task
    """
    try:
        from .models import Message
        
        message = Message.objects.get(id=message_id)
        result = moderate_message_content(content)
        
        if result.get('flagged'):
            message.is_flagged = True
            message.moderation_result = result
            message.save()
            
            logger.info(f"Message {message_id} flagged for: {result.get('reason')}")
            
            # Trigger webhook for flagged content
            from .tasks import send_webhook
            webhook_payload = {
                'event': 'content_flagged',
                'message_id': message_id,
                'reason': result.get('reason'),
                'timestamp': message.created_at.isoformat()
            }
            
            webhook_urls = getattr(settings, 'CONTENT_MODERATION_WEBHOOKS', [])
            for url in webhook_urls:
                send_webhook.delay(url, webhook_payload)
        
        return result
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found for moderation")
        return {'error': 'Message not found'}
    except Exception as exc:
        logger.error(f"Async content moderation failed: {str(exc)}")
        raise self.retry(countdown=60, exc=exc)

def check_message_safety(content, user_id=None):
    """
    Quick safety check for messages before saving
    """
    result = moderate_message_content(content)
    
    if result.get('flagged'):
        logger.warning(f"Unsafe content detected from user {user_id}: {result.get('reason')}")
    
    return result
