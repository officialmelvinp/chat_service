import requests
import json
import hashlib
import hmac
from typing import Dict, Any
from django.utils import timezone
from celery import shared_task
from .models import WebhookEndpoint, WebhookDelivery


class WebhookManager:
    """Manage webhook deliveries"""
    
    @classmethod
    def send_webhook(cls, event_type: str, payload: Dict[Any, Any], user=None):
        """Send webhook to all registered endpoints"""
        endpoints = WebhookEndpoint.objects.filter(
            is_active=True,
            events__contains=[event_type]
        )
        
        for endpoint in endpoints:
            # Queue webhook delivery
            deliver_webhook.delay(endpoint.id, event_type, payload)
    
    @classmethod
    def create_signature(cls, payload: str, secret: str) -> str:
        """Create webhook signature for verification"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()


@shared_task(bind=True, max_retries=3)
def deliver_webhook(self, endpoint_id: int, event_type: str, payload: Dict):
    """Deliver webhook with retry logic"""
    try:
        endpoint = WebhookEndpoint.objects.get(id=endpoint_id)
        
        # Prepare payload
        webhook_payload = {
            'event_type': event_type,
            'timestamp': timezone.now().isoformat(),
            'data': payload
        }
        
        payload_json = json.dumps(webhook_payload)
        signature = WebhookManager.create_signature(payload_json, endpoint.secret_key)
        
        # Create delivery record
        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload=webhook_payload,
            delivery_attempts=1
        )
        
        # Send webhook
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': f'sha256={signature}',
            'User-Agent': 'ChatService-Webhook/1.0'
        }
        
        response = requests.post(
            endpoint.url,
            data=payload_json,
            headers=headers,
            timeout=30
        )
        
        # Update delivery record
        delivery.response_status = response.status_code
        delivery.response_body = response.text[:1000]  # Limit response body
        
        if response.status_code == 200:
            delivery.is_delivered = True
            endpoint.total_sent += 1
            endpoint.last_sent_at = timezone.now()
        else:
            endpoint.total_failed += 1
            # Schedule retry
            delivery.next_retry_at = timezone.now() + timezone.timedelta(minutes=5 * (delivery.delivery_attempts))
        
        delivery.save()
        endpoint.save()
        
        # Retry if failed
        if not delivery.is_delivered and delivery.delivery_attempts < 3:
            raise Exception(f"Webhook delivery failed with status {response.status_code}")
            
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# Webhook event triggers
class WebhookEvents:
    """Define webhook events"""
    
    @staticmethod
    def message_sent(message):
        """Trigger webhook when message is sent"""
        payload = {
            'message_id': message.id,
            'conversation_id': message.conversation.id,
            'sender_id': message.sender.id,
            'sender_username': message.sender.username,
            'message_type': message.message_type,
            'content': message.content if not message.is_deleted else None,
            'timestamp': message.created_at.isoformat()
        }
        
        WebhookManager.send_webhook('message.sent', payload)
    
    @staticmethod
    def user_joined(user, conversation):
        """Trigger webhook when user joins conversation"""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'conversation_id': conversation.id,
            'conversation_type': conversation.conversation_type,
            'timestamp': timezone.now().isoformat()
        }
        
        WebhookManager.send_webhook('user.joined', payload)
    
    @staticmethod
    def reaction_added(reaction):
        """Trigger webhook when reaction is added"""
        payload = {
            'reaction_id': reaction.id,
            'message_id': reaction.message.id,
            'user_id': reaction.user.id,
            'emoji': reaction.emoji,
            'timestamp': reaction.created_at.isoformat()
        }
        
        WebhookManager.send_webhook('reaction.added', payload)
