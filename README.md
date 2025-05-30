Chat Service - Real-time Messaging Platform

A comprehensive chat application built with Django REST Framework and React, featuring real-time messaging, friend systems, and chat rooms.

##  Features

Real-time Messaging - WebSocket-powered instant messaging
Friend System - Send/accept friend requests
Chat Rooms- Create and join group conversations  
User Authentication - JWT-based secure authentication
REST API - Comprehensive API with Swagger documentation

##  Tech Stack

Backend:
Django & Django REST Framework
PostgreSQL
Django Channels (WebSockets)
JWT Authentication

Frontend:
Next.js/React
WebSocket client
Responsive design

##  Project Structure

chat_service/
├── authentication/      # User management and JWT authentication
├── messaging/          # Direct messaging between users
├── friends/           # Friend requests and relationships
├── rooms/             # Chat rooms and group messaging
├── common/            # Shared utilities and base models
├── service_chat/      # Django project settings and configuration
├── frontend/          # Next.js chat interface (coming soon)
├── docs/             # Project documentation and API guides
├── venv/             # Python virtual environment
├── .env              # Environment variables
├── manage.py         # Django management script
├── requirements.txt  # Python dependencies
└── README.md         # This file


## Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL
- Node.js (for frontend)

### Backend Setup
```bash
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


### Frontend Setup (Coming Soon)

```shellscript
cd frontend
npm install
npm run dev
```



## Documentation

- **API Documentation**: Visit `/api/docs/` when the server is running
- **Detailed Docs**: See the `docs/` folder for comprehensive guides
- **Frontend Guide**: Check `frontend/README.md` for frontend-specific instructions


##  Testing

```shellscript
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test authentication
```

## API Endpoints

### Authentication

- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh JWT token


### Messaging

- `GET /api/messages/` - Get user's conversations
- `POST /api/messages/send/` - Send a message
- `GET /api/messages/{conversation_id}/` - Get conversation history


### Friends

- `POST /api/friends/request/` - Send friend request
- `POST /api/friends/accept/{request_id}/` - Accept friend request
- `GET /api/friends/` - Get friends list


### Rooms

- `POST /api/rooms/create/` - Create chat room
- `POST /api/rooms/{room_id}/join/` - Join room
- `GET /api/rooms/` - Get user's rooms


## Environment Variables

Create a `.env` file with:

SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_NAME=chat_service
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Deployment

### Using Docker (Coming Soon)

```shellscript
docker-compose up
```

### Manual Deployment

See `docs/deployment.md` for detailed deployment instructions.

##  Contact

- **GitHub**: [@officialmelvinp](https://github.com/officialmelvinp)
- **Email**: [ajayiadeboye2002@gmail.cm](ajayiadeboye2002@gmail.com)
- **LinkedIn**: [adeboye-melvin](https://www.linkedin.com/in/adeboye-melvin/)

