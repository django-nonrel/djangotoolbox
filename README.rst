Djangotoolbox, a common API for running Django on non-relational/NoSQL databases
=========================================================

Documentation at http://djangotoolbox.readthedocs.org/

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

Contributing
------------
You are highly encouraged to participate in the development, simply use
GitHub's fork/pull request system.

If you don't like GitHub (for some reason) you're welcome
to send regular patches to the mailing list.

:Mailing list: http://groups.google.com/group/django-non-relational
:Bug tracker: https://github.com/django-nonrel/djangotoolbox/issues
:License: 3-clause BSD, see LICENSE
:Keywords: django, app engine, mongodb, orm, nosql, database, python

.. _djangotoolbox: https://github.com/django-nonrel/djangotoolbox
.. _nonrel permission backend: https://github.com/django-nonrel/django-permission-backend-nonrel
