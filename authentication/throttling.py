from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

class MessageSendRateThrottle(UserRateThrottle):
    scope = 'message_send'