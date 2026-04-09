#!/usr/bin/env python3
"""
Test script to verify the project structure.
"""
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        # Core modules
        from app.config import settings
        print("✅ app.config imported successfully")
        
        from app.main import app
        print("✅ app.main imported successfully")
        
        from app.database import get_db
        print("✅ app.database imported successfully")
        
        from app.utils.logging import setup_logging
        print("✅ app.utils.logging imported successfully")
        
        # Models
        from app.models.base import BaseModel
        print("✅ app.models.base imported successfully")
        
        from app.models.user import User
        print("✅ app.models.user imported successfully")
        
        from app.models.book import Book
        print("✅ app.models.book imported successfully")
        
        from app.models.borrowing import BorrowingRecord
        print("✅ app.models.borrowing imported successfully")
        
        from app.models.role import Role, Permission
        print("✅ app.models.role imported successfully")
        
        # Repositories
        from app.repositories.base import BaseRepository
        print("✅ app.repositories.base imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_structure():
    """Test project structure."""
    print("\nTesting project structure...")
    
    required_dirs = [
        "app",
        "app/config",
        "app/controllers",
        "app/services",
        "app/repositories",
        "app/models",
        "app/schemas",
        "app/middleware",
        "app/utils",
        "app/exceptions",
        "tests",
        "alembic",
        "alembic/versions",
        "docker",
        "scripts",
    ]
    
    required_files = [
        "requirements.txt",
        ".env.example",
        "docker-compose.yml",
        "Dockerfile",
        "alembic.ini",
        "README.md",
        "setup.sh",
        "app/__init__.py",
        "app/main.py",
        "app/database.py",
        "app/config/__init__.py",
        "app/controllers/__init__.py",
        "app/models/__init__.py",
        "app/models/base.py",
        "app/models/user.py",
        "app/models/book.py",
        "app/models/borrowing.py",
        "app/models/role.py",
        "app/repositories/__init__.py",
        "app/repositories/base.py",
        "app/utils/__init__.py",
        "app/utils/logging.py",
        "app/middleware/__init__.py",
        "app/middleware/request_id.py",
    ]
    
    all_good = True
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"❌ Missing directory: {dir_path}")
            all_good = False
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ File exists: {file_path}")
        else:
            print(f"❌ Missing file: {file_path}")
            all_good = False
    
    return all_good

def main():
    """Run all tests."""
    print("=" * 60)
    print("OpenClaw Library Management System - Structure Test")
    print("=" * 60)
    
    imports_ok = test_imports()
    structure_ok = test_structure()
    
    print("\n" + "=" * 60)
    if imports_ok and structure_ok:
        print("✅ All tests passed! Project structure is correct.")
        print("\nNext steps:")
        print("1. Run: chmod +x setup.sh && ./setup.sh")
        print("2. Update .env file with your configuration")
        print("3. Run database migrations")
        print("4. Start the application: uvicorn app.main:app --reload")
        return 0
    else:
        print("❌ Some tests failed. Please check the project structure.")
        return 1

if __name__ == "__main__":
    sys.exit(main())