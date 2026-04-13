#!/bin/bash
# Deployment script for Library Management System
# Covers: SCRUM-40

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="./backups"
LOG_DIR="./logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f ".env.${ENVIRONMENT}" ]; then
        print_warning "Environment file .env.${ENVIRONMENT} not found"
        if [ ! -f ".env" ]; then
            print_error "No environment file found"
            exit 1
        fi
        print_status "Using default .env file"
    else
        print_status "Using environment file .env.${ENVIRONMENT}"
        cp ".env.${ENVIRONMENT}" ".env"
    fi
    
    print_status "Prerequisites check passed"
}

# Function to create backup
create_backup() {
    print_status "Creating backup..."
    
    mkdir -p "${BACKUP_DIR}"
    
    # Backup database
    print_status "Backing up database..."
    docker-compose -f "${DOCKER_COMPOSE_FILE}" exec -T postgres \
        pg_dump -U library_user library_db > "${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"
    
    # Backup Redis data
    print_status "Backing up Redis data..."
    docker-compose -f "${DOCKER_COMPOSE_FILE}" exec -T redis \
        redis-cli --rdb /data/dump.rdb
    docker cp "$(docker-compose -f "${DOCKLE_COMPOSE_FILE}" ps -q redis):/data/dump.rdb" \
        "${BACKUP_DIR}/redis_backup_${TIMESTAMP}.rdb"
    
    # Backup logs
    print_status "Backing up logs..."
    tar -czf "${BACKUP_DIR}/logs_backup_${TIMESTAMP}.tar.gz" "${LOG_DIR}" 2>/dev/null || true
    
    print_status "Backup completed: ${BACKUP_DIR}/"
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker-compose -f "${DOCKER_COMPOSE_FILE}" exec -T postgres \
            pg_isready -U library_user -d library_db > /dev/null 2>&1; then
            print_status "Database is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Database is not ready after 30 seconds"
            exit 1
        fi
        sleep 1
    done
    
    # Run migrations
    docker-compose -f "${DOCKER_COMPOSE_FILE}" run --rm api \
        alembic upgrade head
    
    print_status "Database migrations completed"
}

# Function to deploy application
deploy_application() {
    print_status "Deploying application..."
    
    # Pull latest images
    print_status "Pulling latest Docker images..."
    docker-compose -f "${DOCKER_COMPOSE_FILE}" pull
    
    # Build images if needed
    print_status "Building Docker images..."
    docker-compose -f "${DOCKER_COMPOSE_FILE}" build
    
    # Start services
    print_status "Starting services..."
    docker-compose -f "${DOCKER_COMPOSE_FILE}" up -d --remove-orphans
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    print_status "Checking service health..."
    
    # Check API health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_status "API is healthy"
    else
        print_error "API is not healthy"
        docker-compose -f "${DOCKER_COMPOSE_FILE}" logs api
        exit 1
    fi
    
    # Check database health
    if docker-compose -f "${DOCKER_COMPOSE_FILE}" exec -T postgres \
        pg_isready -U library_user -d library_db > /dev/null 2>&1; then
        print_status "Database is healthy"
    else
        print_error "Database is not healthy"
        exit 1
    fi
    
    # Check Redis health
    if docker-compose -f "${DOCKER_COMPOSE_FILE}" exec -T redis \
        redis-cli ping > /dev/null 2>&1; then
        print_status "Redis is healthy"
    else
        print_error "Redis is not healthy"
        exit 1
    fi
    
    print_status "Application deployment completed"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Run unit tests
    docker-compose -f "${DOCKER_COMPOSE_FILE}" run --rm api \
        pytest tests/ -v
    
    print_status "Tests completed"
}

# Function to clean up old backups
cleanup_backups() {
    print_status "Cleaning up old backups..."
    
    # Keep only last 7 days of backups
    find "${BACKUP_DIR}" -name "*.sql" -mtime +7 -delete
    find "${BACKUP_DIR}" -name "*.rdb" -mtime +7 -delete
    find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +7 -delete
    
    print_status "Backup cleanup completed"
}

# Function to display deployment info
display_deployment_info() {
    print_status "Deployment Information:"
    echo "Environment: ${ENVIRONMENT}"
    echo "Timestamp: ${TIMESTAMP}"
    echo "API URL: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    echo "Health Check: http://localhost:8000/health"
    
    if [ "${ENVIRONMENT}" = "production" ]; then
        echo ""
        print_warning "Production deployment completed!"
        print_warning "Please verify the deployment before notifying users."
    fi
}

# Main deployment process
main() {
    echo "========================================="
    echo "Library Management System Deployment"
    echo "Environment: ${ENVIRONMENT}"
    echo "========================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Create backup
    create_backup
    
    # Run migrations
    run_migrations
    
    # Deploy application
    deploy_application
    
    # Run tests (optional)
    if [ "${ENVIRONMENT}" = "staging" ]; then
        run_tests
    fi
    
    # Cleanup old backups
    cleanup_backups
    
    # Display deployment info
    display_deployment_info
    
    echo "========================================="
    print_status "Deployment completed successfully!"
    echo "========================================="
}

# Handle command line arguments
case "$1" in
    staging|production)
        main
        ;;
    *)
        echo "Usage: $0 {staging|production}"
        echo "Example: $0 staging"
        exit 1
        ;;
esac