from django.contrib import admin
from .models import (
    Conversation, ConversationParticipant, Message,
    MessageReaction, TypingIndicator, UserOnlineStatus
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation_type', 'title', 'get_participants', 'created_at', 'last_message_at')
    list_filter = ('conversation_type', 'is_active', 'created_at')
    search_fields = ('title', 'participant1__username', 'participant2__username')
    date_hierarchy = 'created_at'
    
    def get_participants(self, obj):
        if obj.conversation_type == 'direct':
            return f"{obj.participant1.username} & {obj.participant2.username}"
        else:
            participants = obj.participants.filter(is_active=True)
            return f"{participants.count()} participants"
    get_participants.short_description = 'Participants'


class MessageReactionInline(admin.TabularInline):
    model = MessageReaction
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'message_type', 'short_content', 'status', 'created_at')
    list_filter = ('message_type', 'status', 'is_deleted', 'created_at')
    search_fields = ('content', 'sender__username')
    date_hierarchy = 'created_at'
    inlines = [MessageReactionInline]
    
    def short_content(self, obj):
        if obj.is_deleted:
            return "[Deleted]"
        if obj.content:
            return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
        return f"[{obj.get_message_type_display()}]"
    short_content.short_description = 'Content'


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'user', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'joined_at')
    search_fields = ('user__username', 'conversation__title')
    date_hierarchy = 'joined_at'


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'emoji', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'emoji')
    date_hierarchy = 'created_at'


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'user', 'started_at')
    list_filter = ('started_at',)
    search_fields = ('user__username',)
    date_hierarchy = 'started_at'


@admin.register(UserOnlineStatus)
class UserOnlineStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_online', 'last_seen', 'status_message')
    list_filter = ('is_online', 'last_seen')
    search_fields = ('user__username', 'status_message')
    date_hierarchy = 'last_seen'
