# All fields except for BlobField written by Jonas Haag <jonas@lophus.org>

from django.db import models
from django.core.exceptions import ValidationError

__all__ = ('RawField', 'ListField', 'DictField', 'SetField', 'BlobField')

class _HandleAssignment(object):
    """
    A placeholder class that provides a way to set the attribute on the model.
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, type=None):
        if obj is None:
            raise AttributeError('Can only be accessed via an instance.')
        return obj.__dict__[self.field.name]

    def __set__(self, obj, value):
        obj.__dict__[self.field.name] = self.field.to_python(value)

class RawField(models.Field):
    """ Generic field to store anything your database backend allows you to. """
    def get_internal_type(self):
        return 'RawField'

class AbstractIterableField(models.Field):
    """
    Abstract field for fields for storing iterable data type like ``list``,
    ``set`` and ``dict``.

    You can pass an instance of a field as the first argument.
    If you do, the iterable items will be piped through the passed field's
    validation and conversion routines, converting the items to the
    appropriate data type.
    """
    def __init__(self, item_field=None, *args, **kwargs):
        if item_field is None:
            item_field = RawField()
        self.item_field = item_field
        default = kwargs.get('default', None if kwargs.get('null') else ())
        if default is not None and not callable(default):
            # ensure a new object is created every time the default is accessed
            kwargs['default'] = lambda: self._type(default)
        super(AbstractIterableField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        self.item_field.model = cls
        self.item_field.name = name
        super(AbstractIterableField, self).contribute_to_class(cls, name)

        metaclass = getattr(self.item_field, '__metaclass__', None)
        if issubclass(metaclass, models.SubfieldBase):
            setattr(cls, self.name, _HandleAssignment(self))

    def db_type(self, connection):
        item_db_type = self.item_field.db_type(connection=connection)
        return '%s:%s' % (self.__class__.__name__, item_db_type)

    def _convert(self, func, values, *args, **kwargs):
        if isinstance(values, (list, tuple, set)):
            return self._type(func(value, *args, **kwargs) for value in values)
        return values

    def to_python(self, value):
        return self._convert(self.item_field.to_python, value)

    def get_db_prep_value(self, value, connection, prepared=False):
        return self._convert(self.item_field.get_db_prep_value, value,
                             connection=connection, prepared=prepared)

    def get_db_prep_save(self, value, connection):
        return self._convert(self.item_field.get_db_prep_save,
                             value, connection=connection)

    def validate(self, values, model_instance):
        try:
            iter(values)
        except TypeError:
            raise ValidationError('Value of type %r is not iterable' % type(values))

    def formfield(self, **kwargs):
        raise NotImplementedError('No form field implemented for %r' % type(self))

class ListField(AbstractIterableField):
    """
    Field representing a Python ``list``.

    If the optional keyword argument `ordering` is given, it must be a callable
    that is passed to :meth:`list.sort` as `key` argument. If `ordering` is
    given, the items in the list will be sorted before sending them to the
    database.
    """
    _type = list

    def __init__(self, *args, **kwargs):
        self.ordering = kwargs.pop('ordering', None)
        if self.ordering is not None and not callable(self.ordering):
            raise TypeError("'ordering' has to be a callable or None, "
                            "not of type %r" %  type(self.ordering))
        super(ListField, self).__init__(*args, **kwargs)

    def _convert(self, func, values, *args, **kwargs):
        values = super(ListField, self)._convert(func, values, *args, **kwargs)
        if values is not None and self.ordering is not None:
            values.sort(key=self.ordering)
        return values

class SetField(AbstractIterableField):
    """
    Field representing a Python ``set``.
    """
    _type = set

class DictField(AbstractIterableField):
    """
    Field representing a Python ``dict``.

    The field type conversions described in :class:`AbstractIterableField`
    only affect values of the dictionary, not keys.

    Depending on the backend, keys that aren't strings might not be allowed.
    """
    _type = dict

    def _convert(self, func, values, *args, **kwargs):
        if values is None:
            return None
        return dict((key, func(value, *args, **kwargs))
                     for key, value in values.iteritems())

    def validate(self, values, model_instance):
        if not isinstance(values, dict):
            raise ValidationError('Value is of type %r. Should be a dict.' % type(values))

class BlobField(models.Field):
    """
    A field for storing blobs of binary data.

    The value might either be a string (or something that can be converted to
    a string), or a file-like object.

    In the latter case, the object has to provide a ``read`` method from which
    the blob is read.
    """
    def get_internal_type(self):
        return 'BlobField'

    def formfield(self, **kwargs):
        # A file widget is provided, but use model FileField or ImageField
        # for storing specific files most of the time
        from .widgets import BlobWidget
        from django.forms import FileField
        defaults = {'form_class': FileField, 'widget': BlobWidget}
        defaults.update(kwargs)
        return super(BlobField, self).formfield(**defaults)

    def get_db_prep_value(self, value, connection, prepared=False):
        if hasattr(value, 'read'):
            return value.read()
        else:
            return str(value)

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        raise TypeError("BlobFields do not support lookups")

    def value_to_string(self, obj):
        return str(self._get_val_from_obj(obj))
