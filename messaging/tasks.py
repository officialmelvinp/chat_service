from celery import shared_task
from django.conf import settings
from django.utils import timezone
import requests
import logging
import json

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_webhook(self, webhook_url, payload, headers=None):
    """
    Send webhook to external service
    """
    try:
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ChatService-Webhook/1.0'
        }
        
        if headers:
            default_headers.update(headers)
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=default_headers,
            timeout=getattr(settings, 'WEBHOOK_TIMEOUT', 30)
        )
        
        response.raise_for_status()
        
        logger.info(f"Webhook sent successfully to {webhook_url}")
        return {
            'status': 'success',
            'status_code': response.status_code,
            'response': response.text[:500]
        }
        
    except requests.exceptions.RequestException as exc:
        logger.error(f"Webhook failed for {webhook_url}: {str(exc)}")
        
        try:
            countdown = getattr(settings, 'WEBHOOK_RETRY_DELAY', 60) * (2 ** self.request.retries)
            raise self.retry(countdown=countdown, exc=exc)
        except self.MaxRetriesExceededError:
            return {
                'status': 'failed',
                'error': str(exc),
                'retries_exceeded': True
            }

@shared_task
def moderate_content(message_id, content):
    """
    Moderate message content
    """
    from .models import Message
    from .content_moderation import moderate_message_content
    
    try:
        message = Message.objects.get(id=message_id)
        result = moderate_message_content(content)
        
        if result.get('flagged'):
            message.is_flagged = True
            message.moderation_result = result
            message.save()
            
            # Send webhook for flagged content
            webhook_payload = {
                'event': 'content_flagged',
                'message_id': message_id,
                'reason': result.get('reason'),
                'timestamp': timezone.now().isoformat()
            }
            
            # You can add webhook URLs from your settings or database
            webhook_urls = getattr(settings, 'CONTENT_MODERATION_WEBHOOKS', [])
            for url in webhook_urls:
                send_webhook.delay(url, webhook_payload)
        
        return result
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found for moderation")
        return {'error': 'Message not found'}
    except Exception as exc:
        logger.error(f"Content moderation failed for message {message_id}: {str(exc)}")
        return {'error': str(exc)}

@shared_task
def cleanup_expired_messages():
    """
    Clean up expired messages
    """
    from .models import Message
    from datetime import timedelta
    
    try:
        cutoff_date = timezone.now() - timedelta(days=30)  # Adjust as needed
        expired_count = Message.objects.filter(
            created_at__lt=cutoff_date,
            is_deleted=False
        ).update(is_deleted=True)
        
        logger.info(f"Cleaned up {expired_count} expired messages")
        return {'cleaned_up': expired_count}
        
    except Exception as exc:
        logger.error(f"Message cleanup failed: {str(exc)}")
        return {'error': str(exc)}

@shared_task
def calculate_analytics():
    """
    Calculate messaging analytics
    """
    from .models import Message, Conversation
    from .analytics import calculate_message_analytics
    
    try:
        result = calculate_message_analytics()
        
        # Send analytics webhook if configured
        webhook_payload = {
            'event': 'analytics_calculated',
            'data': result,
            'timestamp': timezone.now().isoformat()
        }
        
        analytics_webhooks = getattr(settings, 'ANALYTICS_WEBHOOKS', [])
        for url in analytics_webhooks:
            send_webhook.delay(url, webhook_payload)
        
        return result
        
    except Exception as exc:
        logger.error(f"Analytics calculation failed: {str(exc)}")
        return {'error': str(exc)}

@shared_task
def process_message_encryption(message_id):
    """
    Process message encryption
    """
    from .models import Message
    from .encryption import encrypt_message_content
    
    try:
        message = Message.objects.get(id=message_id)
        
        if not message.is_encrypted:
            encrypted_content = encrypt_message_content(message.content)
            message.encrypted_content = encrypted_content
            message.is_encrypted = True
            message.save()
            
            logger.info(f"Message {message_id} encrypted successfully")
            return {'status': 'encrypted', 'message_id': message_id}
        
        return {'status': 'already_encrypted', 'message_id': message_id}
        
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found for encryption")
        return {'error': 'Message not found'}
    except Exception as exc:
        logger.error(f"Message encryption failed for {message_id}: {str(exc)}")
        return {'error': str(exc)}
