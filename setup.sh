#!/bin/bash

# Setup script for OpenClaw Library Management System

echo "Setting up OpenClaw Library Management System..."

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file from example
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please update the .env file with your configuration"
fi

# Initialize git
echo "Initializing git repository..."
git init
git add .
git commit -m "Initial commit: Project structure and core setup"

echo ""
echo "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Update the .env file with your configuration"
echo "2. Run database migrations: alembic upgrade head"
echo "3. Start the application: uvicorn app.main:app --reload"
echo "4. Access the API at: http://localhost:8000"
echo "5. View documentation at: http://localhost:8000/docs"
echo ""
echo "Or use Docker: docker-compose up -d"