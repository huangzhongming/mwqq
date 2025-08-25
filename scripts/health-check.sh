#!/bin/bash

# Health Check Script for MWQQ Passport Photo Application
# This script validates that all services are healthy after deployment

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# Configuration
APP_NAME="mwqq"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost"
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=5

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

# Check if a service is responding
check_service_health() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-$HEALTH_CHECK_TIMEOUT}
    
    log "Checking health of $service_name..."
    
    local start_time=$(date +%s)
    local end_time=$((start_time + timeout))
    
    while [[ $(date +%s) -lt $end_time ]]; do
        if curl -f -s --max-time 10 "$health_url" >/dev/null 2>&1; then
            log_success "$service_name is healthy"
            return 0
        fi
        
        log "Waiting for $service_name to respond... (timeout in $((end_time - $(date +%s)))s)"
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    log_error "$service_name health check failed (timeout after ${timeout}s)"
    return 1
}

# Check Docker containers status
check_containers() {
    log "Checking Docker containers status..."
    
    local failed_containers=()
    
    # Get all running containers for the application
    while IFS= read -r container; do
        if [[ -n "$container" ]]; then
            local container_name=$(echo "$container" | awk '{print $1}')
            local container_status=$(echo "$container" | awk '{print $3}')
            
            if [[ "$container_status" != *"Up"* ]]; then
                failed_containers+=("$container_name")
                log_error "Container $container_name is not running: $container_status"
            else
                log_success "Container $container_name is running"
            fi
        fi
    done < <(docker-compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}" | tail -n +2)
    
    if [[ ${#failed_containers[@]} -gt 0 ]]; then
        log_error "Failed containers: ${failed_containers[*]}"
        return 1
    fi
    
    log_success "All containers are running"
    return 0
}

# Check database connectivity
check_database() {
    log "Checking database connectivity..."
    
    if docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        log_success "Database is accessible"
        return 0
    else
        log_error "Database is not accessible"
        return 1
    fi
}

# Check Redis connectivity
check_redis() {
    log "Checking Redis connectivity..."
    
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis is accessible"
        return 0
    else
        log_error "Redis is not accessible"
        return 1
    fi
}

# Check application-specific endpoints
check_application_endpoints() {
    log "Checking application-specific endpoints..."
    
    # Check backend API endpoints
    local backend_endpoints=(
        "/health/"
        "/api/v1/"
        "/api/v1/auth/"
    )
    
    for endpoint in "${backend_endpoints[@]}"; do
        local url="${BACKEND_URL}${endpoint}"
        if curl -f -s --max-time 10 "$url" >/dev/null 2>&1; then
            log_success "Backend endpoint $endpoint is accessible"
        else
            log_error "Backend endpoint $endpoint is not accessible"
            return 1
        fi
    done
    
    # Check frontend
    if curl -f -s --max-time 10 "$FRONTEND_URL" >/dev/null 2>&1; then
        log_success "Frontend is accessible"
    else
        log_error "Frontend is not accessible"
        return 1
    fi
    
    return 0
}

# Check disk space
check_disk_space() {
    log "Checking disk space..."
    
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $disk_usage -gt 90 ]]; then
        log_error "Disk usage is critical: ${disk_usage}%"
        return 1
    elif [[ $disk_usage -gt 80 ]]; then
        log_warning "Disk usage is high: ${disk_usage}%"
    else
        log_success "Disk usage is normal: ${disk_usage}%"
    fi
    
    return 0
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Check memory usage
    local memory_usage=$(free | awk 'NR==2{printf "%.2f", $3/$2*100}')
    if (( $(echo "$memory_usage > 90" | bc -l) )); then
        log_error "Memory usage is critical: ${memory_usage}%"
        return 1
    elif (( $(echo "$memory_usage > 80" | bc -l) )); then
        log_warning "Memory usage is high: ${memory_usage}%"
    else
        log_success "Memory usage is normal: ${memory_usage}%"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    local cpu_usage=$(echo "scale=2; $cpu_load / $cpu_cores * 100" | bc)
    
    if (( $(echo "$cpu_usage > 90" | bc -l) )); then
        log_error "CPU usage is critical: ${cpu_usage}%"
        return 1
    elif (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_warning "CPU usage is high: ${cpu_usage}%"
    else
        log_success "CPU usage is normal: ${cpu_usage}%"
    fi
    
    return 0
}

# Comprehensive health check
main() {
    log "========================================="
    log "Starting comprehensive health check for $APP_NAME"
    log "========================================="
    
    local failed_checks=0
    
    # Run all health checks
    check_containers || ((failed_checks++))
    check_database || ((failed_checks++))
    check_redis || ((failed_checks++))
    check_service_health "Backend" "$BACKEND_URL/health/" || ((failed_checks++))
    check_application_endpoints || ((failed_checks++))
    check_disk_space || ((failed_checks++))
    check_system_resources || ((failed_checks++))
    
    log "========================================="
    
    if [[ $failed_checks -eq 0 ]]; then
        log_success "All health checks passed! 🎉"
        log_success "Application is healthy and ready to serve traffic"
        exit 0
    else
        log_error "$failed_checks health check(s) failed"
        log_error "Application may not be ready to serve traffic"
        exit 1
    fi
}

# Show usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -t, --timeout SECONDS   Set health check timeout (default: $HEALTH_CHECK_TIMEOUT)"
    echo "  -i, --interval SECONDS  Set health check interval (default: $HEALTH_CHECK_INTERVAL)"
    echo "  --backend-url URL       Set backend URL (default: $BACKEND_URL)"
    echo "  --frontend-url URL      Set frontend URL (default: $FRONTEND_URL)"
    echo ""
    echo "Examples:"
    echo "  $0                                # Run with default settings"
    echo "  $0 --timeout 60                  # Wait up to 60 seconds for each check"
    echo "  $0 --backend-url http://api.local # Use custom backend URL"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -t|--timeout)
            HEALTH_CHECK_TIMEOUT="$2"
            shift 2
            ;;
        -i|--interval)
            HEALTH_CHECK_INTERVAL="$2"
            shift 2
            ;;
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --frontend-url)
            FRONTEND_URL="$2"
            shift 2
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