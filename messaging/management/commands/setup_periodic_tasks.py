from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json

class Command(BaseCommand):
    help = 'Set up periodic tasks for messaging app'

    def handle(self, *args, **options):
        # Create schedules
        
        # Every 30 minutes
        interval_30min, created = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.MINUTES,
        )
        
        # Daily at 2 AM
        daily_2am, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=2,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Weekly on Sunday at 3 AM
        weekly_sunday, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=3,
            day_of_week=0,  # Sunday
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create periodic tasks
        
        # Cleanup expired messages daily
        PeriodicTask.objects.get_or_create(
            name='Daily Message Cleanup',
            defaults={
                'task': 'messaging.tasks.cleanup_expired_messages',
                'crontab': daily_2am,
                'enabled': True,
            }
        )
        
        # Calculate analytics weekly
        PeriodicTask.objects.get_or_create(
            name='Weekly Analytics Calculation',
            defaults={
                'task': 'messaging.tasks.calculate_analytics',
                'crontab': weekly_sunday,
                'enabled': True,
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up periodic tasks')
        )
