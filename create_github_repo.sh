#!/bin/bash

# Script to create GitHub repository and push code
# This requires a GitHub Personal Access Token with repo scope

set -e

REPO_NAME="openclaw_library_management_system"
GITHUB_USER="dehusnain-collab"
GITHUB_TOKEN="${GITHUB_TOKEN}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set"
    echo "Please set your GitHub Personal Access Token:"
    echo "export GITHUB_TOKEN=your_token_here"
    exit 1
fi

echo "Creating GitHub repository: $REPO_NAME..."

# Create repository using GitHub API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\",\"private\":false,\"description\":\"A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.\",\"homepage\":\"https://github.com/$GITHUB_USER/$REPO_NAME\"}"

echo ""
echo "Repository created successfully!"
echo ""

# Add remote origin and push code
echo "Setting up git remote and pushing code..."
git remote add origin "https://$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git"
git branch -M main
git push -u origin main

echo ""
echo "✅ Repository created and code pushed successfully!"
echo ""
echo "🔗 Repository URL: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "📚 View your code at: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "Next steps:"
echo "1. Run: chmod +x setup.sh && ./setup.sh"
echo "2. Update .env file with your configuration"
echo "3. Run database migrations: alembic upgrade head"
echo "4. Start the application: uvicorn app.main:app --reload"
echo "5. Or use Docker: docker-compose up -d"