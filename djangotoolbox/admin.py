import settings
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.auth.utils import update_permissions_user, \
     update_user_groups, update_permissions_group
from djangotoolbox.auth.models import UserPermissionList, GroupList, \
     GroupPermissionList

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                  'is_staff', 'is_superuser')


class NonrelPermissionUserForm(UserForm):
    user_permissions = forms.MultipleChoiceField(required=False)
    groups = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(NonrelPermissionUserForm, self).__init__(*args, **kwargs)

        self.fields['user_permissions'] = forms.MultipleChoiceField(required=False)
        self.fields['groups'] = forms.MultipleChoiceField(required=False)
        
        permissions_objs = Permission.objects.all().order_by('name')
        choices = []
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])
        self.fields['user_permissions'].choices = choices
        
        group_objs = Group.objects.all()
        choices = []
        for group_obj in group_objs:
            choices.append([group_obj.id, group_obj.name])
        self.fields['groups'].choices = choices

        try:
            user_perm_list = UserPermissionList.objects.get(
                user=kwargs['instance'])
            self.fields['user_permissions'].initial = user_perm_list.fk_list
        except (UserPermissionList.DoesNotExist, KeyError):
            self.fields['user_permissions'].initial = list()
            
        try:
            user_group_list = GroupList.objects.get(
                user=kwargs['instance'])
            self.fields['groups'].initial = user_group_list.fk_list
        except (GroupList.DoesNotExist, KeyError):
            self.fields['groups'].initial = list()


class CustomUserAdmin(UserAdmin):
    fieldsets = None
    form = UserForm
    

class NonrelPermissionCustomUserAdmin(UserAdmin):
    fieldsets = None
    form = NonrelPermissionUserForm
    
    def save_model(self, request, obj, form, change):
        super(NonrelPermissionCustomUserAdmin, self).save_model(request, obj, form, change)

        if len(form.cleaned_data['user_permissions']) > 0:
            permissions = list(Permission.objects.filter(
                id__in=form.cleaned_data['user_permissions']).order_by('name'))
        else:
            permissions = []

        update_permissions_user(permissions, obj)

        if len(form.cleaned_data['groups']) > 0:
            groups = list(Group.objects.filter(
                id__in=form.cleaned_data['groups']))
        else:
            groups = []

        update_user_groups(obj, groups)


class PermissionAdmin(admin.ModelAdmin):
    ordering = ('name',)


class GroupForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)

        self.fields['permissions'] = forms.MultipleChoiceField(required=False)
   
        permissions_objs = Permission.objects.all().order_by('name')
        choices = []
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])
        self.fields['permissions'].choices = choices

        try:
            current_perm_list = GroupPermissionList.objects.get(
                group=kwargs['instance'])
            self.fields['permissions'].initial = current_perm_list.fk_list
        except (GroupPermissionList.DoesNotExist, KeyError):
            self.fields['permissions'].initial = []
        
    class Meta:
        model = Group
        fields = ('name',)


class CustomGroupAdmin(admin.ModelAdmin):
    form = GroupForm
    fieldsets = None

    def save_model(self, request, obj, form, change):
        super(CustomGroupAdmin, self).save_model(request, obj, form, change)

        if len(form.cleaned_data['permissions']) > 0:
            permissions = list(Permission.objects.filter(
                id__in=form.cleaned_data['permissions']).order_by('name'))
        else:
            permissions = []
            

        update_permissions_group(permissions, obj)

admin.site.unregister(User)
admin.site.unregister(Group)

backends = getattr(settings, 'AUTHENTICATION_BACKENDS', list())
backend_name = 'djangotoolbox.auth.backends.NonrelPermissionBackend'
if backend_name in backends:
    admin.site.register(User, NonrelPermissionCustomUserAdmin)
    admin.site.register(Permission, PermissionAdmin)
    admin.site.register(Group, CustomGroupAdmin)
else:
    admin.site.register(User, CustomUserAdmin)

