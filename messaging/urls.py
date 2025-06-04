from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    # ViewSet URLs (this gives you /api/conversations/ and /api/messages/)
    path('', include(router.urls)),
    
    # 🔥 ADD: Your function-based view URLs
    path('create_message/', views.create_message, name='create_message'),
    path('bulk_message_cleanup/', views.bulk_message_cleanup, name='bulk_message_cleanup'),
    path('generate_analytics/', views.generate_analytics, name='generate_analytics'),
    path('task_status/<str:task_id>/', views.task_status, name='task_status'),
    path('conversation_analytics/<uuid:conversation_id>/', views.conversation_analytics, name='conversation_analytics'),
    path('user_engagement/', views.user_engagement, name='user_engagement'),
]
