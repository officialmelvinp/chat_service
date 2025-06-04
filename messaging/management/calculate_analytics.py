from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from messaging.analytics import AnalyticsEngine

User = get_user_model()


class Command(BaseCommand):
    help = 'Calculate user engagement analytics'
    
    def handle(self, *args, **options):
        users = User.objects.all()
        
        for user in users:
            try:
                AnalyticsEngine.get_user_engagement_summary(user)
                self.stdout.write(f'Updated analytics for {user.username}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating analytics for {user.username}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully updated analytics for all users')
        )
