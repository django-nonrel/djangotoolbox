from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group, Permission, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from djangotoolbox.auth.models import UserPermissionList, \
     GroupPermissionList, GroupList
from djangotoolbox.auth.utils import add_permission_to_user, \
     add_user_to_group, add_permission_to_group


class BackendTest(TestCase):

    backend = 'djangotoolbox.contrib.auth.backends.NonrelModelBackend'

    def setUp(self):
        User.objects.create_user('test', 'test@example.com', 'test')

    def test_add_permission_to_user(self):
        content_type = ContentType.objects.get_for_model(User)
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user = User.objects.get(username='test')
        add_permission_to_user(perm, user)
        self.assertEqual(UserPermissionList.objects.count(), 1)
        pl = UserPermissionList.objects.all()[0]
        self.assertEqual(pl.permissions , set([perm]))
        self.assertEqual(user.has_perm('auth.test'), True)

    def test_add_user_to_group(self):
        user = User.objects.get(username='test')
        group = Group.objects.create(name='test_group')
        add_user_to_group(user, group)
        self.assertEqual(GroupList.objects.count(), 1)
        self.assertNotEqual(GroupList.objects.all()[0] , None)

    def test_add_permission_to_group(self):
        content_type = ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user = User.objects.get(username='test')
        group = Group.objects.create(name='test_group')
        add_user_to_group(user, group)
        add_permission_to_group(perm, group)
        self.assertEqual(GroupPermissionList.objects.count(), 1)
        gl = GroupPermissionList.objects.all()[0]
        self.assertEqual(gl.permissions , set([perm]))
        self.assertEqual(user.has_perm('auth.test'), True)
        
    def test_has_perm(self):
        user = User.objects.get(username='test')
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_staff = True
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_superuser = True
        user.save()
        self.assertEqual(user.has_perm('auth.test'), True)
        user.is_staff = False
        user.is_superuser = False
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = False
        user.save()
        self.assertEqual(user.has_perm('auth.test'), False)

    def test_custom_perms(self):
        user = User.objects.get(username='test')
        content_type = ContentType.objects.get_for_model(Permission)
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        # default django way (ManyToManyField)
        #user.user_permissions.add(perm)      

        add_permission_to_user(perm, user)
        
        # reloading user to purge the _perm_cache
        user = User.objects.get(username='test')
        self.assertEqual(user.get_all_permissions() == set([u'auth.test']), True)
        self.assertEqual(user.get_group_permissions(), set([]))
        self.assertEqual(user.has_module_perms('Group'), False)
        self.assertEqual(user.has_module_perms('auth'), True)
        
        perm = Permission.objects.create(name='test2',
                                         content_type=content_type,
                                         codename='test2')
        
        # default django way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)
        
        perm = Permission.objects.create(name='test3',
                                         content_type=content_type,
                                         codename='test3')

        # default django  way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)

        user = User.objects.get(username='test')
        self.assertEqual(user.get_all_permissions(),
                         set([u'auth.test2', u'auth.test', u'auth.test3']))
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), True)
        
        perm = Permission.objects.create(name='test_group',
                                         content_type=content_type,
                                         codename='test_group')
        group = Group.objects.create(name='test_group')

        # default django way (ManyToManyField)
        #group.permissions.add(perm)

        add_permission_to_group(perm, group)

        # default django way (ManyToManyField)
        #user.groups.add(group)

        add_user_to_group(user, group)
        
        user = User.objects.get(username='test')
        exp = set([u'auth.test2', u'auth.test',
                   u'auth.test3', u'auth.test_group'])
        self.assertEqual(user.get_all_permissions(), exp)
        self.assertEqual(user.get_group_permissions(),
                         set([u'auth.test_group']))
        self.assertEqual(user.has_perms(['auth.test3', 'auth.test_group']),
                         True)

        user = AnonymousUser()
        self.assertEqual(user.has_perm('test'), False)
        self.assertEqual(user.has_perms(['auth.test2', 'auth.test3']), False)
        
    def test_has_no_object_perm(self):
        """Regressiontest for #12462"""
        
        user = User.objects.get(username='test')
        content_type = ContentType.objects.get_for_model(Group)
        content_type.save()
        perm = Permission.objects.create(name='test',
                                         content_type=content_type,
                                         codename='test')
        
        # default django way (ManyToManyField)
        #user.user_permissions.add(perm)

        add_permission_to_user(perm, user)

        self.assertEqual(user.has_perm('auth.test', 'object'), False)
        self.assertEqual(user.get_all_permissions('object'), set([]))
        self.assertEqual(user.has_perm('auth.test'), True)
        self.assertEqual(user.get_all_permissions(), set(['auth.test']))
        
    def test_authenticate(self):
        user = User.objects.get(username='test')
        self.assertEquals(authenticate(username='test', password='test'), user)
        self.assertEquals(authenticate(username='test', password='testNones'),
                          None)
