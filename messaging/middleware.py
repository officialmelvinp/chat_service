from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt

User = get_user_model()

class JwtAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that takes a token from the query string and authenticates the user.
    """
    
    async def __call__(self, scope, receive, send):
        # Get the token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = dict(param.split('=') for param in query_string.split('&') if param)
        
        token = query_params.get('token', None)
        scope['user'] = AnonymousUser()
        
        if token:
            try:
                # Authenticate with token
                user = await self.get_user_from_token(token)
                scope['user'] = user
            except (InvalidToken, TokenError, jwt.PyJWTError):
                pass
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            # Verify the token and get the user
            access_token = AccessToken(token)
            user_id = access_token.payload.get('user_id')
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()
