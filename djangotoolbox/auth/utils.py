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

def update_list(objs, list_cls, filter):
    obj_list, created = list_cls.objects.get_or_create(**filter)

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
    
def update_permissions_user(perms, user):
    update_list(perms, UserPermissionList, {'user': user})

def update_permissions_group(perms, group):
    update_list(perms, GroupPermissionList, {'group': group})

def update_user_groups(user, group):
    update_list(group, GroupList, {'user': user})
