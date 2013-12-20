Changelog
=========

Version 1.6.2 (Dec 20, 2013)
-------------

* Fixed broken query in User admin

Version 1.6.1 (Nov 29, 2013)
-------------

* Fixed packaging issues

Version 1.6.0
-------------

Note: This is release includes support for Django versions 1.4, 1.5 and 1.6.
You no longer need to use the separate branches for each Django version.

* Added support for Django 1.6

Version 1.5.0
-------------

* Added support for Django 1.5

Version 1.4.0
-------------

* Added support for Django 1.4

Version 0.9.2
-------------

* Moved all code required for value conversion for / deconversion from
  database to ``DatabaseOperations``
* Moved nonrel fields' values handling to toolbox, allowing backends to
  just select an appropriate storage type (including string and binary)
* Moved decimal-to-string implementation preserving comparisons to
  toolbox (previously in the GAE backend)
* Let backends use the QuerySet's ``standard_ordering`` when no field
  ordering is defined
* Fixed conversion of values for ``EmbeddedModelField`` subfields
* Fixed preparation of lookup arguments for ``List/Set/DictField``
* Fixed value comparisons in in-memory filtering (only used by GAE)
* Fixed ``update`` for ``EmbeddedModelField`` nested in a nonrel field

Version 0.9.1
-------------

* Added lazy model lookups to EmbeddedModelField
* Simplified CapturingTestSuiteRunner by using Django's integrated unittest2 package
* Several new unit tests

Version 0.8.1
-------------

* Added default implementation for ``check_aggregate_support()``. Contributed by Jonas Haag
* Added ``ListField``/etc. support for fields that require ``SubfieldBase``

Version 0.8
-----------

This release unifies the field types of all existing nonrel backends.

* Merged with ``ListField`` from MongoDB backend. Contributed by Jonas Haag
* Added ``SetField``, ``DictField``, and ``RawField``. Contributed by Jonas Haag
* Fixed support for proxy models. Contributed by Vladimir Mihailenco
* Several cleanups and minor bug fixes
