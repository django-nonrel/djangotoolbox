from djangotoolbox.auth.models import UserPermissionList, GroupPermissionList, GroupList

def add_to(obj, list_cls, filter):
    try:
        obj_list = list_cls.objects.get(**filter)
    except list_cls.DoesNotExist:
        obj_list = list_cls.objects.create(**filter)

    obj_list._fk_list.append(obj.id)
    obj_list.save()

def add_permission_to_user(perm, user):
    add_to(perm, UserPermissionList,  {'user': user }) 

def add_user_to_group(user, group):
    add_to(group, GroupList, {'user': user})
        
def add_permission_to_group(perm, group):
    add_to(perm, GroupPermissionList, {'group': group})

