djangotoolbox_ provides a common API for running Django on
non-relational/NoSQL databases (currently via Django-nonrel_).

In ``djangotoolbox.db`` you can find base classes for writing
non-relational DB backends. Read
`Writing a non-relational Django backend`_
for more information.

In ``djangotoolbox.fields`` you can find several common field
types for non-relational DB backends (``ListField``, ``SetField``,
``DictField``, ``RawField``, ``BlobField``).

The ``djangotoolbox.admin`` module provides admin overrides for
making ``django.contrib.auth`` work correctly in the admin UI.
Simply add ``'djangotoolbox'`` to ``INSTALLED_APPS`` **after**
``django.contrib.admin``. This will disable features that
require JOINs. If you still need permission handling you should
use the `nonrel permission backend`_.

Changelog
=============================================================

Version 0.9.1
-------------------------------------------------------------

* Added lazy model lookups to EmbeddedModelField
* Simplified CapturingTestSuiteRunner by using Django's integrated unittest2 package
* Several new unit tests

Version 0.8.1
-------------------------------------------------------------

* Added default implementation for ``check_aggregate_support()``. Contributed by Jonas Haag
* Added ``ListField``/etc. support for fields that require ``SubfieldBase``

Version 0.8
-------------------------------------------------------------

This release unifies the field types of all existing nonrel backends.

* Merged with ``ListField`` from MongoDB backend. Contributed by Jonas Haag
* Added ``SetField``, ``DictField``, and ``RawField``. Contributed by Jonas Haag
* Fixed support for proxy models. Contributed by Vladimir Mihailenco
* Several cleanups and minor bug fixes

.. _djangotoolbox: http://www.allbuttonspressed.com/projects/djangotoolbox
.. _Django-nonrel: http://www.allbuttonspressed.com/projects/django-nonrel
.. _Writing a non-relational Django backend: http://www.allbuttonspressed.com/blog/django/2010/04/Writing-a-non-relational-Django-backend
.. _nonrel permission backend: https://bitbucket.org/fhahn/django-permission-backend-nonrel
