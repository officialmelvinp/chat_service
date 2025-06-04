from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.urls import path, include

User = get_user_model()

class SafeSchemaGenerator(OpenAPISchemaGenerator):
    """Schema generator that handles AnonymousUser safely"""
    
    def get_schema(self, request=None, public=False):
        """Generate schema with a dummy user for testing"""
        if request is None:
            return super().get_schema(request, public)
        
        # 🔥 FIX: Don't try to set is_authenticated - create a proper mock user
        if isinstance(request.user, AnonymousUser):
            # Create a mock authenticated user for schema generation
            class MockUser:
                def __init__(self):
                    self.id = -1
                    self.username = "swagger-dummy"
                    self.email = "swagger@example.com"
                    self.is_active = True
                    self.is_staff = False
                    self.is_superuser = False
                
                @property
                def is_authenticated(self):
                    return True
                
                def __str__(self):
                    return self.username
            
            request.user = MockUser()
        
        return super().get_schema(request, public)

# Create schema view with custom generator AND exclude messaging endpoints
schema_view = get_schema_view(
    openapi.Info(
        title="Chat Service API",
        default_version='v1',
        description="API for real-time messaging platform",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[JWTAuthentication, SessionAuthentication],
    generator_class=SafeSchemaGenerator,
    patterns=[
        path('api/auth/', include('authentication.urls')),
        path('api/friends/', include('friends.urls')),
        # Messaging URLs are excluded from Swagger to avoid conflicts
    ],
)
