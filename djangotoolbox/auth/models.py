from django.db import models
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.fields import ListField


def get_objs(obj_cls, obj_ids):
    objs = set()
    if len(obj_ids) > 0:
        # order_by() has to be used to override invalid default Permission filter
        objs.update(obj_cls .objects.filter(id__in=obj_ids).order_by('name'))
    return objs

class UserPermissionList(models.Model):
    user = models.ForeignKey(User)
    fk_list = ListField(models.ForeignKey(Permission))

    def _get_permissions(self):
        if not hasattr(self, '_permissions_cache'):
            setattr(self, '_permissions_cache', get_objs(Permission, self.fk_list))            
        return self._permissions_cache
    permissions = property(_get_permissions)


class GroupPermissionList(models.Model):
    group = models.ForeignKey(Group)
    fk_list = ListField(models.ForeignKey(Permission))

    def _get_permissions(self):
        if not hasattr(self, '_permissions_cache'):
            setattr(self, '_permissions_cache', get_objs(Permission, self.fk_list))            
        return self._permissions_cache
    permissions = property(_get_permissions)

class GroupList(models.Model):
    """
    GroupLists are used to map a list of groups to a user
    """
    user = models.ForeignKey(User)
    fk_list = ListField(models.ForeignKey(Group))

    def __unicode__(self):
        return u'%s' %(self.user.username)
    
    def _get_group_list(self):
        if not hasattr(self, '_groups_cache'):
            setattr(self, '_groups_cache', get_objs(Group, self.fk_list))
        return self._groups_cache
    groups = property(_get_group_list)
