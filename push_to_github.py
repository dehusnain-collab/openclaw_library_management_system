#!/usr/bin/env python3
"""
Script to push project to GitHub and set up complete workflow.
"""
import os
import sys
import subprocess
import json
from pathlib import Path
import requests

def check_git_status():
    """Check git status and ensure we're ready to push."""
    print("Checking git status...")
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode != 0:
            print("❌ Not in a git repository or git not available")
            return False
        
        print("✅ Git repository ready")
        return True
        
    except Exception as e:
        print(f"❌ Error checking git status: {e}")
        return False

def create_github_repo_instructions():
    """Create instructions for creating GitHub repository."""
    print("\n" + "=" * 60)
    print("GitHub Repository Setup Instructions")
    print("=" * 60)
    
    instructions = """
Since GitHub CLI is not available, here are the steps to create the repository:

STEP 1: Create Repository on GitHub.com
----------------------------------------
1. Go to: https://github.com/new
2. Fill in:
   - Owner: dehusnain-collab
   - Repository name: openclaw_library_management_system
   - Description: A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.
   - Visibility: Public
   - UNCHECK: Initialize with README (we already have one)
   - Add .gitignore: Python
   - Choose a license: MIT License
3. Click "Create repository"

STEP 2: Push Existing Code
--------------------------
After creating the repository, run these commands:

# Add remote origin
git remote add origin https://github.com/dehusnain-collab/openclaw_library_management_system.git

# Rename branch to main
git branch -M main

# Push code
git push -u origin main

STEP 3: Verify Push
-------------------
Visit: https://github.com/dehusnain-collab/openclaw_library_management_system
You should see all the project files.
"""
    
    print(instructions)
    
    # Create a script for the user to run after creating the repo
    push_script = """#!/bin/bash
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
"""
    
    script_path = Path("push_after_github_created.sh")
    script_path.write_text(push_script)
    script_path.chmod(0o755)
    
    print(f"✅ Created push script: {script_path}")
    print("Run this script AFTER creating the repository on GitHub.com")
    
    return True

def create_branch_structure():
    """Create branch structure for Jira tickets."""
    print("\n" + "=" * 60)
    print("Creating Branch Structure for Jira Tickets")
    print("=" * 60)
    
    # List of tickets to implement (from Jira board)
    tickets = [
        # Sprint 1
        ("SCRUM-11", "project-structure-core-setup", "✅ COMPLETED"),
        ("SCRUM-12", "create-project-folder-structure", "✅ COMPLETED"),
        ("SCRUM-13", "database-layer-migrations", "✅ COMPLETED"),
        
        # Remaining tickets to implement
        ("SCRUM-15", "user-registration-login", "🔜 NEXT"),
        ("SCRUM-22", "password-management", "PENDING"),
        ("SCRUM-14", "authentication-security-module", "PENDING"),
        ("SCRUM-16", "role-based-access-control", "PENDING"),
        ("SCRUM-17", "role-permission-system", "PENDING"),
        ("SCRUM-23", "admin-role-management", "PENDING"),
        ("SCRUM-24", "user-management", "PENDING"),
        ("SCRUM-25", "user-profile-management", "PENDING"),
        ("SCRUM-26", "user-deactivation", "PENDING"),
        ("SCRUM-18", "book-management", "PENDING"),
        ("SCRUM-19", "add-update-books", "PENDING"),
        ("SCRUM-27", "delete-view-books", "PENDING"),
        ("SCRUM-28", "borrowing-system", "PENDING"),
        ("SCRUM-29", "borrow-book", "PENDING"),
        ("SCRUM-30", "return-book-fine-calculation", "PENDING"),
        ("SCRUM-31", "search-filtering-system", "PENDING"),
        ("SCRUM-32", "basic-book-search-filtering", "PENDING"),
        ("SCRUM-33", "redis-caching-layer", "PENDING"),
        ("SCRUM-34", "cache-book-data", "PENDING"),
        ("SCRUM-20", "background-jobs-queue-system", "PENDING"),
        ("SCRUM-21", "email-notification-system", "PENDING"),
        ("SCRUM-35", "asynchronous-task-processing", "PENDING"),
        ("SCRUM-36", "audit-logging-system", "PENDING"),
        ("SCRUM-37", "user-action-auditing", "PENDING"),
        ("SCRUM-38", "performance-security", "PENDING"),
        ("SCRUM-39", "rate-limiting-input-validation", "PENDING"),
        ("SCRUM-40", "devops-deployment", "PENDING"),
        ("SCRUM-41", "docker-environment-setup", "PENDING"),
    ]
    
    # Create branch creation script
    branch_script = """#!/bin/bash
# Script to create feature branches for all Jira tickets

echo "Creating feature branches for Jira tickets..."

# Make sure we're on main branch
git checkout main

"""
    
    for ticket_id, ticket_slug, status in tickets:
        if "COMPLETED" in status:
            branch_script += f"# {ticket_id}: {ticket_slug} - {status}\n"
        elif "NEXT" in status:
            branch_script += f"echo \"Creating branch for {ticket_id}...\"\n"
            branch_script += f"git checkout -b feature/{ticket_id}-{ticket_slug}\n"
            branch_script += f"echo \"✅ Created branch: feature/{ticket_id}-{ticket_slug}\"\n"
            branch_script += f"git checkout main\n\n"
        else:
            branch_script += f"# git checkout -b feature/{ticket_id}-{ticket_slug}  # {ticket_id}: {ticket_slug}\n"
    
    branch_script += """
echo ""
echo "✅ Branch creation script ready!"
echo "To create a branch for a specific ticket, uncomment the corresponding line."
echo "First, create and work on: feature/SCRUM-15-user-registration-login"
"""
    
    script_path = Path("create_feature_branches.sh")
    script_path.write_text(branch_script)
    script_path.chmod(0o755)
    
    print("✅ Created branch creation script: create_feature_branches.sh")
    print("\nBranch Structure:")
    print("-" * 60)
    
    for ticket_id, ticket_slug, status in tickets:
        print(f"{ticket_id:12} → feature/{ticket_id}-{ticket_slug:35} [{status}]")
    
    return True

def create_pr_workflow():
    """Create PR workflow and templates."""
    print("\n" + "=" * 60)
    print("Creating PR Workflow and Templates")
    print("=" * 60)
    
    # Create .github directory structure
    github_dir = Path(".github")
    github_dir.mkdir(exist_ok=True)
    
    workflows_dir = github_dir / "workflows"
    workflows_dir.mkdir(exist_ok=True)
    
    # Create CI/CD workflow
    ci_workflow = """name: CI/CD Pipeline

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
          POSTGRES_DB: test_library_db
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
        pytest tests/ -v --cov=app --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
  
  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install black isort flake8 mypy
    
    - name: Check code formatting with black
      run: |
        black --check app/
    
    - name: Check import sorting with isort
      run: |
        isort --check-only app/
    
    - name: Lint with flake8
      run: |
        flake8 app/
    
    - name: Type check with mypy
      run: |
        mypy app/
  
  build-docker:
    runs-on: ubuntu-latest
    needs: [test, lint]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Build Docker image
      run: |
        docker build -t openclaw-library-management:latest .
    
    - name: Test Docker image
      run: |
        docker run --rm openclaw-library-management:latest python -c "import sys; print('Python version:', sys.version)"
"""
    
    ci_file = workflows_dir / "ci.yml"
    ci_file.write_text(ci_workflow)
    print(f"✅ Created CI/CD workflow: {ci_file}")
    
    # Create PR template
    pr_template_dir = github_dir / "PULL_REQUEST_TEMPLATE"
    pr_template_dir.mkdir(exist_ok=True)
    
    pr_template = """## Description
Implements [Jira Ticket Number]: [Ticket Title]

## Type of Change
- [ ] 🎉 New feature (non-breaking change which adds functionality)
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ♻️ Refactor (non-breaking change that restructures code)
- [ ] 📚 Documentation update
- [ ] 🧪 Test addition/update
- [ ] 🚀 Performance improvement
- [ ] 🔧 CI/CD improvement
- [ ] 🎨 Style improvement
- [ ] 🗑️ Chore (maintenance, dependencies, etc.)

## Changes Made
- [ ] Change 1
- [ ] Change 2
- [ ] Change 3

## Testing
### Unit Tests
- [ ] Added new unit tests
- [ ] Updated existing unit tests
- [ ] All unit tests pass

### Integration Tests
- [ ] Added integration tests
- [ ] Updated integration tests
- [ ] All integration tests pass

### Manual Testing
- [ ] Tested locally
- [ ] Tested in Docker
- [ ] Tested API endpoints

## Screenshots (if applicable)

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules

## Related Issues
Closes #[issue_number]

## Deployment Notes
- [ ] Database migration required
- [ ] Environment variables updated
- [ ] Documentation updated
- [ ] Backward compatible

## Reviewers
@dehusnain-collab
"""
    
    pr_file = pr_template_dir / "PULL_REQUEST_TEMPLATE.md"
    pr_file.write_text(pr_template)
    print(f"✅ Created PR template: {pr_file}")
    
    return True

def create_implementation_plan():
    """Create detailed implementation plan for remaining tickets."""
    print("\n" + "=" * 60)
    print("Creating Detailed Implementation Plan")
    print("=" * 60)
    
    plan_content = """# Complete Implementation Plan for Library Management System

## 🎯 Current Status
✅ **Sprint 1: Foundation & Core Authentication - PARTIALLY COMPLETED**
- ✅ SCRUM-11: Project Structure & Core Setup
- ✅ SCRUM-12: Create project folder structure  
- ✅ SCRUM-13: Database Layer & Migrations
- 🔄 SCRUM-15: User Registration & Login (IN PROGRESS)
- ⏳ Remaining Sprint 1 tickets

## 📋 Implementation Roadmap

### PHASE 1: Complete Sprint 1 (Authentication & Security)
**Priority: HIGH | Estimated: 2-3 days**

#### 1. SCRUM-15: User Registration & Login
**Tasks:**
- [ ] Create auth service with JWT token generation
- [ ] Implement password hashing with bcrypt
- [ ] Build registration endpoint with validation
- [ ] Build login endpoint with credential verification
- [ ] Add email format validation
- [ ] Implement password strength requirements

#### 2. SCRUM-22: Password Management
**Tasks:**
- [ ] Password reset request endpoint
- [ ] Password reset token generation
- [ ] Password reset completion endpoint
- [ ] Change password endpoint
- [ ] Password history tracking

#### 3. SCRUM-14: Authentication & Security Module (Epic Completion)
**Tasks:**
- [ ] Token refresh mechanism
- [ ] Redis token blacklisting
- [ ] Logout functionality
- [ ] Authentication middleware

### PHASE 2: Sprint 2 (RBAC & Core Management)
**Priority: HIGH | Estimated: 3-4 days**

#### 4. SCRUM-16 & 17: Role-Based Access Control
**Tasks:**
- [ ] Role and Permission models
- [ ] Many-to-many relationships
- [ ] Authorization middleware
- [ ] Default roles and permissions
- [ ] User role assignment

#### 5. SCRUM-23: Admin Role Management
**Tasks:**
- [ ] Admin CRUD operations for users
- [ ] Role assignment endpoints
- [ ] Permission management
- [ ] Audit logging for admin actions

#### 6. SCRUM-24, 25, 26: User Management
**Tasks:**
- [ ] User profile endpoints
- [ ] Profile update validation
- [ ] User deactivation
- [ ] Account status management

### PHASE 3: Sprint 3 (Core Features & Performance)
**Priority: MEDIUM | Estimated: 4-5 days**

#### 7. SCRUM-18, 19, 27: Book Management
**Tasks:**
- [ ] Book CRUD operations
- [ ] ISBN uniqueness validation
- [ ] Availability tracking
- [ ] Book search and filtering

#### 8. SCRUM-28, 29, 30: Borrowing System
**Tasks:**
- [ ] Borrow book functionality
- [ ] Return book functionality
- [ ] Fine calculation logic
- [ ] Borrowing limits and validation

#### 9. SCRUM-31, 32: Search & Filtering
**Tasks:**
- [ ] Search by title/author/category
- [ ] Pagination implementation
- [ ] Advanced filtering
- [ ] Sorting options

#### 10. SCRUM-33, 34: Redis Caching
**Tasks:**
- [ ] Redis client setup
- [ ] Cache book lists and search results
- [ ] Cache invalidation strategy
- [ ] Cache expiration configuration

### PHASE 4: Sprint 4 (Advanced Features & Deployment)
**Priority: LOW | Estimated: 5-6 days**

#### 11. SCRUM-20, 21, 35: Background Jobs
**Tasks:**
- [ ] Celery setup with Redis
- [ ] Email notification tasks
- [ ] Overdue book notifications
- [ ] Async task processing

#### 12. SCRUM-36, 37: Audit & Logging
**Tasks:**
- [ ] User action tracking
- [ ] Audit log storage
- [ ] Searchable audit logs
- [ ]