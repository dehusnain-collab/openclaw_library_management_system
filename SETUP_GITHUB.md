# GitHub Repository Setup Instructions

## Step 1: Create GitHub Repository

### Option A: Using GitHub Website
1. Go to https://github.com/new
2. Fill in repository details:
   - **Repository name**: `openclaw_library_management_system`
   - **Description**: `A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.`
   - **Visibility**: Public
   - **Initialize with README**: ❌ **UNCHECK** (we already have README.md)
   - **Add .gitignore**: Python
   - **Choose a license**: MIT License
3. Click "Create repository"

### Option B: Using GitHub CLI (if available)
```bash
# Login to GitHub CLI
gh auth login

# Create repository
gh repo create openclaw_library_management_system \
  --public \
  --description "A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery." \
  --license MIT \
  --gitignore Python
```

## Step 2: Push Existing Code

After creating the repository on GitHub, run these commands:

```bash
# Navigate to project directory
cd /home/node/.openclaw/workspace/openclaw_library_management_system

# Add remote origin (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/openclaw_library_management_system.git

# Rename branch to main
git branch -M main

# Push code to GitHub
git push -u origin main
```

## Step 3: Set Up GitHub Actions (Optional)

Create `.github/workflows/ci.yml`:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v
```

## Step 4: Create First Pull Request

### Branch for SCRUM-13: Database Layer & Migrations
```bash
# Create feature branch
git checkout -b feature/SCRUM-13-database-migrations

# Make changes for database migrations
# ... implement Alembic migrations ...

# Commit changes
git add .
git commit -m "feat: implement database migrations (SCRUM-13)"

# Push to GitHub
git push origin feature/SCRUM-13-database-migrations
```

### Create Pull Request on GitHub
1. Go to your repository on GitHub
2. Click "Pull requests" → "New pull request"
3. Select:
   - **base**: `main`
   - **compare**: `feature/SCRUM-13-database-migrations`
4. Add title: `feat: implement database migrations (SCRUM-13)`
5. Add description referencing Jira ticket
6. Assign reviewers if needed
7. Click "Create pull request"

## Step 5: Project Setup for Development

### Local Development
```bash
# 1. Clone the repository (after creating on GitHub)
git clone https://github.com/YOUR_USERNAME/openclaw_library_management_system.git
cd openclaw_library_management_system

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 4. Start services with Docker
docker-compose up -d

# 5. Run database migrations
docker-compose exec api alembic upgrade head

# 6. Access the application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# PGAdmin: http://localhost:5050 (admin@library.com / admin123)
# Redis Commander: http://localhost:8081
```

### Docker Development
```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest tests/

# Stop services
docker-compose down
```

## Step 6: Configure GitHub Secrets (for CI/CD)

If using GitHub Actions, add these secrets in repository settings:
1. Go to Settings → Secrets and variables → Actions
2. Add New Repository Secret:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token
   - `PRODUCTION_HOST`: Production server host
   - `PRODUCTION_SSH_KEY`: SSH private key for deployment

## Step 7: Set Up Project Board

### GitHub Projects
1. Go to your repository → Projects
2. Click "New project"
3. Choose "Board" template
4. Name: "Library Management System"
5. Add columns:
   - 📋 Backlog
   - 🚀 Sprint 1: Foundation
   - 🚀 Sprint 2: RBAC & Management
   - 🚀 Sprint 3: Core Features
   - 🚀 Sprint 4: Advanced Features
   - 🔄 In Progress
   - 👀 Code Review
   - ✅ Done

### Link with Jira
1. Install GitHub for Jira app
2. Connect your GitHub repository to Jira project SCRUM
3. Enable development panel in Jira tickets

## 📊 Repository Statistics

After pushing code, you should see:
- ✅ **Language**: Python (primary), Dockerfile, Shell
- ✅ **Files**: ~50 files
- ✅ **Lines of code**: ~2000+ lines
- ✅ **Structure**: Clean Architecture pattern
- ✅ **Documentation**: Comprehensive README and setup guides

## 🆘 Troubleshooting

### Common Issues

1. **Permission denied when pushing**
   ```bash
   # Use HTTPS with token
   git remote set-url origin https://TOKEN@github.com/USER/REPO.git
   ```

2. **Docker compose errors**
   ```bash
   # Check if ports are in use
   sudo lsof -i :5432  # PostgreSQL
   sudo lsof -i :6379  # Redis
   sudo lsof -i :8000  # FastAPI
   ```

3. **Database connection issues**
   ```bash
   # Test database connection
   docker-compose exec postgres psql -U postgres -d library_db -c "SELECT 1;"
   ```

4. **Alembic migration errors**
   ```bash
   # Reset migrations (development only)
   docker-compose exec api alembic downgrade base
   docker-compose exec api alembic upgrade head
   ```

## 🎉 Success Checklist

- [ ] Repository created on GitHub
- [ ] Code pushed successfully
- [ ] Docker services running
- [ ] Database migrations applied
- [ ] API accessible at http://localhost:8000
- [ ] Documentation complete
- [ ] First PR created for SCRUM-13
- [ ] Project board set up

## 📞 Support

For help with GitHub setup:
- GitHub Documentation: https://docs.github.com
- Git Handbook: https://guides.github.com/introduction/git-handbook/
- Docker Documentation: https://docs.docker.com
- FastAPI Documentation: https://fastapi.tiangolo.com