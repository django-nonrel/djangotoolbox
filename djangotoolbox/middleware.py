from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.cache import patch_cache_control

LOGIN_REQUIRED_PREFIXES = getattr(settings, 'LOGIN_REQUIRED_PREFIXES', ())
NO_LOGIN_REQUIRED_PREFIXES = getattr(settings, 'NO_LOGIN_REQUIRED_PREFIXES', ())

class LoginRequiredMiddleware(object):
    """
    Redirects to login page if request path begins with a
    LOGIN_REQURED_PREFIXES prefix. You can also specify
    NO_LOGIN_REQUIRED_PREFIXES which take precedence.
    """
    def process_request(self, request):
        for prefix in NO_LOGIN_REQUIRED_PREFIXES:
            if request.path.startswith(prefix):
                return None
        for prefix in LOGIN_REQUIRED_PREFIXES:
            if request.path.startswith(prefix) and \
                    not request.user.is_authenticated():
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
        return None

class RedirectMiddleware(object):
    """
    A static redirect middleware. Mostly useful for hosting providers that
    automatically setup an alternative domain for your website. You might
    not want anyone to access the site via those possibly well-known URLs.
    """
    def process_request(self, request):
        host = request.get_host().split(':')[0]
        # Turn off redirects when in debug mode, running unit tests, or
        # when handling an App Engine cron job.
        if settings.DEBUG or host == 'testserver' or \
                not getattr(settings, 'ALLOWED_DOMAINS', None) or \
                request.META.get('HTTP_X_APPENGINE_CRON') == 'true':
            return
        if host not in settings.ALLOWED_DOMAINS:
            return HttpResponseRedirect('http://' + settings.ALLOWED_DOMAINS[0])

class NoHistoryCacheMiddleware(object):
    """
    If user is authenticated we disable browser caching of pages in history.
    """
    def process_response(self, request, response):
        if 'Expires' not in response and \
                'Cache-Control' not in response and \
                hasattr(request, 'session') and \
                request.user.is_authenticated():
            patch_cache_control(response,
                no_store=True, no_cache=True, must_revalidate=True, max_age=0)
        return response
