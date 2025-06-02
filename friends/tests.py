from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from datetime import datetime, timezone

from .models import FriendRequest, Friendship

User = get_user_model()


class FriendModelsTest(TestCase):
    """Test the Friend models"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User1'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User2'
        )
        self.user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User3'
        )

    def test_friend_request_creation(self):
        """Test creating a friend request"""
        friend_request = FriendRequest.objects.create(
            sender=self.user1,
            receiver=self.user2
        )
        
        self.assertEqual(friend_request.sender, self.user1)
        self.assertEqual(friend_request.receiver, self.user2)
        self.assertEqual(friend_request.status, 'pending')
        self.assertIsNotNone(friend_request.created_at)

    def test_friend_request_str_method(self):
        """Test the string representation of FriendRequest"""
        friend_request = FriendRequest.objects.create(
            sender=self.user1,
            receiver=self.user2
        )
        expected_str = f"{self.user1.username} → {self.user2.username}: pending"
        self.assertEqual(str(friend_request), expected_str)

    def test_friendship_creation(self):
        """Test creating a friendship"""
        friendship = Friendship.objects.create(
            user1=self.user1,
            user2=self.user2
        )
        
        self.assertEqual(friendship.user1, self.user1)
        self.assertEqual(friendship.user2, self.user2)
        self.assertIsNotNone(friendship.created_at)

    def test_friendship_str_method(self):
        """Test the string representation of Friendship"""
        friendship = Friendship.objects.create(
            user1=self.user1,
            user2=self.user2
        )
        expected_str = f"{self.user1.username} ↔ {self.user2.username}"
        self.assertEqual(str(friendship), expected_str)

    def test_friendship_are_friends_method(self):
        """Test the are_friends class method"""
        # Initially not friends
        self.assertFalse(Friendship.are_friends(self.user1, self.user2))
        
        # Create friendship
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        
        # Now they are friends
        self.assertTrue(Friendship.are_friends(self.user1, self.user2))
        self.assertTrue(Friendship.are_friends(self.user2, self.user1))

    def test_friendship_get_friends_method(self):
        """Test the get_friends class method"""
        # Create friendships
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        Friendship.objects.create(user1=self.user1, user2=self.user3)
        
        # Get friends of user1
        friends = Friendship.get_friends(self.user1)
        self.assertEqual(len(friends), 2)
        self.assertIn(self.user2, friends)
        self.assertIn(self.user3, friends)
        
        # Get friends of user2
        friends = Friendship.get_friends(self.user2)
        self.assertEqual(len(friends), 1)
        self.assertIn(self.user1, friends)


class FriendAPITest(APITestCase):
    """Test the Friend API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User1'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User2'
        )
        self.user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User3'
        )
        self.user4 = User.objects.create_user(
            username='testuser4',
            email='test4@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User4'
        )
        
        # Generate JWT tokens
        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)
        self.token3 = str(RefreshToken.for_user(self.user3).access_token)

    def authenticate_user(self, token):
        """Helper method to authenticate a user"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_send_friend_request_success(self):
        """Test sending a friend request successfully"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:send-request')
        data = {'receiver_username': 'testuser2'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('Friend request sent to testuser2', response.data['message'])
        
        # Verify friend request was created
        friend_request = FriendRequest.objects.get(sender=self.user1, receiver=self.user2)
        self.assertEqual(friend_request.status, 'pending')

    def test_send_friend_request_to_nonexistent_user(self):
        """Test sending a friend request to a non-existent user"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:send-request')
        data = {'receiver_username': 'nonexistent'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_friend_request_to_self(self):
        """Test sending a friend request to yourself"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:send-request')
        data = {'receiver_username': 'testuser1'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_duplicate_friend_request(self):
        """Test sending a duplicate friend request"""
        # Create initial friend request
        FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:send-request')
        data = {'receiver_username': 'testuser2'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_friend_request_success(self):
        """Test accepting a friend request successfully"""
        # Create friend request
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        
        self.authenticate_user(self.token2)
        
        url = reverse('friends:respond-request')
        data = {
            'request_id': friend_request.id,
            'action': 'accept'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')
        
        # Verify friendship was created
        self.assertTrue(Friendship.are_friends(self.user1, self.user2))
        
        # Verify friend request was updated
        friend_request.refresh_from_db()
        self.assertEqual(friend_request.status, 'accepted')

    def test_reject_friend_request_success(self):
        """Test rejecting a friend request successfully"""
        # Create friend request
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        
        self.authenticate_user(self.token2)
        
        url = reverse('friends:respond-request')
        data = {
            'request_id': friend_request.id,
            'action': 'reject'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'rejected')
        
        # Verify no friendship was created
        self.assertFalse(Friendship.are_friends(self.user1, self.user2))
        
        # Verify friend request was updated
        friend_request.refresh_from_db()
        self.assertEqual(friend_request.status, 'rejected')

    def test_respond_to_nonexistent_request(self):
        """Test responding to a non-existent friend request"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:respond-request')
        data = {
            'request_id': 999,
            'action': 'accept'
        }
        
        response = self.client.post(url, data, format='json')
        
        # This should return 400 because the serializer validation fails
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_friends_list(self):
        """Test getting the user's friends list"""
        # Create friendships
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        Friendship.objects.create(user1=self.user1, user2=self.user3)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:friends-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Changed from 'friends' to 'results' due to pagination
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['total_friends'], 2)        
        

    def test_get_pending_requests(self):
        """Test getting pending friend requests"""
        # Create pending requests
        FriendRequest.objects.create(sender=self.user2, receiver=self.user1)  # Received
        FriendRequest.objects.create(sender=self.user1, receiver=self.user3)  # Sent
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:pending-requests')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Updated to match new response structure
        self.assertEqual(len(response.data['received_requests']['results']), 1)
        self.assertEqual(len(response.data['sent_requests']['results']), 1)
        self.assertEqual(response.data['total_pending_received'], 1)
        self.assertEqual(response.data['total_pending_sent'], 1)

    def test_get_friend_stats(self):
        """Test getting friendship statistics"""
        # Create friendships and requests
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        FriendRequest.objects.create(sender=self.user3, receiver=self.user1)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:friend-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_friends'], 1)
        self.assertEqual(response.data['pending_received'], 1)

    def test_search_users(self):
        """Test searching for users"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:search-users')
        data = {'query': 'testuser'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Updated to use 'results' instead of direct count
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['count'], 3)

    def test_search_users_excludes_friends(self):
        """Test that search excludes current friends"""
        # Make user2 a friend
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:search-users')
        data = {'query': 'testuser'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Updated to use 'results' and expect 2 users (3, 4)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)

    def test_get_mutual_friends(self):
        """Test getting mutual friends"""
        # Create friendships
        # user1 friends with user3 and user4
        Friendship.objects.create(user1=self.user1, user2=self.user3)
        Friendship.objects.create(user1=self.user1, user2=self.user4)
        
        # user2 friends with user3 and user4
        Friendship.objects.create(user1=self.user2, user2=self.user3)
        Friendship.objects.create(user1=self.user2, user2=self.user4)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:mutual-friends', kwargs={'username': 'testuser2'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Updated to use 'results' instead of direct count
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)
        
        

    def test_remove_friendship(self):
        """Test removing a friendship"""
        # Create friendship
        Friendship.objects.create(user1=self.user1, user2=self.user2)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:remove-friend')
        data = {'username': 'testuser2'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Friendship with testuser2 has been removed', response.data['message'])
        
        # Verify friendship was deleted
        self.assertFalse(Friendship.are_friends(self.user1, self.user2))

    def test_remove_nonexistent_friendship(self):
        """Test removing a non-existent friendship"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:remove-friend')
        data = {'username': 'testuser2'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_friend_request(self):
        """Test canceling a sent friend request"""
        # Create friend request
        friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:cancel-request', kwargs={'request_id': friend_request.id})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Friend request to testuser2 has been canceled', response.data['message'])
        
        # Verify friend request was deleted
        self.assertFalse(FriendRequest.objects.filter(id=friend_request.id).exists())

    def test_cancel_nonexistent_request(self):
        """Test canceling a non-existent friend request"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:cancel-request', kwargs={'request_id': 999})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_mutual_friends(self):
        """Test getting mutual friends"""
        # Create friendships
        # user1 friends with user3 and user4
        Friendship.objects.create(user1=self.user1, user2=self.user3)
        Friendship.objects.create(user1=self.user1, user2=self.user4)
        
        # user2 friends with user3 and user4
        Friendship.objects.create(user1=self.user2, user2=self.user3)
        Friendship.objects.create(user1=self.user2, user2=self.user4)
        
        self.authenticate_user(self.token1)
        
        url = reverse('friends:mutual-friends', kwargs={'username': 'testuser2'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # user3 and user4 are mutual friends

    def test_get_mutual_friends_with_nonexistent_user(self):
        """Test getting mutual friends with a non-existent user"""
        self.authenticate_user(self.token1)
        
        url = reverse('friends:mutual-friends', kwargs={'username': 'nonexistent'})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access friend endpoints"""
        url = reverse('friends:friends-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FriendIntegrationTest(APITestCase):
    """Integration tests for the complete friend workflow"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123',
            first_name='Alice',
            last_name='Smith'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123',
            first_name='Bob',
            last_name='Johnson'
        )
        
        self.token1 = str(RefreshToken.for_user(self.user1).access_token)
        self.token2 = str(RefreshToken.for_user(self.user2).access_token)
        

    def test_complete_friend_workflow(self):
        """Test the complete friend request workflow"""
        # Step 1: Alice sends friend request to Bob
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        response = self.client.post(
            reverse('friends:send-request'),
            {'receiver_username': 'bob'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Step 2: Bob checks pending requests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        
        response = self.client.get(reverse('friends:pending-requests'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_pending_received'], 1)
        
        request_id = response.data['received_requests']['results'][0]['id']
        
        # Step 3: Bob accepts the friend request
        response = self.client.post(
            reverse('friends:respond-request'),
            {'request_id': request_id, 'action': 'accept'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 4: Verify they are now friends (with pagination)
        response = self.client.get(reverse('friends:friends-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'alice')
        
        # Step 5: Alice checks her friends list
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        
        response = self.client.get(reverse('friends:friends-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'bob')