#!/bin/bash

# Rollback Script for MWQQ Passport Photo Application
# This script handles automatic rollback to previous working state

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Configuration
APP_NAME="mwqq"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
LOG_FILE="${LOG_FILE:-/var/log/${APP_NAME}/rollback.log}"
COMPOSE_FILE="docker-compose.yml"
ROLLBACK_TIMEOUT=300  # Maximum rollback time in seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Find the latest backup
find_latest_backup() {
    log "Searching for latest backup..."
    
    local latest_backup=$(find "$BACKUP_DIR" -maxdepth 1 -name "${APP_NAME}_backup_*" -type d -printf '%T+ %p\n' | sort -r | head -n 1 | cut -d' ' -f2-)
    
    if [[ -z "$latest_backup" ]]; then
        log_error "No backup found in $BACKUP_DIR"
        return 1
    fi
    
    if [[ ! -d "$latest_backup" ]]; then
        log_error "Backup directory not found: $latest_backup"
        return 1
    fi
    
    log_success "Latest backup found: $latest_backup"
    echo "$latest_backup"
}

# Find specific backup by name or timestamp
find_backup_by_name() {
    local backup_name=$1
    log "Searching for backup: $backup_name"
    
    local backup_path="$BACKUP_DIR/$backup_name"
    
    if [[ ! -d "$backup_path" ]]; then
        # Try to find partial match
        local found_backup=$(find "$BACKUP_DIR" -maxdepth 1 -name "*${backup_name}*" -type d | head -n 1)
        if [[ -n "$found_backup" ]]; then
            backup_path="$found_backup"
        else
            log_error "Backup not found: $backup_name"
            return 1
        fi
    fi
    
    log_success "Backup found: $backup_path"
    echo "$backup_path"
}

# Stop current services gracefully
stop_current_services() {
    log "Stopping current services..."
    
    # Try graceful stop first
    if docker-compose down --timeout 30; then
        log_success "Services stopped gracefully"
    else
        log_warning "Graceful stop failed, forcing stop..."
        docker-compose kill
        docker-compose rm -f
        log_success "Services force stopped"
    fi
}

# Restore database from backup
restore_database() {
    local backup_path=$1
    log "Restoring database from backup..."
    
    local db_backup="$backup_path/database/postgres_backup.sql.gz"
    
    if [[ ! -f "$db_backup" ]]; then
        log_error "Database backup not found: $db_backup"
        return 1
    fi
    
    # Start only database service
    docker-compose up -d db
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "Database failed to become ready for restore"
            return 1
        fi
        sleep 2
    done
    
    # Stop database to perform clean restore
    docker-compose stop db
    
    # Remove current database data
    log_warning "Removing current database data..."
    docker-compose run --rm --entrypoint="" db rm -rf /var/lib/postgresql/data/*
    
    # Start database again
    docker-compose up -d db
    
    # Wait for database initialization
    log "Waiting for database initialization..."
    for i in {1..60}; do
        if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
            break
        fi
        if [[ $i -eq 60 ]]; then
            log_error "Database initialization failed"
            return 1
        fi
        sleep 2
    done
    
    # Restore database
    log "Restoring database data..."
    if gunzip -c "$db_backup" | docker-compose exec -T db psql -U postgres; then
        log_success "Database restored successfully"
    else
        log_error "Database restore failed"
        return 1
    fi
}

# Restore Redis data from backup
restore_redis() {
    local backup_path=$1
    log "Restoring Redis from backup..."
    
    local redis_backup="$backup_path/redis/redis_backup.rdb.gz"
    
    if [[ ! -f "$redis_backup" ]]; then
        log_warning "Redis backup not found, skipping Redis restore"
        return 0
    fi
    
    # Stop Redis service
    docker-compose stop redis
    
    # Restore Redis data
    local temp_rdb="/tmp/dump.rdb"
    gunzip -c "$redis_backup" > "$temp_rdb"
    
    # Copy the RDB file to Redis data directory
    docker-compose run --rm --entrypoint="" redis cp "$temp_rdb" /data/dump.rdb
    
    # Start Redis
    docker-compose up -d redis
    
    # Verify Redis is working
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis restored successfully"
        rm -f "$temp_rdb"
    else
        log_error "Redis restore verification failed"
        rm -f "$temp_rdb"
        return 1
    fi
}

# Restore application configuration
restore_application_config() {
    local backup_path=$1
    log "Restoring application configuration..."
    
    local config_backup_dir="$backup_path/application"
    
    if [[ ! -d "$config_backup_dir" ]]; then
        log_error "Application config backup not found"
        return 1
    fi
    
    # Backup current config files
    local timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "/tmp/config_backup_$timestamp"
    
    # Restore environment files
    if [[ -f "$config_backup_dir/env.backup" ]]; then
        [[ -f ".env" ]] && cp ".env" "/tmp/config_backup_$timestamp/"
        cp "$config_backup_dir/env.backup" ".env"
        log_success "Environment file restored"
    fi
    
    if [[ -f "$config_backup_dir/env.production.backup" ]]; then
        [[ -f ".env.production" ]] && cp ".env.production" "/tmp/config_backup_$timestamp/"
        cp "$config_backup_dir/env.production.backup" ".env.production"
        log_success "Production environment file restored"
    fi
    
    # Restore docker-compose files if they exist in backup
    if [[ -f "$config_backup_dir/docker-compose.yml.backup" ]]; then
        [[ -f "docker-compose.yml" ]] && cp "docker-compose.yml" "/tmp/config_backup_$timestamp/"
        cp "$config_backup_dir/docker-compose.yml.backup" "docker-compose.yml"
        log_success "Docker Compose file restored"
    fi
    
    if [[ -f "$config_backup_dir/docker-compose.prod.yml.backup" ]]; then
        [[ -f "docker-compose.prod.yml" ]] && cp "docker-compose.prod.yml" "/tmp/config_backup_$timestamp/"
        cp "$config_backup_dir/docker-compose.prod.yml.backup" "docker-compose.prod.yml"
        log_success "Production Docker Compose file restored"
    fi
    
    # Restore SSL certificates
    if [[ -d "$config_backup_dir/ssl" ]]; then
        [[ -d "ssl" ]] && cp -r "ssl" "/tmp/config_backup_$timestamp/"
        cp -r "$config_backup_dir/ssl" "./"
        log_success "SSL certificates restored"
    fi
    
    log_success "Application configuration restored"
    log "Current config backed up to: /tmp/config_backup_$timestamp"
}

# Restore media files
restore_media_files() {
    local backup_path=$1
    log "Restoring media files..."
    
    local media_backup_dir="$backup_path/media"
    
    if [[ ! -d "$media_backup_dir" ]]; then
        log_warning "Media backup not found, skipping media restore"
        return 0
    fi
    
    # Restore media directories
    local media_dirs=("media" "uploads" "static" "public")
    
    for dir in "${media_dirs[@]}"; do
        if [[ -d "$media_backup_dir/$dir" ]]; then
            if [[ -d "$dir" ]]; then
                log_warning "Backing up current $dir directory"
                mv "$dir" "${dir}.backup.$(date +%Y%m%d_%H%M%S)"
            fi
            cp -r "$media_backup_dir/$dir" "./"
            log_success "$dir directory restored"
        fi
    done
}

# Start services with previous configuration
start_services_from_backup() {
    local backup_path=$1
    log "Starting services from backup configuration..."
    
    # Use the docker info from backup to determine what services to start
    local container_status="$backup_path/docker/container_status.txt"
    
    if [[ -f "$container_status" ]]; then
        log "Previous container status:"
        cat "$container_status" | tee -a "$LOG_FILE"
    fi
    
    # Start core services first
    log "Starting database and Redis..."
    docker-compose up -d db redis
    
    # Wait for core services
    sleep 10
    
    log "Starting application services..."
    docker-compose up -d backend celery-worker
    
    # Wait for backend
    sleep 15
    
    log "Starting frontend and other services..."
    docker-compose up -d --remove-orphans
    
    log_success "All services started"
}

# Verify rollback success
verify_rollback() {
    log "Verifying rollback success..."
    
    # Run health checks
    if command -v ./scripts/health-check.sh &> /dev/null; then
        log "Running health checks..."
        if ./scripts/health-check.sh --timeout 60; then
            log_success "Health checks passed"
            return 0
        else
            log_error "Health checks failed after rollback"
            return 1
        fi
    else
        log_warning "Health check script not found, performing basic verification"
        
        # Basic container status check
        local failed_containers=0
        while IFS= read -r service; do
            if [[ -n "$service" ]]; then
                if docker-compose ps "$service" | grep -q "Up"; then
                    log_success "Service $service is running"
                else
                    log_error "Service $service is not running"
                    ((failed_containers++))
                fi
            fi
        done < <(docker-compose config --services)
        
        if [[ $failed_containers -eq 0 ]]; then
            log_success "All services are running"
            return 0
        else
            log_error "$failed_containers services failed to start"
            return 1
        fi
    fi
}

# List available backups
list_backups() {
    log "Available backups:"
    echo "========================================"
    
    find "$BACKUP_DIR" -maxdepth 1 -name "${APP_NAME}_backup_*" -type d -printf '%TY-%Tm-%Td %TH:%TM %p\n' | sort -r | while read -r date time backup_path; do
        local backup_name=$(basename "$backup_path")
        local backup_size=$(du -sh "$backup_path" 2>/dev/null | cut -f1 || echo "unknown")
        
        echo "$date $time - $backup_name ($backup_size)"
        
        # Show backup contents
        if [[ -f "$backup_path/BACKUP_MANIFEST.txt" ]]; then
            echo "  Contains: $(grep -A 20 "Contents:" "$backup_path/BACKUP_MANIFEST.txt" | tail -n +2 | head -3 | wc -l) files"
        fi
    done
    
    echo "========================================"
}

# Perform complete rollback
rollback() {
    local backup_path=$1
    local start_time=$(date +%s)
    
    log "========================================="
    log "Starting rollback process for $APP_NAME"
    log "Using backup: $(basename "$backup_path")"
    log "========================================="
    
    # Stop current services
    stop_current_services
    
    # Restore from backup
    restore_application_config "$backup_path"
    restore_database "$backup_path"
    restore_redis "$backup_path"
    restore_media_files "$backup_path"
    
    # Start services
    start_services_from_backup "$backup_path"
    
    # Verify rollback
    if verify_rollback; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "========================================="
        log_success "Rollback completed successfully!"
        log_success "Duration: ${duration}s"
        log_success "Application restored to previous working state"
        log "========================================="
    else
        log_error "Rollback verification failed"
        log_error "Manual intervention may be required"
        return 1
    fi
}

# Main function
main() {
    local backup_name=""
    local list_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--backup)
                backup_name="$2"
                shift 2
                ;;
            -l|--list)
                list_only=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # List backups if requested
    if [[ "$list_only" == true ]]; then
        list_backups
        exit 0
    fi
    
    # Find backup to use
    local backup_path
    if [[ -n "$backup_name" ]]; then
        backup_path=$(find_backup_by_name "$backup_name")
    else
        backup_path=$(find_latest_backup)
    fi
    
    if [[ -z "$backup_path" ]]; then
        log_error "No suitable backup found"
        exit 1
    fi
    
    # Perform rollback
    rollback "$backup_path"
}

# Show usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -b, --backup NAME       Use specific backup (default: latest)"
    echo "  -l, --list              List available backups and exit"
    echo ""
    echo "Examples:"
    echo "  $0                              # Rollback to latest backup"
    echo "  $0 --list                       # List available backups"
    echo "  $0 --backup mwqq_backup_20240825_143022  # Use specific backup"
}

# Run the main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi