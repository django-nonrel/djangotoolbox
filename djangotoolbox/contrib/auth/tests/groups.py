from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from djangotoolbox.contrib.auth.models import Group, User, GroupList, Permission, PermissionList


class GroupPermissionTest(TestCase):

    backend = 'djangotoolbox.contrib.auth.backends.ModelBackend'

    def setUp(self):
        self.curr_auth = settings.AUTHENTICATION_BACKENDS
        settings.AUTHENTICATION_BACKENDS = (self.backend,)
        User.objects.create_user('test', 'test@example.com', 'test')

    def tearDown(self):
        settings.AUTHENTICATION_BACKENDS = self.curr_auth

    def test_group_perms(self):
        user = User.objects.get(username='test')
        group = Group.objects.create(name='test_group')
        
        user.group_list.groups.append(group.id)
        user.save()
        
        content_type=ContentType.objects.get_for_model(Group)
        perm = Permission.objects.create(name='test_group', content_type=content_type, codename='test_group')

        group.permissions.permissions.append(perm.id)
        
        content_type=ContentType.objects.get_for_model(ContentType)
        perm = Permission.objects.create(name='test_group', content_type=content_type, codename='test_group')
        group.permissions.permissions.append(perm.id)
        group.save()
        self.assertEqual(user.get_group_permissions(), set([u'contenttypes.test_group', u'auth.test_group']))

        
        perm = Permission.objects.create(name='perm1', content_type=content_type, codename='perm1')
        user.user_permissions.permissions.append(perm.id)
        user.save()

        self.assertEqual(user.has_perm('contenttypes.perm1'),True)
        self.assertEqual(user.get_all_permissions(), set([u'contenttypes.perm1', u'contenttypes.test_group', u'auth.test_group']))
