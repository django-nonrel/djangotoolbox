from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from djangotoolbox.auth.models import UserPermissionList, GroupPermissionList, GroupList


class NonrelPermissionBackend(ModelBackend):
    """
    Implements Django's permission system on Django-Nonrel
    """
    supports_object_permissions = False
    supports_anonymous_user = True

    def get_group_permissions(self, user_obj):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        """
        if not hasattr(user_obj, '_group_perm_cache'):
            perm_objs = set([])
            try:
                gl = GroupList.objects.get(user=user_obj)
                group_ids = gl.fk_list
                if len(group_ids) > 0:
                    group_permissions = set()
                    for group_id in group_ids:
                        group_permissions.update(GroupPermissionList.objects.filter(group__id=group_id))
                    for group_perm in group_permissions:
                        perm_objs.update(group_perm.permissions)
                    
            except GroupList.DoesNotExist:
                pass
            
            perms = list([[perm.content_type.app_label, perm.codename] for perm in perm_objs])
            user_obj._group_perm_cache = set(["%s.%s" % (ct, name) for ct, name in perms])
        return user_obj._group_perm_cache

    def get_all_permissions(self, user_obj):
        if user_obj.is_anonymous():
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            try:
                pl = UserPermissionList.objects.get(user=user_obj)
                user_obj._perm_cache = set([u"%s.%s" % (p.content_type.app_label, p.codename) for p in pl.permissions])
            except UserPermissionList.DoesNotExist:
                user_obj._perm_cache = set()
                pass
            user_obj._perm_cache.update(self.get_group_permissions(user_obj))
        return user_obj._perm_cache

    def has_perm(self, user_obj, perm):
        return perm in self.get_all_permissions(user_obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Returns True if user_obj has any permissions in the given app_label.
        """
        for perm in self.get_all_permissions(user_obj):
            if perm[:perm.index('.')] == app_label:
                return True
        return False

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
