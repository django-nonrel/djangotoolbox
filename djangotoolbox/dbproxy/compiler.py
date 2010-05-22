from .base import Proxy
from django.conf import settings
from django.db.models.sql import aggregates as sqlaggregates
from django.db.models.sql.constants import LOOKUP_SEP, MULTI, SINGLE
from django.db.models.sql.where import AND, OR
from django.db.utils import DatabaseError, IntegrityError
from django.utils.tree import Node

class SQLCompiler(Proxy):
    def execute_sql(self, result_type=MULTI):
        """
        Handles aggregate/count queries
        """
        pass

    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        pass

    def has_results(self):
        pass

class SQLInsertCompiler(Proxy):
    def execute_sql(self, return_id=False):
        pass

class SQLUpdateCompiler(Proxy):
    def execute_sql(self, result_type=MULTI):
        pass

class SQLDeleteCompiler(Proxy):
    def execute_sql(self, result_type=MULTI):
        pass
