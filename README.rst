djangotoolbox_ provides a common API for running Django on
non-relational/NoSQL databases (currently via Django-nonrel_).

In ``djangotoolbox.db`` you can find base classes for writing
non-relational DB backends.

In ``djangotoolbox.fields`` you can find several common field
types for non-relational DB backends (``ListField``, ``SetField``,
``DictField``, ``RawField``, ``BlobField``).

The ``djangotoolbox.admin`` module provides admin overrides for
making ``django.contrib.auth`` work correctly in the admin UI.
Simply add ``'djangotoolbox'`` to ``INSTALLED_APPS`` **after**
``django.contrib.admin``.

Changelog
=============================================================

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
