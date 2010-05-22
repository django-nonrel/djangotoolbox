from django.db.backends.creation import BaseDatabaseCreation

class NonrelDatabaseCreation(BaseDatabaseCreation):
    data_types = {
        'DateTimeField':     'datetime',
        'DateField':         'date',
        'TimeField':         'time',
        'FloatField':        'float',
        'EmailField':        'text',
        'URLField':          'text',
        'BooleanField':      'bool',
        'NullBooleanField':  'bool',
        'CharField':         'text',
        'CommaSeparatedIntegerField': 'text',
        'IPAddressField':    'text',
        'SlugField':         'text',
        'FileField':         'text',
        'FilePathField':     'text',
        'TextField':         'longtext',
        'XMLField':          'longtext',
        'IntegerField':      'integer',
        'SmallIntegerField': 'integer',
        'PositiveIntegerField': 'integer',
        'PositiveSmallIntegerField': 'integer',
        'BigIntegerField':   'long',
        'AutoField':         'integer',
        'OneToOneField':     'integer',
        'DecimalField':      'decimal:%(max_digits)s,%(decimal_places)s',
        'BlobField':         'blob',
#        'ImageField':
    }
