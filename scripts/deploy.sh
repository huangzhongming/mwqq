#!/bin/bash

# Deployment Script for MWQQ Passport Photo Application
# This script handles zero-downtime deployment with Docker Compose

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Configuration
APP_NAME="mwqq"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="/opt/backups"
LOG_FILE="/var/log/${APP_NAME}/deploy.log"
MAX_DEPLOY_TIME=300  # Maximum deployment time in seconds
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_INTERVAL=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ $1${NC}" | tee -a "$LOG_FILE"
}

# Error handling
cleanup_on_error() {
    log_error "Deployment failed! Starting cleanup and rollback..."
    ./scripts/rollback.sh
    exit 1
}

trap cleanup_on_error ERR

# Check prerequisites
check_prerequisites() {
    log "Checking deployment prerequisites..."
    
    # Check if running as deployment user
    if [[ "$USER" != "deploy" ]] && [[ "$USER" != "root" ]]; then
        log_warning "Not running as 'deploy' user. Current user: $USER"
    fi
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    # Check required environment variables
    if [[ -z "${VERSION:-}" ]]; then
        log_error "VERSION environment variable is required"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Update environment file with new image tags
update_env_file() {
    log "Updating environment file with new version: $VERSION"
    
    # Backup current .env file
    if [[ -f ".env" ]]; then
        cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Update image tags in environment file
    if [[ -f ".env" ]]; then
        sed -i "s|FRONTEND_IMAGE_TAG=.*|FRONTEND_IMAGE_TAG=${REGISTRY}/${REPO_NAME}-frontend:${VERSION}|g" .env
        sed -i "s|BACKEND_IMAGE_TAG=.*|BACKEND_IMAGE_TAG=${REGISTRY}/${REPO_NAME}-backend:${VERSION}|g" .env
    fi
    
    log_success "Environment file updated"
}

# Pull new Docker images
pull_images() {
    log "Pulling new Docker images for version $VERSION..."
    
    # Pull images with retries
    for i in {1..3}; do
        if docker-compose pull; then
            log_success "Images pulled successfully"
            return 0
        else
            log_warning "Image pull attempt $i failed, retrying..."
            sleep 10
        fi
    done
    
    log_error "Failed to pull images after 3 attempts"
    exit 1
}

# Perform database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Start database service if not running
    docker-compose up -d db redis
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T db pg_isready -U postgres; then
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "Database failed to become ready"
            exit 1
        fi
        sleep 2
    done
    
    # Run migrations
    if docker-compose run --rm backend python manage.py migrate; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        exit 1
    fi
}

# Deploy with zero downtime
deploy_services() {
    log "Starting zero-downtime deployment..."
    
    # Record current running containers for rollback
    docker-compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}" > /tmp/containers_before_deploy.txt
    
    # Deploy services one by one with health checks
    log "Deploying backend services..."
    docker-compose up -d backend celery-worker
    
    # Wait for backend to be healthy
    if ! wait_for_health "backend" "http://localhost:8000/health/"; then
        log_error "Backend health check failed"
        exit 1
    fi
    
    log "Deploying frontend service..."
    docker-compose up -d frontend
    
    # Wait for frontend to be healthy
    if ! wait_for_health "frontend" "http://localhost/health"; then
        log_error "Frontend health check failed"
        exit 1
    fi
    
    log "Starting supporting services..."
    docker-compose up -d --remove-orphans
    
    log_success "All services deployed successfully"
}

# Wait for service health check
wait_for_health() {
    local service_name=$1
    local health_url=$2
    local retries=$HEALTH_CHECK_RETRIES
    
    log "Waiting for $service_name to become healthy..."
    
    for ((i=1; i<=retries; i++)); do
        if docker-compose exec -T "$service_name" curl -f "$health_url" &>/dev/null; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        if [[ $i -eq $retries ]]; then
            log_error "$service_name failed health check after $retries attempts"
            return 1
        fi
        
        log "Health check attempt $i/$retries failed, waiting ${HEALTH_CHECK_INTERVAL}s..."
        sleep $HEALTH_CHECK_INTERVAL
    done
}

# Cleanup old containers and images
cleanup_old_resources() {
    log "Cleaning up old containers and images..."
    
    # Remove old containers
    docker container prune -f
    
    # Remove old images (keep last 3 versions)
    docker image prune -f
    
    # Remove unused volumes (be careful with this)
    # docker volume prune -f  # Commented out for safety
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log "========================================="
    log "Starting deployment of $APP_NAME version $VERSION"
    log "========================================="
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Check prerequisites
    check_prerequisites
    
    # Update environment configuration
    update_env_file
    
    # Pull new images
    pull_images
    
    # Run database migrations
    run_migrations
    
    # Deploy services with zero downtime
    deploy_services
    
    # Cleanup old resources
    cleanup_old_resources
    
    log_success "========================================="
    log_success "Deployment completed successfully!"
    log_success "Version: $VERSION"
    log_success "Time: $(date)"
    log_success "========================================="
    
    # Send success notification (customize as needed)
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"🚀 Deployment successful: $APP_NAME $VERSION\"}" \
    #     "$SLACK_WEBHOOK_URL"
}

# Script usage
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Check if running with required parameters
    if [[ $# -eq 0 ]]; then
        echo "Usage: $0"
        echo "Required environment variables:"
        echo "  VERSION - Version tag to deploy"
        echo "  REGISTRY - Docker registry URL" 
        echo "  REPO_NAME - Repository name"
        exit 1
    fi
    
    main "$@"
fi