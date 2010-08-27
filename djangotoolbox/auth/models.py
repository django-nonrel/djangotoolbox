from django.contrib.auth.models import User, Group
from django.db import models
from djangotoolbox.fields import ListField


def get_objs(obj_cls, obj_ids):
    objs = set()
    if len(obj_ids) > 0:
        objs.update(obj_cls .objects.filter(id__in=obj_ids).order_by('name'))
    return objs

class UserPermissionList(models.Model):
    user = models.ForeignKey(User)
    permission_list = ListField(models.CharField(max_length=128))
    group_permission_list = ListField(models.CharField(max_length=128))
    fk_list = ListField(models.PositiveIntegerField())

class GroupPermissionList(models.Model):
    group = models.ForeignKey(Group)
    permission_list = ListField(models.CharField(max_length=128))
    fk_list = ListField(models.PositiveIntegerField())


class GroupList(models.Model):
    """
    GroupLists are used to map a list of groups to a user
    """
    user = models.ForeignKey(User)
    fk_list = ListField(models.ForeignKey(Group))
    
    def __unicode__(self):
        return u'%s' %(self.user.username)
    
    def _get_objs(self):
        if not hasattr(self, '_groups_cache'):
            setattr(self, '_groups_cache', get_objs(Group, self.fk_list))
        return self._groups_cache
    groups = property(_get_objs)
