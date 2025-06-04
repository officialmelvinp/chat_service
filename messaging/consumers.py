import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import (
    Conversation, Message, MessageType, MessageStatus,
    TypingIndicator, UserOnlineStatus
)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Reject connection if user is not authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Set user as online
        await self.set_user_online()
        
        # Get conversation ID from URL route
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        
        # Check if user is participant in this conversation
        is_participant = await self.is_conversation_participant()
        if not is_participant:
            await self.close()
            return
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send user online status to group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online',
                'timestamp': timezone.now().isoformat(),
            }
        )
        
        # Mark messages as delivered
        await self.mark_messages_delivered()

    async def disconnect(self, close_code):
        if hasattr(self, 'conversation_group_name'):
            # Leave conversation group
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
            
            # Stop typing indicator if active
            await self.stop_typing_indicator()
            
            # Set user as offline
            await self.set_user_offline()
            
            # Send user offline status to group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'user_offline',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status': 'offline',
                    'timestamp': timezone.now().isoformat(),
                }
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            await self.handle_chat_message(data)
        elif message_type == 'typing_start':
            await self.handle_typing_start()
        elif message_type == 'typing_stop':
            await self.handle_typing_stop()
        elif message_type == 'mark_read':
            await self.handle_mark_read(data)
        elif message_type == 'reaction':
            await self.handle_reaction(data)

    async def handle_chat_message(self, data):
        content = data.get('message')
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to')
        
        # Save message to database
        message = await self.save_message(content, message_type, reply_to_id)
        
        # Send message to conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'chat_message',
                'message_id': message.id,
                'message': content,
                'message_type': message_type,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'timestamp': message.created_at.isoformat(),
                'reply_to': reply_to_id,
            }
        )

    async def handle_typing_start(self):
        # Save typing indicator to database
        await self.start_typing_indicator()
        
        # Send typing indicator to conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'typing': True,
                'timestamp': timezone.now().isoformat(),
            }
        )

    async def handle_typing_stop(self):
        # Remove typing indicator from database
        await self.stop_typing_indicator()
        
        # Send typing stopped to conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'typing': False,
                'timestamp': timezone.now().isoformat(),
            }
        )

    async def handle_mark_read(self, data):
        message_id = data.get('message_id')
        
        # Mark message as read in database
        success = await self.mark_message_read(message_id)
        
        if success:
            # Send read receipt to conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat(),
                }
            )

    async def handle_reaction(self, data):
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        
        # Save reaction to database
        success = await self.save_reaction(message_id, emoji)
        
        if success:
            # Send reaction to conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_reaction',
                    'message_id': message_id,
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'emoji': emoji,
                    'timestamp': timezone.now().isoformat(),
                }
            )

    # Channel layer message handlers
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'message_type': event['message_type'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'timestamp': event['timestamp'],
            'reply_to': event.get('reply_to'),
        }))

    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'user_id': event['user_id'],
            'username': event['username'],
            'typing': event['typing'],
            'timestamp': event['timestamp'],
        }))

    async def read_receipt(self, event):
        # Send read receipt to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp'],
        }))

    async def message_reaction(self, event):
        # Send message reaction to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message_reaction',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'emoji': event['emoji'],
            'timestamp': event['timestamp'],
        }))

    async def user_online(self, event):
        # Send user online status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status'],
            'timestamp': event['timestamp'],
        }))

    async def user_offline(self, event):
        # Send user offline status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status'],
            'timestamp': event['timestamp'],
        }))

    # Database access methods
    @database_sync_to_async
    def is_conversation_participant(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.is_participant(self.user)
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, message_type_str, reply_to_id=None):
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        # Map string message type to enum
        message_type = MessageType.TEXT
        if message_type_str in [choice[0] for choice in MessageType.choices]:
            message_type = message_type_str
        
        # Get reply_to message if provided
        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id)
            except Message.DoesNotExist:
                pass
        
        # Create and save message
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            message_type=message_type,
            content=content,
            status=MessageStatus.SENT,
            reply_to=reply_to
        )
        
        return message

    @database_sync_to_async
    def mark_message_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            
            # Only mark as read if user is a recipient
            if message.sender != self.user and message.conversation.is_participant(self.user):
                message.mark_as_read()
                return True
            return False
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_messages_delivered(self):
        conversation = Conversation.objects.get(id=self.conversation_id)
        
        # Mark all unread messages from others as delivered
        unread_messages = Message.objects.filter(
            conversation=conversation,
            status=MessageStatus.SENT
        ).exclude(sender=self.user)
        
        for message in unread_messages:
            message.mark_as_delivered()

    @database_sync_to_async
    def save_reaction(self, message_id, emoji):
        from django.db import IntegrityError
        
        try:
            message = Message.objects.get(id=message_id)
            
            # Check if user is participant in the conversation
            if not message.conversation.is_participant(self.user):
                return False
            
            # Create or update reaction
            try:
                message.reactions.create(user=self.user, emoji=emoji)
                return True
            except IntegrityError:
                # User already reacted with this emoji
                return False
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def start_typing_indicator(self):
        conversation = Conversation.objects.get(id=self.conversation_id)
        TypingIndicator.start_typing(conversation, self.user)

    @database_sync_to_async
    def stop_typing_indicator(self):
        if hasattr(self, 'conversation_id'):
            try:
                conversation = Conversation.objects.get(id=self.conversation_id)
                TypingIndicator.stop_typing(conversation, self.user)
            except Conversation.DoesNotExist:
                pass

    @database_sync_to_async
    def set_user_online(self):
        UserOnlineStatus.set_online(self.user)

    @database_sync_to_async
    def set_user_offline(self):
        UserOnlineStatus.set_offline(self.user)
