from django.test import TestCase
from django.contrib.auth import get_user_model
from .encryption import MessageEncryption, UserKeyManager
from .models import Conversation, Message, MessageType

User = get_user_model()


class EncryptionSpecificTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )

    def test_key_pair_generation(self):
        """Test RSA key pair generation"""
        private_key, public_key = MessageEncryption.generate_key_pair()
        
        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        self.assertIn(b'BEGIN PRIVATE KEY', private_key)
        self.assertIn(b'BEGIN PUBLIC KEY', public_key)

    def test_message_encryption_decryption(self):
        """Test full encryption/decryption cycle"""
        # Generate keys for recipient
        private_key, public_key = MessageEncryption.generate_key_pair()
        
        # Test message
        original_message = "This is a secret message!"
        
        # Encrypt message
        encrypted_data = MessageEncryption.encrypt_message(original_message, public_key)
        
        self.assertIn('encrypted_message', encrypted_data)
        self.assertIn('encrypted_key', encrypted_data)
        
        # Decrypt message
        decrypted_message = MessageEncryption.decrypt_message(encrypted_data, private_key)
        
        self.assertEqual(original_message, decrypted_message)

    def test_user_key_manager(self):
        """Test user key management"""
        # Get or create keys for user1
        private_key1, public_key1 = UserKeyManager.get_or_create_keys(self.user1)
        
        self.assertIsNotNone(private_key1)
        self.assertIsNotNone(public_key1)
        
        # Get keys again - should return same keys
        private_key2, public_key2 = UserKeyManager.get_or_create_keys(self.user1)
        
        self.assertEqual(private_key1, private_key2)
        self.assertEqual(public_key1, public_key2)

    def test_get_public_key(self):
        """Test getting user's public key"""
        # This should create keys if they don't exist
        public_key = UserKeyManager.get_public_key(self.user1)
        
        self.assertIsNotNone(public_key)
        self.assertIn(b'BEGIN PUBLIC KEY', public_key)
