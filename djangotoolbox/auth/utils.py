from copy import copy

from djangotoolbox.auth.models import UserPermissionList, GroupPermissionList


def add_perm_to(obj, list_cls, filter):
    obj_list, created = list_cls.objects.get_or_create(**filter)
    obj_list.permission_list.append('%s.%s' % (obj.content_type.app_label,\
                                               obj.codename))
    obj_list.save()

def add_permission_to_user(perm, user):
    add_perm_to(perm, UserPermissionList,  {'user': user }) 

def add_user_to_group(user, group):
    obj_list, created = UserPermissionList.objects.get_or_create(user=user)
    obj_list.group_fk_list.append(group.id)
    obj_list.save()
    
def add_permission_to_group(perm, group):
    add_perm_to(perm, GroupPermissionList, {'group': group})

def update_list(perm_objs, list_cls, filter):
    """
    updates a list of permissions
    list_cls can be GroupPermissionList or UserPermissionList
    """
    
    list_obj, created = list_cls.objects.get_or_create(**filter)    
    old_perms = copy(list_obj.permission_list)

    perm_strs = ['%s.%s' % (perm.content_type.app_label, perm.codename) \
                 for perm in perm_objs]
    perm_ids = [perm.id for perm in perm_objs]
    
    for perm in old_perms:
        try: 
            perm_strs.index(perm)
        except ValueError:
            i = list_obj.permission_list.index(perm)
            list_obj.permission_list.pop(i)
            list_obj.permission_fk_list.pop(i)

    i = 0    
    for perm in perm_strs:
        try:
            old_perms.index(perm)
        except ValueError:
            list_obj.permission_list.append(perm)
            list_obj.permission_fk_list.append(perm_ids[i])
        i += 1

    list_obj.save()
    
def update_permissions_user(perms, user):
    update_list(perms, UserPermissionList, {'user': user})

def update_permissions_group(perms, group):
    update_list(perms, GroupPermissionList, {'group': group})

def update_user_groups(user, groups):
    new_group_ids = [ group.id for group in groups]
    pl, created = UserPermissionList.objects.get_or_create(user=user)
    old_group_ids = copy(pl.group_fk_list)
    
    for group_id in old_group_ids:
        try:
            new_group_ids.index(group_id)
        except ValueError:
            pl.group_fk_list.remove(group_id)
    
    for group_id in new_group_ids:
        try:
            old_group_ids.index(group_id)
        except ValueError:
            pl.group_fk_list.append(group_id)
    
    pl.save()
