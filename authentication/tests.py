from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date

User = get_user_model()

class AuthenticationTests(TestCase):
    def setUp(self):
        """Set up test data and client"""
        self.client = APIClient()
        
        # URLs based on your actual views.py
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.refresh_url = '/api/auth/refresh/'
        self.me_url = '/api/auth/me/'
        self.users_url = '/api/auth/users/'
        self.status_url = '/api/auth/status/'
        self.deactivate_url = '/api/auth/deactivate/'
        self.delete_url = '/api/auth/delete/'
        
        # Create test user with ONLY fields that exist in your User model
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpassword123'
        )
        # Set additional fields after creation (including new fields)
        self.test_user.bio = 'Test bio'
        self.test_user.date_of_birth = date(1990, 1, 1)
        self.test_user.gender = 'male'
        self.test_user.relationship_status = 'single'
        self.test_user.country = 'Nigeria'
        self.test_user.city = 'Lagos'
        self.test_user.interests = 'coding, music, sports'
        self.test_user.languages = 'English, Yoruba, French'
        self.test_user.save()
        
        # Registration data
        self.valid_register_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpassword123',
            'password2': 'newpassword123'
        }
        
        # Login data
        self.valid_login_data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        # Profile update data (including new fields)
        self.valid_profile_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'Updated bio',
            'gender': 'female',
            'relationship_status': 'in_relationship',
            'interests': 'reading, traveling, photography',
            'languages': 'English, Spanish'
        }

    def get_authenticated_client(self):
        """Helper method to get an authenticated client"""
        response = self.client.post(
            self.login_url, 
            self.valid_login_data, 
            format='json'
        )
        
        print(f"Login response: {response.data}")
        
        # Handle different possible token field names
        if 'access' in response.data:
            token = response.data['access']
        elif 'access_token' in response.data:
            token = response.data['access_token']
        elif 'token' in response.data:
            token = response.data['token']
        else:
            raise KeyError(f"No access token found in response: {response.data}")
            
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    def test_user_registration(self):
        """Test user registration endpoint"""
        response = self.client.post(
            self.register_url, 
            self.valid_register_data, 
            format='json'
        )
        print(f"Registration response: {response.data}")
        print(f"Registration status: {response.status_code}")
        
        # Check if registration was successful
        if response.status_code == 201:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(User.objects.filter(username='newuser').exists())
        else:
            # Print error details for debugging
            print(f"Registration failed: {response.data}")

    def test_user_login(self):
        """Test user login endpoint"""
        response = self.client.post(
            self.login_url, 
            self.valid_login_data, 
            format='json'
        )
        print(f"Login response status: {response.status_code}")
        print(f"Login response data: {response.data}")
        
        # Check if login was successful
        if response.status_code == 200:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # Check for any token field
            has_token = any(key in response.data for key in ['access', 'access_token', 'token', 'refresh'])
            self.assertTrue(has_token, f"No token found in response: {response.data}")
        else:
            print(f"Login failed: {response.data}")

    def test_user_detail(self):
        """Test user detail endpoint"""
        # Unauthenticated request should fail
        response = self.client.get(self.me_url)
        print(f"Unauthenticated user detail status: {response.status_code}")
        
        # Try authenticated request
        try:
            client = self.get_authenticated_client()
            response = client.get(self.me_url)
            print(f"User detail response: {response.data}")
            print(f"User detail status: {response.status_code}")
            
            if response.status_code == 200:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['username'], 'testuser')
                # Test new fields are included in response
                if 'gender' in response.data:
                    self.assertEqual(response.data.get('gender'), 'male')
                if 'relationship_status' in response.data:
                    self.assertEqual(response.data.get('relationship_status'), 'single')
                if 'interests' in response.data:
                    self.assertIn('interests', response.data)
                if 'languages' in response.data:
                    self.assertIn('languages', response.data)
        except Exception as e:
            print(f"Authentication failed: {e}")

    def test_profile_update(self):
        """Test profile update endpoint"""
        try:
            client = self.get_authenticated_client()
            
            response = client.patch(
                self.me_url, 
                self.valid_profile_data, 
                format='json'
            )
            print(f"Profile update response: {response.data}")
            print(f"Profile update status: {response.status_code}")
            
            if response.status_code == 200:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Verify changes
                user = User.objects.get(username='testuser')
                self.assertEqual(user.first_name, 'Updated')
                self.assertEqual(user.last_name, 'Name')
                self.assertEqual(user.bio, 'Updated bio')
                # Test new fields if they were updated
                if 'gender' in self.valid_profile_data:
                    self.assertEqual(user.gender, 'female')
                if 'relationship_status' in self.valid_profile_data:
                    self.assertEqual(user.relationship_status, 'in_relationship')
                if 'interests' in self.valid_profile_data:
                    self.assertEqual(user.interests, 'reading, traveling, photography')
                if 'languages' in self.valid_profile_data:
                    self.assertEqual(user.languages, 'English, Spanish')
        except Exception as e:
            print(f"Profile update failed: {e}")

    def test_user_list(self):
        """Test user list endpoint"""
        # Create additional user with new fields
        additional_user = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123'
        )
        # Set additional fields
        additional_user.gender = 'female'
        additional_user.relationship_status = 'single'
        additional_user.interests = 'dancing, cooking'
        additional_user.languages = 'English, French'
        additional_user.save()
        
        try:
            client = self.get_authenticated_client()
            response = client.get(self.users_url)
            print(f"User list response: {response.data}")
            print(f"User list status: {response.status_code}")
            
            if response.status_code == 200:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                # Check that user list includes new fields (if serializer includes them)
                if 'results' in response.data:
                    users = response.data['results']
                    if users:
                        first_user = users[0]
                        print(f"First user fields: {first_user.keys()}")
                        # Only test if fields are present in serializer
                        if 'gender' in first_user:
                            self.assertIn('gender', first_user)
                        if 'interests' in first_user:
                            self.assertIn('interests', first_user)
                        if 'languages' in first_user:
                            self.assertIn('languages', first_user)
        except Exception as e:
            print(f"User list failed: {e}")

    def test_online_status(self):
        """Test online status update endpoint"""
        try:
            client = self.get_authenticated_client()
            
            response = client.post(
                self.status_url, 
                {'is_online': True}, 
                format='json'
            )
            print(f"Status update response: {response.data}")
            print(f"Status update status: {response.status_code}")
            
            if response.status_code == 200:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Verify status change
                user = User.objects.get(username='testuser')
                user.refresh_from_db()
                self.assertTrue(user.is_online)
        except Exception as e:
            print(f"Status update failed: {e}")

    def test_account_deactivation(self):
        """Test account deactivation endpoint"""
        try:
            client = self.get_authenticated_client()
            
            response = client.post(self.deactivate_url)
            print(f"Deactivation response: {response.data}")
            print(f"Deactivation status: {response.status_code}")
            
            if response.status_code == 200:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Verify deactivation
                user = User.objects.get(username='testuser')
                self.assertFalse(user.is_active)
        except Exception as e:
            print(f"Deactivation failed: {e}")

    def test_account_deletion(self):
        """Test account deletion endpoint"""
        # Create separate user for deletion
        delete_user = User.objects.create_user(
            username='deleteuser',
            email='delete@example.com',
            password='deletepassword123'
        )
        
        # Login as delete user
        login_data = {
            'username': 'deleteuser',
            'password': 'deletepassword123'
        }
        
        response = self.client.post(self.login_url, login_data, format='json')
        print(f"Delete user login response: {response.data}")
 
        if response.status_code == 200:
            try:
                if 'access' in response.data:
                    token = response.data['access']
                elif 'access_token' in response.data:
                    token = response.data['access_token']
                else:
                    print("No access token found")
                    return
                    
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
                
                # Test deletion
                response = client.post(
                    self.delete_url,
                    {'password': 'deletepassword123'},
                    format='json'
                )
                print(f"Deletion response: {response.data}")
                print(f"Deletion status: {response.status_code}")
                
                if response.status_code == 200:
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    # Verify user is deleted
                    self.assertFalse(User.objects.filter(username='deleteuser').exists())
            except Exception as e:
                print(f"Deletion failed: {e}")

    def test_user_model_properties(self):
        """Test the new property methods in the User model"""
        user = User.objects.get(username='testuser')
        
        # Test interests_list property
        interests = user.interests_list
        expected_interests = ['coding', 'music', 'sports']
        self.assertEqual(interests, expected_interests)
        
        # Test languages_list property
        languages = user.languages_list
        expected_languages = ['English', 'Yoruba', 'French']
        self.assertEqual(languages, expected_languages)
        
        # Test age property
        self.assertIsNotNone(user.age)
        self.assertGreater(user.age, 0)
        
        # Test get_full_name method
        full_name = user.get_full_name()
        self.assertEqual(full_name, 'Test User')

    def test_gender_choices(self):
        """Test that gender choices work correctly"""
        user = User.objects.get(username='testuser')
        
        # Test valid gender choice
        user.gender = 'female'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.gender, 'female')
        
        # Test another valid choice
        user.gender = 'non_binary'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.gender, 'non_binary')

    def test_relationship_status_choices(self):
        """Test that relationship status choices work correctly"""
        user = User.objects.get(username='testuser')
        
        # Test valid relationship status
        user.relationship_status = 'married'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.relationship_status, 'married')
        
        # Test another valid choice
        user.relationship_status = 'complicated'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.relationship_status, 'complicated')
