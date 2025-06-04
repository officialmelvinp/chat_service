import os
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.fernet import Fernet
import json
from django.conf import settings
from django.db import models

class MessageEncryption:
    """Handle message encryption and decryption"""
    
    @staticmethod
    def generate_key_pair():
        """Generate RSA key pair for asymmetric encryption"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Get public key
        public_key = private_key.public_key()
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    @staticmethod
    def encrypt_message(message, public_key_pem):
        """Encrypt message using hybrid encryption"""
        # Generate symmetric key
        symmetric_key = Fernet.generate_key()
        cipher = Fernet(symmetric_key)
        
        # Encrypt message with symmetric key
        encrypted_message = cipher.encrypt(message.encode())
        
        # Load public key
        public_key = serialization.load_pem_public_key(public_key_pem)
        
        # Encrypt symmetric key with public key
        encrypted_key = public_key.encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Return both encrypted message and encrypted key
        return {
            'encrypted_message': base64.b64encode(encrypted_message).decode(),
            'encrypted_key': base64.b64encode(encrypted_key).decode()
        }
    
    @staticmethod
    def decrypt_message(encrypted_data, private_key_pem):
        """Decrypt message using hybrid encryption"""
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None
        )
        
        # Decode encrypted data
        encrypted_message = base64.b64decode(encrypted_data['encrypted_message'])
        encrypted_key = base64.b64decode(encrypted_data['encrypted_key'])
        
        # Decrypt symmetric key
        symmetric_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt message
        cipher = Fernet(symmetric_key)
        decrypted_message = cipher.decrypt(encrypted_message).decode()
        
        return decrypted_message
    
    @staticmethod
    def encrypt_message_content(content):
        """Encrypt message content using server key"""
        # Use a server-side key for encryption
        key = getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)
        if not key:
            # Generate a key if not available
            key = Fernet.generate_key()
        
        cipher = Fernet(key)
        encrypted_content = cipher.encrypt(content.encode())
        
        return base64.b64encode(encrypted_content).decode()
    
    @staticmethod
    def decrypt_message_content(encrypted_content):
        """Decrypt message content using server key"""
        key = getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("Encryption key not found")
        
        cipher = Fernet(key)
        decrypted_content = cipher.decrypt(base64.b64decode(encrypted_content))
        
        return decrypted_content.decode()


class UserKeyManager:
    """Manage user encryption keys"""
    
    @staticmethod
    def get_or_create_keys(user):
        """Get existing keys or create new ones for user"""
        from .models import UserEncryptionKey
        
        try:
            key_obj = UserEncryptionKey.objects.get(user=user)
            # Convert binary fields back to bytes for consistency
            private_key = bytes(key_obj.private_key) if isinstance(key_obj.private_key, memoryview) else key_obj.private_key
            public_key = bytes(key_obj.public_key) if isinstance(key_obj.public_key, memoryview) else key_obj.public_key
            return private_key, public_key
        except UserEncryptionKey.DoesNotExist:
            # Generate new keys
            private_key, public_key = MessageEncryption.generate_key_pair()
            
            # Save to database
            key_obj = UserEncryptionKey.objects.create(
                user=user,
                private_key=private_key,
                public_key=public_key
            )
            
            return private_key, public_key
    
    @staticmethod
    def get_public_key(user):
        """Get user's public key for encryption"""
        from .models import UserEncryptionKey
        
        try:
            key_obj = UserEncryptionKey.objects.get(user=user)
            # Convert binary field back to bytes for consistency
            public_key = bytes(key_obj.public_key) if isinstance(key_obj.public_key, memoryview) else key_obj.public_key
            return public_key
        except UserEncryptionKey.DoesNotExist:
            # Generate keys if they don't exist
            private_key, public_key = UserKeyManager.get_or_create_keys(user)
            return public_key
    
    @staticmethod
    def encrypt_for_user(message, recipient):
        """Encrypt message for a specific user"""
        public_key = UserKeyManager.get_public_key(recipient)
        return MessageEncryption.encrypt_message(message, public_key)
    
    @staticmethod
    def decrypt_from_user(encrypted_data, recipient):
        """Decrypt message sent to a specific user"""
        private_key, _ = UserKeyManager.get_or_create_keys(recipient)
        return MessageEncryption.decrypt_message(encrypted_data, private_key)
