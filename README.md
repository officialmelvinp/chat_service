# Chat Service - Enterprise-Grade Real-time Messaging Platform

A comprehensive social messaging platform built with Django REST Framework, featuring real-time messaging, advanced friend management, enterprise-scale performance, and AI-powered content moderation.

> **Portfolio Project Notice**  
> This is a portfolio project developed to demonstrate full-stack development skills, scalable architecture design, and modern web development practices. Built as part of my software engineering journey to showcase expertise in Django, REST APIs, database design, real-time applications, and enterprise-scale system architecture.

##  Features

### **Completed Features**

- **JWT Authentication** - Secure user registration, login, and profile management
- **Advanced Friend System** - Send/accept/reject friend requests with smart user discovery
- **Real-time Messaging** - WebSocket-powered instant messaging with encryption
- **Message Encryption** - End-to-end encryption using RSA + AES hybrid system
- **AI Content Moderation** - Automatic filtering of inappropriate content with confidence scoring
- **Analytics Dashboard** - User engagement tracking and conversation analytics
- **Advanced Search** - Multi-filter message search with caching optimization
- **Background Processing** - Celery-powered webhook integration and task management
- **Rate Limiting** - Smart spam prevention and abuse protection
- **Smart User Search** - Find users with intelligent filtering and pagination
- **Scalable Architecture** - Built to handle millions of concurrent connections
- **Complete API Documentation** - Interactive Swagger UI with 30+ endpoints

### **Coming Soon**
- **Chat Rooms** - Create and join group conversations with admin controls
- **File Sharing** - Image, video, and document sharing with optimization
- **Voice/Video Calls** - WebRTC-powered real-time communication
- **Frontend Interface** - Next.js responsive chat application

## Tech Stack

**Backend:** Django, Django REST Framework, PostgreSQL, Django Channels, Redis, Celery  
**Security:** JWT Authentication, RSA+AES Encryption, AI Content Moderation  
**Performance:** Redis Caching, Database Optimization, Background Task Processing  
**Real-time:** WebSockets, Live Messaging, Typing Indicators  
**Testing:** 100% test coverage with comprehensive test suites  
**Documentation:** Swagger/OpenAPI with interactive testing  
**Monitoring:** Celery Flower, Analytics Dashboard  

## Project Structure

\`\`\`
chat_service/
├── authentication/      # User management and JWT authentication
├── friends/            # Advanced friend management system  
├── messaging/          #  Real-time messaging with encryption & moderation
├── rooms/             # Chat rooms and group messaging (coming soon)
├── common/            # Shared utilities and base models
├── service_chat/      # Django project settings and configuration
├── frontend/          # Next.js chat interface (coming soon)
├── docs/             # Project documentation and API guides
├── venv/             # Python virtual environment
├── .env              # Environment variables
├── manage.py         # Django management script
├── requirements.txt  # Python dependencies
└── README.md         # This file
\`\`\`

##  Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Redis (for caching and Celery)
- Node.js (for frontend)

### Backend Setup
\`\`\`bash
# Clone the repository
git clone https://github.com/yourusername/chat_service.git
cd chat_service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Edit with your database credentials

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start Redis (required for caching and Celery)
redis-server

# Start Celery worker (in new terminal)
celery -A service_chat worker --loglevel=info

# Start Celery beat (in new terminal)
celery -A service_chat beat --loglevel=info

# Start development server
python manage.py runserver
\`\`\`

### Frontend Setup (Coming Soon)
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

## 📚 Documentation

- **API Documentation:** `/swagger/` - Interactive Swagger UI
- **Alternative Docs:** `/redoc/` - ReDoc interface
- **Celery Monitoring:** `http://localhost:5555/` - Flower dashboard
- **Detailed Guides:** `docs/` directory
- **Frontend Guide:** `frontend/README.md` (coming soon)

## 🧪 Testing

\`\`\`bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test authentication
python manage.py test friends
python manage.py test messaging

# Run with coverage
coverage run --source='.' manage.py test
coverage report

# Test specific features
python manage.py test messaging.test_encryption_specific -v 2
python manage.py test messaging.test_advanced_features -v 2
\`\`\`

##  API Endpoints

###  Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/me/` - Get current user profile
- `PUT /api/auth/me/` - Update user profile
- `GET /api/auth/users/` - List all users
- `POST /api/auth/status/` - Update user status
- `POST /api/auth/logout/` - User logout

### 👥 Friends System
- `POST /api/friends/request/send/` - Send friend request
- `POST /api/friends/request/respond/` - Accept/reject friend request
- `DELETE /api/friends/request/cancel/{request_id}/` - Cancel sent request
- `GET /api/friends/list/` - List friends (paginated)
- `GET /api/friends/search/` - Search users (smart filtering)
- `GET /api/friends/pending/` - View pending requests
- `GET /api/friends/mutual/{username}/` - Find mutual friends
- `POST /api/friends/remove/` - Remove friend
- `GET /api/friends/stats/` - Friend statistics

###  Messaging System
- `GET /api/conversations/` - List user conversations (cached & paginated)
- `POST /api/conversations/direct/` - Create direct conversation
- `POST /api/conversations/group/` - Create group conversation
- `GET /api/messages/?conversation_id={id}` - Get conversation messages
- `POST /api/messages/send/` - Send message with background processing
- `POST /api/messages/{id}/react/` - Add reaction to message
- `POST /api/messages/{id}/edit/` - Edit message content
- `POST /api/messages/{id}/mark_read/` - Mark message as read
- `POST /api/messages/bulk_mark_read/` - Bulk mark messages as read
- `GET /api/messages/search/` - Advanced message search with filters

###  Analytics & Background Tasks
- `GET /api/conversation_analytics/{id}/` - Get conversation analytics
- `GET /api/user_engagement/` - Get user engagement metrics
- `POST /api/create_message/` - Create message with background tasks
- `POST /api/bulk_message_cleanup/` - Trigger message cleanup
- `POST /api/generate_analytics/` - Generate analytics report
- `GET /api/task_status/{task_id}/` - Check background task status

###  Rooms (Coming Soon)
- `POST /api/rooms/create/` - Create chat room
- `POST /api/rooms/{room_id}/join/` - Join room
- `GET /api/rooms/` - List available rooms

##  Environment Variables

\`\`\`env
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True

# Database
DATABASE_NAME=chat_service
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis & Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Content Moderation
CONTENT_MODERATION_ENABLED=True
WEBHOOK_TIMEOUT=30
WEBHOOK_MAX_RETRIES=3

# Analytics
ANALYTICS_ENABLED=True
ANALYTICS_BATCH_SIZE=100
\`\`\`

##  Key Features Implemented

###  Enterprise Messaging System
-  **End-to-End Encryption** - RSA + AES hybrid encryption for message security
-  **Real-time Communication** - WebSocket-powered instant messaging
-  **AI Content Moderation** - Automatic filtering with confidence scoring
-  **Advanced Search** - Multi-filter search with caching optimization
-  **Background Processing** - Celery-powered webhook and task management
-  **Performance Optimization** - Redis caching, database indexing, pagination
-  **Message Features** - Reactions, replies, editing, bulk operations

###  Advanced Friend Management
-  **Smart Friend Requests** - Send, accept, reject, and cancel with full state management
-  **Intelligent User Search** - Excludes existing friends and pending requests
-  **Mutual Friends Discovery** - Find common connections between users
-  **Scalable Pagination** - Custom pagination for different use cases
-  **Admin Interface** - Comprehensive management with bulk operations
-  **100% Test Coverage** - 26+ comprehensive test cases

###  Authentication System
-  **JWT Security** - Secure token-based authentication
-  **User Profiles** - Complete profile management
-  **Status Updates** - Real-time user status tracking
-  **Admin Panel** - Full user management interface

###  Analytics & Monitoring
-  **User Engagement Tracking** - Comprehensive analytics dashboard
-  **Conversation Analytics** - Message patterns and activity metrics
-  **Performance Monitoring** - Celery Flower integration
-  **Rate Limiting** - Smart spam prevention and abuse protection

##  API Documentation

### Swagger UI
- **Development:** [http://localhost:8000/swagger/](http://localhost:8000/swagger/)
- **Production:** [https://your-deployed-app.com/swagger/](https://your-deployed-app.com/swagger/)

**How to use Swagger UI:**
1. Browse available endpoints
2. Click "Authorize" button
3. Enter `Bearer your_access_token`
4. Click "Try it out" on any endpoint
5. Fill in parameters and execute

### Alternative Documentation
- **ReDoc:** [http://localhost:8000/redoc/](http://localhost:8000/redoc/)
- **OpenAPI JSON:** [http://localhost:8000/swagger.json](http://localhost:8000/swagger.json)
- **Celery Monitoring:** [http://localhost:5555/](http://localhost:5555/)

##  Deployment

### Using Docker (Coming Soon)
\`\`\`bash
docker-compose up
\`\`\`

### Manual Deployment
See `docs/deployment.md` for detailed deployment instructions.

##  Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Contact

- **GitHub:** [@officialmelvinp](https://github.com/officialmelvinp)
- **Email:** [ajayiadeboye2002@gmail.com](mailto:ajayiadeboye2002@gmail.com)
- **LinkedIn:** [adeboye-melvin](https://www.linkedin.com/in/adeboye-melvin/)

##  Roadmap

- [x] User Authentication System
- [x] Advanced Friend Management
- [x] Real-time Messaging with WebSockets
- [x] Message Encryption & Security
- [x] AI Content Moderation
- [x] Analytics & Performance Monitoring
- [x] Background Task Processing
- [ ] Group Chat Rooms
- [ ] File Sharing with Optimization
- [ ] Voice/Video Calls
- [ ] Frontend Interface (Next.js)
- [ ] Mobile App (React Native)
- [ ] Push Notifications

---

⭐ **Star this repo if you find it helpful!**

##  Business Potential

This platform demonstrates enterprise-grade architecture and can be positioned as:
- **Dating Platform** - Location-based matching with secure messaging
- **Social Network** - Friend management with real-time communication
- **Enterprise Chat** - Secure messaging with content moderation
- **Community Platform** - Group discussions with advanced moderation

Perfect for showcasing to investors or potential employers! 
