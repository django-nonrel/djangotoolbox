from django.db.backends.creation import BaseDatabaseCreation


class NonrelDatabaseCreation(BaseDatabaseCreation):

    # "Types" used by database conversion methods to decide how to
    # convert data for or from the database. Type is understood here
    # a bit differently than in vanilla Django -- it should be read
    # as an identifier of an encoding / decoding procedure rather than
    # just a database column type.
    data_types = {

        # NoSQL databases often have specific concepts of entity keys.
        # For example, GAE has the db.Key class, MongoDB likes to use
        # ObjectIds, Redis uses strings, while Cassandra supports
        # different types (including binary data).
        'AutoField':                  'key',
        'RelatedAutoField':           'key',
        'ForeignKey':                 'key',
        'OneToOneField':              'key',
        'ManyToManyField':            'key',

        # Standard field types, more or less suitable for a database
        # (or its client / driver) being able to directly store or
        # process Python objects.
        'BigIntegerField':            'long',
        'BooleanField':               'bool',
        'CharField':                  'string',
        'CommaSeparatedIntegerField': 'string',
        'DateField':                  'date',
        'DateTimeField':              'datetime',
        'DecimalField':               'decimal',
        'EmailField':                 'string',
        'FileField':                  'string',
        'FilePathField':              'string',
        'FloatField':                 'float',
        'ImageField':                 'string',
        'IntegerField':               'integer',
        'IPAddressField':             'string',
        'NullBooleanField':           'bool',
        'PositiveIntegerField':       'integer',
        'PositiveSmallIntegerField':  'integer',
        'SlugField':                  'string',
        'SmallIntegerField':          'integer',
        'TextField':                  'string',
        'TimeField':                  'time',
        'URLField':                   'string',
        'XMLField':                   'string',

        # You may use "list" for SetField, or even DictField and
        # EmbeddedModelField (if your database supports nested lists).
        # All following fields also support "string" and "bytes" as
        # their storage types -- which work by serializing using pickle
        # protocol 0 or 2 respectively.
        # Please note that if you can't support the "natural" storage
        # type then the order of field values will be undetermined, and
        # lookups or filters may not work as specified (e.g. the same
        # set or dict may be represented by different lists, with
        # elements in different order, so the same two instances may
        # compare one way or the other).
        'AbstractIterableField':      'list',
        'ListField':                  'list',
        'SetField':                   'set',
        'DictField':                  'dict',
        'EmbeddedModelField':         'dict',

        # RawFields ("raw" db_type) are used when type is not known
        # (untyped collections) or for values that do not come from
        # a field at all (model info serialization), only do generic
        # processing for them (if any). On the other hand, anything
        # using the "bytes" db_type should be converted to a database
        # blob type or stored as binary data.
        'RawField':                   'raw',
        'BlobField':                  'bytes',
    }

    def db_type(self, field):
        """
        Allows back-ends to override db_type determined by the field.

        This has to be called instead of the Field.db_type, because we
        may need to override a db_type a custom field returns directly,
        and need more freedom in handling types of primary keys and
        related fields.

        :param field: A field we want to know the storage type of

        TODO: Field.db_type (as of 1.3.1) is used mostly for generating
              SQL statements (through a couple of methods in
              DatabaseCreation and DatabaseOperations.field_cast_sql)
              or within back-end implementations -- nonrel is not
              dependend on any of these; but there are two cases that
              might need to be fixed, namely:
              -- management/createcachetable (calls field.db_type),
              -- and contrib/gis (defines its own geo_db_type method).
        """
        return field.db_type(connection=self.connection)

    def sql_create_model(self, model, style, known_models=set()):
        """
        Most NoSQL databases are mostly schema-less, no data
        definitions are needed.
        """
        return [], {}

    def sql_indexes_for_model(self, model, style):
        """
        Creates all indexes needed for local (not inherited) fields of
        a model.
        """
        return []
