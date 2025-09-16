# Email Configuration Deployment Guide

## 🚀 Quick Production Setup

### 1. Set Environment Variables

Add these to your production `.env` file:

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

### 2. Gmail App Password Setup

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create app password for "ISR Datasets"
5. Use the 16-character password as `EMAIL_HOST_PASSWORD`

### 3. Deploy and Test

```bash
# Deploy with new email settings
docker compose -f docker compose.prod.yml up -d

# Test email configuration
docker compose -f docker compose.prod.yml exec app python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Test message', 'noreply@isrdatasets.dataplexity.eu', ['your-email@example.com'])
"
```

## ✅ Features Configured

- **Password Reset**: Custom branded HTML emails
- **Email Confirmation**: Custom branded HTML emails  
- **SMTP Configuration**: Production-ready email sending
- **Security**: 1-hour password reset timeout
- **Branding**: ISR Datasets logo and styling
- **Multilingual**: German and English support

## 🔧 Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Use App Password, not regular password
   - Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD

2. **Connection Refused**
   - Verify EMAIL_HOST and EMAIL_PORT
   - Check firewall settings

3. **Emails Not Received**
   - Check spam folder
   - Verify email address
   - Check email provider settings

### Debug Commands

```bash
# Check email settings
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

## 📧 Email Templates

Custom templates are located in:
- `app/templates/account/email/password_reset_key_message.html`
- `app/templates/account/email/email_confirmation_message.html`
- `app/templates/account/email/base_message.html`

## 🔒 Security Features

- Password reset tokens expire in 1 hour
- Email confirmation expires in 7 days
- Rate limiting on password reset attempts
- Secure SMTP with TLS encryption
- App passwords for Gmail (not regular passwords)

## 📊 Monitoring

Monitor email delivery in production:
- Check application logs for email errors
- Monitor email provider delivery reports
- Set up alerts for failed email deliveries
- Track password reset success rates
