from django.db import models
from django.forms import FileField, widgets
from django.utils.safestring import mark_safe

class ListField(models.Field):
    def __init__(self, field_type, *args, **kwargs):
        self.field_type = field_type
        kwargs['default'] = lambda: None if self.null else []
        super(ListField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'ListField:' + self.field_type.db_type(connection=connection)

    def call_for_each(self, function_name, values, *args, **kwargs):
        if isinstance(values, (list, tuple)) and len(values):
            for i, value in enumerate(values):
                values[i] = getattr(self.field_type, function_name)(value, *args,
                    **kwargs)
        return values

    def to_python(self, value):
        return self.call_for_each( 'to_python', value)

    def get_prep_value(self, value):
        return self.call_for_each('get_prep_value', value)

    def get_db_prep_value(self, value, connection, prepared=False):
        return self.call_for_each('get_db_prep_value', value, connection=connection,
            prepared=prepared)

    def get_db_prep_save(self, value, connection):
        return self.call_for_each('get_db_prep_save', value, connection=connection)

    def formfield(self, **kwargs):
        return None

class BlobWidget(widgets.FileInput):
    def render(self, name, value, attrs=None):
        try:
            blob_size = len(value)
        except:
            blob_size = 0
        original = super(BlobWidget, self).render(name, value, attrs=None)
        return mark_safe('%s<p>Current Blob Length: %s</p>' % (original,
                                                               blob_size))

class BlobField(models.Field):
    """
    A field for storing blobs of binary data though App Engine's binary field
    property.
    """

    def __init__(self, *args, **kwargs):
        super(BlobField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'BlobField'

    def formfield(self, **kwargs):
        # A file widget is provided, but use  model FileField or ImageField 
        # for storing specific files most of the time
        defaults = {'form_class': FileField, 'widget': BlobWidget}
        defaults.update(kwargs)
        field = super(BlobField, self).formfield(**defaults)

        # I set the class so that any Blob Store upload middleware can ignore
        # this input
        field.widget.attrs['class'] = "BlobFieldFileInput"
        return field

    def get_db_prep_value(self, value, connection, prepared=False):        
        try:
            # Sees if the object passed in is file-like
            return value.read()
        except:
            return str(value)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        raise TypeError("BlobFields do not support lookups")

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return str(value)
