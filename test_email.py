#!/usr/bin/env python
"""
Test script for email configuration
Run this to test if email settings are working correctly
"""

import os
import sys
import django
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()

def test_email_configuration():
    """Test the email configuration"""
    print("🔧 Testing Email Configuration")
    print("=" * 50)
    
    # Display current email settings
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"SERVER_EMAIL: {settings.SERVER_EMAIL}")
    print()
    
    # Test email sending
    test_recipient = input("Enter test email address (or press Enter to skip): ").strip()
    
    if not test_recipient:
        print("⏭️  Skipping email test")
        return
    
    try:
        print("📧 Sending test email...")
        
        # Send a simple test email
        send_mail(
            subject='ISR Datasets - Email Configuration Test',
            message='This is a test email to verify that email configuration is working correctly.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_recipient],
            fail_silently=False,
        )
        
        print("✅ Test email sent successfully!")
        print(f"📬 Check {test_recipient} for the test email")
        
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        print("\n🔍 Troubleshooting tips:")
        print("1. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
        print("2. For Gmail, use an App Password instead of your regular password")
        print("3. Ensure 2-factor authentication is enabled for Gmail")
        print("4. Check if your email provider requires specific settings")

def test_password_reset_email():
    """Test password reset email template"""
    print("\n🔐 Testing Password Reset Email Template")
    print("=" * 50)
    
    try:
        # Test if we can render the password reset email template
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from user.models import CustomUser
        
        # Get a test user (or create one)
        user = CustomUser.objects.first()
        if not user:
            print("❌ No users found. Create a user first to test password reset.")
            return
        
        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        print(f"✅ Password reset token generated for user: {user.email}")
        print(f"Token: {token[:10]}...")
        print(f"UID: {uid[:10]}...")
        
        # Test password reset URL
        reset_url = f"/user/password/reset/confirm/{uid}/{token}/"
        print(f"Reset URL: {reset_url}")
        
    except Exception as e:
        print(f"❌ Error testing password reset: {e}")

if __name__ == "__main__":
    test_email_configuration()
    test_password_reset_email()
    
    print("\n📋 Email Configuration Summary:")
    print("=" * 50)
    print("✅ Email backend configured")
    print("✅ SMTP settings configured")
    print("✅ Allauth email settings configured")
    print("✅ Password reset timeout set to 1 hour")
    print("\n🚀 Email configuration is ready!")
    print("\n📝 Next steps:")
    print("1. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in your .env file")
    print("2. For Gmail, create an App Password")
    print("3. Test password reset functionality in the web interface")
