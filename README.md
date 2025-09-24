# ISR Datasets

A comprehensive Django-based platform for managing, accessing, and analyzing research datasets. Built with modern web technologies and designed for researchers, data scientists, and academic institutions.

## 🚀 Features

- **Dataset Management**: Upload, organize, and manage research datasets with comprehensive import/export capabilities
- **ETL Pipeline**: Advanced Extract, Transform, Load pipeline for dataset processing with error handling and recovery
- **Import Management**: Queue-based dataset import system with priority handling and status monitoring
- **User Authentication**: Secure user registration and login with Django Allauth
- **Modern UI**: Responsive design with Bootstrap 5 and custom ISR branding
- **Database Support**: PostgreSQL with PostGIS for geospatial data and dedicated import database
- **Docker Deployment**: Containerized application for easy deployment
- **Admin Interface**: Django admin panel for system administration
- **System Monitoring**: Comprehensive logging system with level filtering and real-time monitoring
- **Error Recovery**: Automated error diagnosis and fixing for import failures
- **Audit Logging**: Track user actions and system changes
- **Multi-language Support**: Internationalization ready

## 🛠️ Technology Stack

- **Backend**: Django 5.2.6
- **Database**: PostgreSQL 15 with PostGIS 3.3
- **Frontend**: Bootstrap 5.3.3, Bootstrap Icons
- **Authentication**: Django Allauth
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx

## 🔧 Development

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

## 🔄 ETL Pipeline & Import Management

The application features a sophisticated Extract, Transform, Load (ETL) pipeline for processing datasets with comprehensive error handling and recovery mechanisms.

### ETL Pipeline Features

- **Queue-Based Processing**: Import requests are queued and processed sequentially to prevent system overload
- **Priority Handling**: Support for urgent, high, normal, and low priority imports
- **Error Recovery**: Automated error diagnosis and fixing for failed imports
- **Status Monitoring**: Real-time tracking of import progress and status
- **Multiple File Formats**: Support for CSV, JSON, GeoJSON, Excel, GDB, SQLite, GeoPackage, and SQL files
- **Database Integration**: Direct import to dedicated import database with table creation

### Import Management Interface

Access the import management system at `/datasets/import-management/` (Administrator access required):

#### Key Features

- **Queue Statistics**: Overview of pending, processing, completed, and failed imports
- **Pipeline Controls**: Start/stop pipeline processing with status monitoring
- **Error Diagnosis**: Automated error detection and fix suggestions
- **Import History**: Track all import operations with detailed logs
- **Bulk Processing**: Process multiple imports simultaneously

#### Import Queue Operations

```bash
# Start pipeline processing
curl -X POST http://localhost/datasets/pipeline/start/

# Process all pending imports
curl -X POST http://localhost/datasets/pipeline/process-all/

# Get pipeline status
curl http://localhost/datasets/pipeline/status/
```

### Error Recovery System

The application includes an intelligent error recovery system:

#### Automatic Error Diagnosis

- **File Accessibility**: Checks for missing or inaccessible files
- **Database Connectivity**: Verifies import database availability
- **Format Validation**: Ensures file formats are supported
- **Status Reset**: Automatically resets stuck processing states
- **Cleanup Operations**: Removes orphaned database tables and records

#### Manual Error Fixing

Administrators can manually trigger error diagnosis and fixing:

1. Navigate to failed import: `/datasets/import-queue/{id}/`
2. Click "Fix Import Error" button
3. Review diagnosis results and applied fixes
4. Retry the import if issues are resolved

### ETL Pipeline Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Extract       │    │   Transform     │    │   Load          │
│                 │    │                 │    │                 │
│ • File Reading  │───▶│ • Data Cleaning │───▶│ • Database      │
│ • URL Fetching  │    │ • Validation    │    │   Import        │
│ • Format Parse  │    │ • Structure     │    │ • Table Create  │
│                 │    │   Mapping       │    │ • Indexing      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| CSV | `.csv` | Comma-separated values |
| JSON | `.json` | JavaScript Object Notation |
| GeoJSON | `.geojson` | Geographic JSON format |
| Excel | `.xlsx`, `.xls` | Microsoft Excel files |
| GDB | `.gdb` | Esri File Geodatabase |
| SQLite | `.sqlite` | SQLite database files |
| GeoPackage | `.gpkg` | OGC GeoPackage format |
| SQL | `.sql` | SQL script files |

### Monitoring & Logging

The ETL pipeline provides comprehensive monitoring:

- **Real-time Status**: Live updates of processing status
- **Detailed Logs**: Complete operation logs with timestamps
- **Error Tracking**: Detailed error messages and stack traces
- **Performance Metrics**: Processing time and resource usage
- **Audit Trail**: Complete history of all import operations

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

## 🎨 User Interface & Customization

The application features a modern, responsive user interface with consistent design patterns and comprehensive customization options.

### UI Features

- **Responsive Design**: Mobile-first approach with Bootstrap 5.3.3
- **Consistent Layout**: Unified design patterns across all pages
- **Bootstrap Icons**: Modern icon system throughout the interface
- **ISR Branding**: Custom color scheme and branding elements
- **Accessibility**: WCAG compliant design with proper contrast and navigation
- **Internationalization**: Multi-language support with Django i18n

### Template Architecture

The application uses a hierarchical template system:

```
templates/
├── _base.html              # Base template with navigation and layout
├── account/                # Authentication templates
├── datasets/               # Dataset management templates
│   ├── dataset_detail.html # Enhanced dataset detail view
│   ├── import_management.html # Import management interface
│   └── import_queue_detail.html # Import queue detail view
├── main/                   # System administration templates
│   └── logs.html          # System logs with filtering
├── user/                   # User management templates
│   ├── email_confirm.html  # Enhanced email confirmation
│   └── list.html          # User listing interface
└── projects/               # Project management templates
```

### Enhanced Templates

#### Import Management Interface

The import management system features:

- **Statistics Dashboard**: Real-time overview of import queue status
- **Pipeline Controls**: Start/stop pipeline with status monitoring
- **Error Recovery**: Automated error diagnosis and fixing
- **Queue Management**: Comprehensive import queue administration
- **Database Statistics**: Import database health and metrics

#### System Logs Interface

The logging system provides:

- **Level Filtering**: Filter logs by ERROR, WARNING, INFO, DEBUG levels
- **Real-time Updates**: Live log monitoring with automatic refresh
- **Multi-log Support**: Django and email log viewing
- **Pagination**: Efficient browsing of large log files
- **Status Indicators**: Visual feedback for log file availability

#### Email Confirmation

Enhanced email confirmation template with:

- **Modern Layout**: Card-based design with clear visual hierarchy
- **Status Indicators**: Visual feedback for confirmation states
- **Error Handling**: Comprehensive error messaging and recovery
- **User Guidance**: Clear instructions and next steps

### Branding & Styling

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

#### Color Usage

- **Primary Blue (#0047BB)**: Main brand color for buttons, links, and headers
- **Secondary Blue (#001A70)**: Darker shade for navigation and footers
- **Accent Blue (#92C1E9)**: Light accent for highlights and secondary elements
- **Status Colors**: Green (success), Red (error), Yellow (warning), Blue (info)

### Responsive Design

The interface is fully responsive with:

- **Mobile-First**: Optimized for mobile devices
- **Tablet Support**: Enhanced layouts for tablet screens
- **Desktop Optimization**: Full-featured desktop experience
- **Touch-Friendly**: Large touch targets for mobile interaction

### Accessibility Features

- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG AA compliant color combinations
- **Focus Indicators**: Clear focus states for interactive elements
- **Alternative Text**: Descriptive alt text for images and icons

### Customization Options

#### Template Customization

Templates are located in `app/templates/` and can be customized:

```bash
# Override base template
cp app/templates/_base.html app/templates/custom_base.html

# Customize specific pages
cp app/templates/datasets/dataset_detail.html app/templates/datasets/custom_detail.html
```

#### Styling Customization

```css
/* Custom CSS overrides */
:root {
    --custom-primary: #your-color;
    --custom-secondary: #your-color;
}

/* Component-specific styling */
.dataset-card {
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Internationalization

The application supports multiple languages:

- **English**: Default language
- **German**: Full German translation support
- **Template Tags**: All text uses Django's `{% trans %}` tags
- **Dynamic Language**: User-selectable language preferences
- **Email Templates**: Localized email content

## 🔐 Security

- User authentication handled by Django Allauth
- CSRF protection enabled
- Secure session management
- Audit logging for user actions
- Environment-based configuration

## 📊 System Monitoring & Logging

The application provides comprehensive monitoring and logging capabilities with advanced filtering and real-time monitoring.

### Log Management Interface

Access the system logs at `/logs/` (Superuser access required):


#### Log Types

| Log Type | Description | Location |
|----------|-------------|----------|
| Django | Application logs | `logs/django.log` |
| Email | Email operation logs | `logs/email.log` |

#### Log Level Filtering

The system supports filtering by log levels:

- **ERROR**: Critical errors requiring immediate attention
- **WARNING**: Warning messages and potential issues
- **INFO**: General information and status updates
- **DEBUG**: Detailed debugging information
- **All Levels**: View all log entries (default)

### Log Monitoring Features

#### Real-time Monitoring

```bash
# Monitor Django logs in real-time
docker compose exec app tail -f logs/django.log

# Monitor email logs in real-time
docker compose exec app tail -f logs/email.log

# Monitor all logs
docker compose logs -f app
```

#### Log Analysis

```bash
# Count error messages
docker compose exec app grep -c "ERROR" logs/django.log

# Find specific error patterns
docker compose exec app grep -i "database" logs/django.log

# Monitor email operations
docker compose exec app grep "email" logs/email.log
```

### System Health Monitoring

The application includes comprehensive health checks:

#### Database Health

- **Connection Status**: Verify database connectivity
- **Import Database**: Check dedicated import database status
- **Table Integrity**: Validate database table structures
- **Performance Metrics**: Monitor query performance and resource usage

#### Service Health

- **Application Status**: Django application health
- **Email Service**: SMTP connectivity and configuration
- **File System**: Media and static file accessibility
- **Container Status**: Docker container health and resource usage

#### Monitoring Endpoints

```bash
# Check application health
curl http://localhost/health/

# Check database connectivity
curl http://localhost/datasets/import-management/

# Check log system status
curl http://localhost/logs/
```

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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the GPL-3.0 license - see the [LICENSE](LICENSE) file for details.

## Management Commands

### ETL Pipeline Commands

```bash
# Process import queue
docker compose exec app python manage.py process_import_queue

# Clean up old imports
docker compose exec app python manage.py shell -c "
from datasets.etl_pipeline import ETLPipelineManager
ETLPipelineManager.cleanup_old_imports(days=30)
"

# Check pipeline status
docker compose exec app python manage.py shell -c "
from datasets.etl_pipeline import ETLPipelineManager
status = ETLPipelineManager.get_queue_status()
print(f'Queue Status: {status}')
"
```

### Database Management

```bash
# Create database backup
docker compose exec app python manage.py dumpdata > backup.json

# Restore database
docker compose exec app python manage.py loaddata backup.json

# Check database integrity
docker compose exec app python manage.py check --database default
docker compose exec app python manage.py check --database import
```