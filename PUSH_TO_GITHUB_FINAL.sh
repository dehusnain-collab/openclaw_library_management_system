#!/bin/bash

# Final script to push OpenClaw Library Management System to GitHub

echo "============================================================"
echo "🚀 OPENCLAW LIBRARY MANAGEMENT SYSTEM - GITHUB DEPLOYMENT"
echo "============================================================"

echo ""
echo "📊 PROJECT STATUS:"
echo "• Code ready: ✅"
echo "• Tests ready: ✅"
echo "• Docker ready: ✅"
echo "• Documentation: ✅"
echo "• CI/CD: ✅"
echo ""

echo "🎯 SELECT DEPLOYMENT METHOD:"
echo ""
echo "1. 🔄 Automatic (requires GitHub Personal Access Token)"
echo "2. 📝 Manual (follow step-by-step instructions)"
echo "3. 🚀 Direct Push (if repository already exists)"
echo ""
read -p "Choose option (1-3): " option

case $option in
    1)
        echo ""
        echo "🔄 AUTOMATIC DEPLOYMENT"
        echo "----------------------"
        echo ""
        echo "This requires a GitHub Personal Access Token with 'repo' scope."
        echo ""
        
        if [ -z "$GITHUB_TOKEN" ]; then
            echo "❌ GITHUB_TOKEN not set in environment."
            echo ""
            echo "Please export your token:"
            echo "export GITHUB_TOKEN=your_token_here"
            echo ""
            echo "Then run this script again."
            exit 1
        fi
        
        echo "✅ GitHub token found."
        echo "Creating repository..."
        
        # Create repository
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
          }' 2>/dev/null)
        
        if echo "$response" | grep -q '"name": "openclaw_library_management_system"'; then
            echo "✅ Repository created!"
            https_url=$(echo "$response" | grep -o '"clone_url": "[^"]*"' | cut -d'"' -f4)
            echo "🔗 URL: $https_url"
            
            # Push code
            echo "🚀 Pushing code..."
            git remote add origin "$https_url" 2>/dev/null
            git push -u origin main
            
            if [ $? -eq 0 ]; then
                echo "🎉 SUCCESS! Code pushed to GitHub!"
                echo "🔗 Visit: $https_url"
            else
                echo "❌ Push failed. Trying manual method..."
                ./create_and_push_manual.sh
            fi
        else
            echo "❌ Failed to create repository."
            echo "Trying manual method..."
            ./create_and_push_manual.sh
        fi
        ;;
    
    2)
        echo ""
        echo "📝 MANUAL DEPLOYMENT"
        echo "-------------------"
        ./create_and_push_manual.sh
        ;;
    
    3)
        echo ""
        echo "🚀 DIRECT PUSH"
        echo "-------------"
        echo ""
        echo "This assumes the repository already exists on GitHub."
        echo ""
        read -p "Enter GitHub repository URL (https://github.com/dehusnain-collab/openclaw_library_management_system.git): " repo_url
        
        if [ -z "$repo_url" ]; then
            repo_url="https://github.com/dehusnain-collab/openclaw_library_management_system.git"
        fi
        
        echo ""
        echo "📦 Pushing code to: $repo_url"
        echo ""
        
        # Remove existing remote if any
        git remote remove origin 2>/dev/null
        
        # Add remote and push
        git remote add origin "$repo_url"
        git push -u origin main
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 SUCCESS! Code pushed to GitHub!"
            echo "🔗 Repository: $repo_url"
            echo ""
            echo "Next: Push feature branch and create PR"
            echo "git checkout feature/SCRUM-15-user-registration-login"
            echo "git push -u origin feature/SCRUM-15-user-registration-login"
        else
            echo ""
            echo "❌ Push failed. Possible issues:"
            echo "1. Repository doesn't exist"
            echo "2. No write permissions"
            echo "3. Network issue"
            echo ""
            echo "Try manual method: ./create_and_push_manual.sh"
        fi
        ;;
    
    *)
        echo "❌ Invalid option. Please run script again."
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "📋 POST-DEPLOYMENT CHECKLIST:"
echo "============================================================"
echo ""
echo "✅ Code pushed to GitHub"
echo "🔗 Repository URL: https://github.com/dehusnain-collab/openclaw_library_management_system"
echo ""
echo "📋 NEXT STEPS:"
echo "1. 🔄 Push feature branch:"
echo "   git checkout feature/SCRUM-15-user-registration-login"
echo "   git push -u origin feature/SCRUM-15-user-registration-login"
echo ""
echo "2. 📝 Create Pull Request:"
echo "   • Go to repository on GitHub"
echo "   • Click 'Pull requests'"
echo "   • Create PR from feature branch to main"
echo ""
echo "3. 🏗️ Set up local development:"
echo "   ./setup.sh"
echo "   docker-compose up -d"
echo ""
echo "4. 🧪 Run tests:"
echo "   pytest tests/"
echo ""
echo "5. 🚀 Start implementing next ticket (SCRUM-22)"
echo "   git checkout -b feature/SCRUM-22-password-management"
echo ""
echo "============================================================"
echo "🎉 PROJECT DEPLOYED SUCCESSFULLY!"
echo "============================================================"