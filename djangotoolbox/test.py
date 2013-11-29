from django.test import TestCase
from django.utils.unittest import TextTestResult, TextTestRunner

try:
    from django.test.runner import DiscoverRunner as TestRunner
except ImportError:
    from django.test.simple import DjangoTestSuiteRunner as TestRunner

from .utils import object_list_to_table

import re


class ModelTestCase(TestCase):
    """
    A test case for models that provides an easy way to validate the DB
    contents against a given list of row-values.

    You have to specify the model to validate using the 'model'
    attribute:

    class MyTestCase(ModelTestCase):
        model = MyModel
    """

    def validate_state(self, columns, *state_table):
        """
        Validates that the DB contains exactly the values given in the
        state table. The list of columns is given in the columns tuple.

        Example:
        self.validate_state(
            ('a', 'b', 'c'),
            (1, 2, 3),
            (11, 12, 13),
        )
        validates that the table contains exactly two rows and that
        their 'a', 'b', and 'c' attributes are 1, 2, 3 for one row and
        11, 12, 13 for the other row. The order of the rows doesn't
        matter.
        """
        current_state = object_list_to_table(
            columns, self.model.all())[1:]
        if not equal_lists(current_state, state_table):
            print "DB state not valid:"
            print "Current state:"
            print columns
            for state in current_state:
                print state
            print "Should be:"
            for state in state_table:
                print state
            self.fail("DB state not valid.")


class CapturingTestSuiteRunner(TestRunner):
    """
    Captures stdout/stderr during test and shows them next to
    tracebacks.
    """

    def run_suite(self, suite, **kwargs):
        return TextTestRunner(verbosity=self.verbosity,
                              failfast=self.failfast,
                              buffer=True).run(suite)

_EXPECTED_ERRORS = [
    r"This query is not supported by the database\.",
    r"Multi-table inheritance is not supported by non-relational DBs\.",
    r"TextField is not indexed, by default, so you can't filter on it\.",
    r"First ordering property must be the same as inequality filter property",
    r"This database doesn't support filtering on non-primary key ForeignKey fields\.",
    r"Only AND filters are supported\.",
    r"MultiQuery does not support keys_only\.",
    r"You can't query against more than 30 __in filter value combinations\.",
    r"Only strings and positive integers may be used as keys on GAE\.",
    r"This database does not support <class '.*'> aggregates\.",
    r"Subqueries are not supported \(yet\)\.",
    r"Cursors are not supported\.",
    r"This database backend only supports count\(\) queries on the primary key\.",
    r"AutoField \(default primary key\) values must be strings representing an ObjectId on MongoDB",
]


class NonrelTestResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super(NonrelTestResult, self).__init__(*args, **kwargs)
        self._compiled_exception_matchers = [re.compile(expr) for expr in _EXPECTED_ERRORS]

    def __match_exception(self, exc):
        for exc_match in self._compiled_exception_matchers:
            if exc_match.search(str(exc)):
                return True
        return False

    def addError(self, test, err):
        exc = err[1]
        if self.__match_exception(exc):
            super(NonrelTestResult, self).addExpectedFailure(test, err)
        else:
            super(NonrelTestResult, self).addError(test, err)


class NonrelTestSuiteRunner(TestRunner):
    def run_suite(self, suite, **kwargs):
        return TextTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
            resultclass=NonrelTestResult,
            buffer=False
        ).run(suite)
