from django.contrib.auth.models import User, Permission
from djangotoolbox.contrib.auth.models import PermissionList

def add_permission_to_user(user, perm):
    try:
        perm_list = PermissionList.objects.get(user=user)
    except PermissionList.DoesNotExist:
        perm_list = PermissionList.objects.create(user=user)

    perm_list._permission_list.append(perm.id)
    perm_list.save()
