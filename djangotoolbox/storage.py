from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.utils.importlib import import_module
import mimetypes

DEFAULT_FILE_UPLOAD_BACKEND = getattr(settings, 'DEFAULT_FILE_UPLOAD_BACKEND',
                                     'djangotoolbox.storage.prepare_upload')
DEFAULT_FILE_SERVING_BACKEND = getattr(settings, 'DEFAULT_FILE_SERVING_BACKEND',
                                       'djangotoolbox.storage.serve_chunked_file')

_upload_backends = {}
_file_serving_backends = {}

# Public API
def prepare_upload(url, backend=None):
    # TODO: Support specifying maxmium file upload size and other constraints?
    # Probably can't be done for all backends, so maybe the developer should
    # always check these constraints after the upload?
    handler = _load_backend(backend, DEFAULT_FILE_UPLOAD_BACKEND, _upload_backends)
    result = handler(url)
    if isinstance(result, (tuple, list)):
        return result
    return result, {}

def serve_file(request, file, backend=None, save_as=False, content_type=None):
    """
    Serves a file to the browser.

    This function provides a common API, so you can write reusable Django apps
    which don't make any assumptions about the underlying file storage service.
    For example, files could be stored somewhere in the cloud on a different
    server or they could be served efficiently via xsendfile.

    Arguments:
    * request: The current request
    * file: The Django File object that should be served (e.g. from FileField)
    * backend: Overrides default backend (settings.DEFAULT_FILE_SERVING_BACKEND)
    * save_as: Forces browser to open a "Save as..." window. If this is True
               the file's name will be file.name. Alternatively, pass a string
               to override the file name. The default is to let the browser
               decide how to handle the download.
    * content_type: Overrides the file's content type in the response.
                    By default the content type will be detected via
                    mimetypes.guess_type().

    Returns an HttpResponse object that handles the downoad.
    """
    # Backends are responsible for handling range requests.
    handler = _load_backend(backend, DEFAULT_FILE_SERVING_BACKEND, _file_serving_backends)
    filename = file.name.rsplit('/')[-1]
    if save_as is True:
        save_as = filename
    if not content_type:
        content_type = mimetypes.guess_type(filename)[0]
    return handler(request, file, save_as=save_as, content_type=content_type)

# Internal default backends
def simple_upload_url(url):
    return url

def serve_chunked_file(request, file, save_as, content_type):
    response = HttpResponse(ChunkedFile(file), content_type=content_type)
    if save_as:
        response['Content-Disposition'] = smart_str(u'attachment; filename=%s' % save_as)
    if file.size is not None:
        response['Content-Length'] = file.size
    return response

# Internal utilities
def _load_backend(backend, default_backend, backends_cache):
    if backend is None:
        backend = default_backend
    if backend not in _file_serving_backends:
        module_name, func_name = backend.rsplit('.', 1)
        backends_cache[backend] = getattr(import_module(module_name), func_name)
    return backends_cache[backend]

class ChunkedFile(object):
    def __init__(self, file):
        self.file = file

    def __iter__(self):
        return self.file.chunks()
