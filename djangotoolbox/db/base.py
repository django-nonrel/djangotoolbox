import cPickle as pickle
import datetime

from django.conf import settings
from django.db.backends import (
    BaseDatabaseFeatures,
    BaseDatabaseOperations,
    BaseDatabaseWrapper,
    BaseDatabaseClient,
    BaseDatabaseValidation,
    BaseDatabaseIntrospection)
from django.db.utils import DatabaseError
from django.utils.functional import Promise
from django.utils.safestring import EscapeString, EscapeUnicode, SafeString, \
    SafeUnicode
from django.utils import timezone

from .creation import NonrelDatabaseCreation


class NonrelDatabaseFeatures(BaseDatabaseFeatures):
    # Most NoSQL databases don't have true transaction support.
    supports_transactions = False

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

    # Django 1.4 compatibility
    def _supports_transactions(self):
        return False


class NonrelDatabaseOperations(BaseDatabaseOperations):
    """
    Override all database conversions normally done by fields (through
    `get_db_prep_value/save/lookup`) to make it possible to pass Python
    values directly to the database layer. On the other hand, provide a
    framework for making type-based conversions --  drivers of NoSQL
    database either can work with Python objects directly, sometimes
    representing one type using a another or expect everything encoded
    in some specific manner.

    Django normally handles conversions for the database by providing
    `BaseDatabaseOperations.value_to_db_*` / `convert_values` methods,
    but there are some problems with them:
    -- some preparations need to be done for all values or for values
       of a particular "kind" (e.g. lazy objects evaluation or casting
       strings wrappers to standard types);
    -- some conversions need more info about the field or model the
       value comes from (e.g. key conversions, embedded deconversion);
    -- there are no value_to_db_* methods for some value types (bools);
    -- we need to handle collecion fields (list, set, dict): they
       need to differentiate between deconverting from database and
       deserializing (so single to_python is inconvenient) and need to
       do some recursion, so a single `value_for_db` is better than one
       method for each field kind.
    Don't use these standard methods in nonrel, `value_for/from_db` are
    more elastic and keeping all conversions in one place makes the
    code easier to analyse.

    Please note, that after changes to type conversions, data saved
    using preexisting methods needs to be handled; and also that Django
    does not expect any special database driver exceptions, so any such
    exceptions should be reraised as django.db.utils.DatabaseError.

    TODO: Consider replacing all `value_to_db_*` and `convert_values`
          with just `BaseDatabaseOperations.value_for/from_db` and also
          moving there code from `Field.get_db_prep_lookup` (and maybe
          `RelatedField.get_db_prep_lookup`).
    """

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

        This method is added my nonrel to allow various types to be
        used for automatic primary keys. `AutoField.get_db_prep_value`
        calls it to prepare field's value for the database.

        Note that Django can pass a string representation of the value
        instead of the value itself (after receiving it as a query
        parameter for example), so you'll likely need to limit
        your `AutoFields` in a way that makes `str(value)` reversible.

        TODO: This could become a part of `value_for_db` if it makes
              to Django (with a `field_kind` condition).
        """
        return value

    def value_to_db_date(self, value):
        """
        Unlike with SQL database clients, it's better to assume that
        a date can be stored directly.
        """
        return value

    def value_to_db_datetime(self, value):
        """
        We may pass a datetime object to a database driver without
        casting it to a string.
        """
        return value

    def value_to_db_time(self, value):
        """
        Unlike with SQL database clients, we may assume that a time can
        be stored directly.
        """
        return value

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        """
        We may assume that a decimal can be passed to a NoSQL database
        driver directly.
        """
        return value

    # Django 1.4 compatibility
    def year_lookup_bounds(self, value):
        return self.year_lookup_bounds_for_datetime_field(value)

    def year_lookup_bounds_for_date_field(self, value):
        """
        Converts year bounds to date bounds as these can likely be
        used directly, also adds one to the upper bound as it should be
        natural to use one strict inequality for BETWEEN-like filters
        for most nonrel back-ends.
        """
        first = datetime.date(value, 1, 1)
        second = datetime.date(value + 1, 1, 1)
        return [first, second]

    def year_lookup_bounds_for_datetime_field(self, value):
        """
        Converts year bounds to datetime bounds.
        """
        first = datetime.datetime(value, 1, 1, 0, 0, 0, 0)
        second = datetime.datetime(value + 1, 1, 1, 0, 0, 0, 0)
        if settings.USE_TZ:
            tz = timezone.get_current_timezone()
            first = timezone.make_aware(first, tz)
            second = timezone.make_aware(second, tz)
        return [first, second]

    def convert_values(self, value, field):
        """
        We may assume that values returned by the database are standard
        Python types suitable to be passed to fields.
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

    def value_for_db(self, value, field, lookup=None):
        """
        Does type-conversions needed before storing a value in the
        the database or using it as a filter parameter.

        This is a convience wrapper that only precomputes field's kind
        and a db_type for the field (or the primary key of the related
        model for ForeignKeys etc.) and knows that arguments to the
        `isnull` lookup (`True` or `False`) should not be converted,
        while some other lookups take a list of arguments.
        In the end, it calls `_value_for_db` to do the real work; you
        should typically extend that method, but only call this one.

        :param value: A value to be passed to the database driver
        :param field: A field the value comes from
        :param lookup: None if the value is being prepared for storage;
                       lookup type name, when its going to be used as a
                       filter argument
        """
        field, field_kind, db_type = self._convert_as(field, lookup)

        # Argument to the "isnull" lookup is just a boolean, while some
        # other lookups take a list of values.
        if lookup == 'isnull':
            return value
        elif lookup in ('in', 'range', 'year'):
            return [self._value_for_db(subvalue, field,
                                       field_kind, db_type, lookup)
                    for subvalue in value]
        else:
            return self._value_for_db(value, field,
                                      field_kind, db_type, lookup)

    def value_from_db(self, value, field):
        """
        Performs deconversions defined by `_value_from_db`.

        :param value: A value received from the database client
        :param field: A field the value is meant for
        """
        return self._value_from_db(value, *self._convert_as(field))

    def _convert_as(self, field, lookup=None):
        """
        Computes parameters that should be used for preparing the field
        for the database or deconverting a database value for it.
        """
        # We need to compute db_type using the original field to allow
        # GAE to use different storage for primary and foreign keys.
        db_type = self.connection.creation.db_type(field)

        if field.rel is not None:
            field = field.rel.get_related_field()
        field_kind = field.get_internal_type()

        # Values for standard month / day queries are integers.
        if (field_kind in ('DateField', 'DateTimeField') and
                lookup in ('month', 'day')):
            db_type = 'integer'

        return field, field_kind, db_type

    def _value_for_db(self, value, field, field_kind, db_type, lookup):
        """
        Converts a standard Python value to a type that can be stored
        or processed by the database driver.

        This implementation only converts elements of iterables passed
        by collection fields, evaluates Django's lazy objects and
        marked strings and handles embedded models.
        Currently, we assume that dict keys and column, model, module
        names (strings) of embedded models require no conversion.

        We need to know the field for two reasons:
        -- to allow back-ends having separate key spaces for different
           tables to create keys refering to the right table (which can
           be the field model's table or the table of the model of the
           instance a ForeignKey or other relation field points to).
        -- to know the field of values passed by typed collection
           fields and to use the proper fields when deconverting values
           stored for typed embedding field.
        Avoid using the field in any other way than by inspecting its
        properties, it may not hold any value or hold a value other
        than the one you're asked to convert.

        You may want to call this method before doing other back-end
        specific conversions.

        :param value: A value to be passed to the database driver
        :param field: A field having the same properties as the field
                      the value comes from; instead of related fields
                      you'll get the related model primary key, as the
                      value usually needs to be converted using its
                      properties
        :param field_kind: Equal to field.get_internal_type()
        :param db_type: Same as creation.db_type(field)
        :param lookup: None if the value is being prepared for storage;
                       lookup type name, when its going to be used as a
                       filter argument
        """

        # Back-ends may want to store empty lists or dicts as None.
        if value is None:
            return None

        # Force evaluation of lazy objects (e.g. lazy translation
        # strings).
        # Some back-ends pass values directly to the database driver,
        # which may fail if it relies on type inspection and gets a
        # functional proxy.
        # This code relies on unicode cast in django.utils.functional
        # just evaluating the wrapped function and doing nothing more.
        # TODO: This has been partially fixed in vanilla with:
        #       https://code.djangoproject.com/changeset/17698, however
        #       still fails for proxies in lookups; reconsider in 1.4.
        #       Also research cases of database operations not done
        #       through the sql.Query.
        if isinstance(value, Promise):
            value = unicode(value)

        # Django wraps strings marked as safe or needed escaping,
        # convert them to just strings for type-inspecting back-ends.
        if isinstance(value, (SafeString, EscapeString)):
            value = str(value)
        elif isinstance(value, (SafeUnicode, EscapeUnicode)):
            value = unicode(value)

        # Convert elements of collection fields.
        if field_kind in ('ListField', 'SetField', 'DictField',):
            value = self._value_for_db_collection(value, field,
                                                  field_kind, db_type, lookup)

        # Store model instance fields' values.
        elif field_kind == 'EmbeddedModelField':
            value = self._value_for_db_model(value, field,
                                             field_kind, db_type, lookup)

        return value

    def _value_from_db(self, value, field, field_kind, db_type):
        """
        Converts a database type to a type acceptable by the field.

        If you encoded a value for storage in the database, reverse the
        encoding here. This implementation only recursively deconverts
        elements of collection fields and handles embedded models.

        You may want to call this method after any back-end specific
        deconversions.

        :param value: A value to be passed to the database driver
        :param field: A field having the same properties as the field
                      the value comes from
        :param field_kind: Equal to field.get_internal_type()
        :param db_type: Same as creation.db_type(field)

        Note: lookup values never get deconverted.
        """

        # We did not convert Nones.
        if value is None:
            return None

        # Deconvert items or values of a collection field.
        if field_kind in ('ListField', 'SetField', 'DictField',):
            value = self._value_from_db_collection(value, field,
                                                   field_kind, db_type)

        # Reinstatiate a serialized model.
        elif field_kind == 'EmbeddedModelField':
            value = self._value_from_db_model(value, field,
                                              field_kind, db_type)

        return value

    def _value_for_db_collection(self, value, field, field_kind, db_type,
                                 lookup):
        """
        Recursively converts values from AbstractIterableFields.

        Note that collection lookup values are plain values rather than
        lists, sets or dicts, but they still should be converted as a
        collection item (assuming all items or values are converted in
        the same way).

        We base the conversion on field class / kind and assume some
        knowledge about field internals (e.g. that the field has an
        "item_field" property that gives the right subfield for any of
        its values), to avoid adding a framework for determination of
        parameters for items' conversions; we do the conversion here
        rather than inside get_db_prep_save/lookup for symmetry with
        deconversion (which can't be in to_python because the method is
        also used for data not coming from the database).

        Returns a list, set, dict, string or bytes according to the
        db_type given.
        If the "list" db_type used for DictField, a list with keys and
        values interleaved will be returned (list of pairs is not good,
        because lists / tuples may need conversion themselves; the list
        may still be nested for dicts containing collections).
        The "string" and "bytes" db_types use serialization with pickle
        protocol 0 or 2 respectively.
        If an unknown db_type is specified, returns a generator
        yielding converted elements / pairs with converted values.
        """
        subfield, subkind, db_subtype = self._convert_as(field.item_field,
                                                         lookup)

        # Do convert filter parameters.
        if lookup:
            # Special case where we are looking for an empty list
            if lookup == 'exact' and db_type == 'list' and value == u'[]':
                return []
            value = self._value_for_db(value, subfield,
                                       subkind, db_subtype, lookup)

        # Convert list/set items or dict values.
        else:
            if field_kind == 'DictField':

                # Generator yielding pairs with converted values.
                value = (
                    (key, self._value_for_db(subvalue, subfield,
                                             subkind, db_subtype, lookup))
                    for key, subvalue in value.iteritems())

                # Return just a dict, a once-flattened list;
                if db_type == 'dict':
                    return dict(value)
                elif db_type == 'list':
                    return list(item for pair in value for item in pair)

            else:

                # Generator producing converted items.
                value = (
                    self._value_for_db(subvalue, subfield,
                                       subkind, db_subtype, lookup)
                    for subvalue in value)

                # "list" may be used for SetField.
                if db_type in 'list':
                    return list(value)
                elif db_type == 'set':
                    # assert field_kind != 'ListField'
                    return set(value)

            # Pickled formats may be used for all collection fields,
            # the fields "natural" type is serialized (something
            # concrete is needed, pickle can't handle generators :-)
            if db_type == 'bytes':
                return pickle.dumps(field._type(value), protocol=2)
            elif db_type == 'string':
                return pickle.dumps(field._type(value))

        # If nothing matched, pass the generator to the back-end.
        return value

    def _value_from_db_collection(self, value, field, field_kind, db_type):
        """
        Recursively deconverts values for AbstractIterableFields.

        Assumes that all values in a collection can be deconverted
        using a single field (Field.item_field, possibly a RawField).

        Returns a value in a format proper for the field kind (the
        value will normally not go through to_python).
        """
        subfield, subkind, db_subtype = self._convert_as(field.item_field)

        # Unpickle (a dict) if a serialized storage is used.
        if db_type == 'bytes' or db_type == 'string':
            value = pickle.loads(value)

        if field_kind == 'DictField':

            # Generator yielding pairs with deconverted values, the
            # "list" db_type stores keys and values interleaved.
            if db_type == 'list':
                value = zip(value[::2], value[1::2])
            else:
                value = value.iteritems()

            # DictField needs to hold a dict.
            return dict(
                (key, self._value_from_db(subvalue, subfield,
                                          subkind, db_subtype))
                for key, subvalue in value)
        else:

            # Generator yielding deconverted items.
            value = (
                self._value_from_db(subvalue, subfield,
                                    subkind, db_subtype)
                for subvalue in value)

            # The value will be available from the field without any
            # further processing and it has to have the right type.
            if field_kind == 'ListField':
                return list(value)
            elif field_kind == 'SetField':
                return set(value)

            # A new field kind? Maybe it can take a generator.
            return value

    def _value_for_db_model(self, value, field, field_kind, db_type, lookup):
        """
        Converts a field => value mapping received from an
        EmbeddedModelField the format chosen for the field storage.

        The embedded instance fields' values are also converted /
        deconverted using value_for/from_db, so any back-end
        conversions will be applied.

        Returns (field.column, value) pairs, possibly augmented with
        model info (to be able to deconvert the embedded instance for
        untyped fields) encoded according to the db_type chosen.
        If "dict" db_type is given a Python dict is returned.
        If "list db_type is chosen a list with columns and values
        interleaved will be returned. Note that just a single level of
        the list is flattened, so it still may be nested -- when the
        embedded instance holds other embedded models or collections).
        Using "bytes" or "string" pickles the mapping using pickle
        protocol 0 or 2 respectively.
        If an unknown db_type is used a generator yielding (column,
        value) pairs with values converted will be returned.

        TODO: How should EmbeddedModelField lookups work?
        """
        if lookup:
            # raise NotImplementedError("Needs specification.")
            return value

        # Convert using proper instance field's info, change keys from
        # fields to columns.
        # TODO/XXX: Arguments order due to Python 2.5 compatibility.
        value = (
            (subfield.column, self._value_for_db(
                subvalue, lookup=lookup, *self._convert_as(subfield, lookup)))
            for subfield, subvalue in value.iteritems())

        # Cast to a dict, interleave columns with values on a list,
        # serialize, or return a generator.
        if db_type == 'dict':
            value = dict(value)
        elif db_type == 'list':
            value = list(item for pair in value for item in pair)
        elif db_type == 'bytes':
            value = pickle.dumps(dict(value), protocol=2)
        elif db_type == 'string':
            value = pickle.dumps(dict(value))

        return value

    def _value_from_db_model(self, value, field, field_kind, db_type):
        """
        Deconverts values stored for EmbeddedModelFields.

        Embedded instances are stored as a (column, value) pairs in a
        dict, a single-flattened list or a serialized dict.

        Returns a tuple with model class and field.attname => value
        mapping.
        """

        # Separate keys from values and create a dict or unpickle one.
        if db_type == 'list':
            value = dict(zip(value[::2], value[1::2]))
        elif db_type == 'bytes' or db_type == 'string':
            value = pickle.loads(value)

        # Let untyped fields determine the embedded instance's model.
        embedded_model = field.stored_model(value)

        # Deconvert fields' values and prepare a dict that can be used
        # to initialize a model (by changing keys from columns to
        # attribute names).
        return embedded_model, dict(
            (subfield.attname, self._value_from_db(
                value[subfield.column], *self._convert_as(subfield)))
            for subfield in embedded_model._meta.fields
            if subfield.column in value)

    def _value_for_db_key(self, value, field_kind):
        """
        Converts value to be used as a key to an acceptable type.
        On default we do no encoding, only allowing key values directly
        acceptable by the database for its key type (if any).

        The conversion has to be reversible given the field type,
        encoding should preserve comparisons.

        Use this to expand the set of fields that can be used as
        primary keys, return value suitable for a key rather than
        a key itself.
        """
        raise DatabaseError(
            "%s may not be used as primary key field." % field_kind)

    def _value_from_db_key(self, value, field_kind):
        """
        Decodes a value previously encoded for a key.
        """
        return value


class NonrelDatabaseClient(BaseDatabaseClient):
    pass


class NonrelDatabaseValidation(BaseDatabaseValidation):
    pass


class NonrelDatabaseIntrospection(BaseDatabaseIntrospection):

    def table_names(self, cursor=None):
        """
        Returns a list of names of all tables that exist in the
        database.
        """
        return self.django_table_names()


class FakeCursor(object):

    def __getattribute__(self, name):
        raise Database.NotSupportedError("Cursors are not supported.")

    def __setattr__(self, name, value):
        raise Database.NotSupportedError("Cursors are not supported.")


class FakeConnection(object):

    def commit(self):
        pass

    def rollback(self):
        pass

    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


class Database(object):
    class Error(StandardError):
        pass

    class InterfaceError(Error):
        pass

    class DatabaseError(Error):
        pass

    class DataError(DatabaseError):
        pass

    class OperationalError(DatabaseError):
        pass

    class IntegrityError(DatabaseError):
        pass

    class InternalError(DatabaseError):
        pass

    class ProgrammingError(DatabaseError):
        pass

    class NotSupportedError(DatabaseError):
        pass

class NonrelDatabaseWrapper(BaseDatabaseWrapper):

    Database = Database

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

    def get_connection_params(self):
        return {}

    def get_new_connection(self, conn_params):
        return FakeConnection()

    def init_connection_state(self):
        pass

    def _set_autocommit(self, autocommit):
        pass

    def _cursor(self):
        return FakeCursor()
