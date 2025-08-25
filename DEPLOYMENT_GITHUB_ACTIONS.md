# GitHub Actions Deployment Guide for MWQQ Passport Photo Application

## 📋 Overview

This guide provides comprehensive instructions for deploying the MWQQ Passport Photo Application using GitHub Actions with automated CI/CD pipeline. The deployment system supports tag-based releases with zero-downtime deployment, automatic health checks, and rollback capabilities.

## 🏗️ Architecture

### Deployment Flow
```
Developer → Git Tag → GitHub Actions → Docker Build → Deploy → Health Check → Success/Rollback
```

### Components
- **GitHub Actions Workflows**: Automated CI/CD pipelines
- **Docker Containers**: Application containerization
- **MySQL 8.0**: Primary database
- **Redis**: Caching and message broker
- **Nginx**: Reverse proxy and SSL termination
- **Celery**: Background task processing
- **Health Monitoring**: Automated health checks and rollback

## 🚀 Quick Start

### 1. Initial Setup
```bash
# Clone the repository
git clone https://github.com/your-org/mwqq.git
cd mwqq

# Switch to the deployment branch
git checkout feature/github-actions-deployment

# Review the deployment files
ls -la .github/workflows/
ls -la scripts/
```

### 2. Server Preparation
```bash
# On your production server
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# Create deployment directory
sudo mkdir -p /opt/mwqq
sudo chown $USER:$USER /opt/mwqq
```

### 3. Configure GitHub Secrets
In your GitHub repository, go to Settings → Secrets and variables → Actions and add:

```
SSH_PRIVATE_KEY=your-ssh-private-key
SSH_USER=deploy
SERVER_HOST=your-server-ip
REGISTRY=ghcr.io
REPO_NAME=mwqq
```

### 4. Deploy
```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0

# Monitor deployment in GitHub Actions tab
```

## 📁 File Structure

```
.github/workflows/
├── deploy.yml          # Main deployment workflow
└── test.yml           # Testing and validation workflow

scripts/
├── deploy.sh          # Server deployment script
├── health-check.sh    # Health validation script
├── backup.sh          # Pre-deployment backup script
└── rollback.sh        # Rollback script

docker-compose.prod.yml  # Production Docker Compose
.env.production         # Production environment template
```

## ⚙️ Configuration Details

### GitHub Actions Workflows

#### 1. Test Workflow (`.github/workflows/test.yml`)
Triggers on:
- Pull requests
- Pushes to main branches

Features:
- Backend testing with MySQL service
- Frontend TypeScript checking
- Security scanning with Trivy
- Docker build testing
- Coverage reporting

#### 2. Deploy Workflow (`.github/workflows/deploy.yml`)
Triggers on:
- Version tags (v*.*.*)

Features:
- Multi-stage deployment (Test → Build → Deploy → Notify)
- Docker image building and pushing
- SSH deployment to production
- Health checks and automatic rollback
- Slack/Discord notifications

### Production Environment

#### Docker Compose Services
- **Frontend**: Nginx-served React application
- **Backend**: Django API server
- **Celery Worker**: Background task processing
- **Celery Beat**: Scheduled task execution
- **MySQL**: Primary database with optimizations
- **Redis**: Caching and message broker
- **Nginx**: SSL termination and load balancing
- **Monitoring**: Prometheus and Grafana (optional)

#### Resource Limits
```yaml
Backend/Celery Worker:
  CPU: 0.5-1.0 cores
  Memory: 512MB-1GB

Database (MySQL):
  CPU: 0.5-1.0 cores
  Memory: 512MB-1GB

Redis:
  CPU: 0.25-0.5 cores
  Memory: 256MB-512MB
```

## 🔧 Setup Instructions

### Step 1: Server Prerequisites

#### System Requirements
- **OS**: Ubuntu 20.04+ or CentOS 8+
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: Minimum 50GB SSD
- **CPU**: Minimum 2 cores, Recommended 4+ cores
- **Network**: Static IP with SSH access

#### Install Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose git curl wget

# CentOS/RHEL
sudo yum update -y
sudo yum install -y docker docker-compose git curl wget

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker deploy
```

#### Create Deploy User
```bash
# Create deployment user
sudo adduser deploy
sudo usermod -aG docker deploy
sudo mkdir -p /home/deploy/.ssh

# Add your SSH public key to /home/deploy/.ssh/authorized_keys
# Set proper permissions
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

### Step 2: Directory Structure
```bash
# Create application directories
sudo mkdir -p /opt/mwqq
sudo mkdir -p /opt/backups
sudo mkdir -p /var/log/mwqq
sudo chown -R deploy:deploy /opt/mwqq /opt/backups /var/log/mwqq

# Create configuration directories
sudo mkdir -p /opt/mwqq/{nginx,ssl,mysql,monitoring}
sudo chown -R deploy:deploy /opt/mwqq
```

### Step 3: SSL Certificates

#### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to application directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/mwqq/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/mwqq/ssl/
sudo chown deploy:deploy /opt/mwqq/ssl/*
```

#### Option B: Self-Signed (Development)
```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/mwqq/ssl/privkey.pem \
    -out /opt/mwqq/ssl/fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=yourdomain.com"
```

### Step 4: Configure GitHub Repository

#### Set Repository Secrets
```bash
# Generate SSH key pair for deployment
ssh-keygen -t rsa -b 4096 -C "deployment@yourdomain.com" -f ~/.ssh/deploy_key

# Add public key to server's authorized_keys
cat ~/.ssh/deploy_key.pub >> /home/deploy/.ssh/authorized_keys
```

Add these secrets in GitHub Settings → Secrets and variables → Actions:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `SSH_PRIVATE_KEY` | Private SSH key for server access | `-----BEGIN RSA PRIVATE KEY-----...` |
| `SSH_USER` | SSH username for deployment | `deploy` |
| `SERVER_HOST` | Production server IP/hostname | `203.0.113.10` |
| `REGISTRY` | Container registry URL | `ghcr.io` |
| `REPO_NAME` | Repository name for images | `mwqq` |
| `MYSQL_ROOT_PASSWORD` | MySQL root password | `super-secure-root-password` |
| `SECRET_KEY` | Django secret key | `django-insecure-change-me...` |
| `SLACK_WEBHOOK` | Slack notification URL (optional) | `https://hooks.slack.com/...` |

### Step 5: Environment Configuration

#### Production Environment File
```bash
# Copy the production environment template
cp .env.production .env

# Edit the environment file with your production values
nano .env
```

Key variables to configure:
```bash
# Application
SECRET_KEY=your-super-secret-key-change-this-in-production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-server-ip

# Database
MYSQL_DATABASE=passport_photo
MYSQL_USER=mwqq_user
MYSQL_PASSWORD=your-secure-mysql-password
MYSQL_ROOT_PASSWORD=your-secure-mysql-root-password
DATABASE_URL=mysql://mwqq_user:password@db:3306/passport_photo

# Redis
REDIS_URL=redis://redis:6379/0

# Domain
DOMAIN_NAME=yourdomain.com
```

## 🚀 Deployment Process

### Manual Deployment
```bash
# 1. Create a version tag
git tag v1.0.0
git push origin v1.0.0

# 2. Monitor GitHub Actions
# Go to: https://github.com/your-org/mwqq/actions

# 3. Check deployment status
curl -f http://your-server/health/
```

### Automated Deployment Flow

1. **Tag Creation**: Developer creates version tag
2. **Trigger**: GitHub Actions workflow triggered by tag
3. **Test Phase**: Run test suite and security scans
4. **Build Phase**: Build and push Docker images
5. **Deploy Phase**: 
   - SSH to production server
   - Create backup
   - Pull new images
   - Update services with zero-downtime
   - Run health checks
6. **Verification**: Automated health checks
7. **Notification**: Success/failure notifications
8. **Rollback**: Automatic rollback on failure

### Zero-Downtime Deployment Strategy

The deployment uses a rolling update strategy:

1. **Database Migration**: Run migrations first
2. **Backend Services**: Update backend and Celery workers
3. **Frontend Service**: Update frontend last
4. **Health Checks**: Verify each service before proceeding
5. **Rollback**: Automatic rollback if any step fails

## 🔍 Monitoring & Health Checks

### Health Check Endpoints
- **Basic Health**: `GET /health/`
- **Detailed Health**: `GET /health/detailed/`
- **Database Health**: `GET /health/db/`
- **Cache Health**: `GET /health/cache/`

### Automated Monitoring
```bash
# Manual health check
./scripts/health-check.sh

# Custom health check with options
./scripts/health-check.sh --timeout 60 --backend-url http://api.yourdomain.com
```

### Service Logs
```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs mysql

# Follow logs in real-time
docker-compose logs -f backend
```

### Performance Monitoring (Optional)

Enable monitoring stack with Prometheus and Grafana:
```bash
# Start monitoring services
docker-compose --profile monitoring up -d

# Access Grafana dashboard
# http://your-server:3000
# Username: admin
# Password: (set in GRAFANA_ADMIN_PASSWORD)
```

## 🔄 Backup & Recovery

### Automated Backups
```bash
# Manual backup
./scripts/backup.sh

# Backup with custom options
./scripts/backup.sh --backup-dir /custom/backup/path --keep 5
```

### Backup Contents
- MySQL database dump
- Redis data snapshot
- Application configuration files
- Media files and uploads
- SSL certificates
- Docker container information

### Restore from Backup
```bash
# List available backups
./scripts/rollback.sh --list

# Rollback to latest backup
./scripts/rollback.sh

# Rollback to specific backup
./scripts/rollback.sh --backup mwqq_backup_20240825_143022
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Deployment Fails at Health Check
```bash
# Check service status
docker-compose ps

# Check service logs
docker-compose logs backend

# Manual health check
curl -f http://localhost/health/

# Check database connectivity
docker-compose exec backend python manage.py dbshell
```

#### 2. Database Connection Issues
```bash
# Check MySQL status
docker-compose exec mysql mysql -u root -p -e "SHOW PROCESSLIST;"

# Check database logs
docker-compose logs mysql

# Verify environment variables
docker-compose exec backend env | grep DATABASE
```

#### 3. SSL/TLS Issues
```bash
# Check certificate validity
openssl x509 -in /opt/mwqq/ssl/fullchain.pem -text -noout

# Check Nginx configuration
docker-compose exec nginx nginx -t

# Reload Nginx configuration
docker-compose exec nginx nginx -s reload
```

#### 4. Out of Disk Space
```bash
# Check disk usage
df -h

# Clean up old Docker resources
docker system prune -a

# Clean up old backups
find /opt/backups -name "mwqq_backup_*" -mtime +30 -exec rm -rf {} \;
```

### Debugging Commands

```bash
# Check all container status
docker-compose ps

# Check resource usage
docker stats

# Execute commands in containers
docker-compose exec backend python manage.py shell
docker-compose exec mysql mysql -u root -p

# View container logs
docker-compose logs --tail=100 backend

# Check network connectivity
docker-compose exec backend ping mysql
docker-compose exec backend ping redis
```

## 🔧 Maintenance

### Regular Maintenance Tasks

#### Weekly
- Review application logs
- Check disk space usage
- Verify backup integrity
- Update SSL certificates if needed

#### Monthly
- Update Docker base images
- Review and rotate secrets
- Performance optimization review
- Security scan and updates

#### Quarterly
- Full disaster recovery test
- Security audit
- Capacity planning review
- Documentation updates

### Update Procedures

#### Application Updates
```bash
# Create new version tag
git tag v1.1.0
git push origin v1.1.0

# Monitor deployment
# Deployment happens automatically via GitHub Actions
```

#### Security Updates
```bash
# Update base images
docker-compose pull
docker-compose up -d

# Update system packages
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### Scaling

#### Horizontal Scaling
```bash
# Scale Celery workers
docker-compose up -d --scale celery-worker=3

# Scale backend services (with load balancer)
docker-compose up -d --scale backend=2
```

#### Vertical Scaling
Update resource limits in `docker-compose.prod.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

## 📞 Support

### Emergency Contacts
- **Primary**: DevOps Team - devops@yourdomain.com
- **Secondary**: Development Team - dev@yourdomain.com
- **Infrastructure**: infra@yourdomain.com

### Emergency Procedures

#### Critical Issues
1. Check system status dashboard
2. Review recent deployments
3. Execute rollback if needed
4. Contact emergency response team
5. Document incident for post-mortem

#### Rollback Procedure
```bash
# Immediate rollback to previous version
./scripts/rollback.sh

# If rollback fails, manual recovery
docker-compose down
docker-compose up -d --scale backend=1
./scripts/health-check.sh
```

### Documentation Links
- [GitHub Repository](https://github.com/your-org/mwqq)
- [Production Dashboard](https://monitoring.yourdomain.com)
- [Status Page](https://status.yourdomain.com)
- [API Documentation](https://api.yourdomain.com/docs/)

---

## 📝 Changelog

### v1.0.0 - 2024-08-25
- Initial GitHub Actions deployment implementation
- Zero-downtime deployment strategy
- Automated backup and rollback system
- Health monitoring and alerting
- Production Docker Compose configuration
- SSL/TLS termination with Nginx
- MySQL 8.0 database integration
- Redis caching and message broker
- Celery task processing
- Prometheus and Grafana monitoring (optional)

---

**Last Updated**: August 25, 2024  
**Maintainer**: DevOps Team  
**Version**: 1.0.0