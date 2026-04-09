#!/bin/bash
# Script to push code after creating GitHub repository

echo "Adding remote origin..."
git remote add origin https://github.com/dehusnain-collab/openclaw_library_management_system.git

echo "Renaming branch to main..."
git branch -M main

echo "Pushing code to GitHub..."
git push -u origin main

echo ""
echo "✅ Code pushed successfully!"
echo "🔗 Repository: https://github.com/dehusnain-collab/openclaw_library_management_system"
