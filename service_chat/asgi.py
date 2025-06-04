import os
import django
from django.core.asgi import get_asgi_application

# Set Django settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'service_chat.settings')

# Setup Django BEFORE importing anything else
django.setup()

# Now we can safely import Django-related modules
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from messaging.routing import websocket_urlpatterns
from messaging.middleware import JwtAuthMiddleware

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

# Create the main ASGI application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})  # <-- Added the missing closing parenthesis here
