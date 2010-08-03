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

def update_permissions_user(perms, user):
    obj_list, created = UserPermissionList.objects.get_or_create(user=user)

    old_permissions = list(obj_list.permissions)
    
    for perm in old_permissions:
        try:
            perms.index(perm)
        except ValueError:
            obj_list.fk_list.remove(perm.id)
    
    for perm in perms      :
        try:
            old_permissions.index(perm)
        except ValueError:
            obj_list.fk_list.append(perm.id)
    
    obj_list.save()
