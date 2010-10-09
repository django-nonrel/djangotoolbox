from django.db.backends.creation import BaseDatabaseCreation

class NonrelDatabaseCreation(BaseDatabaseCreation):
    data_types = {
        'AutoField':         'integer',
        'BigIntegerField':   'long',
        'BooleanField':      'bool',
        'CharField':         'text',
        'CommaSeparatedIntegerField': 'text',
        'DateField':         'date',
        'DateTimeField':     'datetime',
        'DecimalField':      'decimal:%(max_digits)s,%(decimal_places)s',
        'EmailField':        'text',
        'FileField':         'text',
        'FilePathField':     'text',
        'FloatField':        'float',
        'ImageField':        'text',
        'IntegerField':      'integer',
        'IPAddressField':    'text',
        'NullBooleanField':  'bool',
        'OneToOneField':     'integer',
        'PositiveIntegerField': 'integer',
        'PositiveSmallIntegerField': 'integer',
        'SlugField':         'text',
        'SmallIntegerField': 'integer',
        'TextField':         'longtext',
        'TimeField':         'time',
        'URLField':          'text',
        'XMLField':          'longtext',

        'BlobField':         'blob',
        'RawField':          'raw',
    }
