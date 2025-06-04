from django.core.management.base import BaseCommand
from django.utils import timezone
from messaging.models import MessageExpiration, Message


class Command(BaseCommand):
    help = 'Clean up expired messages'
    
    def handle(self, *args, **options):
        # Find expired messages
        expired_expirations = MessageExpiration.objects.filter(
            expires_at__lte=timezone.now(),
            is_expired=False
        )
        
        count = 0
        for expiration in expired_expirations:
            # Mark message as deleted
            expiration.message.soft_delete()
            expiration.is_expired = True
            expiration.save()
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned up {count} expired messages')
        )
