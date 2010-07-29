from django.db import models
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.fields import ListField

        
class UserPermissionList(models.Model):
    user = models.ForeignKey(User)
    _fk_list = ListField(models.ForeignKey(Permission))

    def _get_permissions(self):
        if not hasattr(self, '_permissions_cache'):
            perm_ids = self._fk_list
            permissions = set()
            if len(perm_ids) > 0:
                # order_by() has to be used to override invalid default Permission filter
                permissions.update(Permission.objects.filter(id__in=perm_ids).order_by('name'))
            setattr(self, '_permissions_cache', permissions)
            
        return self._permissions_cache
    permission_list = property(_get_permissions)


class GroupPermissionList(models.Model):
    group = models.ForeignKey(Group)
    _fk_list = ListField(models.ForeignKey(Permission))

    def _get_permissions(self):
        if not hasattr(self, '_permissions_cache'):
            perm_ids = self._fk_list
            permissions = set()
            if len(perm_ids) > 0:
                # order_by() has to be used to override invalid default Permission filter
                permissions.update(Permission.objects.filter(id__in=perm_ids).order_by('name'))
            setattr(self, '_permissions_cache', permissions)
            
        return self._permissions_cache
    permissions = property(_get_permissions)

class GroupList(models.Model):
    """
    GroupLists are used to map a list of groups to a user
    """
    user = models.ForeignKey(User)
    _fk_list = ListField(models.ForeignKey(Group))

    def __unicode__(self):
        return u'%s' %(self.user.username)
    
    def _get_group_list(self):
        if not hasattr(self, '_groups_cache'):
            group_ids = self._fk_list
            groups = set()
            if len(group_ids) > 0:
                # order_by() has to be used to override invalid default Permission filter
                groups.update(Group.objects.filter(id__in=group_ids))
            setattr(self, '_groups_cache', groups)
            
        return self._groups_cache
    groups = property(_get_group_list)

    
