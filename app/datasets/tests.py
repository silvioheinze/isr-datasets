from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from unittest.mock import patch
from .models import Dataset, DatasetVersion, Comment, Publisher
from .views import (
    send_comment_notification_email,
    send_dataset_update_notification_email,
    send_new_version_notification_email
)

User = get_user_model()


class NotificationEmailTests(TestCase):
    """Test cases for email notification functions"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            notify_comments=True,
            notify_dataset_updates=True,
            notify_new_versions=True
        )
        
        self.commenter = User.objects.create_user(
            username='commenter',
            email='commenter@test.com',
            password='testpass123'
        )
        
        self.other_user = User.objects.create_user(
            username='other_user',
            email='other@test.com',
            password='testpass123',
            notify_dataset_updates=True,
            notify_new_versions=True
        )
        
        # Create test publisher
        self.publisher = Publisher.objects.create(
            name='Test Publisher',
            description='Test publisher for notifications'
        )
        
        # Create test dataset
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for notifications',
            abstract='Test abstract',
            owner=self.owner,
            publisher=self.publisher,
            status='published',
            access_level='public'
        )
        
        # Create test dataset version
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset,
            version_number='1.0',
            description='Initial version',
            created_by=self.owner
        )
        
        # Create test comment
        self.comment = Comment.objects.create(
            dataset=self.dataset,
            author=self.commenter,
            content='Test comment for notifications'
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@test.com',
        SITE_NAME='Test Site',
        SITE_URL='http://test.com'
    )
    def test_send_comment_notification_email_success(self):
        """Test successful comment notification email sending"""
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification
        send_comment_notification_email(self.comment)
        
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.owner.email])
        self.assertEqual(email.from_email, 'noreply@test.com')
        self.assertIn('New comment on your dataset: Test Dataset', email.subject)
        self.assertIn('Test comment for notifications', email.body)
        self.assertIn('Test Site', email.body)

    def test_send_comment_notification_email_disabled(self):
        """Test that comment notification is not sent when disabled"""
        # Disable comment notifications for owner
        self.owner.notify_comments = False
        self.owner.save()
        
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification
        send_comment_notification_email(self.comment)
        
        # Check that no email was sent
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@test.com',
        SITE_NAME='Test Site',
        SITE_URL='http://test.com'
    )
    def test_send_dataset_update_notification_email_success(self):
        """Test successful dataset update notification email sending"""
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification
        send_dataset_update_notification_email(self.dataset)
        
        # Check that emails were sent to users with notifications enabled
        self.assertEqual(len(mail.outbox), 3)  # owner, commenter, and other_user
        
        # Check email content
        for email in mail.outbox:
            self.assertEqual(email.from_email, 'noreply@test.com')
            self.assertIn('Dataset updated: Test Dataset', email.subject)
            self.assertIn('Test Dataset', email.body)
            self.assertIn('Test Site', email.body)

    def test_send_dataset_update_notification_email_no_users(self):
        """Test that no emails are sent when no users have notifications enabled"""
        # Disable notifications for all users
        User.objects.filter(notify_dataset_updates=True).update(notify_dataset_updates=False)
        
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification
        send_dataset_update_notification_email(self.dataset)
        
        # Check that no emails were sent
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='noreply@test.com',
        SITE_NAME='Test Site',
        SITE_URL='http://test.com'
    )
    def test_send_new_version_notification_email_success(self):
        """Test successful new version notification email sending"""
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification
        send_new_version_notification_email(self.dataset, self.version)
        
        # Check that emails were sent to users with notifications enabled
        self.assertEqual(len(mail.outbox), 3)  # owner, commenter, and other_user
        
        # Check email content
        for email in mail.outbox:
            self.assertEqual(email.from_email, 'noreply@test.com')
            self.assertIn('New version available: Test Dataset v1.0', email.subject)
            self.assertIn('Test Dataset', email.body)
            self.assertIn('1.0', email.body)
            self.assertIn('Test Site', email.body)

    def test_send_new_version_notification_email_no_users(self):
        """Test that no emails are sent when no users have notifications enabled"""
        # Disable notifications for all users
        User.objects.filter(notify_new_versions=True).update(notify_new_versions=False)
        
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification
        send_new_version_notification_email(self.dataset, self.version)
        
        # Check that no emails were sent
        self.assertEqual(len(mail.outbox), 0)

    @patch('django.core.mail.send_mail')
    def test_send_comment_notification_email_exception_handling(self, mock_send_mail):
        """Test exception handling in comment notification email"""
        # Make send_mail raise an exception
        mock_send_mail.side_effect = Exception('SMTP Error')
        
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification (should not raise exception)
        try:
            send_comment_notification_email(self.comment)
        except Exception as e:
            self.fail(f"send_comment_notification_email raised an exception: {e}")
        
        # Check that send_mail was called
        mock_send_mail.assert_called_once()

    @patch('django.core.mail.send_mail')
    def test_send_dataset_update_notification_email_exception_handling(self, mock_send_mail):
        """Test exception handling in dataset update notification email"""
        # Make send_mail raise an exception
        mock_send_mail.side_effect = Exception('SMTP Error')
        
        # Clear any existing emails
        mail.outbox = []
        
        # Send notification (should not raise exception)
        try:
            send_dataset_update_notification_email(self.dataset)
        except Exception as e:
            self.fail(f"send_dataset_update_notification_email raised an exception: {e}")
        
        # Check that send_mail was called for each user
        self.assertEqual(mock_send_mail.call_count, 3)  # owner, commenter, and other_user

    def test_notification_email_templates_exist(self):
        """Test that all required email templates exist"""
        from django.template.loader import get_template
        
        # Test comment notification templates
        comment_html_template = get_template('datasets/email/comment_notification.html')
        comment_txt_template = get_template('datasets/email/comment_notification.txt')
        self.assertIsNotNone(comment_html_template)
        self.assertIsNotNone(comment_txt_template)
        
        # Test dataset update notification templates
        update_html_template = get_template('datasets/email/dataset_update_notification.html')
        update_txt_template = get_template('datasets/email/dataset_update_notification.txt')
        self.assertIsNotNone(update_html_template)
        self.assertIsNotNone(update_txt_template)
        
        # Test new version notification templates
        version_html_template = get_template('datasets/email/new_version_notification.html')
        version_txt_template = get_template('datasets/email/new_version_notification.txt')
        self.assertIsNotNone(version_html_template)
        self.assertIsNotNone(version_txt_template)
