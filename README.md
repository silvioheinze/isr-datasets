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

# Site Configuration
SITE_NAME=ISR Datasets
SITE_URL=http://localhost:8000
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

## 🧪 Testing

The application includes comprehensive unit tests for all major features, including API key functionality.

### Running Tests

#### Run All Tests

```bash
# Run all tests
docker compose exec app python manage.py test

# Run tests with verbosity
docker compose exec app python manage.py test --verbosity=2
```

#### Run Tests for Specific App

```bash
# Run all user app tests
docker compose exec app python manage.py test user

# Run all dataset app tests
docker compose exec app python manage.py test datasets
```

#### Run Specific Test Classes

```bash
# API Key Model Tests
docker compose exec app python manage.py test user.APIKeyModelTests

# API Key Authentication Tests
docker compose exec app python manage.py test user.APIKeyAuthenticationTests

# API Key Form Tests
docker compose exec app python manage.py test user.APIKeyFormTests

# API Key View Tests
docker compose exec app python manage.py test user.APIKeyViewTests

# API Key Dataset Download Tests
docker compose exec app python manage.py test user.APIKeyDatasetDownloadTests
```

#### Run Tests Matching Pattern

```bash
# Run all API key related tests
docker compose exec app python manage.py test user -k APIKey

# Run tests matching a specific pattern
docker compose exec app python manage.py test -k test_api_key
```

#### Run Specific Test Method

```bash
# Run a specific test method
docker compose exec app python manage.py test user.APIKeyModelTests.test_api_key_creation

# Run multiple specific tests
docker compose exec app python manage.py test user.APIKeyModelTests.test_api_key_creation user.APIKeyModelTests.test_api_key_is_valid
```

### Test Coverage

The test suite includes comprehensive coverage for:

- **API Key Model**: Creation, validation, expiration, revocation, relationships
- **API Key Authentication**: Header-based and query parameter authentication, expiration handling
- **API Key Forms**: Validation, expiration date handling, revocation confirmation
- **API Key Views**: Creation, listing, revocation, permissions
- **API Key Integration**: Dataset downloads with API key authentication, download tracking

### Test Options

```bash
# Keep test database (faster for repeated runs)
docker compose exec app python manage.py test --keepdb

# Run tests in parallel (faster execution)
docker compose exec app python manage.py test --parallel

# Show all output including print statements
docker compose exec app python manage.py test --verbosity=2

# Stop at first failure
docker compose exec app python manage.py test --failfast

# Run tests without creating migrations check
docker compose exec app python manage.py test --noinput
```

### Running Tests in Development

For faster test iteration during development:

```bash
# Keep test database and run specific test class
docker compose exec app python manage.py test user.APIKeyModelTests --keepdb --verbosity=2

# Run tests matching pattern with keepdb
docker compose exec app python manage.py test user -k APIKey --keepdb
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

### Site Configuration

The application uses environment variables to configure the site name and URL, which are used throughout the application for links, page titles, email templates, and front-end elements.

#### Environment Variables

- **`SITE_NAME`**: The name of the site displayed in the navbar, page titles, email templates, and footer. Default: `ISR Datasets`
- **`SITE_URL`**: The base URL of the installation used for generating absolute links in emails and notifications. Default: `http://localhost:8000`

These variables are automatically available in all templates via the context processor as `{{ SITE_NAME }}` and `{{ SITE_URL }}`.

#### Example Configuration

```env
SITE_NAME=My Research Datasets
SITE_URL=https://datasets.example.com
```

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
