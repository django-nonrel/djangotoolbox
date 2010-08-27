from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from djangotoolbox.auth.models import UserPermissionList, GroupPermissionList, GroupList


class NonrelPermissionBackend(ModelBackend):
    """
    Implements Django's permission system on Django-Nonrel
    """
    supports_object_permissions = False
    supports_anonymous_user = True
    
    def get_group_permissions(self, user_obj, user_perm_obj=None):
        """
        Returns a set of permission strings that this user has through his/her
        groups.
        """
        if not hasattr(user_obj, '_group_perm_cache'):
            perms = set([])
            if user_perm_obj is None:
                try:
                    pl = UserPermissionList.objects.get(user=user_obj)
                    perms = pl.group_permission_list
                except UserPermissionList.DoesNotExist:
                    pass
            else:
                perms = user_perm_obj.group_permission_list

            user_obj._group_perm_cache = perms
        return user_obj._group_perm_cache
    
    def get_all_permissions(self, user_obj):
        if user_obj.is_anonymous():
            return set()
        if not hasattr(user_obj, '_perm_cache'):
            try:
                pl = UserPermissionList.objects.get(user=user_obj)
                user_obj._perm_cache = set(pl.permission_list)
                
            except UserPermissionList.DoesNotExist:
                pl = None
                user_obj._perm_cache = set()
                
            user_obj._perm_cache.update(self.get_group_permissions(user_obj, pl))
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
