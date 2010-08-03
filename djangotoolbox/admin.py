from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group, Permission

from djangotoolbox.auth.utils import update_permissions_user
from djangotoolbox.auth.models import UserPermissionList


class UserForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
   
        permissions_objs = Permission.objects.all().order_by('name')
        choices = list ()
        for perm_obj in permissions_objs:
            choices.append([perm_obj.id, perm_obj.name])

        selected = list()
        try:
            user_perm_list = UserPermissionList.objects.get(user=kwargs['instance'])
            self.fields['permissions'].initial = user_perm_list.fk_list
        except UserPermissionList.DoesNotExist:
            pass
                                    
        self.fields['permissions'].choices = choices
        
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

                
class PermissionAdmin(admin.ModelAdmin):
    ordering = ('name',)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
