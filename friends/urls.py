from django.urls import path
from . import views

app_name = 'friends'

urlpatterns = [
    # Friend requests
    path('request/send/', views.FriendRequestView.as_view(), name='send-request'),
    path('request/respond/', views.FriendRequestResponseView.as_view(), name='respond-request'),
    path('request/cancel/<int:request_id>/', views.CancelFriendRequestView.as_view(), name='cancel-request'),
    
    # Friends management
    path('list/', views.FriendListView.as_view(), name='friends-list'),
    path('pending/', views.PendingRequestsView.as_view(), name='pending-requests'),
    path('stats/', views.FriendStatsView.as_view(), name='friend-stats'),
    path('search/', views.FriendSearchView.as_view(), name='search-users'),
    path('remove/', views.FriendshipManagementView.as_view(), name='remove-friend'),
    path('mutual/<str:username>/', views.MutualFriendsView.as_view(), name='mutual-friends'),
]