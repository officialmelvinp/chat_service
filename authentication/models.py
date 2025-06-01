from django.contrib.auth.models import AbstractUser
from django.db import models
from common.models import TimeStampedModel

class User(AbstractUser, TimeStampedModel):
    """Extended user model with chat-specific fields"""
    
    # Gender choices
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('non_binary', 'Non-Binary'),
        ('transgender', 'Transgender'),
        ('prefer_not_to_say', 'Prefer not to say'),
        ('other', 'Other'),
    ]
    
    # Relationship status choices
    RELATIONSHIP_STATUS_CHOICES = [
        ('single', 'Single'),
        ('in_relationship', 'In a relationship'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('complicated', "It's complicated"),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    # Profile fields
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    relationship_status = models.CharField(max_length=20, choices=RELATIONSHIP_STATUS_CHOICES, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Interests and languages (simple text fields for now - can be upgraded to ManyToMany later)
    interests = models.TextField(max_length=1000, blank=True, help_text="Comma-separated list of interests/hobbies")
    languages = models.CharField(max_length=200, blank=True, help_text="Comma-separated list of languages spoken")
    
    # Chat-specific fields
    is_online = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            from datetime import date
            return (date.today() - self.date_of_birth).days // 365
        return None
    
    @property
    def interests_list(self):
        """Return interests as a list"""
        if self.interests:
            return [interest.strip() for interest in self.interests.split(',') if interest.strip()]
        return []
    
    @property
    def languages_list(self):
        """Return languages as a list"""
        if self.languages:
            return [lang.strip() for lang in self.languages.split(',') if lang.strip()]
        return []
    
    def get_full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def update_last_active(self):
        """Update last active timestamp"""
        from django.utils import timezone
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])
    
    def __str__(self):
        return self.username
