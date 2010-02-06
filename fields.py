from django.db import models

class ListField(models.Field):
    def __init__(self, field_type, *args, **kwargs):
        self.field_type = field_type
        super(ListField, self).__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'ListField:' + self.field_type.db_type(connection=connection)

    def call_for_each(self, function_name, values, *args, **kwargs):
        if isinstance(values, (list, tuple)) and len(values):
            for i, value in enumerate(values):
                values[i] = getattr(self.field_type, function_name)(value, *args,
                    **kwargs)
        return values

    def get_default(self):
#        Django converts default values different from types.NoneType, int, long,
#        datetime.datetime, datetime.date, datetime.time, float, Decimal to strings
        if self.has_default():
            if callable(self.default):
                return self.default()
            return self.default
        if self.null:
            return None
        return []

#    def pre_save(self, model_instance, add):
#        pass

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