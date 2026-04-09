#!/usr/bin/env python3
"""
Direct GitHub repository creation script.
Tries multiple methods to create repository.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def try_github_cli():
    """Try using GitHub CLI if available."""
    print("Trying GitHub CLI...")
    try:
        # Check if gh is available
        result = subprocess.run(["which", "gh"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ GitHub CLI not found")
            return None
        
        # Try to create repository
        repo_name = "openclaw_library_management_system"
        description = "A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery."
        
        cmd = [
            "gh", "repo", "create", 
            f"dehusnain-collab/{repo_name}",
            "--public",
            "--description", description,
            "--disable-wiki",
            "--gitignore", "Python",
            "--license", "MIT"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Repository created: {repo_name}")
            return f"https://github.com/dehusnain-collab/{repo_name}.git"
        else:
            print(f"❌ GitHub CLI failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error with GitHub CLI: {e}")
        return None

def try_github_api():
    """Try using GitHub API with token from environment."""
    print("\nTrying GitHub API...")
    
    # Check for token in environment
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN not found in environment")
        return None
    
    print("✅ Found GITHUB_TOKEN in environment")
    
    # Create repository using curl
    repo_name = "openclaw_library_management_system"
    data = {
        "name": repo_name,
        "description": "A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.",
        "private": False,
        "auto_init": False,
        "gitignore_template": "Python",
        "license_template": "mit"
    }
    
    curl_cmd = [
        "curl", "-s", "-X", "POST",
        "-H", "Authorization: token " + token,
        "-H", "Accept: application/vnd.github.v3+json",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data),
        "https://api.github.com/user/repos"
    ]
    
    print(f"Running curl command...")
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if "clone_url" in response:
                clone_url = response["clone_url"]
                print(f"✅ Repository created: {clone_url}")
                return clone_url
            else:
                print(f"❌ Unexpected response: {result.stdout}")
                return None
        else:
            print(f"❌ Curl failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error with GitHub API: {e}")
        return None

def try_openclaw_config():
    """Try to get GitHub token from OpenClaw configuration."""
    print("\nChecking OpenClaw configuration...")
    
    # Try to get config from openclaw
    try:
        result = subprocess.run(["openclaw", "config", "get", "github.token"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            token = result.stdout.strip()
            print("✅ Found GitHub token in OpenClaw config")
            os.environ["GITHUB_TOKEN"] = token
            return try_github_api()
    except:
        pass
    
    print("❌ No GitHub token in OpenClaw config")
    return None

def push_code(repo_url):
    """Push code to the created repository."""
    print(f"\n🚀 Pushing code to {repo_url}")
    
    try:
        # Remove existing remote if any
        subprocess.run(["git", "remote", "remove", "origin"], 
                      capture_output=True, text=True)
        
        # Add new remote
        result = subprocess.run(["git", "remote", "add", "origin", repo_url],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to add remote: {result.stderr}")
            return False
        
        # Push code
        print("Pushing code to GitHub...")
        result = subprocess.run(["git", "push", "-u", "origin", "main"],
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Code pushed successfully!")
            return True
        else:
            print(f"❌ Push failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error pushing code: {e}")
        return False

def main():
    print("=" * 60)
    print("GitHub Repository Creation Script")
    print("=" * 60)
    
    # Check if we're in a git repository
    if not Path(".git").exists():
        print("❌ Not in a git repository")
        return
    
    # Try different methods to create repository
    repo_url = None
    
    # Method 1: Try GitHub CLI
    repo_url = try_github_cli()
    
    # Method 2: Try GitHub API with env token
    if not repo_url:
        repo_url = try_github_api()
    
    # Method 3: Try OpenClaw config
    if not repo_url:
        repo_url = try_openclaw_config()
    
    if repo_url:
        # Push code
        if push_code(repo_url):
            print("\n" + "=" * 60)
            print("🎉 SUCCESS! Repository created and code pushed!")
            print(f"🔗 Repository: {repo_url}")
            print("=" * 60)
            
            # Push feature branch
            print("\n📋 Next steps:")
            print("1. Push feature branch:")
            print("   git checkout feature/SCRUM-15-user-registration-login")
            print("   git push -u origin feature/SCRUM-15-user-registration-login")
            print("\n2. Create PR on GitHub")
            print("\n3. Run ./setup.sh for local development")
        else:
            print("\n❌ Failed to push code")
    else:
        print("\n" + "=" * 60)
        print("❌ Could not create repository")
        print("\n📋 Manual instructions:")
        print("1. Create repository at: https://github.com/new")
        print("2. Name: openclaw_library_management_system")
        print("3. Owner: dehusnain-collab")
        print("4. Public, MIT license, Python .gitignore")
        print("5. DO NOT initialize with README")
        print("6. After creation, run:")
        print("   git remote add origin https://github.com/dehusnain-collab/openclaw_library_management_system.git")
        print("   git push -u origin main")
        print("=" * 60)

if __name__ == "__main__":
    main()