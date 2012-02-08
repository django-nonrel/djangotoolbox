from django import http
from django.template import RequestContext, loader


def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: `500.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/')
    """

    # You need to create a 500.html template.
    t = loader.get_template(template_name)

    return http.HttpResponseServerError(
        t.render(RequestContext(request, {'request_path': request.path})))
