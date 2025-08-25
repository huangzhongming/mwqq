#!/bin/bash

# Backup Script for MWQQ Passport Photo Application
# This script creates comprehensive backups before deployment

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Configuration
APP_NAME="mwqq"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${APP_NAME}_backup_${TIMESTAMP}"
DB_CONTAINER="db"
REDIS_CONTAINER="redis"
MAX_BACKUPS=10  # Keep last 10 backups

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ $1${NC}"
}

# Create backup directory structure
create_backup_directory() {
    log "Creating backup directory structure..."
    
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"/{database,redis,application,docker}
    
    if [[ ! -d "$BACKUP_DIR/$BACKUP_NAME" ]]; then
        log_error "Failed to create backup directory"
        exit 1
    fi
    
    log_success "Backup directory created: $BACKUP_DIR/$BACKUP_NAME"
}

# Backup PostgreSQL database
backup_database() {
    log "Backing up PostgreSQL database..."
    
    local backup_file="$BACKUP_DIR/$BACKUP_NAME/database/postgres_backup.sql"
    
    # Check if database container is running
    if ! docker-compose ps | grep -q "$DB_CONTAINER.*Up"; then
        log_error "Database container is not running"
        return 1
    fi
    
    # Create database backup
    if docker-compose exec -T "$DB_CONTAINER" pg_dumpall -U postgres > "$backup_file"; then
        # Compress the backup
        gzip "$backup_file"
        log_success "Database backup created: ${backup_file}.gz"
        
        # Get backup size
        local backup_size=$(du -h "${backup_file}.gz" | cut -f1)
        log "Database backup size: $backup_size"
    else
        log_error "Failed to create database backup"
        return 1
    fi
}

# Backup Redis data
backup_redis() {
    log "Backing up Redis data..."
    
    local backup_file="$BACKUP_DIR/$BACKUP_NAME/redis/redis_backup.rdb"
    
    # Check if Redis container is running
    if ! docker-compose ps | grep -q "$REDIS_CONTAINER.*Up"; then
        log_warning "Redis container is not running, skipping Redis backup"
        return 0
    fi
    
    # Save Redis data
    if docker-compose exec -T "$REDIS_CONTAINER" redis-cli BGSAVE; then
        # Wait for background save to complete
        local save_in_progress=1
        while [[ $save_in_progress -eq 1 ]]; do
            if docker-compose exec -T "$REDIS_CONTAINER" redis-cli PING | grep -q "PONG"; then
                save_in_progress=0
            fi
            sleep 1
        done
        
        # Copy the RDB file
        docker-compose exec -T "$REDIS_CONTAINER" cat /data/dump.rdb > "$backup_file"
        
        # Compress the backup
        gzip "$backup_file"
        log_success "Redis backup created: ${backup_file}.gz"
        
        # Get backup size
        local backup_size=$(du -h "${backup_file}.gz" | cut -f1)
        log "Redis backup size: $backup_size"
    else
        log_error "Failed to create Redis backup"
        return 1
    fi
}

# Backup application configuration and environment files
backup_application_config() {
    log "Backing up application configuration..."
    
    local config_backup_dir="$BACKUP_DIR/$BACKUP_NAME/application"
    
    # Backup environment files
    if [[ -f ".env" ]]; then
        cp ".env" "$config_backup_dir/env.backup"
        log_success "Environment file backed up"
    fi
    
    if [[ -f ".env.production" ]]; then
        cp ".env.production" "$config_backup_dir/env.production.backup"
        log_success "Production environment file backed up"
    fi
    
    # Backup docker-compose files
    if [[ -f "docker-compose.yml" ]]; then
        cp "docker-compose.yml" "$config_backup_dir/docker-compose.yml.backup"
        log_success "Docker Compose file backed up"
    fi
    
    if [[ -f "docker-compose.prod.yml" ]]; then
        cp "docker-compose.prod.yml" "$config_backup_dir/docker-compose.prod.yml.backup"
        log_success "Production Docker Compose file backed up"
    fi
    
    # Backup SSL certificates if they exist
    if [[ -d "ssl" ]]; then
        cp -r "ssl" "$config_backup_dir/"
        log_success "SSL certificates backed up"
    fi
    
    # Backup any custom configuration files
    for config_file in nginx.conf uwsgi.ini celery.conf; do
        if [[ -f "$config_file" ]]; then
            cp "$config_file" "$config_backup_dir/"
            log_success "$config_file backed up"
        fi
    done
}

# Backup Docker images and containers info
backup_docker_info() {
    log "Backing up Docker information..."
    
    local docker_backup_dir="$BACKUP_DIR/$BACKUP_NAME/docker"
    
    # Save current container status
    docker-compose ps > "$docker_backup_dir/container_status.txt"
    
    # Save current images
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" > "$docker_backup_dir/images.txt"
    
    # Save docker-compose config
    docker-compose config > "$docker_backup_dir/compose_config.yml"
    
    # Save container logs (last 1000 lines)
    mkdir -p "$docker_backup_dir/logs"
    for container in $(docker-compose ps --services); do
        if docker-compose ps | grep -q "$container.*Up"; then
            docker-compose logs --tail=1000 "$container" > "$docker_backup_dir/logs/${container}.log" 2>&1 || true
        fi
    done
    
    log_success "Docker information backed up"
}

# Backup uploaded files and media
backup_media_files() {
    log "Backing up media files..."
    
    local media_backup_dir="$BACKUP_DIR/$BACKUP_NAME/media"
    mkdir -p "$media_backup_dir"
    
    # Look for common media directories
    local media_dirs=("media" "uploads" "static" "public")
    
    for dir in "${media_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            cp -r "$dir" "$media_backup_dir/"
            log_success "$dir directory backed up"
        fi
    done
    
    # Backup Docker volume data if mounted
    local volumes=$(docker-compose config --volumes 2>/dev/null || true)
    if [[ -n "$volumes" ]]; then
        log "Found Docker volumes: $volumes"
        # Note: Volume backup would require more complex logic based on volume types
        log_warning "Docker volume backup not implemented - consider manual backup if needed"
    fi
}

# Create backup manifest
create_backup_manifest() {
    log "Creating backup manifest..."
    
    local manifest_file="$BACKUP_DIR/$BACKUP_NAME/BACKUP_MANIFEST.txt"
    
    cat > "$manifest_file" << EOF
MWQQ Application Backup Manifest
================================

Backup Name: $BACKUP_NAME
Timestamp: $(date)
Application: $APP_NAME
Backup Directory: $BACKUP_DIR/$BACKUP_NAME

Contents:
$(find "$BACKUP_DIR/$BACKUP_NAME" -type f -exec ls -lh {} \; | awk '{print $9, $5}' | sort)

Total Backup Size: $(du -sh "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)

Database Status:
$(docker-compose exec -T db pg_isready -U postgres 2>/dev/null || echo "Database not available")

Redis Status:
$(docker-compose exec -T redis redis-cli ping 2>/dev/null || echo "Redis not available")

Container Status:
$(docker-compose ps)

System Info:
Hostname: $(hostname)
User: $(whoami)
Disk Usage: $(df -h / | awk 'NR==2 {print $5}')
Memory Usage: $(free -h | awk 'NR==2{print $3"/"$2}')

EOF
    
    log_success "Backup manifest created"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Keep only the most recent backups
    local backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -name "${APP_NAME}_backup_*" -type d | wc -l)
    
    if [[ $backup_count -gt $MAX_BACKUPS ]]; then
        local backups_to_remove=$((backup_count - MAX_BACKUPS))
        log "Found $backup_count backups, removing oldest $backups_to_remove"
        
        find "$BACKUP_DIR" -maxdepth 1 -name "${APP_NAME}_backup_*" -type d -printf '%T+ %p\n' | \
            sort | head -n "$backups_to_remove" | cut -d' ' -f2- | \
            while read -r old_backup; do
                rm -rf "$old_backup"
                log_success "Removed old backup: $(basename "$old_backup")"
            done
    else
        log "Current backup count ($backup_count) is within limit ($MAX_BACKUPS)"
    fi
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    local backup_path="$BACKUP_DIR/$BACKUP_NAME"
    local errors=0
    
    # Check if all expected directories exist
    local expected_dirs=("database" "application" "docker")
    for dir in "${expected_dirs[@]}"; do
        if [[ ! -d "$backup_path/$dir" ]]; then
            log_error "Missing backup directory: $dir"
            ((errors++))
        fi
    done
    
    # Check if database backup exists and is not empty
    if [[ -f "$backup_path/database/postgres_backup.sql.gz" ]]; then
        if [[ ! -s "$backup_path/database/postgres_backup.sql.gz" ]]; then
            log_error "Database backup file is empty"
            ((errors++))
        fi
    else
        log_error "Database backup file not found"
        ((errors++))
    fi
    
    # Check backup manifest
    if [[ ! -f "$backup_path/BACKUP_MANIFEST.txt" ]]; then
        log_error "Backup manifest not found"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Backup verification passed"
        return 0
    else
        log_error "Backup verification failed with $errors errors"
        return 1
    fi
}

# Main backup function
main() {
    log "========================================="
    log "Starting backup process for $APP_NAME"
    log "========================================="
    
    # Create backup directory
    create_backup_directory
    
    # Perform all backups
    backup_database
    backup_redis
    backup_application_config
    backup_docker_info
    backup_media_files
    
    # Create manifest and verify
    create_backup_manifest
    verify_backup
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "========================================="
    log_success "Backup process completed successfully!"
    log_success "Backup location: $BACKUP_DIR/$BACKUP_NAME"
    log_success "Total size: $(du -sh "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)"
    log "========================================="
    
    # Return backup path for use by other scripts
    echo "$BACKUP_DIR/$BACKUP_NAME"
}

# Show usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help                Show this help message"
    echo "  -d, --backup-dir DIR      Set backup directory (default: $BACKUP_DIR)"
    echo "  -n, --name NAME           Set backup name prefix (default: $APP_NAME)"
    echo "  -k, --keep COUNT          Number of backups to keep (default: $MAX_BACKUPS)"
    echo "  --skip-db                 Skip database backup"
    echo "  --skip-redis              Skip Redis backup"
    echo "  --skip-media              Skip media files backup"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run full backup"
    echo "  $0 --backup-dir /custom/backup       # Use custom backup directory"
    echo "  $0 --skip-redis                      # Skip Redis backup"
}

# Parse command line arguments
SKIP_DB=false
SKIP_REDIS=false
SKIP_MEDIA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--backup-dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -n|--name)
            APP_NAME="$2"
            BACKUP_NAME="${APP_NAME}_backup_${TIMESTAMP}"
            shift 2
            ;;
        -k|--keep)
            MAX_BACKUPS="$2"
            shift 2
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-redis)
            SKIP_REDIS=true
            shift
            ;;
        --skip-media)
            SKIP_MEDIA=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run the main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi