from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, UserDetailView, UserListView, update_online_status,logout_view,
    deactivate_account, delete_account
)

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', logout_view, name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User profile endpoints
    path('me/', UserDetailView.as_view(), name='user_detail'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('status/', update_online_status, name='update_status'),
    
    # Account management
    path('deactivate/', deactivate_account, name='deactivate_account'),
    path('delete/', delete_account, name='delete_account'),
]