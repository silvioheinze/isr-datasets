# Email Configuration Guide

This guide explains how to configure email sending for password reset and other notifications in the ISR Datasets application.

## 📧 Email Configuration Overview

The application supports two email backends:
- **Development**: Console backend (emails printed to console)
- **Production**: SMTP backend (real email sending)

## 🔧 Configuration Steps

### 1. Environment Variables

Add these variables to your `.env.prod` file:

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

### 2. Gmail Setup (Recommended)

#### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification

#### Step 2: Create App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "Other (custom name)"
3. Enter "ISR Datasets" as the name
4. Copy the generated 16-character password
5. Use this password as `EMAIL_HOST_PASSWORD`

#### Step 3: Configure Environment
```bash
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password
```

### 3. Other Email Providers

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

## 🧪 Testing Email Configuration

### 1. Run the Test Script
```bash
docker compose exec app python test_email.py
```

### 2. Test Password Reset
1. Go to `/user/login/`
2. Click "Forgot Password?"
3. Enter your email address
4. Check your email for the reset link

### 3. Check Logs
```bash
# Development (emails printed to console)
docker compose logs app

# Production (check email delivery)
# Check your email provider's sent items
```

## 🔐 Password Reset Features

### Configuration
- **Reset Timeout**: 1 hour (3600 seconds)
- **Email Verification**: Mandatory for new accounts
- **Confirmation Expiry**: 7 days

### URLs
- **Password Reset**: `/user/password/reset/`
- **Reset Confirm**: `/user/password/reset/confirm/`
- **Login**: `/user/login/`

## 🚨 Troubleshooting

### Common Issues

#### 1. "Authentication failed"
- **Cause**: Wrong username/password
- **Solution**: Use App Password for Gmail, check credentials

#### 2. "Connection refused"
- **Cause**: Wrong SMTP server/port
- **Solution**: Verify EMAIL_HOST and EMAIL_PORT

#### 3. "SSL/TLS error"
- **Cause**: Wrong encryption settings
- **Solution**: Check EMAIL_USE_TLS and EMAIL_USE_SSL

#### 4. "Email not received"
- **Cause**: Email in spam folder
- **Solution**: Check spam folder, whitelist sender

### Debug Commands

```bash
# Test email configuration
docker compose exec app python test_email.py

# Check Django settings
docker compose exec app python manage.py shell -c "
from django.conf import settings
print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
print('EMAIL_HOST:', settings.EMAIL_HOST)
print('EMAIL_PORT:', settings.EMAIL_PORT)
"

# Test email sending
docker compose exec app python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'noreply@example.com', ['test@example.com'])
"
```

## 📋 Email Templates

The application uses Django Allauth templates for:
- Password reset emails
- Email confirmation emails
- Account activation emails

Templates are located in:
- `app/templates/account/email/`
- `app/templates/user/email/`

## 🔒 Security Considerations

1. **Use App Passwords**: Never use your main email password
2. **Environment Variables**: Store credentials in environment variables, not code
3. **TLS/SSL**: Always use encrypted connections
4. **Rate Limiting**: Allauth includes rate limiting for password reset attempts
5. **Token Expiry**: Password reset tokens expire after 1 hour

## 📊 Monitoring

### Email Delivery Monitoring
- Check email provider's delivery reports
- Monitor application logs for email errors
- Set up alerts for failed email deliveries

### Performance Monitoring
- Monitor email sending performance
- Track password reset success rates
- Monitor email bounce rates

## 🚀 Production Deployment

### 1. Set Environment Variables
```bash
# In your production environment
export EMAIL_HOST=smtp.gmail.com
export EMAIL_PORT=587
export EMAIL_USE_TLS=True
export EMAIL_HOST_USER=your_email@gmail.com
export EMAIL_HOST_PASSWORD=your_app_password
export DEFAULT_FROM_EMAIL=noreply@isrdatasets.dataplexity.eu
```

### 2. Test in Production
```bash
# Test email sending
docker compose -f docker compose.prod.yml exec app python test_email.py
```

### 3. Monitor Logs
```bash
# Check for email errors
docker compose -f docker compose.prod.yml logs app | grep -i email
```

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run the test script to diagnose problems
3. Check application logs for error messages
4. Verify email provider settings and credentials
