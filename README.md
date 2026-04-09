# OpenClaw Library Management System

A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.

## 🎯 Features

- **Authentication & Authorization**: JWT-based authentication with role-based access control
- **User Management**: User registration, profile management, and account deactivation
- **Book Management**: CRUD operations for books with availability tracking
- **Borrowing System**: Book borrowing, returning, and fine calculation
- **Search & Filtering**: Advanced search capabilities with pagination
- **Redis Caching**: Performance optimization with Redis caching layer
- **Background Jobs**: Asynchronous task processing with Celery
- **Audit Logging**: Comprehensive user action tracking
- **Production Ready**: Dockerized deployment with health checks

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis
- **Queue**: Celery with Redis broker
- **Architecture**: Clean Architecture (Controller → Service → Repository)
- **API**: RESTful with OpenAPI documentation

## 📁 Project Structure

```
openclaw_library_management_system/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config/              # Configuration management
│   ├── controllers/         # API endpoints
│   ├── services/           # Business logic
│   ├── repositories/       # Data access layer
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── middleware/        # Custom middleware
│   ├── utils/            # Utility functions
│   └── exceptions/       # Custom exceptions
├── tests/                 # Test suite
├── alembic/              # Database migrations
├── docker/               # Docker configuration
├── scripts/              # Utility scripts
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── docker-compose.yml   # Docker Compose setup
└── README.md            # This file
```

## 🚀 Getting Started
## 🗄️ Database Setup

### Initial Setup
```bash
# Create database (if not using Docker)
createdb library_db

# Run migrations
alembic upgrade head

# Create admin user (optional)
python scripts/create_admin.py
```

### Migration Commands
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show migration history
alembic history

# Show current revision
alembic current
```

### Database Health
- Health endpoint: `GET /health/database`
- Full health check: `GET /health/full`
- Basic health: `GET /health`


### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/dehusnain-collab/openclaw_library_management_system.git
cd openclaw_library_management_system
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the application:
```bash
uvicorn app.main:app --reload
```

### Docker Setup

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📚 API Documentation

Once the application is running, access the API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🧪 Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/

# Run specific test module
pytest tests/test_auth.py -v
```

## 🔧 Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **mypy** for type checking

```bash
# Format code
black app/

# Sort imports
isort app/

# Run linting
flake8 app/

# Type checking
mypy app/
```

### Git Workflow

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and commit:
```bash
git add .
git commit -m "feat: description of changes"
```

3. Push to remote:
```bash
git push origin feature/your-feature-name
```

4. Create a Pull Request on GitHub

## 📋 Jira Integration

This project follows the Jira board structure with tickets organized into 4 sprints:

- **Sprint 1**: Foundation & Core Authentication
- **Sprint 2**: RBAC & Core Management
- **Sprint 3**: Core Features & Performance
- **Sprint 4**: Advanced Features & Deployment

Each PR should reference the corresponding Jira ticket (e.g., `SCRUM-11`).

## 🛡️ Security

- JWT authentication with refresh tokens
- Password hashing with bcrypt
- Role-based access control (Admin, Librarian, Member)
- Input validation with Pydantic
- Rate limiting
- CORS configuration
- Secure headers

## 📈 Monitoring & Logging

- Structured JSON logging
- Request ID tracking
- Health check endpoints
- Performance metrics
- Error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI team for the excellent web framework
- SQLAlchemy for ORM
- Redis for caching and queuing
- Celery for background tasks
- All contributors and maintainers

## 📞 Support

For issues, questions, or suggestions:
- Create an issue on GitHub
- Check the documentation
- Review existing issues

---

**Happy Coding!** 🚀