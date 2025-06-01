Chat Service - Real-time Messaging Platform

A comprehensive chat application built with Django REST Framework and React, featuring real-time messaging, friend systems, and chat rooms.

## Features

Real-time WebSocket-powered messaging, friend requests, group chat rooms, JWT-secured user authentication, and a fully documented REST API.

## Tech Stack

Backend: Django, Django REST Framework, PostgreSQL, Django Channels, JWT Authentication
Frontend: Next.js, React, WebSocket client, responsive design

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

Python 3.8+, PostgreSQL, Node.js (for frontend)

### Backend Setup

```
git clone https://github.com/yourusername/chat_service.git
cd chat_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend Setup (Coming Soon)

```
cd frontend
npm install
npm run dev
```

## Documentation

API docs at `/api/docs/`, detailed guides in `docs/`, frontend guide in `frontend/README.md`

## Testing

```
python manage.py test
python manage.py test authentication
```

## API Endpoints

### Authentication

POST /api/auth/register/, POST /api/auth/login/, POST /api/auth/refresh/, GET /api/auth/me/, PUT /api/auth/me/, GET /api/auth/users/, POST /api/auth/status/, POST /api/auth/logout/

### Messaging

GET /api/messages/, POST /api/messages/send/, GET /api/messages/{conversation\_id}/

### Friends

POST /api/friends/request/, POST /api/friends/accept/{request\_id}/, GET /api/friends/

### Rooms

POST /api/rooms/create/, POST /api/rooms/{room\_id}/join/, GET /api/rooms/

## Environment Variables

SECRET\_KEY=your-secret-key
DEBUG=True
DATABASE\_NAME=chat\_service
DATABASE\_USER=postgres
DATABASE\_PASSWORD=your-password
DATABASE\_HOST=localhost
DATABASE\_PORT=5432

## Contributing

Fork the repo, create a feature branch, commit changes, push, and open a pull request.

## License

MIT License — see LICENSE file.

## Deployment

### Using Docker (Coming Soon)

```
docker-compose up
```

## API Documentation

Swagger at [http://localhost:8000/swagger/](http://localhost:8000/swagger/), production at [https://your-deployed-app.com/swagger/](https://your-deployed-app.com/swagger/)

To use Swagger UI: browse endpoints, click Authorize, enter `Bearer your_access_token`, click "Try it out," fill parameters, and execute.

Alternative views: ReDoc at [http://localhost:8000/redoc/](http://localhost:8000/redoc/), OpenAPI JSON at [http://localhost:8000/swagger.json](http://localhost:8000/swagger.json)

### Manual Deployment

See `docs/deployment.md`.

## Contact

GitHub: [@officialmelvinp](https://github.com/officialmelvinp)
Email: [ajayiadeboye2002@gmail.com](mailto:ajayiadeboye2002@gmail.com)
LinkedIn: [adeboye-melvin](https://www.linkedin.com/in/adeboye-melvin/)
