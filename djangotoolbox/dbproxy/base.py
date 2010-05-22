from django.db import connections

class Proxy(object):
    def __init__(self, target):
        self.__target = target
    
    def __getattr__(self, name):
        return getattr(self.__target, name)

class DatabaseWrapper(Proxy):
    def __init__(self, settings_dict, *args, **kwds):
        super(DatabaseWrapper, self).__init__(
            connections[settings_dict['TARGET_BACKEND']])
