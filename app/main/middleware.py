from django.utils import translation
from django.utils.deprecation import MiddlewareMixin


class UserLanguageMiddleware(MiddlewareMixin):
    """
    Middleware to activate user's preferred language if they are authenticated.
    This should be placed after AuthenticationMiddleware in the middleware stack.
    """
    
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Get user's preferred language
            user_language = getattr(request.user, 'language', None)
            
            if user_language:
                # Activate the user's preferred language
                translation.activate(user_language)
                request.LANGUAGE_CODE = user_language
            else:
                # Fall back to default language
                translation.activate(translation.get_language())
        else:
            # For anonymous users, use the default language detection
            translation.activate(translation.get_language())
    
    def process_response(self, request, response):
        # Ensure the language is properly set in the response
        if hasattr(request, 'LANGUAGE_CODE'):
            response['Content-Language'] = request.LANGUAGE_CODE
        return response
