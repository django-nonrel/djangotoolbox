from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.auth.models import UserPermissionList


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                  'is_staff', 'is_superuser')

class CustomUserAdmin(UserAdmin):
  fieldsets = None
  form = UserForm


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = ('permissions')


class CustomGroupAdmin(GroupAdmin):
    fieldsets = None
    form = GroupForm


class PermissionAdmin(admin.ModelAdmin):
    ordering = ('codename',)

class UserPermissionListAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserPermissionList, UserPermissionListAdmin)
admin.site.register(Permission, PermissionAdmin)

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Group, CustomGroupAdmin) 
