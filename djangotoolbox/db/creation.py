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

        # RawFields ("raw" db_type) are used when type is not known
        # (untyped collections) or for values that do not come from
        # a field at all (model info serialization), only do generic
        # processing for them (if any). On the other hand, anything
        # using the "bytes" db_type should be converted to a database
        # blob type or stored as binary data.
        'RawField':                   'raw',
        'BlobField':                  'bytes',
    }

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
