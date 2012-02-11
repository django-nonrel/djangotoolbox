import datetime

from django.db.backends import BaseDatabaseFeatures, BaseDatabaseOperations, \
    BaseDatabaseWrapper, BaseDatabaseClient, BaseDatabaseValidation, \
    BaseDatabaseIntrospection

from .creation import NonrelDatabaseCreation


class NonrelDatabaseFeatures(BaseDatabaseFeatures):

    # NoSQL databases usually return a key after saving a new object.
    can_return_id_from_insert = True

    # TODO: Doesn't seem necessary in general, move to back-ends.
    #       Mongo: see PyMongo's FAQ; GAE: see: http://timezones.appspot.com/.
    supports_date_lookup_using_string = False
    supports_timezones = False

    # Features that are commonly not available on nonrel databases.
    supports_joins = False
    supports_select_related = False
    supports_deleting_related_objects = False

    # Having to decide whether to use an INSERT or an UPDATE query is
    # specific to SQL-based databases.
    distinguishes_insert_from_update = False

    supports_dicts = False

    # Can primary_key be used on any field? Without encoding usually
    # only a limited set of types is acceptable for keys. This is a set
    # of all field kinds (internal_types) for which the primary_key
    # argument may be used.
    # TODO: Use during model validation.
    # TODO: Move to core and use to skip unsuitable Django tests.
    supports_primary_key_on = set(NonrelDatabaseCreation.data_types.keys()) - \
        set(('ForeignKey', 'OneToOneField', 'ManyToManyField', 'RawField',
             'AbstractIterableField', 'ListField', 'SetField', 'DictField',
             'EmbeddedModelField', 'BlobField'))

    def _supports_transactions(self):
        return False


class NonrelDatabaseOperations(BaseDatabaseOperations):

    def __init__(self, connection):
        self.connection = connection
        super(NonrelDatabaseOperations, self).__init__()

    def pk_default_value(self):
        """
        Returns None, to be interpreted by back-ends as a request to
        generate a new key for an "inserted" object.
        """
        return None

    def quote_name(self, name):
        """
        Does not do any quoting, as it is not needed for most NoSQL
        databases.
        """
        return name

    def prep_for_like_query(self, value):
        """
        Does no conversion, parent string-cast is SQL specific.
        """
        return value

    def prep_for_iexact_query(self, value):
        """
        Does no conversion, parent string-cast is SQL specific.
        """
        return value

    def value_to_db_auto(self, value):
        """
        Assuming that the database has its own key type, leaves any
        conversions to the back-end.

        Note that Django can pass a string representation of the value
        instead of the value itself (after receiving it as a query
        parameter for example), so you'll likely need to limit
        your AutoFields in a way that makes str(value) reversible.
        """
        return value

    def value_to_db_date(self, value):
        """
        Does not do any conversion, assuming that a date can be stored
        directly.
        """
        return value

    def value_to_db_datetime(self, value):
        """
        Does not do any conversion, assuming that a datetime can be
        stored directly.
        """
        return value

    def value_to_db_time(self, value):
        """
        Does not do any conversion, assuming that a time can be stored
        directly.
        """
        return value

    def value_to_db_decimal(self, value):
        """
        Does not do any conversion, assuming that a decimal can be
        stored directly.
        """
        return value

    def year_lookup_bounds(self, value):
        """
        Converts year bounds to datetime bounds as these can likely be
        used directly, also adds one to the upper bound as it should be
        natural to use one strict inequality for BETWEEN-like filters
        for most nonrel back-ends.
        """
        return [datetime.datetime(value, 1, 1, 0, 0, 0, 0),
                datetime.datetime(value + 1, 1, 1, 0, 0, 0, 0)]

    def convert_values(self, value, field):
        """
        Does no conversion, assuming that values returned by the
        database are standard Python types suitable to be passed to
        fields.
        """
        return value

    def check_aggregate_support(self, aggregate):
        """
        Nonrel back-ends are only expected to implement COUNT in
        general.
        """
        from django.db.models.sql.aggregates import Count
        if not isinstance(aggregate, Count):
            raise NotImplementedError("This database does not support %r "
                                      "aggregates." % type(aggregate))


class NonrelDatabaseClient(BaseDatabaseClient):
    pass


class NonrelDatabaseValidation(BaseDatabaseValidation):
    pass


class NonrelDatabaseIntrospection(BaseDatabaseIntrospection):

    def table_names(self):
        """
        Returns a list of names of all tables that exist in the
        database.
        """
        return self.django_table_names()


class FakeCursor(object):

    def __getattribute__(self, name):
        raise NotImplementedError("Cursors are not supported.")

    def __setattr__(self, name, value):
        raise NotImplementedError("Cursors are not supported.")


class NonrelDatabaseWrapper(BaseDatabaseWrapper):

    # These fake operators are required for SQLQuery.as_sql() support.
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'LIKE UPPER(%s)',
        'regex': '~ %s',
        'iregex': '~* %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'LIKE UPPER(%s)',
        'iendswith': 'LIKE UPPER(%s)',
    }

    def _cursor(self):
        return FakeCursor()
