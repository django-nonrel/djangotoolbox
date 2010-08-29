from .fields import ListField
from django.conf import settings
from django.db import models
from django.db.models import Q
#from django.db.utils import DatabaseError
from django.test import TestCase


class ListModel(models.Model):
    floating_point = models.FloatField()
    names = ListField(models.CharField(max_length=500))
    names_with_default = ListField(models.CharField(max_length=500), default=[])
    names_nullable = ListField(models.CharField(max_length=500), null=True)

class FilterTest(TestCase):
    floats = [5.3, 2.6, 9.1, 1.58]
    names = [u'Kakashi', u'Naruto', u'Sasuke', u'Sakura',]

    def setUp(self):
        for i, float in enumerate(FilterTest.floats):
            ListModel(floating_point=float, names=FilterTest.names[:i+1]).save()

    def test_equals_empty(self):
        self.assertEqual(ListModel.objects.filter(names=[]).count(), 0)

    def test_startswith(self):
        self.assertEquals([entity.names for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [['Kakashi', 'Naruto', 'Sasuke',],
                            ['Kakashi', 'Naruto', 'Sasuke', 'Sakura',]])

    def test_options(self):
        self.assertEquals([entity.names_with_default for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [[], []])

        # TODO: should it be NULL or None here?
        self.assertEquals([entity.names_nullable for entity in
                           ListModel.objects.filter(names__startswith='Sa')],
                          [None, None])

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
# passes on production but not on sdk
#    def test_Q_objects(self):
#        self.assertEquals([entity.names for entity in
#            ListModel.objects.exclude(Q(names__lt='Sakura') | Q(names__gte='Sasuke'))],
#                [['Kakashi', 'Naruto', 'Sasuke', 'Sakura'], ])
