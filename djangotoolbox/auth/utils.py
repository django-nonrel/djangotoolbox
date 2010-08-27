from djangotoolbox.auth.models import UserPermissionList, GroupPermissionList, GroupList

def add_to(obj, list_cls, filter):
    obj_list, created = list_cls.objects.get_or_create(**filter)

    obj_list.fk_list.append(obj.id)
    obj_list.save()

def add_permission_to_user(perm, user):
    add_to(perm, UserPermissionList,  {'user': user }) 

def add_user_to_group(user, group):
    add_to(group, GroupList, {'user': user})
        
def add_permission_to_group(perm, group):
    add_to(perm, GroupPermissionList, {'group': group})

def update_list(perm_objs, list_cls, filter):
    list_obj, created = list_cls.objects.get_or_create(**filter)

    old_perms = list_obj.permission_list

    perm_strs = ['%s.%s' % (perm.content_type.app_label, perm.codename) for perm in perm_objs]

    for perm in old_perms:
        try: 
            perm_strs.index(perm)
        except ValueError:
            list_obj.permission_list.remove(perm)

    for perm in perm_strs:
        try:
            old_perms.index(perm)
        except ValueError:
            list_obj.permission_list.append(perm)

    if len(perm_strs) == 0:
        list_obj.permission_list = []
        
    list_obj.save()
    
def update_permissions_user(perms, user):
    update_list(perms, UserPermissionList, {'user': user})

def update_permissions_group(perms, group):
    update_list(perms, GroupPermissionList, {'group': group})

def update_user_groups(user, group):
    objs = group
    obj_list, created = GroupList.objects.get_or_create(user=user)

    old_objs = list(obj_list._get_objs())
    
    for obj in old_objs:
        try:
            objs.index(obj)
        except ValueError:
            obj_list.fk_list.remove(obj.id)
    
    for obj in objs:
        try:
            old_objs.index(obj)
        except ValueError:
            obj_list.fk_list.append(obj.id)
    
    obj_list.save()

