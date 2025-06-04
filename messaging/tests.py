from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from .models import (
    Conversation, ConversationParticipant, Message, MessageReaction,
    TypingIndicator, UserOnlineStatus, ConversationType, MessageType,
    MessageStatus, ParticipantRole
)

User = get_user_model()


class ConversationModelTest(TestCase):
    def setUp(self):
        """Set up test users"""
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
        self.user3 = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='testpass123'
        )

    def test_create_direct_conversation(self):
        """Test creating a direct conversation between two users"""
        conversation, created = Conversation.get_or_create_direct_conversation(
            self.user1, self.user2
        )
        
        self.assertTrue(created)
        self.assertEqual(conversation.conversation_type, ConversationType.DIRECT)
        self.assertEqual(conversation.participant1, self.user1)
        self.assertEqual(conversation.participant2, self.user2)
        self.assertTrue(conversation.is_active)

    def test_direct_conversation_participant_order(self):
        """Test that participants are ordered by ID consistently"""
        # Create conversation with users in different order
        conv1, _ = Conversation.get_or_create_direct_conversation(self.user2, self.user1)
        conv2, _ = Conversation.get_or_create_direct_conversation(self.user1, self.user2)
        
        # Should be the same conversation
        self.assertEqual(conv1.id, conv2.id)
        # Lower ID should always be participant1
        self.assertEqual(conv1.participant1.id, min(self.user1.id, self.user2.id))
        self.assertEqual(conv1.participant2.id, max(self.user1.id, self.user2.id))

    def test_prevent_self_conversation(self):
        """Test that users cannot create conversations with themselves"""
        with self.assertRaises(ValidationError):
            Conversation.get_or_create_direct_conversation(self.user1, self.user1)

    def test_create_group_conversation(self):
        """Test creating a group conversation"""
        conversation = Conversation.create_group_conversation(
            creator=self.user1,
            title="Test Group",
            description="A test group chat",
            participants=[self.user2, self.user3]
        )
        
        self.assertEqual(conversation.conversation_type, ConversationType.GROUP)
        self.assertEqual(conversation.title, "Test Group")
        self.assertEqual(conversation.created_by, self.user1)
        self.assertEqual(conversation.get_participant_count(), 3)  # Creator + 2 participants

    def test_group_conversation_validation(self):
        """Test group conversation validation"""
        with self.assertRaises(ValidationError):
            # Group conversation without title should fail
            Conversation.objects.create(
                conversation_type=ConversationType.GROUP,
                created_by=self.user1
            )

    def test_get_user_conversations(self):
        """Test retrieving all conversations for a user"""
        # Create direct conversation
        direct_conv, _ = Conversation.get_or_create_direct_conversation(self.user1, self.user2)
        
        # Create group conversation
        group_conv = Conversation.create_group_conversation(
            creator=self.user1,
            title="Test Group",
            participants=[self.user2]
        )
        
        # Get user1's conversations
        conversations = Conversation.get_user_conversations(self.user1)
        
        self.assertEqual(conversations.count(), 2)
        self.assertIn(direct_conv, conversations)
        self.assertIn(group_conv, conversations)

    def test_conversation_participants_management(self):
        """Test adding and removing participants from group conversations"""
        conversation = Conversation.create_group_conversation(
            creator=self.user1,
            title="Test Group"
        )
        
        # Add participant
        participant = conversation.add_participant(self.user2, added_by=self.user1)
        self.assertTrue(participant.is_active)
        self.assertEqual(participant.role, ParticipantRole.MEMBER)
        
        # Remove participant
        conversation.remove_participant(self.user2, removed_by=self.user1)
        participant.refresh_from_db()
        self.assertFalse(participant.is_active)
        self.assertIsNotNone(participant.left_at)

    def test_conversation_participant_limits(self):
        """Test conversation participant limits"""
        conversation = Conversation.create_group_conversation(
            creator=self.user1,
            title="Test Group"
        )
        conversation.max_participants = 2  # Set low limit for testing
        conversation.save()
        
        # Add one participant (should work)
        conversation.add_participant(self.user2)
        
        # Try to add another (should fail due to limit)
        with self.assertRaises(ValidationError):
            conversation.add_participant(self.user3)


class MessageModelTest(TestCase):
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
        
        self.conversation, _ = Conversation.get_or_create_direct_conversation(
            self.user1, self.user2
        )

    def test_create_text_message(self):
        """Test creating a text message"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.TEXT,
            content="Hello, Bob!"
        )
        
        self.assertEqual(message.content, "Hello, Bob!")
        self.assertEqual(message.status, MessageStatus.SENT)
        self.assertFalse(message.is_deleted)
        self.assertFalse(message.is_edited)

    def test_message_validation(self):
        """Test message validation"""
        # Text message without content should fail
        with self.assertRaises(ValidationError):
            message = Message(
                conversation=self.conversation,
                sender=self.user1,
                message_type=MessageType.TEXT,
                content=""
            )
            message.clean()

    def test_message_status_updates(self):
        """Test message status transitions"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.TEXT,
            content="Test message"
        )
        
        # Mark as delivered
        message.mark_as_delivered()
        self.assertEqual(message.status, MessageStatus.DELIVERED)
        self.assertIsNotNone(message.delivered_at)
        
        # Mark as read
        message.mark_as_read()
        self.assertEqual(message.status, MessageStatus.READ)
        self.assertIsNotNone(message.read_at)

    def test_message_editing(self):
        """Test message editing functionality"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.TEXT,
            content="Original message"
        )
        
        # Edit the message
        message.edit_content("Edited message")
        
        self.assertEqual(message.content, "Edited message")
        self.assertTrue(message.is_edited)
        self.assertIsNotNone(message.edited_at)

    def test_message_soft_delete(self):
        """Test soft deletion of messages"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.TEXT,
            content="Message to delete"
        )
        
        # Soft delete the message
        message.soft_delete()
        
        self.assertTrue(message.is_deleted)
        self.assertIsNotNone(message.deleted_at)

    def test_message_replies(self):
        """Test message reply functionality"""
        original_message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.TEXT,
            content="Original message"
        )
        
        reply_message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            message_type=MessageType.TEXT,
            content="Reply to original",
            reply_to=original_message
        )
        
        self.assertTrue(reply_message.is_reply)
        self.assertEqual(reply_message.reply_to, original_message)
        self.assertIn(reply_message, original_message.get_replies())

    def test_file_message(self):
        """Test creating a message with file attachment"""
        # Create a simple test file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"file content",
            content_type="text/plain"
        )
        
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.FILE,
            file=test_file
        )
        
        self.assertEqual(message.message_type, MessageType.FILE)
        self.assertIsNotNone(message.file)
        self.assertIsNotNone(message.file_name)

    def test_location_message(self):
        """Test creating a location message"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.LOCATION,
            latitude=40.7128,
            longitude=-74.0060,
            location_name="New York City"
        )
        
        self.assertEqual(message.message_type, MessageType.LOCATION)
        self.assertEqual(float(message.latitude), 40.7128)
        self.assertEqual(float(message.longitude), -74.0060)
        self.assertEqual(message.location_name, "New York City")


class MessageReactionTest(TestCase):
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
        
        self.conversation, _ = Conversation.get_or_create_direct_conversation(
            self.user1, self.user2
        )
        
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_type=MessageType.TEXT,
            content="React to this message!"
        )

    def test_add_reaction(self):
        """Test adding a reaction to a message"""
        reaction = MessageReaction.objects.create(
            message=self.message,
            user=self.user2,
            emoji="👍"
        )
        
        self.assertEqual(reaction.emoji, "👍")
        self.assertEqual(reaction.user, self.user2)
        self.assertIn(reaction, self.message.reactions.all())

    def test_unique_user_emoji_reaction(self):
        """Test that users can't add the same emoji reaction twice"""
        MessageReaction.objects.create(
            message=self.message,
            user=self.user2,
            emoji="👍"
        )
        
        # Try to add the same reaction again
        with self.assertRaises(Exception):  # Should raise IntegrityError
            MessageReaction.objects.create(
                message=self.message,
                user=self.user2,
                emoji="👍"
            )


class TypingIndicatorTest(TestCase):
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
        
        self.conversation, _ = Conversation.get_or_create_direct_conversation(
            self.user1, self.user2
        )

    def test_start_typing(self):
        """Test starting typing indicator"""
        indicator = TypingIndicator.start_typing(self.conversation, self.user1)
        
        self.assertEqual(indicator.conversation, self.conversation)
        self.assertEqual(indicator.user, self.user1)
        self.assertIsNotNone(indicator.started_at)

    def test_stop_typing(self):
        """Test stopping typing indicator"""
        # Start typing
        TypingIndicator.start_typing(self.conversation, self.user1)
        
        # Verify it exists
        self.assertTrue(
            TypingIndicator.objects.filter(
                conversation=self.conversation,
                user=self.user1
            ).exists()
        )
        
        # Stop typing
        TypingIndicator.stop_typing(self.conversation, self.user1)
        
        # Verify it's removed
        self.assertFalse(
            TypingIndicator.objects.filter(
                conversation=self.conversation,
                user=self.user1
            ).exists()
        )

    def test_get_typing_users(self):
        """Test getting currently typing users"""
        # Start typing for user1
        TypingIndicator.start_typing(self.conversation, self.user1)
        
        typing_users = TypingIndicator.get_typing_users(self.conversation)
        self.assertEqual(typing_users.count(), 1)
        self.assertEqual(typing_users.first().user, self.user1)


class UserOnlineStatusTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )

    def test_set_user_online(self):
        """Test setting user as online"""
        status = UserOnlineStatus.set_online(self.user)
        
        self.assertTrue(status.is_online)
        self.assertIsNotNone(status.last_seen)

    def test_set_user_offline(self):
        """Test setting user as offline"""
        # First set online
        UserOnlineStatus.set_online(self.user)
        
        # Then set offline
        UserOnlineStatus.set_offline(self.user)
        
        status = UserOnlineStatus.objects.get(user=self.user)
        self.assertFalse(status.is_online)

    def test_get_online_users(self):
        """Test getting all online users"""
        user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )
        
        # Set both users online
        UserOnlineStatus.set_online(self.user)
        UserOnlineStatus.set_online(user2)
        
        online_users = UserOnlineStatus.get_online_users()
        self.assertEqual(online_users.count(), 2)

    def test_status_message(self):
        """Test custom status messages"""
        status = UserOnlineStatus.set_online(self.user)
        status.status_message = "Busy"
        status.save()
        
        self.assertEqual(status.status_message, "Busy")


class ConversationParticipantTest(TestCase):
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
        
        self.conversation = Conversation.create_group_conversation(
            creator=self.user1,
            title="Test Group"
        )

    def test_participant_permissions(self):
        """Test participant role permissions"""
        # Get the creator (should be admin)
        admin_participant = self.conversation.participants.get(user=self.user1)
        self.assertEqual(admin_participant.role, ParticipantRole.ADMIN)
        self.assertTrue(admin_participant.can_add_participants())
        self.assertTrue(admin_participant.can_remove_participants())
        
        # Add a regular member
        member_participant = self.conversation.add_participant(self.user2)
        self.assertEqual(member_participant.role, ParticipantRole.MEMBER)
        self.assertFalse(member_participant.can_add_participants())
        self.assertFalse(member_participant.can_remove_participants())

    def test_participant_muting(self):
        """Test participant muting functionality"""
        participant = self.conversation.add_participant(self.user2)
        
        # Mute participant
        participant.is_muted = True
        participant.muted_until = timezone.now() + timedelta(hours=1)
        participant.save()
        
        self.assertTrue(participant.is_muted)
        self.assertIsNotNone(participant.muted_until)
