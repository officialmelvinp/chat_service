# Chat Service - Real-time Messaging Platform

A comprehensive chat application built with Django REST Framework and React, featuring real-time messaging, advanced friend management, and chat rooms.

> **Portfolio Project Notice**  
> This is a portfolio project developed to demonstrate full-stack development skills, scalable architecture design, and modern web development practices. Built as part of my software engineering journey to showcase expertise in Django, REST APIs, database design, and real-time applications.


##  Features

- **JWT Authentication** - Secure user registration, login, and profile management
- **Advanced Friend System** - Send/accept/reject friend requests with smart user discovery
- **Real-time Messaging** - WebSocket-powered instant messaging (coming soon)
- **Chat Rooms** - Create and join group conversations (coming soon)
- **Smart User Search** - Find users with intelligent filtering
- **Scalable Architecture** - Built to handle millions of connections
- **Complete API Documentation** - Interactive Swagger UI with full endpoint coverage

##  Tech Stack

**Backend:** Django, Django REST Framework, PostgreSQL, Django Channels, JWT Authentication  
**Frontend:** Next.js, React, WebSocket client, responsive design (coming soon)  
**Testing:** 100% test coverage with comprehensive test suites  
**Documentation:** Swagger/OpenAPI with interactive testing  

##  Project Structure

\`\`\`
chat_service/
├── authentication/      # User management and JWT authentication
├── friends/            # Advanced friend management system
├── messaging/          # Direct messaging between users (coming soon)
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

# Start development server
python manage.py runserver
\`\`\`

### Frontend Setup (Coming Soon)
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

##  Documentation

- **API Documentation:** `/swagger/` - Interactive Swagger UI
- **Alternative Docs:** `/redoc/` - ReDoc interface
- **Detailed Guides:** `docs/` directory
- **Frontend Guide:** `frontend/README.md` (coming soon)

##  Testing

\`\`\`bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test authentication
python manage.py test friends

# Run with coverage
coverage run --source='.' manage.py test
coverage report
\`\`\`

## 🔌 API Endpoints

###  Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/me/` - Get current user profile
- `PUT /api/auth/me/` - Update user profile
- `GET /api/auth/users/` - List all users
- `POST /api/auth/status/` - Update user status
- `POST /api/auth/logout/` - User logout

###  Friends System
- `POST /api/friends/request/` - Send friend request
- `POST /api/friends/accept/{request_id}/` - Accept friend request
- `POST /api/friends/reject/{request_id}/` - Reject friend request
- `DELETE /api/friends/cancel/{request_id}/` - Cancel sent request
- `GET /api/friends/` - List friends (paginated)
- `GET /api/friends/search/` - Search users (smart filtering)
- `GET /api/friends/requests/pending/` - View pending requests
- `GET /api/friends/mutual/{user_id}/` - Find mutual friends
- `DELETE /api/friends/remove/{friend_id}/` - Remove friend

###  Messaging (Coming Soon)
- `GET /api/messages/` - List conversations
- `POST /api/messages/send/` - Send message
- `GET /api/messages/{conversation_id}/` - Get conversation history

###  Rooms (Coming Soon)
- `POST /api/rooms/create/` - Create chat room
- `POST /api/rooms/{room_id}/join/` - Join room
- `GET /api/rooms/` - List available rooms

##  Environment Variables

\`\`\`env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_NAME=chat_service
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
\`\`\`

##  Key Features Implemented

### Advanced Friend Management
-  **Smart Friend Requests** - Send, accept, reject, and cancel with full state management
-  **Intelligent User Search** - Excludes existing friends and pending requests
-  **Mutual Friends Discovery** - Find common connections between users
-  **Scalable Pagination** - Custom pagination for different use cases
-  **Admin Interface** - Comprehensive management with bulk operations
-  **100% Test Coverage** - 26+ comprehensive test cases

### Authentication System
-  **JWT Security** - Secure token-based authentication
-  **User Profiles** - Complete profile management
-  **Status Updates** - Real-time user status tracking
-  **Admin Panel** - Full user management interface

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
- [ ] Real-time Messaging with WebSockets
- [ ] Group Chat Rooms
- [ ] File Sharing
- [ ] Voice/Video Calls
- [ ] Mobile App (React Native)
- [ ] Push Notifications

---

⭐ **Star this repo if you find it helpful!**
