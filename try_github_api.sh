#!/bin/bash

# Try to create GitHub repository using API

echo "Attempting to create GitHub repository..."

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable not set"
    echo ""
    echo "To create repository automatically, you need a GitHub Personal Access Token."
    echo ""
    echo "1. Create a token at: https://github.com/settings/tokens"
    echo "   • Select 'repo' scope"
    echo "   • Copy the token"
    echo ""
    echo "2. Export the token:"
    echo "   export GITHUB_TOKEN=your_token_here"
    echo ""
    echo "3. Run this script again:"
    echo "   ./try_github_api.sh"
    echo ""
    echo "Alternatively, use manual setup: ./create_and_push_manual.sh"
    exit 1
fi

echo "✅ GitHub token found"

# Create repository using GitHub API
echo "Creating repository: openclaw_library_management_system..."

response=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d '{
    "name": "openclaw_library_management_system",
    "description": "A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.",
    "private": false,
    "auto_init": false,
    "gitignore_template": "Python",
    "license_template": "mit"
  }')

# Check if repository was created
if echo "$response" | grep -q '"name": "openclaw_library_management_system"'; then
    echo "✅ Repository created successfully!"
    
    # Get SSH URL
    ssh_url=$(echo "$response" | grep -o '"ssh_url": "[^"]*"' | cut -d'"' -f4)
    # Get HTTPS URL
    https_url=$(echo "$response" | grep -o '"clone_url": "[^"]*"' | cut -d'"' -f4)
    
    echo ""
    echo "📦 Repository URLs:"
    echo "• SSH: $ssh_url"
    echo "• HTTPS: $https_url"
    echo ""
    
    # Push code
    echo "🚀 Pushing code to GitHub..."
    git remote add origin "$https_url"
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 SUCCESS! Code pushed to GitHub!"
        echo ""
        echo "🔗 Repository: $https_url"
        echo ""
        echo "Next steps:"
        echo "1. Push feature branch:"
        echo "   git checkout feature/SCRUM-15-user-registration-login"
        echo "   git push -u origin feature/SCRUM-15-user-registration-login"
        echo "2. Create PR on GitHub"
        echo "3. Run ./setup.sh for local development"
    else
        echo ""
        echo "❌ Push failed. Please check:"
        echo "• Repository URL: $https_url"
        echo "• GitHub token permissions"
        echo "• Internet connection"
    fi
else
    echo "❌ Failed to create repository"
    echo ""
    echo "Response: $response"
    echo ""
    echo "Possible issues:"
    echo "1. Repository already exists"
    echo "2. Token doesn't have 'repo' scope"
    echo "3. Network issue"
    echo ""
    echo "Try manual setup: ./create_and_push_manual.sh"
fi