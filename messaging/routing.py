from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<conversation_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]


# from django.urls import re_path
# from . import consumers

# websocket_urlpatterns = [
#     # Original route
#     re_path(r'ws/chat/(?P<conversation_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    
#     # Simple test route
#     re_path(r'ws/test/$', consumers.ChatConsumer.as_asgi()),
# ]

