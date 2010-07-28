from django.contrib.auth.models import User, Permission
from djangotoolbox.contrib.auth.models import UserPermissionList, GroupPermissionList

def add_permission_to_user(user, perm):
    try:
        perm_list = UserPermissionList.objects.get(user=user)
    except UserPermissionList.DoesNotExist:
        perm_list = UserPermissionList.objects.create(user=user)

    perm_list._permission_list.append(perm.id)
    perm_list.save()
