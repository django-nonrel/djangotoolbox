from django.conf import settings
from django.db import models
from django.utils.importlib import import_module

_MODULE_NAMES = getattr(settings, 'DB_INDEX_MODULES', ())

FIELD_INDEXES = {}

def register_index(model, mapping):
    for name, lookup_types in mapping.items():
        if isinstance(lookup_types, basestring):
            lookup_types = (lookup_types,)
        FIELD_INDEXES.setdefault(model, {})[name] = lookup_types
        field = model._meta.get_field(name)
        for lookup_type in lookup_types:
            index_name = 'idxf_%s_l_%s' % (field.name, lookup_type)
            index_field = models.CharField(max_length=field.max_length, editable=False, null=True)
            model.add_to_class(index_name, index_field)

def load_indexes():
    for name in _MODULE_NAMES:
        try:
            import_module(name).FIELD_INDEXES
        except ImportError:
            pass
