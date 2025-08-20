# Docker Compose Deployment Guide

This guide covers deploying the AI Passport Photo Generator application using Docker Compose for containerized deployment.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Minimum 2 CPU cores, 4GB RAM, 20GB storage
- Domain name (optional but recommended for production)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/mwqq.git
cd mwqq
```

### 2. Environment Configuration

Create environment files for production:

```bash
# Create backend environment file
cat > backend/passport_photo/.env << EOF
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost,127.0.0.1,frontend
DATABASE_URL=postgresql://postgres:your_db_password@db:5432/passport_photo
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
STATIC_URL=/static/
STATIC_ROOT=/app/staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=/app/media
EOF

# Update docker-compose.yml with secure passwords
sed -i 's/password/your_secure_db_password/g' docker-compose.yml
sed -i 's/your-secret-key-change-in-production/your-actual-secret-key/g' docker-compose.yml
```

### 3. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Initialize Database

```bash
# Run database migrations
docker-compose exec backend python manage.py migrate

# Create superuser (optional)
docker-compose exec backend python manage.py createsuperuser

# Load initial data (if available)
docker-compose exec backend python manage.py loaddata fixtures/countries.json
```

### 5. Access Application

- Frontend: http://localhost
- Backend API: http://localhost/api/
- Admin Panel: http://localhost/api/admin/

## Production Deployment

### 1. Production Configuration

Update `docker-compose.yml` for production:

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    # Remove port mapping for production (handled by nginx-proxy)
    depends_on:
      - backend
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  backend:
    build:
      context: ./backend/passport_photo
      dockerfile: Dockerfile
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/passport_photo
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
    env_file:
      - backend/passport_photo/.env
    depends_on:
      - db
      - redis
    networks:
      - app-network
    restart: unless-stopped
    volumes:
      - media_files:/app/media
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ... rest of services
```

### 2. SSL/HTTPS Setup

Create SSL configuration:

```bash
# Create nginx-proxy.conf for HTTPS
cat > nginx-proxy.conf << EOF
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # File upload settings
        client_max_body_size 10M;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://\$server_name\$request_uri;
}
EOF
```

### 3. SSL Certificate with Let's Encrypt

```bash
# Create SSL directory
mkdir -p ssl

# Using Certbot with Docker
docker run -it --rm --name certbot \
  -v "$PWD/ssl:/etc/letsencrypt" \
  -v "$PWD/ssl:/var/lib/letsencrypt" \
  -p 80:80 \
  certbot/certbot certonly --standalone \
  -d your-domain.com -d www.your-domain.com \
  --email your-email@domain.com \
  --agree-tos --no-eff-email

# Copy certificates to nginx directory
cp ssl/live/your-domain.com/fullchain.pem ssl/
cp ssl/live/your-domain.com/privkey.pem ssl/
```

### 4. Start Production Environment

```bash
# Start with production profile
docker-compose --profile production up -d

# Or start all services
docker-compose up -d
```

## Container Management

### Service Control

```bash
# Start services
docker-compose start

# Stop services
docker-compose stop

# Restart specific service
docker-compose restart backend

# Scale services
docker-compose up -d --scale celery-worker=3

# View service logs
docker-compose logs -f backend
docker-compose logs --tail=100 frontend

# Execute commands in containers
docker-compose exec backend python manage.py shell
docker-compose exec db psql -U postgres -d passport_photo
```

### Health Checks

```bash
# Check all service health
docker-compose ps

# Individual service health
docker inspect $(docker-compose ps -q backend) --format='{{.State.Health.Status}}'

# View health check logs
docker inspect $(docker-compose ps -q backend) --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
```

## Data Management

### Database Operations

```bash
# Create database backup
docker-compose exec db pg_dump -U postgres passport_photo > backup.sql

# Restore database backup
docker-compose exec -T db psql -U postgres passport_photo < backup.sql

# Reset database
docker-compose down -v  # Remove all data
docker-compose up -d db
docker-compose exec backend python manage.py migrate
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect mwqq_postgres_data

# Backup volumes
docker run --rm -v mwqq_postgres_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v mwqq_postgres_data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/postgres_backup.tar.gz -C /data
```

### Media Files

```bash
# Backup media files
docker run --rm -v mwqq_media_files:/data -v $(pwd):/backup alpine \
  tar czf /backup/media_backup.tar.gz -C /data .

# View media files
docker-compose exec backend ls -la /app/media/
```

## Monitoring and Logging

### Application Logs

```bash
# View all logs
docker-compose logs

# Follow logs for specific service
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 celery-worker

# Filter logs by timestamp
docker-compose logs --since="2024-01-01T00:00:00"
```

### Resource Monitoring

```bash
# View resource usage
docker stats

# View specific container resources
docker stats $(docker-compose ps -q)

# System resource usage
docker system df
```

### Performance Monitoring

Add monitoring stack to `docker-compose.yml`:

```yaml
  # Prometheus monitoring
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - app-network
    profiles:
      - monitoring

  # Grafana dashboard
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - app-network
    profiles:
      - monitoring
```

## Updates and Maintenance

### Application Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart services
docker-compose build --no-cache
docker-compose up -d

# Run database migrations
docker-compose exec backend python manage.py migrate

# Collect static files
docker-compose exec backend python manage.py collectstatic --noinput
```

### Container Updates

```bash
# Pull latest base images
docker-compose pull

# Rebuild with latest base images
docker-compose build --pull --no-cache

# Restart with updated containers
docker-compose up -d
```

### Cleanup

```bash
# Remove unused containers, networks, images
docker system prune -f

# Remove unused volumes (be careful!)
docker volume prune

# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a
```

## Security Best Practices

### Container Security

1. **Use Non-root Users**
   ```dockerfile
   # In Dockerfile
   RUN addgroup -S appgroup && adduser -S appuser -G appgroup
   USER appuser
   ```

2. **Environment Variables**
   ```bash
   # Use .env files, not hardcoded values
   echo "SECRET_KEY=generated-secret" >> .env
   ```

3. **Network Security**
   ```yaml
   # Use custom networks
   networks:
     app-network:
       driver: bridge
       internal: true  # Isolate from external networks
   ```

### SSL/TLS Configuration

```bash
# Generate strong DH parameters
openssl dhparam -out ssl/dhparam.pem 4096

# Add to nginx configuration
ssl_dhparam /etc/ssl/certs/dhparam.pem;
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "8080:80"  # Use different port
   ```

2. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER ./
   
   # Fix container permissions
   docker-compose exec backend chown -R www-data:www-data /app/media
   ```

3. **Database Connection Issues**
   ```bash
   # Check database container
   docker-compose exec db pg_isready -U postgres
   
   # Check connection from backend
   docker-compose exec backend python manage.py dbshell
   ```

4. **Memory Issues**
   ```bash
   # Increase memory limits
   deploy:
     resources:
       limits:
         memory: 1G
   ```

### Debugging

```bash
# Debug specific service
docker-compose exec backend bash

# View container processes
docker-compose exec backend ps aux

# Check network connectivity
docker-compose exec backend ping db
docker-compose exec frontend wget -O- http://backend:8000/health/
```

## Backup Strategy

### Automated Backups

Create backup script:

```bash
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database backup
docker-compose exec -T db pg_dump -U postgres passport_photo > $BACKUP_DIR/database.sql

# Media files backup
docker run --rm -v mwqq_media_files:/data -v $BACKUP_DIR:/backup alpine \
  tar czf /backup/media.tar.gz -C /data .

# Application config backup
tar czf $BACKUP_DIR/config.tar.gz docker-compose.yml nginx.conf .env

echo "Backup completed: $BACKUP_DIR"
```

### Restore Procedure

```bash
# Stop services
docker-compose down

# Restore database
docker-compose up -d db
docker-compose exec -T db psql -U postgres passport_photo < backup/database.sql

# Restore media files
docker run --rm -v mwqq_media_files:/data -v backup:/backup alpine \
  tar xzf /backup/media.tar.gz -C /data

# Start all services
docker-compose up -d
```

This Docker deployment provides a scalable, maintainable, and portable solution for the AI Passport Photo Generator application.