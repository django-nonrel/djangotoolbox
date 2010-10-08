from .utils import object_list_to_table, equal_lists
from django.test import TestCase
from django.test.simple import DjangoTestSuiteRunner, DjangoTestRunner
import sys

try:
    from StringIO import StringIO
except ImportError:
    from cStringIO import StringIO

def skip_if(test):
    """Skips a unit test if ``test`` is ``True``"""
    def _inner(func):
        if test:
            return None
        return func
    return _inner

class ModelTestCase(TestCase):
    """
    A test case for models that provides an easy way to validate the DB
    contents against a given list of row-values.

    You have to specify the model to validate using the 'model' attribute:
    class MyTestCase(ModelTestCase):
        model = MyModel
    """
    def validate_state(self, columns, *state_table):
        """
        Validates that the DB contains exactly the values given in the state
        table. The list of columns is given in the columns tuple.

        Example:
        self.validate_state(
            ('a', 'b', 'c'),
            (1, 2, 3),
            (11, 12, 13),
        )
        validates that the table contains exactly two rows and that their
        'a', 'b', and 'c' attributes are 1, 2, 3 for one row and 11, 12, 13
        for the other row. The order of the rows doesn't matter.
        """
        current_state = object_list_to_table(columns,
            self.model.all())[1:]
        if not equal_lists(current_state, state_table):
            print 'DB state not valid:'
            print 'Current state:'
            print columns
            for state in current_state:
                print state
            print 'Should be:'
            for state in state_table:
                print state
            self.fail('DB state not valid')

class CapturingTestRunner(DjangoTestRunner):
    def _makeResult(self):
        result = super(CapturingTestRunner, self)._makeResult()
        stdout = sys.stdout
        stderr = sys.stderr

        def extend_error(errors):
            try:
                captured_stdout = sys.stdout.getvalue()
                captured_stderr = sys.stderr.getvalue()
            except AttributeError:
                captured_stdout = captured_stderr = ''
            sys.stdout = stdout
            sys.stderr = stderr
            t, e = errors[-1]
            if captured_stdout:
                e += '\n--------------- Captured stdout: ---------------\n'
                e += captured_stdout
            if captured_stderr:
                e += '\n--------------- Captured stderr: ---------------\n'
                e += captured_stderr
            if captured_stdout or captured_stderr:
                e += '\n--------------- End captured output ---------------\n\n'
            errors[-1] = (t, e)

        def override(func):
            func.orig = getattr(result, func.__name__)
            setattr(result, func.__name__, func)
            return func

        @override
        def startTest(test):
            startTest.orig(test)
            sys.stdout = StringIO()
            sys.stderr = StringIO()

        @override
        def addSuccess(test):
            addSuccess.orig(test)
            sys.stdout = stdout
            sys.stderr = stderr

        @override
        def addError(test, err):
            addError.orig(test, err)
            extend_error(result.errors)

        @override
        def addFailure(test, err):
            addFailure.orig(test, err)
            extend_error(result.failures)

        return result

class CapturingTestSuiteRunner(DjangoTestSuiteRunner):
    def run_suite(self, suite, **kwargs):
        return CapturingTestRunner(verbosity=self.verbosity, failfast=self.failfast).run(suite)
