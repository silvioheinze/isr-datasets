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
- [📧 Email Configuration](#-email-configuration)
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

## 📧 Email Configuration

### Quick Production Setup

#### 1. Set Environment Variables

Add these to your production `.env.prod` file:

```bash
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password_here
DEFAULT_FROM_EMAIL=noreply@isrdatasets.dataplexity.eu
SERVER_EMAIL=noreply@isrdatasets.dataplexity.eu
```

#### 2. Deploy and Test

```bash
# Deploy with new email settings
docker compose -f docker compose.prod.yml up -d

# Test email configuration
docker compose -f docker compose.prod.yml exec app python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'noreply@isrdatasets.dataplexity.eu', ['your-email@example.com'])
"
```

### Email Features Configured

- **Password Reset**: Custom branded HTML emails
- **Email Confirmation**: Custom branded HTML emails  
- **Dataset Notifications**: Email alerts for dataset updates, new versions, and comments
- **SMTP Configuration**: Production-ready email sending
- **Security**: 1-hour password reset timeout
- **Branding**: ISR Datasets logo and styling
- **Multilingual**: German and English support
- **Comprehensive Logging**: Detailed email operation logging

### Email Backend Configuration

The application automatically configures email backends based on environment:

- **Development**: Console backend (emails printed to console)
- **Production**: SMTP backend (real email sending)

### Testing Email Configuration

#### 1. Run Email Test Script

```bash
# Test email configuration
docker compose -f docker compose.prod.yml exec app python test_email.py
```

This script will:
- Display current email settings
- Test email sending functionality
- Verify SMTP configuration
- Provide troubleshooting guidance

#### 2. Test Email Notifications

```bash
# Test comment notification emails
docker compose -f docker compose.prod.yml exec app python manage.py shell -c "
from datasets.models import Dataset, Comment
from user.models import CustomUser
from datasets.views import send_comment_notification_email

# Create a test comment to trigger email notification
dataset = Dataset.objects.first()
user = CustomUser.objects.first()
if dataset and user:
    comment = Comment.objects.create(
        dataset=dataset,
        author=user,
        content='Test comment for email notification'
    )
    send_comment_notification_email(comment)
    comment.delete()
    print('Email notification test completed')
"
```

#### 3. Check Email Logs

```bash
# View email operation logs
docker compose -f docker compose.prod.yml exec app cat logs/email.log

# Monitor email logs in real-time
docker compose -f docker compose.prod.yml exec app tail -f logs/email.log
```

### Email Logging Features

The application provides comprehensive email logging:

- **Email Backend Logging**: Tracks all email sending operations
- **Notification Function Logging**: Detailed logging for dataset notifications
- **Template Rendering**: Logs email template rendering success/failure
- **User Preferences**: Tracks notification preferences
- **Success/Failure Tracking**: Monitors email delivery success rates

#### Log File Locations

- **`logs/email.log`**: Dedicated email operation logging
- **`logs/django.log`**: General application logging

#### Example Log Output

```
INFO Comment notification email requested for dataset 'Test Dataset' (ID: 123)
INFO Dataset owner: user@example.com
INFO Comment notifications enabled for user, proceeding with email
INFO Email templates rendered successfully
INFO Subject: New comment on your dataset: Test Dataset
INFO Plain message length: 624 chars
INFO HTML message length: 4688 chars
INFO Attempting to send comment notification email to user@example.com
INFO Comment notification email sent successfully to user@example.com
```

### Other Email Providers

#### Outlook/Hotmail
```bash
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

#### Yahoo Mail
```bash
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

#### Custom SMTP Server
```bash
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_username
EMAIL_HOST_PASSWORD=your_password
```

### Email Troubleshooting

#### Common Issues

1. **Authentication Failed**
   - Use App Password, not regular password
   - Check `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`

2. **Connection Refused**
   - Verify `EMAIL_HOST` and `EMAIL_PORT`
   - Check firewall settings

3. **Emails Not Received**
   - Check spam folder
   - Verify email address
   - Check email provider settings

#### Debug Commands

```bash
# Check email settings
docker compose -f docker compose.prod.yml exec app python manage.py shell -c "
from django.conf import settings
print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
print('EMAIL_HOST:', settings.EMAIL_HOST)
print('EMAIL_PORT:', settings.EMAIL_PORT)
print('EMAIL_USE_TLS:', settings.EMAIL_USE_TLS)
"

# Test SMTP connection
docker compose -f docker compose.prod.yml exec app python manage.py shell -c "
from django.core.mail import get_connection
conn = get_connection()
conn.open()
print('SMTP connection successful')
conn.close()
"
```

### Email Templates

Custom templates are located in:
- `app/templates/account/email/password_reset_key_message.html`
- `app/templates/account/email/email_confirmation_message.html`
- `app/templates/account/email/base_message.html`
- `app/templates/datasets/email/` (for dataset notifications)

### Security Features

- Password reset tokens expire in 1 hour
- Email confirmation expires in 7 days
- Rate limiting on password reset attempts
- Secure SMTP with TLS encryption
- App passwords for Gmail (not regular passwords)

### Monitoring

Monitor email delivery in production:
- Check application logs for email errors
- Monitor email provider delivery reports
- Set up alerts for failed email deliveries
- Track password reset success rates
- Use the built-in log page (`/logs/`) for real-time email monitoring

## 🆘 Support

For issues and support:

1. Check the [troubleshooting section](#-troubleshooting)
2. Review application logs
3. Verify environment configuration
4. Check network connectivity
5. Ensure all required services are running
6. For upload issues, see [Large File Upload Configuration](#-large-file-upload-configuration)
