Change log
==========

6.2 (2025-11-16)
----------------

- Move all supported package metadata into ``pyproject.toml``.

- Add support for Python 3.14.

- Drop support for Python 3.8.


6.1 (2024-09-16)
----------------

- Add final support for Python 3.13.


6.0 (2024-05-30)
----------------

- Drop support for Python 3.7.

- Build Windows wheels on GHA.


5.2 (2024-02-13)
----------------

- Add preliminary support for Python 3.13 as of 3.13a3.


5.1 (2023-10-05)
----------------

- Add support for Python 3.12.


5.0 (2023-03-24)
----------------

- Build Linux binary wheels for Python 3.11.

- Drop support for Python 2.7, 3.5, 3.6.

- Add preliminary support for Python 3.12a5.


4.13 (2022-11-17)
-----------------

- Add support for building arm64 wheels on macOS.


4.12 (2022-11-03)
-----------------

- Add support for final Python 3.11 release.


4.11 (2022-09-16)
-----------------

- Add support for Python 3.11 (as of 3.11.0rc1).

- Switch from ``-Ofast`` to ``-O3`` when compiling code for Linux wheels.
  (`#64 <https://github.com/zopefoundation/Acquisition/pull/64>`_)


4.10 (2021-12-07)
-----------------

- Fix bug in the ``PURE_PYTHON`` version affecting ``aq_acquire`` applied
  to a class with a filter.

- Improve interface documentation.

- Add support for Python 3.10.


4.9 (2021-08-19)
----------------

- On CPython no longer omit compiling the C code when ``PURE_PYTHON`` is
  required. Just evaluate it at runtime.
  (`#53 <https://github.com/zopefoundation/Acquisition/issues/53>`_)


4.8 (2021-07-20)
----------------

- Various fixes for the ``PURE_PYTHON`` version, e.g.
  make ``Acquired`` an ``str`` (as required by ``Zope``),
  avoid infinite ``__cmp__`` loop.
  (`#51 <https://github.com/zopefoundation/Acquisition/issues/51>`_,
  `#48 <https://github.com/zopefoundation/Acquisition/issues/48>`_)

- Create aarch64 wheels.


4.7 (2020-10-07)
----------------

- Add support for Python 3.8 and 3.9.


4.6 (2019-04-24)
----------------

- Drop support for Python 3.4.

- Add support for Python 3.8a3.

- Add support to call ``bytes()`` on an object wrapped by an
  ``ImplicitAcquisitionWrapper``.
  (`#38 <https://github.com/zopefoundation/Acquisition/issues/38>`_)


4.5 (2018-10-05)
----------------

- Avoid deprecation warnings by using current API.

- Add support for Python 3.7.


4.4.4 (2017-11-24)
------------------

- Add Appveyor configuration to automate building Windows eggs.


4.4.3 (2017-11-23)
------------------

- Fix the extremely rare potential for a crash when the C extensions
  are in use. See `issue 21 <https://github.com/zopefoundation/Acquisition/issues/21>`_.


4.4.2 (2017-05-12)
------------------

- Fix C capsule name to fix import errors.

- Ensure our dependencies match our expactations about C extensions.


4.4.1 (2017-05-04)
------------------

- Fix C code under Python 3.4, with missing Py_XSETREF.


4.4.0 (2017-05-04)
------------------

- Enable the C extension under Python 3.

- Drop support for Python 3.3.


4.3.0 (2017-01-20)
------------------

- Make tests compatible with ExtensionClass 4.2.0.

- Drop support for Python 2.6 and 3.2.

- Add support for Python 3.5 and 3.6.


4.2.2 (2015-05-19)
------------------

- Make the pure-Python Acquirer objects cooperatively use the
  superclass ``__getattribute__`` method, like the C implementation.
  See https://github.com/zopefoundation/Acquisition/issues/7.

- The pure-Python implicit acquisition wrapper allows wrapped objects
  to use ``object.__getattribute__(self, name)``. This differs from
  the C implementation, but is important for compatibility with the
  pure-Python versions of libraries like ``persistent``. See
  https://github.com/zopefoundation/Acquisition/issues/9.


4.2.1 (2015-04-23)
------------------

- Correct several dangling pointer uses in the C extension,
  potentially fixing a few interpreter crashes. See
  https://github.com/zopefoundation/Acquisition/issues/5.


4.2 (2015-04-04)
----------------

- Add support for PyPy, PyPy3, and Python 3.2, 3.3, and 3.4.


4.1 (2014-12-18)
----------------

- Bump dependency on ``ExtensionClass`` to match current release.


4.0.3 (2014-11-02)
------------------

- Skip readme.rst tests when tests are run outside a source checkout.


4.0.2 (2014-11-02)
------------------

- Include ``*.rst`` files in the release.


4.0.1 (2014-10-30)
------------------

- Tolerate Unicode attribute names (ASCII only).  LP #143358.

- Make module-level ``aq_acquire`` API respect the ``default`` parameter.
  LP #1387363.

- Don't raise an attribute error for ``__iter__`` if the fallback to
  ``__getitem__`` succeeds.  LP #1155760.


4.0 (2013-02-24)
----------------

- Added trove classifiers to project metadata.


4.0a1 (2011-12-13)
------------------

- Raise `RuntimeError: Recursion detected in acquisition wrapper` if an object
  with a `__parent__` pointer points to a wrapper that in turn points to the
  original object.

- Prevent wrappers to be created while accessing `__parent__` on types derived
  from Explicit or Implicit base classes.


2.13.9 (2015-02-17)
-------------------

- Tolerate Unicode attribute names (ASCII only).  LP #143358.

- Make module-level ``aq_acquire`` API respect the ``default`` parameter.
  LP #1387363.

- Don't raise an attribute error for ``__iter__`` if the fallback to
  ``__getitem__`` succeeds.  LP #1155760.


2.13.8 (2011-06-11)
-------------------

- Fixed a segfault on 64bit platforms when providing the `explicit` argument to
  the aq_acquire method of an Acquisition wrapper. Thx to LP #675064 for the
  hint to the solution. The code passed an int instead of a pointer into a
  function.


2.13.7 (2011-03-02)
-------------------

- Fixed bug: When an object did not implement ``__unicode__``, calling
  ``unicode(wrapped)`` was calling ``__str__`` with an unwrapped ``self``.


2.13.6 (2011-02-19)
-------------------

- Add ``aq_explicit`` to ``IAcquisitionWrapper``.

- Fixed bug: ``unicode(wrapped)`` was not calling a ``__unicode__``
  method on wrapped objects.


2.13.5 (2010-09-29)
-------------------

- Fixed unit tests that failed on 64bit Python on Windows machines.


2.13.4 (2010-08-31)
-------------------

- LP 623665: Fixed typo in Acquisition.h.


2.13.3 (2010-04-19)
-------------------

- Use the doctest module from the standard library and no longer depend on
  zope.testing.


2.13.2 (2010-04-04)
-------------------

- Give both wrapper classes a ``__getnewargs__`` method, which causes the ZODB
  optimization to fail and create persistent references using the ``_p_oid``
  alone. This happens to be the persistent oid of the wrapped object. This lets
  these objects to be persisted correctly, even though they are passed to the
  ZODB in a wrapped state.

- Added failing tests for http://dev.plone.org/plone/ticket/10318. This shows
  an edge-case where AQ wrappers can be pickled using the specific combination
  of cPickle, pickle protocol one and a custom Pickler class with an
  ``inst_persistent_id`` hook. Unfortunately this is the exact combination used
  by ZODB3.


2.13.1 (2010-02-23)
-------------------

- Update to include ExtensionClass 2.13.0.

- Fix the ``tp_name`` of the ImplicitAcquisitionWrapper and
  ExplicitAcquisitionWrapper to match their Python visible names and thus have
  a correct ``__name__``.

- Expand the ``tp_name`` of our extension types to hold the fully qualified
  name. This ensures classes have their ``__module__`` set correctly.


2.13.0 (2010-02-14)
-------------------

- Added support for method cache in Acquisition. Patch contributed by
  Yoshinori K. Okuji. See https://bugs.launchpad.net/zope2/+bug/486182.


2.12.4 (2009-10-29)
-------------------

- Fix iteration proxying to pass `self` acquisition-wrapped into both
  `__iter__` as well as `__getitem__` (this fixes
  https://bugs.launchpad.net/zope2/+bug/360761).

- Add tests for the __getslice__ proxying, including open-ended slicing.


2.12.3 (2009-08-08)
-------------------

- More 64-bit fixes in Py_BuildValue calls.

- More 64-bit issues fixed: Use correct integer size for slice operations.


2.12.2 (2009-08-02)
-------------------

- Fixed 64-bit compatibility issues for Python 2.5.x / 2.6.x.  See
  http://www.python.org/dev/peps/pep-0353/ for details.


2.12.1 (2009-04-15)
-------------------

- Update for iteration proxying: The proxy for `__iter__` must not rely on the
  object to have an `__iter__` itself, but also support fall-back iteration via
  `__getitem__` (this fixes https://bugs.launchpad.net/zope2/+bug/360761).


2.12 (2009-01-25)
-----------------

- Release as separate package.
