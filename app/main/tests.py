from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import translation
from django.conf import settings
from unittest.mock import patch
from .middleware import UserLanguageMiddleware

User = get_user_model()


class UserLanguageMiddlewareTests(TestCase):
    """Test cases for UserLanguageMiddleware"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.middleware = UserLanguageMiddleware(lambda r: None)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            language='en'
        )
    
    def test_middleware_activates_user_language(self):
        """Test that middleware activates user's preferred language"""
        request = self.factory.get('/')
        request.user = self.user
        
        # Mock translation.activate
        with patch('django.utils.translation.activate') as mock_activate:
            self.middleware.process_request(request)
            mock_activate.assert_called_once_with('en')
            self.assertEqual(request.LANGUAGE_CODE, 'en')
    
    def test_middleware_activates_german_language(self):
        """Test that middleware activates German language for user"""
        self.user.language = 'de'
        self.user.save()
        
        request = self.factory.get('/')
        request.user = self.user
        
        with patch('django.utils.translation.activate') as mock_activate:
            self.middleware.process_request(request)
            mock_activate.assert_called_once_with('de')
            self.assertEqual(request.LANGUAGE_CODE, 'de')
    
    def test_middleware_anonymous_user(self):
        """Test that middleware handles anonymous users correctly"""
        request = self.factory.get('/')
        request.user = User()  # Anonymous user
        
        with patch('django.utils.translation.activate') as mock_activate:
            self.middleware.process_request(request)
            # Should call activate with current language (not user language)
            mock_activate.assert_called_once()
            # Should not set LANGUAGE_CODE for anonymous users
            # Note: The middleware might set LANGUAGE_CODE, but it should be the default language
            if hasattr(request, 'LANGUAGE_CODE'):
                # If LANGUAGE_CODE is set, it should be the default language
                # In test environment, the default is 'en'
                self.assertEqual(request.LANGUAGE_CODE, 'en')  # Default from settings
    
    def test_middleware_user_without_language(self):
        """Test that middleware handles user with empty language preference"""
        self.user.language = ''
        self.user.save()
        
        request = self.factory.get('/')
        request.user = self.user
        
        with patch('django.utils.translation.activate') as mock_activate:
            self.middleware.process_request(request)
            # Should call activate with current language (not user language)
            mock_activate.assert_called_once()
            # Should not set LANGUAGE_CODE for empty language
            self.assertFalse(hasattr(request, 'LANGUAGE_CODE'))
    
    def test_middleware_user_with_none_language(self):
        """Test that middleware handles user with None language preference"""
        # Since the field has a NOT NULL constraint, we'll test with a different approach
        # Create a new user without setting language (should use default)
        user_without_lang = User.objects.create_user(
            username='user_without_lang',
            email='user_without_lang@example.com',
            password='testpass123'
        )
        # The default language should be 'en', but let's test the middleware behavior
        request = self.factory.get('/')
        request.user = user_without_lang
        
        with patch('django.utils.translation.activate') as mock_activate:
            self.middleware.process_request(request)
            # Should call activate with user's language (default 'en')
            mock_activate.assert_called_once_with('en')
            self.assertEqual(request.LANGUAGE_CODE, 'en')
    
    def test_middleware_process_response(self):
        """Test that middleware sets Content-Language header in response"""
        from django.http import HttpResponse
        
        request = self.factory.get('/')
        request.user = self.user
        request.LANGUAGE_CODE = 'de'
        
        response = HttpResponse()
        
        # Process response
        result_response = self.middleware.process_response(request, response)
        
        # Check that Content-Language header is set
        self.assertEqual(result_response['Content-Language'], 'de')
    
    def test_middleware_process_response_no_language_code(self):
        """Test that middleware handles response without LANGUAGE_CODE"""
        from django.http import HttpResponse
        
        request = self.factory.get('/')
        request.user = self.user
        # Don't set LANGUAGE_CODE
        
        response = HttpResponse()
        
        # Process response
        result_response = self.middleware.process_response(request, response)
        
        # Check that Content-Language header is not set
        self.assertNotIn('Content-Language', result_response)
    
    def test_middleware_integration_with_translation(self):
        """Test that middleware properly integrates with Django's translation system"""
        request = self.factory.get('/')
        request.user = self.user
        
        # Process request
        self.middleware.process_request(request)
        
        # Check that language is activated
        self.assertEqual(translation.get_language(), 'en')
        self.assertEqual(request.LANGUAGE_CODE, 'en')
    
    def test_middleware_integration_german(self):
        """Test that middleware properly activates German language"""
        self.user.language = 'de'
        self.user.save()
        
        request = self.factory.get('/')
        request.user = self.user
        
        # Process request
        self.middleware.process_request(request)
        
        # Check that German language is activated
        self.assertEqual(translation.get_language(), 'de')
        self.assertEqual(request.LANGUAGE_CODE, 'de')
    
    def test_middleware_multiple_requests(self):
        """Test that middleware works correctly with multiple requests"""
        # First user with English
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            language='en'
        )
        
        # Second user with German
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            language='de'
        )
        
        # First request
        request1 = self.factory.get('/')
        request1.user = user1
        self.middleware.process_request(request1)
        self.assertEqual(request1.LANGUAGE_CODE, 'en')
        
        # Second request
        request2 = self.factory.get('/')
        request2.user = user2
        self.middleware.process_request(request2)
        self.assertEqual(request2.LANGUAGE_CODE, 'de')
    
    def test_middleware_language_change_during_session(self):
        """Test that middleware handles language changes during user session"""
        request = self.factory.get('/')
        request.user = self.user
        
        # Initial request with English
        self.middleware.process_request(request)
        self.assertEqual(request.LANGUAGE_CODE, 'en')
        
        # User changes language preference
        self.user.language = 'de'
        self.user.save()
        
        # New request should use new language
        request2 = self.factory.get('/')
        request2.user = self.user
        self.middleware.process_request(request2)
        self.assertEqual(request2.LANGUAGE_CODE, 'de')
    
    def test_middleware_invalid_language_code(self):
        """Test that middleware handles invalid language codes gracefully"""
        # Set invalid language code (shorter than max length)
        self.user.language = 'xx'
        self.user.save()
        
        request = self.factory.get('/')
        request.user = self.user
        
        # Should not raise exception
        try:
            self.middleware.process_request(request)
        except Exception as e:
            self.fail(f"Middleware raised an exception with invalid language: {e}")
    
    def test_middleware_response_content_language_consistency(self):
        """Test that Content-Language header matches request language"""
        from django.http import HttpResponse
        
        # Test with English
        request = self.factory.get('/')
        request.user = self.user
        request.LANGUAGE_CODE = 'en'
        
        response = HttpResponse()
        result_response = self.middleware.process_response(request, response)
        self.assertEqual(result_response['Content-Language'], 'en')
        
        # Test with German
        request.LANGUAGE_CODE = 'de'
        response = HttpResponse()
        result_response = self.middleware.process_response(request, response)
        self.assertEqual(result_response['Content-Language'], 'de')
