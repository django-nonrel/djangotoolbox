from django.contrib.auth.models import User, Permission
from djangotoolbox.contrib.auth.models import UserPermissionList, GroupPermissionList, GroupList

def add_permission_to_user(perm, user):
    try:
        perm_list = UserPermissionList.objects.get(user=user)
    except UserPermissionList.DoesNotExist:
        perm_list = UserPermissionList.objects.create(user=user)

    perm_list._permission_list.append(perm.id)
    perm_list.save()


def add_user_to_group(user, group):
    try:
        group_list = GroupList.objects.get(user=user)
    except GroupList.DoesNotExist:
        group_list = GroupList.objects.create(user=user)

    group_list._group_list.append(group.id)
    group_list.save()

def add_permission_to_group(perm, group):
    try:
        perm_list = GroupPermissionList.objects.get(group=group)
    except GroupPermissionList.DoesNotExist:
        perm_list = GroupPermissionList.objects.create(group=group)
        
    perm_list._permission_list.append(perm.id)
    perm_list.save()          
