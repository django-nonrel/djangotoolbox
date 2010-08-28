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
    permission_fk_list = ListField(models.CharField(max_length=32))

    group_fk_list = ListField(models.CharField(max_length=32))

    def _get_objs(self):
        return get_objs(Group, self.group_fk_list)


class GroupPermissionList(models.Model):
    group = models.ForeignKey(Group)
    permission_list = ListField(models.CharField(max_length=128))
    permission_fk_list = ListField(models.CharField(max_length=32))
