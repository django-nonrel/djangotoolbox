from __future__ import with_statement
from decimal import Decimal, InvalidOperation
import time

from django.core import serializers
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.db.utils import DatabaseError
from django.dispatch.dispatcher import receiver
from django.test import TestCase
from django.utils.unittest import expectedFailure, skip

from .fields import ListField, SetField, DictField, EmbeddedModelField


def count_calls(func):

    def wrapper(*args, **kwargs):
        wrapper.calls += 1
        return func(*args, **kwargs)
    wrapper.calls = 0

    return wrapper


class Target(models.Model):
    index = models.IntegerField()


class Source(models.Model):
    target = models.ForeignKey(Target)
    index = models.IntegerField()


class DecimalModel(models.Model):
    decimal = models.DecimalField(max_digits=9, decimal_places=2)


class DecimalKey(models.Model):
    decimal = models.DecimalField(max_digits=9, decimal_places=2, primary_key=True)


class DecimalParent(models.Model):
    child = models.ForeignKey(DecimalKey)


class DecimalsList(models.Model):
    decimals = ListField(models.ForeignKey(DecimalKey))


class ListModel(models.Model):
    integer = models.IntegerField(primary_key=True)
    floating_point = models.FloatField()
    names = ListField(models.CharField)
    names_with_default = ListField(models.CharField(max_length=500),
                                   default=[])
    names_nullable = ListField(models.CharField(max_length=500), null=True)


class OrderedListModel(models.Model):
    ordered_ints = ListField(models.IntegerField(max_length=500), default=[],
                             ordering=count_calls(lambda x: x), null=True)
    ordered_nullable = ListField(ordering=lambda x: x, null=True)


class SetModel(models.Model):
    setfield = SetField(models.IntegerField())


class DictModel(models.Model):
    dictfield = DictField(models.IntegerField)
    dictfield_nullable = DictField(null=True)
    auto_now = DictField(models.DateTimeField(auto_now=True))


class EmbeddedModelFieldModel(models.Model):
    simple = EmbeddedModelField('EmbeddedModel', null=True)
    simple_untyped = EmbeddedModelField(null=True)
    decimal_parent = EmbeddedModelField(DecimalParent, null=True)
    typed_list = ListField(EmbeddedModelField('SetModel'))
    typed_list2 = ListField(EmbeddedModelField('EmbeddedModel'))
    untyped_list = ListField(EmbeddedModelField())
    untyped_dict = DictField(EmbeddedModelField())
    ordered_list = ListField(EmbeddedModelField(),
                             ordering=lambda obj: obj.index)


class EmbeddedModel(models.Model):
    some_relation = models.ForeignKey(DictModel, null=True)
    someint = models.IntegerField(db_column='custom')
    auto_now = models.DateTimeField(auto_now=True)
    auto_now_add = models.DateTimeField(auto_now_add=True)


class IterableFieldsTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    names = [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']
    unordered_ints = [4, 2, 6, 1]

    def setUp(self):
        for i, float in zip(range(1, 5), IterableFieldsTest.floats):
            ListModel(integer=i, floating_point=float,
                      names=IterableFieldsTest.names[:i]).save()

    def test_startswith(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__startswith='Sa')]),
            dict([(3, ['Kakashi', 'Naruto', 'Sasuke']),
                  (4, ['Kakashi', 'Naruto', 'Sasuke', 'Sakura']), ]))

    def test_options(self):
        self.assertEqual([entity.names_with_default for entity in
                          ListModel.objects.filter(names__startswith='Sa')],
                         [[], []])

        self.assertEqual([entity.names_nullable for entity in
                          ListModel.objects.filter(names__startswith='Sa')],
                         [None, None])

    def test_default_value(self):
        # Make sure default value is copied.
        ListModel().names_with_default.append(2)
        self.assertEqual(ListModel().names_with_default, [])

    def test_ordering(self):
        f = OrderedListModel._meta.fields[1]
        f.ordering.calls = 0

        # Ensure no ordering happens on assignment.
        obj = OrderedListModel()
        obj.ordered_ints = self.unordered_ints
        self.assertEqual(f.ordering.calls, 0)

        obj.save()
        self.assertEqual(OrderedListModel.objects.get().ordered_ints,
                         sorted(self.unordered_ints))
        # Ordering should happen only once, i.e. the order function may
        # be called N times at most (N being the number of items in the
        # list).
        self.assertLessEqual(f.ordering.calls, len(self.unordered_ints))

    def test_gt(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__gt='Kakashi')]),
            dict([(2, [u'Kakashi', u'Naruto']),
                  (3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_lt(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__lt='Naruto')]),
            dict([(1, [u'Kakashi']),
                  (2, [u'Kakashi', u'Naruto']),
                  (3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_gte(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__gte='Sakura')]),
            dict([(3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_lte(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.filter(names__lte='Kakashi')]),
            dict([(1, [u'Kakashi']),
                  (2, [u'Kakashi', u'Naruto']),
                  (3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_equals(self):
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names='Sakura')],
                          [[u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']])

        # Test with additonal pk filter (for DBs that have special pk
        # queries).
        query = ListModel.objects.filter(names='Sakura')
        self.assertEquals(query.get(pk=query[0].pk).names,
                          [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura'])

    def test_is_null(self):
        self.assertEquals(ListModel.objects.filter(
            names__isnull=True).count(), 0)

    def test_exclude(self):
        self.assertEquals(
            dict([(entity.pk, entity.names) for entity in
                  ListModel.objects.all().exclude(names__lt='Sakura')]),
            dict([(3, [u'Kakashi', u'Naruto', u'Sasuke']),
                  (4, [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura']), ]))

    def test_chained_filter(self):
        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .filter(names='Sasuke').filter(names='Sakura')],
            [['Kakashi', 'Naruto', 'Sasuke', 'Sakura'], ])

        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .filter(names__startswith='Sa').filter(names='Sakura')],
            [['Kakashi', 'Naruto', 'Sasuke', 'Sakura']])

        # Test across multiple columns. On app engine only one filter
        # is allowed to be an inequality filter.
        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .filter(floating_point=9.1).filter(names__startswith='Sa')],
            [['Kakashi', 'Naruto', 'Sasuke'], ])

    def test_setfield(self):
        setdata = [1, 2, 3, 2, 1]
        # At the same time test value conversion.
        SetModel(setfield=map(str, setdata)).save()
        item = SetModel.objects.filter(setfield=3)[0]
        self.assertEqual(item.setfield, set(setdata))
        # This shouldn't raise an error because the default value is
        # an empty list.
        SetModel().save()

    def test_dictfield(self):
        DictModel(dictfield=dict(a=1, b='55', foo=3.14),
                  auto_now={'a': None}).save()
        item = DictModel.objects.get()
        self.assertEqual(item.dictfield, {u'a': 1, u'b': 55, u'foo': 3})

        dt = item.auto_now['a']
        self.assertNotEqual(dt, None)
        item.save()
        time.sleep(0.5) # Sleep to avoid false positive failure on the assertion below
        self.assertGreater(DictModel.objects.get().auto_now['a'], dt)
        item.delete()

        # Saving empty dicts shouldn't throw errors.
        DictModel().save()
        # Regression tests for djangoappengine issue #39.
        DictModel.add_to_class('new_dict_field', DictField())
        DictModel.objects.get()

    @skip("GAE specific?")
    def test_Q_objects(self):
        self.assertEquals(
            [entity.names for entity in ListModel.objects
                .exclude(Q(names__lt='Sakura') | Q(names__gte='Sasuke'))],
            [['Kakashi', 'Naruto', 'Sasuke', 'Sakura']])

    def test_list_with_foreignkeys(self):

        class ReferenceList(models.Model):
            keys =  ListField(models.ForeignKey('Model'))

        class Model(models.Model):
            pass

        model1 = Model.objects.create()
        model2 = Model.objects.create()
        ReferenceList.objects.create(keys=[model1.pk, model2.pk])

        self.assertEqual(ReferenceList.objects.get().keys[0], model1.pk)
        self.assertEqual(ReferenceList.objects.filter(keys=model1.pk).count(), 1)

    def test_list_with_foreign_conversion(self):
        decimal = DecimalKey.objects.create(decimal=Decimal('1.5'))
        DecimalsList.objects.create(decimals=[decimal.pk])

    @expectedFailure
    def test_nested_list(self):
        """
        Some back-ends expect lists to be strongly typed or not contain
        other lists (e.g. GAE), this limits how the ListField can be
        used (unless the back-end were to serialize all lists).
        """

        class UntypedListModel(models.Model):
            untyped_list = ListField()

        UntypedListModel.objects.create(untyped_list=[1, [2, 3]])


class Child(models.Model):
    pass


class Parent(models.Model):
    id = models.IntegerField(primary_key=True)
    integer_list = ListField(models.IntegerField)
    integer_dict = DictField(models.IntegerField)
    embedded_list = ListField(EmbeddedModelField(Child))
    embedded_dict = DictField(EmbeddedModelField(Child))


class EmbeddedModelFieldTest(TestCase):

    def assertEqualDatetime(self, d1, d2):
        """Compares d1 and d2, ignoring microseconds."""
        self.assertEqual(d1.replace(microsecond=0),
                         d2.replace(microsecond=0))

    def assertNotEqualDatetime(self, d1, d2):
        self.assertNotEqual(d1.replace(microsecond=0),
                            d2.replace(microsecond=0))

    def _simple_instance(self):
        EmbeddedModelFieldModel.objects.create(
            simple=EmbeddedModel(someint='5'))
        return EmbeddedModelFieldModel.objects.get()

    def test_simple(self):
        instance = self._simple_instance()
        self.assertIsInstance(instance.simple, EmbeddedModel)
        # Make sure get_prep_value is called.
        self.assertEqual(instance.simple.someint, 5)
        # Primary keys should not be populated...
        self.assertEqual(instance.simple.id, None)
        # ... unless set explicitly.
        instance.simple.id = instance.id
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()
        self.assertEqual(instance.simple.id, instance.id)

    def _test_pre_save(self, instance, get_field):
        # Make sure field.pre_save is called for embedded objects.
        from time import sleep
        instance.save()
        auto_now = get_field(instance).auto_now
        auto_now_add = get_field(instance).auto_now_add
        self.assertNotEqual(auto_now, None)
        self.assertNotEqual(auto_now_add, None)

        sleep(1) # FIXME
        instance.save()
        self.assertNotEqualDatetime(get_field(instance).auto_now,
                                    get_field(instance).auto_now_add)

        instance = EmbeddedModelFieldModel.objects.get()
        instance.save()
        # auto_now_add shouldn't have changed now, but auto_now should.
        self.assertEqualDatetime(get_field(instance).auto_now_add,
                                 auto_now_add)
        self.assertGreater(get_field(instance).auto_now, auto_now)

    def test_pre_save(self):
        obj = EmbeddedModelFieldModel(simple=EmbeddedModel())
        self._test_pre_save(obj, lambda instance: instance.simple)

    def test_pre_save_untyped(self):
        obj = EmbeddedModelFieldModel(simple_untyped=EmbeddedModel())
        self._test_pre_save(obj, lambda instance: instance.simple_untyped)

    def test_pre_save_in_list(self):
        obj = EmbeddedModelFieldModel(untyped_list=[EmbeddedModel()])
        self._test_pre_save(obj, lambda instance: instance.untyped_list[0])

    def test_pre_save_in_dict(self):
        obj = EmbeddedModelFieldModel(untyped_dict={'a': EmbeddedModel()})
        self._test_pre_save(obj, lambda instance: instance.untyped_dict['a'])

    def test_pre_save_list(self):
        # Also make sure auto_now{,add} works for embedded object *lists*.
        EmbeddedModelFieldModel.objects.create(typed_list2=[EmbeddedModel()])
        instance = EmbeddedModelFieldModel.objects.get()

        auto_now = instance.typed_list2[0].auto_now
        auto_now_add = instance.typed_list2[0].auto_now_add
        self.assertNotEqual(auto_now, None)
        self.assertNotEqual(auto_now_add, None)

        instance.typed_list2.append(EmbeddedModel())
        instance.save()
        instance = EmbeddedModelFieldModel.objects.get()

        self.assertEqualDatetime(instance.typed_list2[0].auto_now_add,
                                 auto_now_add)
        self.assertGreater(instance.typed_list2[0].auto_now, auto_now)
        self.assertNotEqual(instance.typed_list2[1].auto_now, None)
        self.assertNotEqual(instance.typed_list2[1].auto_now_add, None)

    def test_error_messages(self):
        for kwargs, expected in (
                ({'simple': 42}, EmbeddedModel),
                ({'simple_untyped': 42}, models.Model),
                ({'typed_list': [EmbeddedModel()]}, SetModel)):
            self.assertRaisesRegexp(
                TypeError, "Expected instance of type %r." % expected,
                EmbeddedModelFieldModel(**kwargs).save)

    def test_typed_listfield(self):
        EmbeddedModelFieldModel.objects.create(
            typed_list=[SetModel(setfield=range(3)),
                        SetModel(setfield=range(9))],
            ordered_list=[Target(index=i) for i in xrange(5, 0, -1)])
        obj = EmbeddedModelFieldModel.objects.get()
        self.assertIn(5, obj.typed_list[1].setfield)
        self.assertEqual([target.index for target in obj.ordered_list],
                         range(1, 6))

    def test_untyped_listfield(self):
        EmbeddedModelFieldModel.objects.create(untyped_list=[
            EmbeddedModel(someint=7),
            OrderedListModel(ordered_ints=range(5, 0, -1)),
            SetModel(setfield=[1, 2, 2, 3])])
        instances = EmbeddedModelFieldModel.objects.get().untyped_list
        for instance, cls in zip(instances,
                                 [EmbeddedModel, OrderedListModel, SetModel]):
            self.assertIsInstance(instance, cls)
        self.assertNotEqual(instances[0].auto_now, None)
        self.assertEqual(instances[1].ordered_ints, range(1, 6))

    def test_untyped_dict(self):
        EmbeddedModelFieldModel.objects.create(untyped_dict={
            'a': SetModel(setfield=range(3)),
            'b': DictModel(dictfield={'a': 1, 'b': 2}),
            'c': DictModel(dictfield={}, auto_now={'y': 1})})
        data = EmbeddedModelFieldModel.objects.get().untyped_dict
        self.assertIsInstance(data['a'], SetModel)
        self.assertNotEqual(data['c'].auto_now['y'], None)

    def test_foreignkey_in_embedded_object(self):
        simple = EmbeddedModel(some_relation=DictModel.objects.create())
        obj = EmbeddedModelFieldModel.objects.create(simple=simple)
        simple = EmbeddedModelFieldModel.objects.get().simple
        self.assertNotIn('some_relation', simple.__dict__)
        self.assertIsInstance(simple.__dict__['some_relation_id'],
                              type(obj.id))
        self.assertIsInstance(simple.some_relation, DictModel)

    def test_embedded_field_with_foreign_conversion(self):
        decimal = DecimalKey.objects.create(decimal=Decimal('1.5'))
        decimal_parent = DecimalParent.objects.create(child=decimal)
        EmbeddedModelFieldModel.objects.create(decimal_parent=decimal_parent)

    def test_update(self):
        """
        Test that update can be used on an a subset of objects
        containing collections of embedded instances; see issue #13.
        Also ensure that updated values are coerced according to
        collection field.
        """
        child1 = Child.objects.create()
        child2 = Child.objects.create()
        parent = Parent.objects.create(pk=1,
            integer_list=[1], integer_dict={'a': 2},
            embedded_list=[child1], embedded_dict={'a': child2})
        Parent.objects.filter(pk=1).update(
            integer_list=['3'], integer_dict={'b': '3'},
            embedded_list=[child2], embedded_dict={'b': child1})
        parent = Parent.objects.get()
        self.assertEqual(parent.integer_list, [3])
        self.assertEqual(parent.integer_dict, {'b': 3})
        self.assertEqual(parent.embedded_list, [child2])
        self.assertEqual(parent.embedded_dict, {'b': child1})


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
        self.assertRaises(DatabaseError,
                          lambda: list(ExtendedModelProxy.objects.all()))


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


class DBColumn(models.Model):
    a = models.IntegerField(db_column='b')


class OrderByTest(TestCase):

    def test_foreign_keys(self):
        target1 = Target.objects.create(index=1)
        target2 = Target.objects.create(index=2)
        source1 = Source.objects.create(target=target1, index=3)
        source2 = Source.objects.create(target=target2, index=4)
        self.assertEqual(list(Source.objects.all().order_by('target')),
                         [source1, source2])
        self.assertEqual(list(Source.objects.all().order_by('-target')),
                         [source2, source1])

    def test_db_column(self):
        model1 = DBColumn.objects.create(a=1)
        model2 = DBColumn.objects.create(a=2)
        self.assertEqual(list(DBColumn.objects.all().order_by('a')),
                         [model1, model2])
        self.assertEqual(list(DBColumn.objects.all().order_by('-a')),
                         [model2, model1])

    def test_reverse(self):
        model1 = DBColumn.objects.create(a=1)
        model2 = DBColumn.objects.create(a=2)
        self.assertEqual(list(DBColumn.objects.all().order_by('a').reverse()),
                         [model2, model1])
        self.assertEqual(list(DBColumn.objects.all().order_by('-a').reverse()),
                         [model1, model2])

    def test_chain(self):
        model1 = Target.objects.create(index=1)
        model2 = Target.objects.create(index=2)
        self.assertEqual(
            list(Target.objects.all().order_by('index').order_by('-index')),
            [model2, model1])


class SerializableSetModel(models.Model):
    setfield = SetField(models.IntegerField())
    setcharfield = SetField(models.CharField(), null=True)


class SerializationTest(TestCase):
    """
    JSON doesn't support sets, so they need to be converted to lists
    for serialization; see issue #12.

    TODO: Check if the fix works with embedded models / nested sets.
    """
    names = ['foo', 'bar', 'baz', 'monkey']

    def test_json_listfield(self):
        for i in range(1, 5):
            ListModel(integer=i, floating_point=0,
                      names=SerializationTest.names[:i]).save()
        objects = ListModel.objects.all()
        serialized = serializers.serialize('json', objects)
        deserialized = serializers.deserialize('json', serialized)
        for m in deserialized:
            integer = m.object.integer
            names = m.object.names
            self.assertEqual(names, SerializationTest.names[:integer])

    def test_json_setfield(self):
        for i in range(1, 5):
            SerializableSetModel(
                setfield=set([i - 1]),
                setcharfield=set(SerializationTest.names[:i])).save()
        objects = SerializableSetModel.objects.all()
        serialized = serializers.serialize('json', objects)
        deserialized = serializers.deserialize('json', serialized)
        for m in deserialized:
            integer = m.object.setfield.pop()
            names = m.object.setcharfield
            self.assertEqual(names, set(SerializationTest.names[:integer + 1]))


class String(models.Model):
    s = models.CharField(max_length=20)


class LazyObjectsTest(TestCase):

    def test_translation(self):
        """
        Using a lazy translation call should work just the same as
        a non-lazy one (or a plain string).
        """
        from django.utils.translation import ugettext_lazy

        a = String.objects.create(s='a')
        b = String.objects.create(s=ugettext_lazy('b'))

        self.assertEqual(String.objects.get(s='a'), a)
        self.assertEqual(list(String.objects.filter(s='a')), [a])
        self.assertEqual(list(String.objects.filter(s__lte='a')), [a])
        self.assertEqual(String.objects.get(s=ugettext_lazy('a')), a)
        self.assertEqual(
            list(String.objects.filter(s__lte=ugettext_lazy('a'))), [a])

        self.assertEqual(String.objects.get(s='b'), b)
        self.assertEqual(list(String.objects.filter(s='b')), [b])
        self.assertEqual(list(String.objects.filter(s__gte='b')), [b])
        self.assertEqual(String.objects.get(s=ugettext_lazy('b')), b)
        self.assertEqual(
            list(String.objects.filter(s__gte=ugettext_lazy('b'))), [b])

    def test_marked_strings(self):
        """
        Check that strings marked as safe or needing escaping do not
        confuse the back-end.
        """
        from django.utils.safestring import mark_safe, mark_for_escaping

        a = String.objects.create(s='a')
        b = String.objects.create(s=mark_safe('b'))
        c = String.objects.create(s=mark_for_escaping('c'))

        self.assertEqual(String.objects.get(s='a'), a)
        self.assertEqual(list(String.objects.filter(s__startswith='a')), [a])
        self.assertEqual(String.objects.get(s=mark_safe('a')), a)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_safe('a'))), [a])
        self.assertEqual(String.objects.get(s=mark_for_escaping('a')), a)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_for_escaping('a'))),
            [a])

        self.assertEqual(String.objects.get(s='b'), b)
        self.assertEqual(list(String.objects.filter(s__startswith='b')), [b])
        self.assertEqual(String.objects.get(s=mark_safe('b')), b)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_safe('b'))), [b])
        self.assertEqual(String.objects.get(s=mark_for_escaping('b')), b)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_for_escaping('b'))),
            [b])

        self.assertEqual(String.objects.get(s='c'), c)
        self.assertEqual(list(String.objects.filter(s__startswith='c')), [c])
        self.assertEqual(String.objects.get(s=mark_safe('c')), c)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_safe('c'))), [c])
        self.assertEqual(String.objects.get(s=mark_for_escaping('c')), c)
        self.assertEqual(
            list(String.objects.filter(s__startswith=mark_for_escaping('c'))),
            [c])


class FeaturesTest(TestCase):
    """
    Some things are unlikely to cause problems for SQL back-ends, but
    require special handling in nonrel.
    """

    def test_subqueries(self):
        """
        Django includes SQL statements as WHERE tree values when
        filtering using a QuerySet -- this won't "just work" with
        nonrel back-ends.

        TODO: Subqueries handling may require a bit of Django
              changing, but should be easy to support.
        """
        target = Target.objects.create(index=1)
        source = Source.objects.create(index=2, target=target)
        targets = Target.objects.all()
        with self.assertRaises(DatabaseError):
            Source.objects.get(target__in=targets)
        self.assertEqual(
            Source.objects.get(target__in=list(targets)),
            source)


class DecimalFieldTest(TestCase):
    """
    Some NoSQL databases can't handle Decimals, so respective back-ends
    convert them to strings or floats. This can cause some precision
    and sorting problems.
    """

    def setUp(self):
        for d in (Decimal('12345.6789'), Decimal('5'), Decimal('345.67'),
                  Decimal('45.6'), Decimal('2345.678'),):
            DecimalModel(decimal=d).save()

    def test_filter(self):
        d = DecimalModel.objects.get(decimal=Decimal('5.0'))

        self.assertTrue(isinstance(d.decimal, Decimal))
        self.assertEquals(str(d.decimal), '5.00')

        d = DecimalModel.objects.get(decimal=Decimal('45.60'))
        self.assertEquals(str(d.decimal), '45.60')

        # Filter argument should be converted to Decimal with 2 decimal
        #_places.
        d = DecimalModel.objects.get(decimal='0000345.67333333333333333')
        self.assertEquals(str(d.decimal), '345.67')

    def test_order(self):
        """
        Standard Django decimal-to-string conversion isn't monotonic
        (see `django.db.backends.util.format_number`).
        """
        rows = DecimalModel.objects.all().order_by('decimal')
        values = list(d.decimal for d in rows)
        self.assertEquals(values, sorted(values))

    def test_sign_extend(self):
        DecimalModel(decimal=Decimal('-0.0')).save()

        try:
            # If we've written a valid string we should be able to
            # retrieve the DecimalModel object without error.
            DecimalModel.objects.filter(decimal__lt=1)[0]
        except InvalidOperation:
            self.assertTrue(False)


class DeleteModel(models.Model):
    key = models.IntegerField(primary_key=True)
    deletable = models.BooleanField()

class BasicDeleteTest(TestCase):

    def setUp(self):
        for i in range(1, 10):
            DeleteModel(key=i, deletable=i % 2 == 0).save()

    def test_model_delete(self):
        d = DeleteModel.objects.get(pk=1)
        d.delete()

        with self.assertRaises(DeleteModel.DoesNotExist):
            DeleteModel.objects.get(pk=1)

    def test_delete_all(self):
        DeleteModel.objects.all().delete()

        self.assertEquals(0, DeleteModel.objects.all().count())

    def test_delete_filtered(self):
        DeleteModel.objects.filter(deletable=True).delete()

        self.assertEquals(5, DeleteModel.objects.all().count())


class M2MDeleteChildModel(models.Model):
    key = models.IntegerField(primary_key=True)

class M2MDeleteModel(models.Model):
    key = models.IntegerField(primary_key=True)
    deletable = models.BooleanField()
    children = models.ManyToManyField(M2MDeleteChildModel, blank=True)

class ManyToManyDeleteTest(TestCase):
    """
    Django-nonrel doesn't support many-to-many, but there may be
    models that are used which contain them, even if they're not
    accessed. This test ensures they can be deleted.
    """

    def setUp(self):
        for i in range(1, 10):
            M2MDeleteModel(key=i, deletable=i % 2 == 0).save()

    def test_model_delete(self):
        d = M2MDeleteModel.objects.get(pk=1)
        d.delete()

        with self.assertRaises(M2MDeleteModel.DoesNotExist):
            M2MDeleteModel.objects.get(pk=1)

    @expectedFailure
    def test_delete_all(self):
        M2MDeleteModel.objects.all().delete()

        self.assertEquals(0, M2MDeleteModel.objects.all().count())

    @expectedFailure
    def test_delete_filtered(self):
        M2MDeleteModel.objects.filter(deletable=True).delete()

        self.assertEquals(5, M2MDeleteModel.objects.all().count())


class QuerysetModel(models.Model):
    key = models.IntegerField(primary_key=True)

class QuerysetTest(TestCase):
    """
    Django 1.6 changes how
    """

    def setUp(self):
        for i in range(10):
            QuerysetModel.objects.create(key=i + 1)

    def test_all(self):
        self.assertEqual(10, len(QuerysetModel.objects.all()))

    def test_none(self):
        self.assertEqual(0, len(QuerysetModel.objects.none()))
