from django.db import connections
from django.utils.importlib import import_module

class Proxy(object):
    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        return getattr(self._target, name)

class OperationsProxy(Proxy):
    compiler_module = __name__.rsplit('.', 1)[0] + '.compiler'

    def __init__(self, *args, **kwargs):
        super(OperationsProxy, self).__init__(*args, **kwargs)
        self._cache = {}

    def compiler(self, compiler_name):
        target = self._target.compiler(compiler_name)
        if compiler_name not in self._cache:
            base = getattr(
                import_module(self.compiler_module), compiler_name)
            class Compiler(base, target):
                pass
            self._cache[compiler_name] = Compiler
        return self._cache[compiler_name]

class DatabaseWrapper(Proxy):
    def __init__(self, settings_dict, *args, **kwds):
        super(DatabaseWrapper, self).__init__(
            connections[settings_dict['TARGET']])
        self.ops = OperationsProxy(self.ops)
