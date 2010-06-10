from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

_hidden_data_field = '<input type="hidden" name="%s" value="%s" />'

@register.simple_tag
def render_upload_data(data):
    inputs = ''.join(_hidden_data_field % item for item in data.items())
    if inputs:
        return mark_safe('<div style="display:none">%s</div>' % inputs)
    return ''
