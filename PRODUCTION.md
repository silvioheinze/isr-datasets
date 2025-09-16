# Production Deployment Guide

This guide explains how to deploy ISR Datasets in production using Docker Compose.

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [📋 Environment Configuration](#-environment-configuration)
- [🐳 Docker Compose Files](#-docker-compose-files)
- [🔧 Deployment Options](#-deployment-options)
- [🌐 Network Configuration](#-network-configuration)
- [📊 Service Management](#-service-management)
- [🔒 Security Considerations](#-security-considerations)
- [🚨 Troubleshooting](#-troubleshooting)
- [📝 Maintenance](#-maintenance)
- [📁 Large File Upload Configuration](#-large-file-upload-configuration)
- [🆘 Support](#-support)

## 🚀 Quick Start

### Option 1: Using the Deploy Script (Recommended)

```bash
# 1. Create environment file
cp env.prod.example .env.prod

# 2. Edit environment variables
nano .env.prod

# 3. Run deployment script
./deploy.sh
```

### Option 2: Manual Deployment

```bash
# 1. Create environment file
cp env.prod.example .env.prod

# 2. Edit environment variables
nano .env.prod

# 3. Create proxy network
docker network create proxy

# 4. Deploy with local build
docker compose -f docker compose.prod.local.yml --env-file .env.prod up -d --build
```

## 📋 Environment Configuration

### Required Environment Variables

Create a `.env.prod` file with the following variables:

```bash
# Database Configuration
POSTGRES_DB=isrdatasets
POSTGRES_USER=isruser
POSTGRES_PASSWORD=your_secure_password_here

# Django Configuration
DJANGO_SECRET_KEY=your_secret_key_here
DJANGO_SETTINGS_MODULE=main.settings
DEBUG=False

# Optional: Custom image registry
IMAGE_REGISTRY=ghcr.io
IMAGE_NAMESPACE=silvioheinze
IMAGE_NAME=isr-datasets
IMAGE_TAG=latest
```

### Generating a Secret Key

```bash
# Generate a secure Django secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 🐳 Docker Compose Files

### docker compose.prod.yml
- **Purpose**: Production deployment with registry images
- **Use Case**: When images are available in GitHub Container Registry
- **Features**: 
  - Tries to pull from registry first
  - Falls back to local build if registry images unavailable
  - Configurable image registry and tags

### docker compose.prod.local.yml
- **Purpose**: Production deployment with local builds
- **Use Case**: When registry images are not available or for development
- **Features**:
  - Always builds images locally
  - No dependency on external registries
  - Faster for development and testing

## 🔧 Deployment Options

### 1. Registry Images (Recommended for Production)

If you have images in GitHub Container Registry:

```bash
# Set environment variables
export IMAGE_REGISTRY=ghcr.io
export IMAGE_NAMESPACE=silvioheinze
export IMAGE_NAME=isr-datasets
export IMAGE_TAG=latest

# Deploy
docker compose -f docker compose.prod.yml --env-file .env.prod up -d
```

### 2. Local Build (Fallback)

If registry images are not available:

```bash
# Deploy with local build
docker compose -f docker compose.prod.local.yml --env-file .env.prod up -d --build
```

### 3. Mixed Approach (Automatic)

The deploy script automatically detects if registry images are available and chooses the appropriate method.

## 🌐 Network Configuration

### Required Networks

The application requires two networks:

1. **internal**: Internal communication between services
2. **proxy**: External network for Traefik (must be created manually)

```bash
# Create proxy network
docker network create proxy
```

### Traefik Configuration

The nginx service is configured with Traefik labels for automatic HTTPS:

- **Domain**: `isrdatasets.dataplexity.eu`
- **SSL**: Automatic Let's Encrypt certificates
- **Entry Point**: HTTPS

## 📊 Service Management

### View Service Status

```bash
docker compose -f docker compose.prod.yml ps
```

### View Logs

```bash
# All services
docker compose -f docker compose.prod.yml logs -f

# Specific service
docker compose -f docker compose.prod.yml logs -f app
docker compose -f docker compose.prod.yml logs -f nginx
docker compose -f docker compose.prod.yml logs -f db
```

### Restart Services

```bash
# All services
docker compose -f docker compose.prod.yml restart

# Specific service
docker compose -f docker compose.prod.yml restart app
```

### Update Services

```bash
# Pull latest images and restart
docker compose -f docker compose.prod.yml pull
docker compose -f docker compose.prod.yml up -d
```

## 🔒 Security Considerations

### Environment Variables

- **Never commit** `.env.prod` to version control
- Use **strong passwords** for database
- Generate a **secure Django secret key**
- Consider using **Docker secrets** for sensitive data

### Database Security

- Use a **strong PostgreSQL password**
- Consider **database encryption at rest**
- Regular **database backups**

### Network Security

- Ensure **Traefik is properly configured**
- Use **HTTPS only** in production
- Consider **firewall rules** for database access

## 🚨 Troubleshooting

### Common Issues

#### 1. "Unauthorized" Error

```
Error response from daemon: Head "https://ghcr.io/v2/...": unauthorized
```

**Solution**: Use local build instead:
```bash
docker compose -f docker compose.prod.local.yml --env-file .env.prod up -d --build
```

#### 2. Environment Variable Warnings

```
WARN[0000] The "a" variable is not set. Defaulting to a blank string.
```

**Solution**: Create `.env.prod` file:
```bash
cp env.prod.example .env.prod
# Edit with your values
```

#### 3. Network Not Found

```
ERROR: Network "proxy" not found
```

**Solution**: Create the network:
```bash
docker network create proxy
```

#### 4. Database Connection Issues

**Check database logs**:
```bash
docker compose -f docker compose.prod.yml logs db
```

**Verify environment variables**:
```bash
docker compose -f docker compose.prod.yml config
```

### Health Checks

The application includes health checks for all services:

- **Database**: PostgreSQL readiness check
- **App**: HTTP endpoint check
- **Nginx**: Service dependency check

### Monitoring

```bash
# Check service health
docker compose -f docker compose.prod.yml ps

# Monitor resource usage
docker stats

# Check disk usage
docker system df
```

## 📝 Maintenance

### Database Backups

```bash
# Create backup
docker compose -f docker compose.prod.yml exec db pg_dump -U isruser isrdatasets > backup.sql

# Restore backup
docker compose -f docker compose.prod.yml exec -T db psql -U isruser isrdatasets < backup.sql
```

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# Check log sizes
docker compose -f docker compose.prod.yml logs --tail=1000 | wc -l

# Clean up old logs
docker system prune -f
```

### Updates

1. **Pull latest images**:
   ```bash
   docker compose -f docker compose.prod.yml pull
   ```

2. **Backup database**:
   ```bash
   docker compose -f docker compose.prod.yml exec db pg_dump -U isruser isrdatasets > backup-$(date +%Y%m%d).sql
   ```

3. **Update services**:
   ```bash
   docker compose -f docker compose.prod.yml up -d
   ```

4. **Verify deployment**:
   ```bash
   docker compose -f docker compose.prod.yml ps
   curl -f https://isrdatasets.dataplexity.eu/
   ```

## 📁 Large File Upload Configuration

### Upload Limits

The application is configured to handle large file uploads up to 1GB:

- **Nginx**: `client_max_body_size 1G`
- **Django**: Optimized memory settings for large files
- **Timeouts**: Extended to 300s (5 minutes) for large uploads
- **Proxy**: Buffering disabled for better performance

### Configuration Details

**Nginx Settings** (`nginx/nginx.conf`):
```nginx
# Allow large file uploads up to 1GB
client_max_body_size 1G;

# Increase timeouts for large file uploads
client_body_timeout 300s;
client_header_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
send_timeout 300s;

# Additional proxy settings for large uploads
proxy_request_buffering off;
proxy_buffering off;
```

**Django Settings** (`app/main/settings.py`):
```python
# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Large file upload settings
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
```

### Updating Upload Limits

If you need to update the nginx configuration for upload limits:

```bash
# Option 1: Using the update script
./update-nginx.sh

# Option 2: Manual update
docker build -t isr-datasets-nginx:latest ./nginx
docker tag isr-datasets-nginx:latest ghcr.io/silvioheinze/isr-datasets-nginx:latest
docker push ghcr.io/silvioheinze/isr-datasets-nginx:latest

# Deploy to production
docker compose -f docker-compose.prod.yml pull nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Upload Limits Summary

| Component | Limit | Timeout | Status |
|-----------|-------|---------|---------|
| **Nginx** | 1GB | 300s | ✅ Configured |
| **Django Memory** | 100MB | - | ✅ Configured |
| **Django Data** | 100MB | - | ✅ Configured |
| **Proxy Buffering** | Disabled | - | ✅ Optimized |

### Troubleshooting Upload Issues

**Common Upload Errors**:

1. **413 Request Entity Too Large**
   - **Cause**: File exceeds nginx `client_max_body_size`
   - **Solution**: Check nginx configuration and restart service

2. **504 Gateway Timeout**
   - **Cause**: Upload takes longer than timeout settings
   - **Solution**: Increase timeout values in nginx configuration

3. **500 Internal Server Error**
   - **Cause**: Django or disk space issues
   - **Solution**: Check Django logs and available disk space

**Debug Commands**:
```bash
# Check nginx configuration
docker compose -f docker-compose.prod.yml exec nginx nginx -T | grep client_max_body_size

# Check Django settings
docker compose -f docker-compose.prod.yml exec app python manage.py shell -c "
from django.conf import settings
print('FILE_UPLOAD_MAX_MEMORY_SIZE:', settings.FILE_UPLOAD_MAX_MEMORY_SIZE)
"

# Check disk space
docker compose -f docker-compose.prod.yml exec app df -h

# Monitor upload logs
docker compose -f docker-compose.prod.yml logs -f nginx
```

## 🆘 Support

For issues and support:

1. Check the [troubleshooting section](#-troubleshooting)
2. Review application logs
3. Verify environment configuration
4. Check network connectivity
5. Ensure all required services are running
6. For upload issues, see [Large File Upload Configuration](#-large-file-upload-configuration)
