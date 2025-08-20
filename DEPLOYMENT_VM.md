# Traditional VM Deployment Guide

This guide covers deploying the AI Passport Photo Generator application on a traditional virtual machine or dedicated server.

## Prerequisites

- Ubuntu 20.04+ or CentOS 8+ server
- Minimum 2 CPU cores, 4GB RAM, 20GB storage
- Root or sudo access
- Domain name (optional but recommended)

## System Requirements

### Software Dependencies
- Node.js 18+
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Nginx
- PM2 (for process management)
- Certbot (for SSL certificates)

## Installation Steps

### 1. Update System Packages

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. Install Node.js

```bash
# Install Node.js 18 LTS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

### 3. Install Python and Dependencies

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv python3-dev

# CentOS/RHEL
sudo yum install -y python3 python3-pip python3-devel
```

### 4. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install -y postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl enable postgresql
```

Configure PostgreSQL:
```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE passport_photo;
CREATE USER passport_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE passport_photo TO passport_user;
ALTER USER passport_user CREATEDB;
\q
```

### 5. Install Redis

```bash
# Ubuntu/Debian
sudo apt install -y redis-server

# CentOS/RHEL
sudo yum install -y redis
sudo systemctl enable redis
sudo systemctl start redis
```

### 6. Install Nginx

```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx
sudo systemctl enable nginx
```

### 7. Install PM2

```bash
sudo npm install -g pm2
```

## Application Deployment

### 1. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/yourusername/mwqq.git
sudo chown -R $USER:$USER /opt/mwqq
cd /opt/mwqq
```

### 2. Deploy Backend

```bash
cd backend/passport_photo

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cat > .env << EOF
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-change-this
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,localhost
DATABASE_URL=postgresql://passport_user:your_secure_password@localhost:5432/passport_photo
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
STATIC_URL=/static/
STATIC_ROOT=/opt/mwqq/backend/passport_photo/staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=/opt/mwqq/backend/passport_photo/media
EOF

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser (optional)
python manage.py createsuperuser
```

### 3. Deploy Frontend

```bash
cd /opt/mwqq/frontend

# Install dependencies
npm install --legacy-peer-deps

# Build for production
npm run build

# Copy build files to web root
sudo cp -r build/* /var/www/html/
```

### 4. Configure PM2 for Backend

Create PM2 ecosystem file:

```bash
cat > /opt/mwqq/ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'passport-api',
      cwd: '/opt/mwqq/backend/passport_photo',
      script: 'venv/bin/gunicorn',
      args: 'passport_photo.wsgi:application --bind 127.0.0.1:8000 --workers 3',
      env: {
        DJANGO_SETTINGS_MODULE: 'passport_photo.settings'
      },
      error_file: '/var/log/passport-api.err.log',
      out_file: '/var/log/passport-api.out.log',
      log_file: '/var/log/passport-api.log'
    },
    {
      name: 'passport-celery',
      cwd: '/opt/mwqq/backend/passport_photo',
      script: 'venv/bin/celery',
      args: '-A passport_photo worker --loglevel=info',
      error_file: '/var/log/passport-celery.err.log',
      out_file: '/var/log/passport-celery.out.log',
      log_file: '/var/log/passport-celery.log'
    }
  ]
};
EOF
```

Start services with PM2:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### 5. Configure Nginx

Create Nginx configuration:

```bash
sudo tee /etc/nginx/sites-available/passport-photo << EOF
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    root /var/www/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # Frontend (React SPA)
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeout for file uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        client_max_body_size 10M;
    }

    # Static files (Django admin, etc.)
    location /static/ {
        alias /opt/mwqq/backend/passport_photo/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files (uploaded images)
    location /media/ {
        alias /opt/mwqq/backend/passport_photo/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/passport-photo /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

## SSL Configuration (Recommended)

### Install Certbot

```bash
# Ubuntu/Debian
sudo apt install -y certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y certbot python3-certbot-nginx
```

### Obtain SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Monitoring and Maintenance

### 1. System Monitoring

```bash
# View PM2 processes
pm2 status
pm2 logs

# View system resources
htop
df -h
free -h

# Check services
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis
```

### 2. Log Files

- Nginx: `/var/log/nginx/`
- Application: `/var/log/passport-*.log`
- System: `/var/log/syslog`

### 3. Backup Strategy

Create backup script:

```bash
#!/bin/bash
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U passport_user -h localhost passport_photo > $BACKUP_DIR/database.sql

# Application files backup
tar -czf $BACKUP_DIR/app_files.tar.gz /opt/mwqq

# Media files backup
tar -czf $BACKUP_DIR/media_files.tar.gz /opt/mwqq/backend/passport_photo/media

echo "Backup completed: $BACKUP_DIR"
```

### 4. Updates

```bash
# Update application
cd /opt/mwqq
git pull origin main

# Update backend
cd backend/passport_photo
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput

# Update frontend
cd ../../frontend
npm install --legacy-peer-deps
npm run build
sudo cp -r build/* /var/www/html/

# Restart services
pm2 restart all
sudo systemctl reload nginx
```

## Security Best Practices

1. **Firewall Configuration**
   ```bash
   sudo ufw allow ssh
   sudo ufw allow http
   sudo ufw allow https
   sudo ufw enable
   ```

2. **Regular Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Strong Passwords**
   - Use strong passwords for database and system users
   - Change default SSH port if needed

4. **File Permissions**
   ```bash
   sudo chown -R www-data:www-data /var/www/html
   sudo chmod -R 755 /var/www/html
   ```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   sudo chown -R $USER:$USER /opt/mwqq
   sudo chmod +x /opt/mwqq/backend/passport_photo/manage.py
   ```

2. **Database Connection Issues**
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify database credentials in `.env` file
   - Test connection: `psql -U passport_user -h localhost passport_photo`

3. **Static Files Not Loading**
   ```bash
   cd /opt/mwqq/backend/passport_photo
   source venv/bin/activate
   python manage.py collectstatic --noinput
   ```

4. **PM2 Process Issues**
   ```bash
   pm2 restart all
   pm2 logs --lines 50
   ```

## Performance Optimization

1. **Enable Nginx Caching**
2. **Configure PostgreSQL for Production**
3. **Use Redis for Session Storage**
4. **Implement CDN for Static Assets**
5. **Monitor Resource Usage**

For additional support, refer to the application logs and system monitoring tools.