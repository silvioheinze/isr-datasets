# ISR Datasets

A comprehensive Django-based platform for managing, accessing, and analyzing research datasets. Built with modern web technologies and designed for researchers, data scientists, and academic institutions.

## 🚀 Features

- **Dataset Management**: Upload, organize, and manage research datasets
- **User Authentication**: Secure user registration and login with Django Allauth
- **Modern UI**: Responsive design with Bootstrap 5 and custom ISR branding
- **Database Support**: PostgreSQL with PostGIS for geospatial data
- **Docker Deployment**: Containerized application for easy deployment
- **Admin Interface**: Django admin panel for system administration
- **Audit Logging**: Track user actions and system changes
- **Multi-language Support**: Internationalization ready

## 🛠️ Technology Stack

- **Backend**: Django 5.2.6
- **Database**: PostgreSQL 15 with PostGIS 3.3
- **Frontend**: Bootstrap 5.3.3, Bootstrap Icons
- **Authentication**: Django Allauth
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx
- **Geospatial**: GDAL 3.6.2
- **Python**: 3.13

## 📋 Prerequisites

- Docker and Docker Compose
- Git

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd isr-datasets
```

### 2. Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
POSTGRES_DB=isrdatasets
POSTGRES_USER=isruser
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email Configuration (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 3. Build and Run

```bash
# Build and start all services
docker compose up --build -d

# Check service status
docker compose ps

# View logs
docker compose logs app
```

### 4. Access the Application

- **Main Application**: http://localhost
- **Admin Panel**: http://localhost/admin
- **Database Admin**: http://localhost:8080 (pgAdmin)

## 🏗️ Project Structure

```
isr-datasets/
├── app/                          # Django application
│   ├── main/                     # Main Django project
│   │   ├── settings.py           # Django settings
│   │   ├── urls.py              # Main URL configuration
│   │   └── wsgi.py              # WSGI configuration
│   ├── pages/                    # Pages app
│   │   ├── views.py             # Page views
│   │   ├── urls.py              # Page URLs
│   │   └── models.py            # Page models
│   ├── user/                     # User management app
│   │   ├── views.py             # User views
│   │   ├── models.py            # User models
│   │   ├── forms.py             # User forms
│   │   └── urls.py              # User URLs
│   ├── templates/                # Django templates
│   │   ├── _base.html           # Base template
│   │   ├── home.html            # Home page
│   │   ├── account/             # Allauth templates
│   │   └── user/                # User templates
│   ├── static/                   # Static files
│   ├── media/                    # Media files
│   └── manage.py                 # Django management script
├── nginx/                        # Nginx configuration
│   ├── Dockerfile               # Nginx Dockerfile
│   └── nginx.conf               # Nginx configuration
├── docker compose.yml            # Docker Compose configuration
├── Dockerfile                    # Main application Dockerfile
├── entrypoint.sh                 # Container entrypoint script
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔧 Development

### Local Development Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. **Run Development Server**:
   ```bash
   python manage.py runserver
   ```

### Docker Development

```bash
# Build and run in development mode
docker compose up --build

# Run specific service
docker compose up app

# Execute commands in container
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
```

## 🗄️ Database

The application uses PostgreSQL with PostGIS extension for geospatial data support.

### Database Management

```bash
# Access database shell
docker compose exec db psql -U isruser -d isrdatasets

# Create database backup
docker compose exec db pg_dump -U isruser isrdatasets > backup.sql

# Restore database backup
docker compose exec -T db psql -U isruser -d isrdatasets < backup.sql
```

### Database Admin (pgAdmin)

Access pgAdmin at http://localhost:8080:
- **Email**: admin@example.com
- **Password**: admin

## 📧 Email Configuration & Testing

The application includes comprehensive email functionality with debugging and testing capabilities.

### Email Features

- **Password Reset**: Custom branded HTML emails
- **Email Confirmation**: User account verification emails
- **Dataset Notifications**: Email alerts for dataset updates, new versions, and comments
- **Multilingual Support**: German and English email templates
- **Comprehensive Logging**: Detailed email operation logging

### Email Backend Configuration

The application automatically configures email backends based on environment:

- **Development**: Console backend (emails printed to console)
- **Production**: SMTP backend (real email sending)

### Testing Email Configuration

#### 1. Run Email Test Script

```bash
# Test email configuration
docker compose exec app python test_email.py
```

This script will:
- Display current email settings
- Test email sending functionality
- Verify SMTP configuration
- Provide troubleshooting guidance

#### 2. Test Email Notifications

```bash
# Test comment notification emails
docker compose exec app python manage.py shell -c "
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
docker compose exec app cat logs/email.log

# Monitor email logs in real-time
docker compose exec app tail -f logs/email.log
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

### Production Email Setup

For production deployment, configure these environment variables:

```bash
# SMTP Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=noreply@isrdatasets.dataplexity.eu
SERVER_EMAIL=noreply@isrdatasets.dataplexity.eu
```

#### Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** on your Google account
2. **Create App Password**:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Navigate to "App passwords"
   - Generate password for "ISR Datasets"
   - Use the 16-character password as `EMAIL_HOST_PASSWORD`

### Troubleshooting Email Issues

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
docker compose exec app python manage.py shell -c "
from django.conf import settings
print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
print('EMAIL_HOST:', settings.EMAIL_HOST)
print('EMAIL_PORT:', settings.EMAIL_PORT)
print('EMAIL_USE_TLS:', settings.EMAIL_USE_TLS)
"

# Test SMTP connection
docker compose exec app python manage.py shell -c "
from django.core.mail import get_connection
conn = get_connection()
conn.open()
print('SMTP connection successful')
conn.close()
"
```

## 🎨 Customization

### Branding

The application uses custom ISR branding with the following color scheme:

```css
:root {
    --isr-primary: #0047BB;
    --isr-secondary: #001A70;
    --isr-accent: #92C1E9;
    --isr-primary-light: #0056d6;
    --isr-primary-dark: #003a99;
}
```

### Templates

Templates are located in `app/templates/` and use Django's template system with Bootstrap 5.

## 🔐 Security

- User authentication handled by Django Allauth
- CSRF protection enabled
- Secure session management
- Audit logging for user actions
- Environment-based configuration

## 📊 Monitoring

### Logs

```bash
# View application logs
docker compose logs app

# View database logs
docker compose logs db

# View nginx logs
docker compose logs nginx

# Follow logs in real-time
docker compose logs -f app
```

### Health Checks

The application includes health checks for:
- Database connectivity
- Service availability
- Container status

## 🚀 Deployment

### Production Deployment

1. **Environment Variables**:
   - Set `DEBUG=False`
   - Configure production database
   - Set secure `DJANGO_SECRET_KEY`
   - Configure email settings

2. **Static Files**:
   ```bash
   docker compose exec app python manage.py collectstatic
   ```

3. **Database Migration**:
   ```bash
   docker compose exec app python manage.py migrate
   ```

### Scaling

The application is designed to be horizontally scalable:
- Stateless application containers
- External database
- Shared static/media storage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the logs for troubleshooting

## 🔄 Updates

To update the application:

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose up --build -d

# Run migrations if needed
docker compose exec app python manage.py migrate
```

## 📈 Roadmap

- [ ] Dataset upload and management interface
- [ ] Advanced search and filtering
- [ ] Data visualization tools
- [ ] API endpoints for data access
- [ ] User role management
- [ ] Data export functionality
- [ ] Integration with external data sources

---

**ISR Datasets** - Empowering research through data management
