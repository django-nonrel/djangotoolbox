from .fields import ListField, SetField, DictField, EmbeddedModelField
from django.db import models, connections
from django.db.models import Q
from django.db.models.signals import post_save
from django.db.utils import DatabaseError
from django.dispatch.dispatcher import receiver
from django.test import TestCase
from django.utils import unittest

class Target(models.Model):
    index = models.IntegerField()

class Source(models.Model):
    target = models.ForeignKey(Target)
    index = models.IntegerField()

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
        auto_now = DictField(models.DateTimeField(auto_now=True))

    class EmbeddedModelFieldModel(models.Model):
        simple = EmbeddedModelField('EmbeddedModel', null=True)
        typed_list = ListField(EmbeddedModelField('SetModel'))
        untyped_list = ListField(EmbeddedModelField())
        untyped_dict = DictField(EmbeddedModelField())

    class EmbeddedModel(models.Model):
        some_relation = models.ForeignKey(DictModel, null=True)
        someint = models.IntegerField()
        auto_now = models.DateTimeField(auto_now=True)
        auto_now_add = models.DateTimeField(auto_now_add=True)

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

    @unittest.skipIf(not supports_dicts, "Backend doesn't support dicts")
    def test_dictfield(self):
        DictModel(dictfield=dict(a=1, b='55', foo=3.14),
                  auto_now={'a' : None}).save()
        item = DictModel.objects.get()
        self.assertEqual(item.dictfield, {u'a' : 1, u'b' : 55, u'foo' : 3})

        dt = item.auto_now['a']
        self.assertNotEqual(dt, None)
        item.save()
        self.assertGreater(DictModel.objects.get().auto_now['a'], dt)
        # This shouldn't raise an error becaues the default value is
        # an empty dict
        DictModel().save()

    @unittest.skip('Fails with GAE SDK, but passes on production')
    def test_Q_objects(self):
        self.assertEquals([entity.names for entity in
            ListModel.objects.exclude(Q(names__lt='Sakura') | Q(names__gte='Sasuke'))],
                [['Kakashi', 'Naruto', 'Sasuke', 'Sakura']])

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

class EmbeddedModelFieldTest(TestCase):
    def _simple_instance(self):
        EmbeddedModelFieldModel.objects.create(simple=EmbeddedModel(someint='5'))
        return EmbeddedModelFieldModel.objects.get()

    def test_simple(self):
        instance = self._simple_instance()
        self.assertIsInstance(instance.simple, EmbeddedModel)
        # Make sure get_prep_value is called:
        self.assertEqual(instance.simple.someint, 5)
        # AutoFields' values should not be populated:
        self.assertEqual(instance.simple.id, None)

    def test_pre_save(self):
        # Make sure field.pre_save is called
        instance = self._simple_instance()
        self.assertNotEqual(instance.simple.auto_now, None)
        self.assertNotEqual(instance.simple.auto_now_add, None)
        auto_now = instance.simple.auto_now
        auto_now_add = instance.simple.auto_now_add
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()
        # auto_now_add shouldn't have changed now, but auto_now should.
        self.assertEqual(instance.simple.auto_now_add, auto_now_add)
        self.assertGreater(instance.simple.auto_now, auto_now)

    def test_typed_listfield(self):
        EmbeddedModelFieldModel.objects.create(
            typed_list=[SetModel(setfield=range(3)), SetModel(setfield=range(9))]
        )
        self.assertIn(5, EmbeddedModelFieldModel.objects.get().typed_list[1].setfield)

    def test_untyped_listfield(self):
        EmbeddedModelFieldModel.objects.create(untyped_list=[
            EmbeddedModel(someint=7),
            OrderedListModel(ordered_ints=range(5, 0, -1)),
            SetModel(setfield=[1, 2, 2, 3])
        ])
        instances = EmbeddedModelFieldModel.objects.get().untyped_list
        for instance, cls in zip(instances, [EmbeddedModel, OrderedListModel, SetModel]):
            self.assertIsInstance(instance, cls)
        self.assertNotEqual(instances[0].auto_now, None)
        self.assertEqual(instances[1].ordered_ints, range(1, 6))

    def test_untyped_dict(self):
        EmbeddedModelFieldModel.objects.create(untyped_dict={
            'a' : SetModel(setfield=range(3)),
            'b' : DictModel(dictfield={'a' : 1, 'b' : 2}),
            'c' : DictModel(dictfield={}, auto_now={'y' : 1})
        })
        data = EmbeddedModelFieldModel.objects.get().untyped_dict
        self.assertIsInstance(data['a'], SetModel)
        self.assertNotEqual(data['c'].auto_now['y'], None)

    def test_foreignkey_in_embedded_object(self):
        simple = EmbeddedModel(some_relation=DictModel.objects.create())
        obj = EmbeddedModelFieldModel.objects.create(simple=simple)
        simple = EmbeddedModelFieldModel.objects.get().simple
        self.assertNotIn('some_relation', simple.__dict__)
        self.assertIsInstance(simple.__dict__['some_relation_id'], type(obj.id))
        self.assertIsInstance(simple.some_relation, DictModel)
EmbeddedModelFieldTest = unittest.skipIf(
    not supports_dicts, "Backend doesn't support dicts")(
    EmbeddedModelFieldTest)

class SignalTest(TestCase):
    def test_post_save(self):
        created = []
        @receiver(post_save, sender=SetModel)
        def handle(**kwargs):
            created.append(kwargs['created'])
        SetModel().save()
        self.assertEqual(created, [True])
        SetModel.objects.get().save()
        self.assertEqual(created, [True, False])
        qs = SetModel.objects.all()
        list(qs)[0].save()
        self.assertEqual(created, [True, False, False])
        list(qs)[0].save()
        self.assertEqual(created, [True, False, False, False])
        list(qs.select_related())[0].save()
        self.assertEqual(created, [True, False, False, False, False])

class SelectRelatedTest(TestCase):
    def test_select_related(self):
        target = Target(index=5)
        target.save()
        Source(target=target, index=8).save()
        source = Source.objects.all().select_related()[0]
        self.assertEqual(source.target.pk, target.pk)
        self.assertEqual(source.target.index, target.index)
        source = Source.objects.all().select_related('target')[0]
        self.assertEqual(source.target.pk, target.pk)
        self.assertEqual(source.target.index, target.index)
