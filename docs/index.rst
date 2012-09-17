.. Djangotoolbox documentation master file, created by
   sphinx-quickstart on Sun Sep 16 20:37:57 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Django Toolbox
===============================

Small set of useful Django tools. Goals: 1) be usable with non-relational Django backends 2) load no unnecessary code (faster instance startups) 3) provide good coding conventions and tools which have a real impact on your code (no "matter of taste" utilities).


Writing a non-relational Django backend
=============================================

In our `April 1st post`_ we claimed to have a simplified backend API. Well, this wasn't true, of course, but yesterday it has become true. The Django ORM is pretty complicated and it takes too much time for contributors to understand all the necessary details. In order to make the process as easy as possible we've implemented a `backend template`_ which provides a simple starting point for a new backend based on our simplified API. It also contains sample code, so you can better understand what each function does. All places where you have to make changes are marked with "``# TODO:``" comments. Note, you'll need djangotoolbox_ which provides the base classes for nonrel backends.

Let's start with ``base.py``. You can use the ``DatabaseCreation`` class to define a custom ``data_types`` mapping from Django's fields to your database types. The types will later be passed to functions which you'll have to implement to convert values from and to the DB (``convert_value_from_db()`` and ``convert_value_to_db()``). If the `default values <https://github.com/django-nonrel/djangotoolbox/blob/develop/djangotoolbox/db/creation.py>`__ work for you just leave the class untouched.

Also, if you want to maintain a DB connection we'd recommend storing it in ``DatabaseWrapper``:

.. sourcecode:: python

    class DatabaseWrapper(NonrelDatabaseWrapper):
        def __init__(self, *args, **kwds):
            super(DatabaseWrapper, self).__init__(*args, **kwds)
            ...
            self.db_connection = connect(
                self.settings_dict['HOST'], self.settings_dict['PORT'],
                self.settings_dict['USER'], self.settings_dict['PASSWORD'])

The real meat is in ``compiler.py``. Here, you have to define a BackendQuery class which handles query creation and execution. In the constructor you should create a low-level query instance for your connection. Depending on your DB API this might be nothing more than a dict, but let's say your DB provides a ``LowLevelQuery`` class:

.. sourcecode:: python

    class BackendQuery(NonrelQuery):
        def __init__(self, compiler, fields):
            super(BackendQuery, self).__init__(compiler, fields)
            self.db_query = LowLevelQuery(self.connection.db_connection)

Note, ``self.connection`` is the ``DatabaseWrapper`` instance which is the high-level DB connection object in Django.

Then, you need to define a function that converts Django's filters from Django's internal query object (``SQLQuery``, accessible via ``self.query``) to their counterparts for your DB. This should be done in the ``add_filters()`` function. Since quite a few nonrel DBs seem to only support AND queries we provide a default implementation which makes sure that there is no OR filter (well, it has some logic for converting certain OR filters to AND filters). It expects an ``add_filter()`` function (without the trailing "s"):

.. sourcecode:: python

        @safe_call
        def add_filter(self, column, lookup_type, negated, db_type, value):
            # Emulated/converted lookups
            if column == self.query.get_meta().pk.column:
                column = '_id'

            if negated:
                try:
                    op = NEGATION_MAP[lookup_type]
                except KeyError:
                    raise DatabaseError("Lookup type %r can't be negated" % lookup_type)
            else:
                try:
                    op = OPERATORS_MAP[lookup_type]
                except KeyError:
                    raise DatabaseError("Lookup type %r isn't supported" % lookup_type)

            # Handle special-case lookup types
            if callable(op):
                op, value = op(lookup_type, value)

            db_value = self.convert_value_for_db(db_type, value)
            self.db_query.filter(column, op, db_value)

This is just an example implementation. You don't have to use the same code. At first, we convert the primary key column to the DB's internal reserved column for the primary key. Then, we check if the filter should be negated or not and retrieve the respective DB comparison operator from a mapping like this:

.. sourcecode:: python

    OPERATORS_MAP = {
        'exact': '=',
        'gt': '>',
        'gte': '>=',
        # ...
        'isnull': lambda lookup_type, value: ('=' if value else '!=', None),
    }

    NEGATION_MAP = {
        'exact': '!=',
        'gt': '<=',
        # ...
        'isnull': lambda lookup_type, value: ('!=' if value else '=', None),
    }

In our example implementation the operator can be a string or a callable that returns the comparison operator and a modified value. Finally, in the last two lines of ``add_filter()`` we convert the value to its low-level DB type and then add a filter to the low-level query object.

You might have noticed the ``@save_call`` decorator. This is important. It catches database exceptions and converts them to Django's ``DatabaseError``. That decorator should be used for all your public API methods. Just modify the sample implementation in ``compiler.py`` to match your DB's needs.

Next, you have to define a ``fetch()`` function for retrieving the results from the configured query:

.. sourcecode:: python

        @safe_call
        def fetch(self, low_mark, high_mark):
            if high_mark is None:
                # Infinite fetching
                results = self.db_query.fetch_infinite(offset=low_mark)
            elif high_mark > low_mark:
                # Range fetching
                results = self.db_query.fetch_range(high_mark - low_mark, low_mark)
            else:
                results = ()

            for entity in results:
                entity[self.query.get_meta().pk.column] = entity['_id']
                del entity['_id']
                yield entity

Here, ``low_mark`` and ``high_mark`` define the query range. If ``high_mark`` is not defined you should allow for iterating through the whole result set. At the end, we convert the internal primary key column, again, and return a dict representing the entity. If your DB also supports only fetching specific columns you should get the requested fields from ``self.fields`` (``field.column`` contains the column name).

All values in the resulting dict are automatically converted via ``SQLCompiler.convert_value_from_db()``. You have to implement that function (the backend template contains a sample implementation). That function gets a ``db_type`` parameter which is the type string as defined in your field type mapping in ``DatabaseCreation.data_types``.

We won't look at the whole API in this post. There are additional functions for ordering, counting, and deleting the query results. It's pretty simple. The API might later get extended with support for aggregates, but currently you'll have to handle them at a lower level in your ``SQLCompiler`` implementation if your DB supports those features.

Another important function is called on ``Model.save()``:

.. sourcecode:: python

    class SQLInsertCompiler(NonrelInsertCompiler, SQLCompiler):
        @safe_call
        def insert(self, data, return_id=False):
            pk_column = self.query.get_meta().pk.column
            if pk_column in data:
                data['_id'] = data[pk_column]
                del data[pk_column]

            pk = save_entity(self.connection.db_connection,
                self.query.get_meta().db_table, data)
            return pk

Again, ``data`` is a dict because that maps naturally to nonrel DBs. Note, before insert() is called, all values are automatically converted via ``SQLCompiler.convert_value_for_db()`` (which you have to implement, too), so you don't have to deal with value conversions in that function.

I hope this gives you enough information to get started with a new backend. Please spread the word, so we can find backend contributors for all non-relational DBs. Django 1.3 development is getting closer and in order to get officially integrated into Django we have to prove that it's possible to use Django-nonrel with a wide variety of NoSQL DBs.

Please comment on the API. Should we improve anything? Is it flexible and easy enough?

.. _April 1st post: http://www.allbuttonspressed.com/blog/django/2010/04/SimpleDB-backend-and-JOIN-support
.. _backend template: http://bitbucket.org/wkornewald/backend-template/
.. _djangotoolbox: https://github.com/django-nonrel/djangotoolbox
