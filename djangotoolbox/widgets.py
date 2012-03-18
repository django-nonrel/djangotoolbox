from django.forms import widgets
from django.template.defaultfilters import filesizeformat
from django.utils.safestring import mark_safe


class BlobWidget(widgets.FileInput):

    def render(self, name, value, attrs=None):
        try:
            blob_size = len(value)
        except:
            blob_size = 0

        blob_size = filesizeformat(blob_size)
        original = super(BlobWidget, self).render(name, value, attrs=None)
        return mark_safe("%s<p>Current size: %s</p>" % (original, blob_size))
