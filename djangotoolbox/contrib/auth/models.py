from django.db import models
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.fields import ListField

        
class UserPermissionList(models.Model):
    user = models.ForeignKey(User)
    _permission_list = ListField(models.ForeignKey(Permission))

    def _get_permissions(self):
        if not hasattr(self, '_permissions_cache'):
            perm_ids = self._permission_list
            permissions = set()
            if len(perm_ids) > 0:
                # order_by() has to be used to override invalid default Permission filter
                permissions.update(Permission.objects.filter(id__in=perm_ids).order_by('name'))
            setattr(self, '_permissions_cache', permissions)
            
        return self._permissions_cache
    permission_list = property(_get_permissions)

class GroupPermissionList(models.Model):
    user = models.ForeignKey(Group)
    _permission_list = ListField(models.ForeignKey(Permission))

    def _get_permissions(self):
        if not hasattr(self, '_permissions_cache'):
            perm_ids = self._permission_list
            permissions = set()
            if len(perm_ids) > 0:
                # order_by() has to be used to override invalid default Permission filter
                permissions.update(Permission.objects.filter(id__in=perm_ids).order_by('name'))
            setattr(self, '_permissions_cache', permissions)
            
        return self._permissions_cache
    permission_list = property(_get_permissions)

class GroupList(models.Model):
    """
    GroupLists are used to map a list of groups to a user
    """
    group = models.ForeignKey(Group)
    groups = ListField(models.ForeignKey(Group))
