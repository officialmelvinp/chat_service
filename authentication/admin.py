from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Remove this line - it's causing the error
# admin.site.unregister(User)

class CustomUserAdmin(UserAdmin):
    """Custom admin for User model"""
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'gender', 'relationship_status', 'is_online', 'is_staff', 'created_at')
    list_filter = ('is_online', 'is_staff', 'is_superuser', 'is_active', 'gender', 'relationship_status', 'country')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'country', 'city', 'interests', 'languages')
    readonly_fields = ('last_active', 'created_at', 'updated_at', 'age', 'interests_list', 'languages_list')
    
    # Add our custom fields to the admin interface
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Info', {
            'fields': ('avatar', 'bio', 'date_of_birth', 'age', 'gender', 'relationship_status', 'country', 'city')
        }),
        ('Interests & Languages', {
            'fields': ('interests', 'interests_list', 'languages', 'languages_list'),
            'description': 'Enter interests and languages as comma-separated values'
        }),
        ('Chat Status', {
            'fields': ('is_online', 'last_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Add fields to the add user form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Info', {
            'fields': ('first_name', 'last_name', 'email', 'gender', 'relationship_status')
        }),
    )
    
    def interests_list_display(self, obj):
        """Display interests as a formatted list"""
        return ', '.join(obj.interests_list) if obj.interests_list else 'None'
    interests_list_display.short_description = 'Interests (List)'
    
    def languages_list_display(self, obj):
        """Display languages as a formatted list"""
        return ', '.join(obj.languages_list) if obj.languages_list else 'None'
    languages_list_display.short_description = 'Languages (List)'

# Register with custom admin
admin.site.register(User, CustomUserAdmin)
