import datetime
from django.db.backends import BaseDatabaseFeatures, BaseDatabaseOperations, \
    BaseDatabaseWrapper, BaseDatabaseClient, BaseDatabaseValidation, \
    BaseDatabaseIntrospection

from .creation import NonrelDatabaseCreation

class NonrelDatabaseFeatures(BaseDatabaseFeatures):
    can_return_id_from_insert = True
    supports_unspecified_pk = False
    supports_regex_backreferencing = True
    supports_date_lookup_using_string = False
    supports_timezones = False

    supports_joins = False
    distinguishes_insert_from_update = False
    supports_select_related = False
    supports_deleting_related_objects = False
    string_based_auto_field = False
    supports_dicts = False

    def _supports_transactions(self):
        return False

class NonrelDatabaseOperations(BaseDatabaseOperations):
    def __init__(self, connection):
        self.connection = connection
        super(NonrelDatabaseOperations, self).__init__()

    def quote_name(self, name):
        return name

    def value_to_db_date(self, value):
        # value is a date here, no need to check it
        return value

    def value_to_db_datetime(self, value):
        # value is a datetime here, no need to check it
        return value

    def value_to_db_time(self, value):
        # value is a time here, no need to check it
        return value

    def prep_for_like_query(self, value):
        return value

    def prep_for_iexact_query(self, value):
        return value

    def check_aggregate_support(self, aggregate):
        from django.db.models.sql.aggregates import Count
        if not isinstance(aggregate, Count):
            raise NotImplementedError("This database does not support %r "
                                      "aggregates" % type(aggregate))

    def year_lookup_bounds(self, value):
        return [datetime.datetime(value, 1, 1, 0, 0, 0, 0),
                datetime.datetime(value+1, 1, 1, 0, 0, 0, 0)]

    def pk_default_value(self):
        return None

    def value_to_db_auto(self, value):
        """
        Transform a value to an object compatible with the AutoField required
        by the backend driver for auto columns.
        """
        if self.connection.features.string_based_auto_field:
            if value is None:
                return None
            return unicode(value)
        return super(NonrelDatabaseOperations, self).value_to_db_auto(value)

class NonrelDatabaseClient(BaseDatabaseClient):
    pass

class NonrelDatabaseValidation(BaseDatabaseValidation):
    pass

class NonrelDatabaseIntrospection(BaseDatabaseIntrospection):
    def table_names(self):
        """Returns a list of names of all tables that exist in the database."""
        return self.django_table_names()

class FakeCursor(object):
    def __getattribute__(self, name):
        raise NotImplementedError('Cursors not supported')

    def __setattr__(self, name, value):
        raise NotImplementedError('Cursors not supported')

class NonrelDatabaseWrapper(BaseDatabaseWrapper):
    def _cursor(self):
        return FakeCursor()
