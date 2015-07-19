import datetime

import django
from django.conf import settings
from django.db.models.fields import NOT_PROVIDED
from django.db.models.query import QuerySet
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node
from django.db import connections

try:
    from django.db.models.sql.where import SubqueryConstraint
except ImportError:
    SubqueryConstraint = None

try:
    from django.db.models.sql.datastructures import EmptyResultSet
except ImportError:
    class EmptyResultSet(Exception):
        pass


if django.VERSION >= (1, 5):
    from django.db.models.constants import LOOKUP_SEP
else:
    from django.db.models.sql.constants import LOOKUP_SEP

if django.VERSION >= (1, 6):
    def get_selected_fields(query):
        if query.select:
            return [info.field for info in (query.select +
                        query.related_select_cols)]
        else:
            return query.model._meta.fields
else:
    def get_selected_fields(query):
        if query.select_fields:
            return (query.select_fields + query.related_select_fields)
        else:
            return query.model._meta.fields

EMULATED_OPS = {
    'exact': lambda x, y: y in x if isinstance(x, (list, tuple)) else x == y,
    'iexact': lambda x, y: x.lower() == y.lower(),
    'startswith': lambda x, y: x.startswith(y[0]),
    'istartswith': lambda x, y: x.lower().startswith(y[0].lower()),
    'isnull': lambda x, y: x is None if y else x is not None,
    'in': lambda x, y: x in y,
    'lt': lambda x, y: x < y,
    'lte': lambda x, y: x <= y,
    'gt': lambda x, y: x > y,
    'gte': lambda x, y: x >= y,
}


class NonrelQuery(object):
    """
    Base class for nonrel queries.

    Compilers build a nonrel query when they want to fetch some data.
    They work by first allowing sql.compiler.SQLCompiler to partly build
    a sql.Query, constructing a NonrelQuery query on top of it, and then
    iterating over its results.

    This class provides in-memory filtering and ordering and a
    framework for converting SQL constraint tree built by Django to a
    "representation" more suitable for most NoSQL databases.

    TODO: Replace with FetchCompiler, there are too many query concepts
          around, and it isn't a good abstraction for NoSQL databases.

    TODO: Nonrel currently uses constraint's tree built by Django for
          its SQL back-ends to handle filtering. However, Django
          intermingles translating its lookup / filtering abstraction
          to a logical formula with some preprocessing for joins and
          this results in hacks in nonrel. It would be a better to pull
          out SQL-specific parts from the constraints preprocessing.
    """

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------

    def __init__(self, compiler, fields):
        self.compiler = compiler
        self.connection = compiler.connection
        self.ops = compiler.connection.ops
        self.query = compiler.query  # sql.Query
        self.fields = fields
        self._negated = False

    def fetch(self, low_mark=0, high_mark=None):
        """
        Returns an iterator over some part of query results.
        """
        raise NotImplementedError

    def count(self, limit=None):
        """
        Returns the number of objects that would be returned, if
        this query was executed, up to `limit`.
        """
        raise NotImplementedError

    def delete(self):
        """
        Called by NonrelDeleteCompiler after it builds a delete query.
        """
        raise NotImplementedError

    def order_by(self, ordering):
        """
        Reorders query results or execution order. Called by
        NonrelCompilers during query building.

        :param ordering: A list with (field, ascending) tuples or a
                         boolean -- use natural ordering, if any, when
                         the argument is True and its reverse otherwise
        """
        raise NotImplementedError

    def add_filter(self, field, lookup_type, negated, value):
        """
        Adds a single constraint to the query. Called by add_filters for
        each constraint leaf in the WHERE tree built by Django.

        :param field: Lookup field (instance of Field); field.column
                      should be used for database keys
        :param lookup_type: Lookup name (e.g. "startswith")
        :param negated: Is the leaf negated
        :param value: Lookup argument, such as a value to compare with;
                      already prepared for the database
        """
        raise NotImplementedError

    def add_filters(self, filters):
        """
        Converts a constraint tree (sql.where.WhereNode) created by
        Django's SQL query machinery to nonrel style filters, calling
        add_filter for each constraint.

        This assumes the database doesn't support alternatives of
        constraints, you should override this method if it does.

        TODO: Simulate both conjunctions and alternatives in general
              let GAE override conjunctions not to split them into
              multiple queries.
        """
        if filters.negated:
            self._negated = not self._negated

        if not self._negated and filters.connector != AND:
            raise DatabaseError("Only AND filters are supported.")

        # Remove unneeded children from the tree.
        children = self._get_children(filters.children)

        if self._negated and filters.connector != OR and len(children) > 1:
            raise DatabaseError("When negating a whole filter subgroup "
                                "(e.g. a Q object) the subgroup filters must "
                                "be connected via OR, so the non-relational "
                                "backend can convert them like this: "
                                "'not (a OR b) => (not a) AND (not b)'.")

        # Recursively call the method for internal tree nodes, add a
        # filter for each leaf.
        for child in children:
            if isinstance(child, Node):
                self.add_filters(child)
                continue
            field, lookup_type, value = self._decode_child(child)
            self.add_filter(field, lookup_type, self._negated, value)

        if filters.negated:
            self._negated = not self._negated

    # ----------------------------------------------
    # Internal API for reuse by subclasses
    # ----------------------------------------------

    def _decode_child(self, child):
        """
        Produces arguments suitable for add_filter from a WHERE tree
        leaf (a tuple).
        """

        if django.VERSION < (1, 7):
            # TODO: Call get_db_prep_lookup directly, constraint.process
            #       doesn't do much more.
            constraint, lookup_type, annotation, value = child
            packed, value = constraint.process(lookup_type, value, self.connection)
            alias, column, db_type = packed
            field = constraint.field
        else:
            rhs, rhs_params = child.process_rhs(self.compiler, self.connection)

            lookup_type = child.lookup_name

            # Since NoSql databases generally don't support aggregation or
            # annotation we simply pass true in this case unless the query has a
            # get_aggregation method defined. It's a little troubling however that
            # the _nomalize_lookup_value method seems to only use this value in the case
            # that the value is an iterable and the lookup_type equals isnull.
            if hasattr(self, 'get_aggregation'):
                annotation = self.get_aggregation(using=self.connection)[None]
            else:
                annotation = True

            value = rhs_params

            packed = child.lhs.get_group_by_cols()[0]

            if django.VERSION < (1, 8):
                alias, column = packed
            else:
                alias = packed.alias
                column = packed.target.column
            field = child.lhs.output_field

        opts = self.query.model._meta
        if alias and alias != opts.db_table:
            raise DatabaseError("This database doesn't support JOINs "
                                "and multi-table inheritance.")

        # For parent.child_set queries the field held by the constraint
        # is the parent's primary key, while the field the filter
        # should consider is the child's foreign key field.
        if column != field.column:
            if not field.primary_key:
                raise DatabaseError("This database doesn't support filtering "
                                    "on non-primary key ForeignKey fields.")

            field = (f for f in opts.fields if f.column == column).next()
            assert field.rel is not None

        value = self._normalize_lookup_value(
            lookup_type, value, field, annotation)

        return field, lookup_type, value

    def _normalize_lookup_value(self, lookup_type, value, field, annotation):
        """
        Undoes preparations done by `Field.get_db_prep_lookup` not
        suitable for nonrel back-ends and passes the lookup argument
        through nonrel's `value_for_db`.

        TODO: Blank `Field.get_db_prep_lookup` and remove this method.
        """

        # Undo Field.get_db_prep_lookup putting most values in a list
        # (a subclass may override this, so check if it's a list) and
        # losing the (True / False) argument to the "isnull" lookup.
        if lookup_type not in ('in', 'range', 'year') and \
           isinstance(value, (tuple, list)):
            if len(value) > 1:
                raise DatabaseError("Filter lookup type was %s; expected the "
                                    "filter argument not to be a list. Only "
                                    "'in'-filters can be used with lists." %
                                    lookup_type)
            elif lookup_type == 'isnull':
                value = annotation
            else:
                value = value[0]

        # Remove percents added by Field.get_db_prep_lookup (useful
        # if one were to use the value in a LIKE expression).
        if lookup_type in ('startswith', 'istartswith'):
            value = value[:-1]
        elif lookup_type in ('endswith', 'iendswith'):
            value = value[1:]
        elif lookup_type in ('contains', 'icontains'):
            value = value[1:-1]

        # Prepare the value for a database using the nonrel framework.
        return self.ops.value_for_db(value, field, lookup_type)

    def _get_children(self, children):
        """
        Filters out nodes of the given contraint tree not needed for
        nonrel queries; checks that given constraints are supported.
        """
        result = []
        for child in children:

            if SubqueryConstraint is not None and isinstance(child, SubqueryConstraint):
                raise DatabaseError("Subqueries are not supported.")

            if isinstance(child, tuple):
                constraint, lookup_type, _, value = child

                # When doing a lookup using a QuerySet Django would use
                # a subquery, but this won't work for nonrel.
                # TODO: Add a supports_subqueries feature and let
                #       Django evaluate subqueries instead of passing
                #       them as SQL strings (QueryWrappers) to
                #       filtering.
                if isinstance(value, QuerySet):
                    raise DatabaseError("Subqueries are not supported.")

                # Remove leafs that were automatically added by
                # sql.Query.add_filter to handle negations of outer
                # joins.
                if lookup_type == 'isnull' and constraint.field is None:
                    continue

            result.append(child)
        return result

    def _matches_filters(self, entity, filters):
        """
        Checks if an entity returned by the database satisfies
        constraints in a WHERE tree (in-memory filtering).
        """

        # Filters without rules match everything.
        if not filters.children:
            return True

        result = filters.connector == AND

        for child in filters.children:

            # Recursively check a subtree,
            if isinstance(child, Node):
                submatch = self._matches_filters(entity, child)

            # Check constraint leaf, emulating a database condition.
            else:
                field, lookup_type, lookup_value = self._decode_child(child)
                entity_value = entity[field.column]

                if entity_value is None:
                    if isinstance(lookup_value, (datetime.datetime, datetime.date,
                                          datetime.time)):
                        submatch = lookup_type in ('lt', 'lte')
                    elif lookup_type in (
                            'startswith', 'contains', 'endswith', 'iexact',
                            'istartswith', 'icontains', 'iendswith'):
                        submatch = False
                    else:
                        submatch = EMULATED_OPS[lookup_type](
                            entity_value, lookup_value)
                else:
                    submatch = EMULATED_OPS[lookup_type](
                        entity_value, lookup_value)

            if filters.connector == OR and submatch:
                result = True
                break
            elif filters.connector == AND and not submatch:
                result = False
                break

        if filters.negated:
            return not result
        return result

    def _order_in_memory(self, lhs, rhs):
        for field, ascending in self.compiler._get_ordering():
            column = field.column

            # TOOD: cmp is removed in python 3. Rewrite this logic to leverage
            # the __eq__() special function.
            a = lhs.get(column)
            b = rhs.get(column)

            result = (a > b) - (a < b)
            if result != 0:
                return result if ascending else -result
        return 0


class NonrelCompiler(SQLCompiler):
    """
    Base class for data fetching back-end compilers.

    Note that nonrel compilers derive from sql.compiler.SQLCompiler and
    thus hold a reference to a sql.Query, not a NonrelQuery.

    TODO: Separate FetchCompiler from the abstract NonrelCompiler.
    """

    def __init__(self, query, connection, using):
        """
        Initializes the underlying SQLCompiler.
        """
        super(NonrelCompiler, self).__init__(query, connection, using)
        self.ops = self.connection.ops

    # ----------------------------------------------
    # Public API
    # ----------------------------------------------

    def results_iter(self, results=None):
        """
        Returns an iterator over the results from executing query given
        to this compiler. Called by QuerySet methods.
        """

        if results is None:
            fields = self.get_fields()
            try:
                results = self.build_query(fields).fetch(
                    self.query.low_mark, self.query.high_mark)
            except EmptyResultSet:
                results = []

        for entity in results:
            yield self._make_result(entity, fields)

    def has_results(self):
        return self.get_count(check_exists=True)

    def execute_sql(self, result_type=MULTI):
        """
        Handles SQL-like aggregate queries. This class only emulates COUNT
        by using abstract NonrelQuery.count method.
        """
        self.pre_sql_setup()

        aggregates = self.query.aggregate_select.values()

        # Simulate a count().
        if aggregates:
            assert len(aggregates) == 1
            aggregate = aggregates[0]
            if django.VERSION < (1, 8):
                if aggregate.sql_function != 'COUNT':
                    raise NotImplementedError("The database backend only supports count() queries.")
            else:
                if aggregate.function != 'COUNT':
                    raise NotImplementedError("The database backend only supports count() queries.")

            opts = self.query.get_meta()

            if django.VERSION < (1, 8):
                if aggregate.col != '*' and aggregate.col != (opts.db_table, opts.pk.column):
                    raise DatabaseError("This database backend only supports "
                                        "count() queries on the primary key.")
            else:
                # Fair warning: the latter part of this or statement hasn't been tested
                if aggregate.input_field.value != '*' and aggregate.input_field != (opts.db_table, opts.pk.column):
                    raise DatabaseError("This database backend only supports "
                                        "count() queries on the primary key.")

            count = self.get_count()
            if result_type is SINGLE:
                return [count]
            elif result_type is MULTI:
                return [[count]]

    # ----------------------------------------------
    # Additional NonrelCompiler API
    # ----------------------------------------------

    def _make_result(self, entity, fields):
        """
        Decodes values for the given fields from the database entity.

        The entity is assumed to be a dict using field database column
        names as keys. Decodes values using `value_from_db` as well as
        the standard `convert_values`.
        """
        result = []
        for field in fields:
            value = entity.get(field.column, NOT_PROVIDED)
            if value is NOT_PROVIDED:
                value = field.get_default()
            else:
                value = self.ops.value_from_db(value, field)
                # This is the default behavior of ``query.convert_values``
                # until django 1.8, where multiple converters are a thing.
                value = self.connection.ops.convert_values(value, field)
            if value is None and not field.null:
                raise IntegrityError("Non-nullable field %s can't be None!" %
                                     field.name)
            result.append(value)
        return result

    def check_query(self):
        """
        Checks if the current query is supported by the database.

        In general, we expect queries requiring JOINs (many-to-many
        relations, abstract model bases, or model spanning filtering),
        using DISTINCT (through `QuerySet.distinct()`, which is not
        required in most situations) or using the SQL-specific
        `QuerySet.extra()` to not work with nonrel back-ends.
        """
        if hasattr(self.query, 'is_empty') and self.query.is_empty():
            raise EmptyResultSet()
        if (len([a for a in self.query.alias_map if self.query.alias_refcount[a]]) > 1
                or self.query.distinct or self.query.extra or self.query.having):
            raise DatabaseError("This query is not supported by the database.")

    def get_count(self, check_exists=False):
        """
        Counts objects matching the current filters / constraints.

        :param check_exists: Only check if any object matches
        """
        if check_exists:
            high_mark = 1
        else:
            high_mark = self.query.high_mark
        try:
            return self.build_query().count(high_mark)
        except EmptyResultSet:
            return 0

    def build_query(self, fields=None):
        """
        Checks if the underlying SQL query is supported and prepares
        a NonrelQuery to be executed on the database.
        """
        self.check_query()
        if fields is None:
            fields = self.get_fields()
        query = self.query_class(self, fields)
        query.add_filters(self.query.where)
        query.order_by(self._get_ordering())

        # This at least satisfies the most basic unit tests.
        if django.VERSION < (1, 8):
            if connections[self.using].use_debug_cursor or (connections[self.using].use_debug_cursor is None and settings.DEBUG):
                self.connection.queries.append({'sql': repr(query)})
        else:
            if connections[self.using].force_debug_cursor or (connections[self.using].force_debug_cursor is None and settings.DEBUG):
                self.connection.queries.append({'sql': repr(query)})
        return query

    def get_fields(self):
        """
        Returns fields which should get loaded from the back-end by the
        current query.
        """

        # We only set this up here because related_select_fields isn't
        # populated until execute_sql() has been called.
        fields = get_selected_fields(self.query)

        # If the field was deferred, exclude it from being passed
        # into `resolve_columns` because it wasn't selected.
        only_load = self.deferred_to_columns()
        if only_load:
            db_table = self.query.model._meta.db_table
            only_load = dict((k, v) for k, v in only_load.items()
                             if v or k == db_table)
            if len(only_load.keys()) > 1:
                raise DatabaseError("Multi-table inheritance is not "
                                    "supported by non-relational DBs %s." %
                                    repr(only_load))
            fields = [f for f in fields if db_table in only_load and
                      f.column in only_load[db_table]]

        query_model = self.query.model
        if query_model._meta.proxy:
            query_model = query_model._meta.proxy_for_model

        for field in fields:
            if field.model._meta != query_model._meta:
                raise DatabaseError("Multi-table inheritance is not "
                                    "supported by non-relational DBs.")
        return fields

    def _get_ordering(self):
        """
        Returns a list of (field, ascending) tuples that the query
        results should be ordered by. If there is no field ordering
        defined returns just the standard_ordering (a boolean, needed
        for MongoDB "$natural" ordering).
        """
        opts = self.query.get_meta()
        if not self.query.default_ordering:
            ordering = self.query.order_by
        else:
            ordering = self.query.order_by or opts.ordering

        if not ordering:
            return self.query.standard_ordering

        field_ordering = []
        for order in ordering:
            if LOOKUP_SEP in order:
                raise DatabaseError("Ordering can't span tables on "
                                    "non-relational backends (%s)." % order)
            if order == '?':
                raise DatabaseError("Randomized ordering isn't supported by "
                                    "the backend.")

            ascending = not order.startswith('-')
            if not self.query.standard_ordering:
                ascending = not ascending

            name = order.lstrip('+-')
            if name == 'pk':
                name = opts.pk.name

            field_ordering.append((opts.get_field(name), ascending))
        return field_ordering


class NonrelInsertCompiler(NonrelCompiler):
    """
    Base class for all compliers that create new entities or objects
    in the database. It has to define execute_sql method due to being
    used in place of a SQLInsertCompiler.

    TODO: Analyze if it's always true that when field is None we should
          use the PK from self.query (check if the column assertion
          below ever fails).
    """

    def execute_sql(self, return_id=False):
        self.pre_sql_setup()

        to_insert = []
        pk_field = self.query.get_meta().pk
        for obj in self.query.objs:
            field_values = {}
            for field in self.query.fields:
                value = field.get_db_prep_save(
                    getattr(obj, field.attname) if self.query.raw else field.pre_save(obj, obj._state.adding),
                    connection=self.connection
                )
                if value is None and not field.null and not field.primary_key:
                    raise IntegrityError("You can't set %s (a non-nullable "
                                         "field) to None!" % field.name)

                # Prepare value for database, note that query.values have
                # already passed through get_db_prep_save.
                value = self.ops.value_for_db(value, field)

                field_values[field.column] = value
            to_insert.append(field_values)

        key = self.insert(to_insert, return_id=return_id)

        # Pass the key value through normal database deconversion.
        return self.ops.convert_values(self.ops.value_from_db(key, pk_field), pk_field)

    def insert(self, values, return_id):
        """
        Creates a new entity to represent a model.

        Note that the returned key will go through the same database
        deconversions that every value coming from the database does
        (`convert_values` and `value_from_db`).

        :param values: The model object as a list of (field, value)
                       pairs; each value is already prepared for the
                       database
        :param return_id: Whether to return the id or key of the newly
                          created entity
        """
        raise NotImplementedError


class NonrelUpdateCompiler(NonrelCompiler):

    def execute_sql(self, result_type):
        self.pre_sql_setup()

        values = []
        for field, _, value in self.query.values:
            if hasattr(value, 'prepare_database_save'):
                value = value.prepare_database_save(field)
            else:
                value = field.get_db_prep_save(value,
                                               connection=self.connection)
            value = self.ops.value_for_db(value, field)
            values.append((field, value))
        return self.update(values)

    def update(self, values):
        """
        Changes an entity that already exists in the database.

        :param values: A list of (field, new-value) pairs
        """
        raise NotImplementedError


class NonrelDeleteCompiler(NonrelCompiler):

    def execute_sql(self, result_type=MULTI):
        try:
            self.build_query([self.query.get_meta().pk]).delete()
        except EmptyResultSet:
            pass


class NonrelAggregateCompiler(NonrelCompiler):
    pass


class NonrelDateCompiler(NonrelCompiler):
    pass


class NonrelDateTimeCompiler(NonrelCompiler):
    pass
