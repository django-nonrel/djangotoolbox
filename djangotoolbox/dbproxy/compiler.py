from .api import FIELD_INDEXES
from django.conf import settings
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

LOOKUP_TYPE_CONVERSION = {
    'iexact': lambda value, _: ('exact', value.lower()),
}

VALUE_CONVERSION = {
    'iexact': lambda value: value.lower(),
}

class SQLCompiler(object):
    def results_iter(self):
        self.convert_filters(self.query.where)
        return super(SQLCompiler, self).results_iter()

    def convert_filters(self, filters):
        model = self.query.model
        for index, child in enumerate(filters.children[:]):
            if isinstance(child, Node):
                self.convert_filters(child)
                continue

            constraint, lookup_type, annotation, value = child
            if model in FIELD_INDEXES and constraint.field is not None and \
                    lookup_type in FIELD_INDEXES[model].get(constraint.field.name, ()):
                index_name = 'idxf_%s_l_%s' % (constraint.field.name, lookup_type)
                lookup_type, value = LOOKUP_TYPE_CONVERSION[lookup_type](value, annotation)
                constraint.field = self.query.get_meta().get_field(index_name)
                child = (constraint, lookup_type, annotation, value)
                filters.children[index] = child

class SQLInsertCompiler(object):
    def execute_sql(self, return_id=False):
        position = {}
        for index, (field, value) in enumerate(self.query.values[:]):
            position[field.name] = index

        model = self.query.model
        for field, value in self.query.values[:]:
            if field is None or model not in FIELD_INDEXES or \
                    field.name not in FIELD_INDEXES[model]:
                continue
            for lookup_type in FIELD_INDEXES[model][field.name]:
                index_name = 'idxf_%s_l_%s' % (field.name, lookup_type)
                index_field = model._meta.get_field(index_name)
                self.query.values[position[index_name]] = (index_field, VALUE_CONVERSION[lookup_type](value))
        return super(SQLInsertCompiler, self).execute_sql(return_id=return_id)

class SQLUpdateCompiler(object):
    pass

class SQLDeleteCompiler(object):
    pass
