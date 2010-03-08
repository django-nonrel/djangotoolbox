from copy import deepcopy
import functools, re

PATTERNS = {
    'day':   r'\d{1,2}',
    'id':    r'\d+',
    'num':   r'\d+',
    'month': r'\d{1,2}',
    'mon':   r'[a-z]{3}', # jan, feb, etc...
    'slug':  r'[\w-]+',
    'tag':   r'\w+',
    'year':  r'\d{4}',
}

# <name[:pattern]>
VARIABLE = re.compile(r'<(?P<name>\w+)(?::?(?P<pattern>[^>]+))?>')

class URLPatternGenerator(object):
    def __init__(self, patterns=None, default=r'\d+',
                 append_slash=True, anchor=True, terminate=True):
        self.patterns = patterns or PATTERNS.copy()
        self.default = default              # default pattern
        self.append_slash = append_slash    # trailing /
        self.anchor = anchor                # prepend ^
        self.terminate = terminate          # append $

    def add(self, name, pattern):
        self.patterns[name] = pattern

    def _replace(self, match, url):
        regexp = None
        name = match.group('name')
        pattern = match.group('pattern')
        # pattern may be a name or regexp
        if pattern:
            regexp = self.patterns.get(pattern, pattern)
        # use pattern for name, or default
        else:
            regexp = self.patterns.get(name, self.default)
        segment = '(?P<%s>%s)' % (name, regexp)
        return segment

    def __call__(self, path, *args, **kw):
        # replacement for django.conf.urls.defaults.url
        from django.conf.urls.defaults import url
        return url(self.regex(path), *args, **kw)

    def regex(self, url, **kw):
        r = VARIABLE.sub(functools.partial(self._replace, url=url), url)
        if kw.get('anchor', self.anchor) and r[:1] != '^':
            r = '^' + r
        # special-case so '^$' doesn't end up with a '/' in it
        if url and kw.get('append_slash', self.append_slash) and r[-1:] not in ('$','/'):
            r += '/'
        if kw.get('terminate', self.terminate) and r[-1:] != '$':
            r += '$'
        return r

easyurl = URLPatternGenerator()
regex = easyurl.regex

class ClassFunction(object):
    def __new__(cls, *args, **kwargs):
        obj = super(ClassFunction, cls).__new__(cls)
        return obj(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        pass

class Views(object):
    urlpatterns = patterns('', )

    def __call__(self, request, *args, **kwargs):
        pass

    def render_html(self, request, template, data):
        from django.views.generic.simple import direct_to_template
        return direct_to_template(request, template, extra_context=data)
