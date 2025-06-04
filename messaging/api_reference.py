"""
📚 MESSAGING API ENDPOINTS REFERENCE
Just a reference file to keep track of all your endpoints
"""

# This is just for your reference - not imported anywhere

websocket_endpoints = {
    "ws://localhost:8000/ws/chat/<conversation_id>/": "Live chat messages",
    "ws://localhost:8000/ws/typing/<conversation_id>/": "Typing indicators", 
    "ws://localhost:8000/ws/online/": "Online status"
}


rest_endpoints = {
    # =============================================================================
    # CONVERSATIONS (ViewSet endpoints)
    # =============================================================================
    "GET /api/conversations/": "List user's conversations (OPTIMIZED with caching & pagination)",
    "POST /api/conversations/": "Create new conversation",
    "GET /api/conversations/<id>/": "Get conversation details",
    "PUT /api/conversations/<id>/": "Update conversation",
    "DELETE /api/conversations/<id>/": "Delete conversation",
    
    # NEW: Conversation Actions
    "POST /api/conversations/direct/": "Create or get direct conversation",
    "POST /api/conversations/group/": "Create group conversation", 
    "POST /api/conversations/<id>/add_participant/": "Add participant to group",
    "POST /api/conversations/<id>/remove_participant/": "Remove participant from group",
    
    # =============================================================================
    # MESSAGES (ViewSet endpoints)
    # =============================================================================
    "GET /api/messages/?conversation_id=<id>": "Get messages in conversation (OPTIMIZED with caching & pagination)",
    "POST /api/messages/": "Create new message",
    "GET /api/messages/<id>/": "Get message details",
    "PUT /api/messages/<id>/": "Update message",
    "DELETE /api/messages/<id>/": "Delete message",
    
    # NEW: Message Actions
    "POST /api/messages/send/": "Send new message (OPTIMIZED with background tasks)",
    "POST /api/messages/<id>/mark_read/": "Mark message as read",
    "POST /api/messages/<id>/edit/": "Edit message content",
    "POST /api/messages/<id>/delete/": "Soft delete message",
    "POST /api/messages/<id>/react/": "Add reaction to message",
    "POST /api/messages/<id>/remove_reaction/": "Remove reaction from message",
    
    # NEW: Bulk Operations (PERFORMANCE OPTIMIZED)
    "POST /api/messages/bulk_mark_read/": "Mark multiple messages as read",
    
    # NEW: Advanced Search (CACHED)
    "GET /api/messages/search/": "Search messages with filters (query, type, date, sender)",
    
    # =============================================================================
    # LEGACY FUNCTION-BASED ENDPOINTS (Still working)
    # =============================================================================
    "POST /api/create_message/": "Create message with background processing",
    "POST /api/bulk_message_cleanup/": "Trigger bulk message cleanup",
    "POST /api/generate_analytics/": "Generate analytics report",
    "GET /api/task_status/<task_id>/": "Check background task status",
    
    # =============================================================================
    # NEW: ANALYTICS ENDPOINTS (CACHED)
    # =============================================================================
    "GET /api/conversation_analytics/<conversation_id>/": "Get conversation analytics",
    "GET /api/user_engagement/": "Get user engagement analytics",
    
    # =============================================================================
    # USER MANAGEMENT (From other apps)
    # =============================================================================
    "GET /api/users/": "List users",
    "GET /api/users/<id>/": "Get user profile", 
    "PUT /api/users/<id>/": "Update user profile",
    
    # =============================================================================
    # AUTHENTICATION (From auth app)
    # =============================================================================
    "POST /api/auth/register/": "User registration",
    "POST /api/auth/login/": "User login",
    "POST /api/auth/logout/": "User logout",
    "POST /api/auth/refresh/": "Refresh JWT token",
    
    # =============================================================================
    # FRIENDS (From friends app)
    # =============================================================================
    "GET /api/friends/": "List user's friends",
    "POST /api/friends/request/": "Send friend request",
    "POST /api/friends/accept/": "Accept friend request",
    "POST /api/friends/decline/": "Decline friend request",
}


admin_endpoints = {
    "http://localhost:8000/admin/": "Django admin panel",
    "http://localhost:5555/": "Flower (Celery monitoring)",
    "http://localhost:8000/swagger/": "API Documentation (excluding messaging)",
    "http://localhost:8000/redoc/": "Alternative API Documentation"
}


webhook_endpoints = {
    # These are called by your Celery tasks automatically
    "POST /webhooks/message_created": "Triggered when message is created",
    "POST /webhooks/content_flagged": "Triggered when content is flagged", 
    "POST /webhooks/user_joined": "Triggered when user joins conversation",
    "POST /webhooks/analytics_ready": "Triggered when analytics are calculated"
}