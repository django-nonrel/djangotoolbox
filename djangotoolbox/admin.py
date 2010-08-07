from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.auth.utils import update_permissions_user,\
     update_user_groups, update_permissions_group
from djangotoolbox.auth.models import UserPermissionList, GroupList, \
     GroupPermissionList


class UserForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(required=False)
    groups = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
   
        permissions_objs = Permission.objects.all().order_by('name')
        choices = list ()
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])
        self.fields['permissions'].choices = choices
        
        group_objs = Group.objects.all()
        choices = list ()
        for group_obj in group_objs:
            choices.append([group_obj.id, group_obj.name])
        self.fields['groups'].choices = choices

        try:
            user_perm_list = UserPermissionList.objects.get(user=kwargs['instance'])
            self.fields['permissions'].initial = user_perm_list.fk_list
        except (UserPermissionList.DoesNotExist, KeyError):
            self.fields['permissions'].initial = list()
            
        try:
            user_group_list = GroupList.objects.get(user=kwargs['instance'])
            self.fields['groups'].initial = user_group_list.fk_list
        except (GroupList.DoesNotExist, KeyError):
            self.fields['groups'].initial = list()
                                    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                  'is_staff', 'is_superuser',)


class CustomUserAdmin(UserAdmin):
    fieldsets = None
    form = UserForm
    
    def save_model(self, request, obj, form, change):
        super(CustomUserAdmin, self).save_model(request, obj, form, change)

        if len(form.cleaned_data['permissions']) > 0:
            permissions = list(Permission.objects.filter(id__in=form.cleaned_data['permissions']).order_by('name'))
        else:
            permissions = list()
            

        update_permissions_user(permissions, obj)

        if len(form.cleaned_data['groups']) > 0:
            groups = list(Group.objects.filter(id__in=form.cleaned_data['groups']))
        else:
            groups = list()

        update_user_groups(obj, groups)
                
class PermissionAdmin(admin.ModelAdmin):
    ordering = ('name',)


class GroupForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
   
        permissions_objs = Permission.objects.all().order_by('name')
        choices = list ()
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])
        self.fields['permissions'].choices = choices

        try:
            current_perm_list = GroupPermissionList.objects.get(group=kwargs['instance'])
            self.fields['permissions'].initial = current_perm_list.fk_list
        except (GroupPermissionList.DoesNotExist, KeyError):
            self.fields['permissions'].initial = list()
        
    class Meta:
        model = Group
        fields = ('name',)

class CustomGroupAdmin(admin.ModelAdmin):
    form = GroupForm
    fieldsets = None

    def save_model(self, request, obj, form, change):
        super(CustomGroupAdmin, self).save_model(request, obj, form, change)

        if len(form.cleaned_data['permissions']) > 0:
            permissions = list(Permission.objects.filter(id__in=form.cleaned_data['permissions']).order_by('name'))
        else:
            permissions = list()
            

        update_permissions_group(permissions, obj)

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
