from .fields import ListField, SetField, DictField
from .test import skip_if
from django.db import models, connections
from django.db.models import Q
from django.test import TestCase
from django.db.utils import DatabaseError

class ListModel(models.Model):
    floating_point = models.FloatField()
    names = ListField(models.CharField(max_length=500))
    names_with_default = ListField(models.CharField(max_length=500), default=[])
    names_nullable = ListField(models.CharField(max_length=500), null=True)

class OrderedListModel(models.Model):
    ordered_ints = ListField(models.IntegerField(max_length=500), default=[],
                             ordering=lambda x: x, null=True)
    ordered_nullable = ListField(ordering=lambda x:x, null=True)

class SetModel(models.Model):
    setfield = SetField(models.IntegerField())

supports_dicts = getattr(connections['default'].features, 'supports_dicts', False)
if supports_dicts:
    class DictModel(models.Model):
        dictfield = DictField(models.IntegerField())
        dictfield_nullable = DictField(null=True)

class FilterTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    names = [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]
    unordered_ints = [4, 2, 6, 1]

    def setUp(self):
        for i, float in enumerate(FilterTest.floats):
            ListModel(floating_point=float, names=FilterTest.names[:i+1]).save()

    def test_startswith(self):
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [['Kakashi', 'Naruto', 'Sasuke',],
                            ['Kakashi', 'Naruto', 'Sasuke', 'Sakura',]])

    def test_options(self):
        self.assertEqual([entity.names_with_default for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [[], []])

        self.assertEqual([entity.names_nullable for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [None, None])

    def test_default_value(self):
        # Make sure default value is copied
        ListModel().names_with_default.append(2)
        self.assertEqual(ListModel().names_with_default, [])

    def test_ordering(self):
        OrderedListModel(ordered_ints=self.unordered_ints).save()
        self.assertEqual(OrderedListModel.objects.get().ordered_ints,
                         sorted(self.unordered_ints))

    def test_gt(self):
        # test gt on list
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names__gt='Kakashi')],
                          [[u'Kakashi', u'Naruto',],
                            [u'Kakashi', u'Naruto', u'Sasuke',],
                            [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

    def test_lt(self):
        # test lt on list
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names__lt='Naruto')],
                          [[u'Kakashi',], [u'Kakashi', u'Naruto',],
                            [u'Kakashi', u'Naruto', u'Sasuke',],
                            [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

    def test_gte(self):
        # test gte on list
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names__gte='Sakura')],
                          [[u'Kakashi', u'Naruto', u'Sasuke',],
                            [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

    def test_lte(self):
        # test lte on list
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names__lte='Kakashi')],
                          [[u'Kakashi',], [u'Kakashi', u'Naruto',],
                            [u'Kakashi', u'Naruto', u'Sasuke',],
                            [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

    def test_equals(self):
        # test equality filter on list
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names='Sakura')],
                          [[u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

        # test with additonal pk filter (for DBs that have special pk queries)
        query = ListModel.objects.filter(names='Sakura')
        self.assertEquals(query.get(pk=query[0].pk).names,
                          [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',])

    def test_is_null(self):
        self.assertEquals(ListModel.objects.filter(
            names__isnull=True).count(), 0)

    def test_exclude(self):
        self.assertEquals([entity.names for entity in
                           ListModel.objects.all().exclude(
                            names__lt='Sakura')],
                          [[u'Kakashi', u'Naruto', u'Sasuke',],
                           [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]])

    def test_chained_filter(self):
        self.assertEquals([entity.names for entity in
                          ListModel.objects.filter(names='Sasuke').filter(
                            names='Sakura')], [['Kakashi', 'Naruto',
                            'Sasuke', 'Sakura'],])

        self.assertEquals([entity.names for entity in
                          ListModel.objects.filter(names__startswith='Sa').filter(
                            names='Sakura')], [['Kakashi', 'Naruto',
                            'Sasuke', 'Sakura']])

        # test across multiple columns. On app engine only one filter is allowed
        # to be an inequality filter
        self.assertEquals([entity.names for entity in
                          ListModel.objects.filter(floating_point=9.1).filter(
                            names__startswith='Sa')], [['Kakashi', 'Naruto',
                            'Sasuke',],])

    def test_setfield(self):
        setdata = [1, 2, 3, 2, 1]
        # At the same time test value conversion
        SetModel(setfield=map(str, setdata)).save()
        item = SetModel.objects.filter(setfield=3)[0]
        self.assertEqual(item.setfield, set(setdata))
        # This shouldn't raise an error because the default value is
        # an empty list
        SetModel().save()

    @skip_if(not supports_dicts)
    def test_dictfield(self):
        DictModel(dictfield=dict(a=1, b='55', foo=3.14)).save()
        item = DictModel.objects.get()
        self.assertEqual(item.dictfield, {u'a' : 1, u'b' : 55, u'foo' : 3})
        # This shouldn't raise an error becaues the default value is
        # an empty dict
        DictModel().save()

    # passes on GAE production but not on sdk
    @skip_if(True)
    def test_Q_objects(self):
        self.assertEquals([entity.names for entity in
            ListModel.objects.exclude(Q(names__lt='Sakura') | Q(names__gte='Sasuke'))],
                [['Kakashi', 'Naruto', 'Sasuke', 'Sakura'], ])

class BaseModel(models.Model):
    pass

class ExtendedModel(BaseModel):
    name = models.CharField(max_length=20)

class BaseModelProxy(BaseModel):
    class Meta:
        proxy = True

class ExtendedModelProxy(ExtendedModel):
    class Meta:
        proxy = True

class ProxyTest(TestCase):
    def test_proxy(self):
        list(BaseModelProxy.objects.all())

    def test_proxy_with_inheritance(self):
        self.assertRaises(DatabaseError, lambda: list(ExtendedModelProxy.objects.all()))
