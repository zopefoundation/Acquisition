##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Acquisition test cases (and useful examples)
"""

from __future__ import print_function
import gc
import unittest
import sys
import operator
from doctest import DocTestSuite, DocFileSuite

import ExtensionClass
import Acquisition
from Acquisition import IS_PYPY, IS_PURE


if sys.version_info >= (3,):
    PY3 = True
    PY2 = False

    def unicode(self):
        # For test purposes, redirect the unicode
        # to the type of the object, just like Py2 did
        try:
            return type(self).__unicode__(self)
        except AttributeError as e:
            return type(self).__str__(self)
    long = int
else:
    PY2 = True
    PY3 = False

if not hasattr(gc, 'get_threshold'):
    # PyPy
    gc.get_threshold = lambda: ()
    gc.set_threshold = lambda *x: None

AQ_PARENT = unicode('aq_parent')
UNICODE_WAS_CALLED = unicode('unicode was called')
STR_WAS_CALLED = unicode('str was called')
TRUE = unicode('True')


def test_story():
    """
    Acquisition is a mechanism that allows objects to obtain
    attributes from their environment.  It is similar to inheritence,
    except that, rather than traversing an inheritence hierarchy
    to obtain attributes, a containment hierarchy is traversed.

    The "ExtensionClass":ExtensionClass.html. release includes mix-in
    extension base classes that can be used to add acquisition as a
    feature to extension subclasses.  These mix-in classes use the
    context-wrapping feature of ExtensionClasses to implement
    acquisition. Consider the following example:

    >>> import ExtensionClass, Acquisition

    >>> class C(ExtensionClass.Base):
    ...   color='red'

    >>> class A(Acquisition.Implicit):
    ...   def report(self):
    ...     print(self.color)

    >>> a = A()
    >>> c = C()
    >>> c.a = a

    >>> c.a.report()
    red

    >>> d = C()
    >>> d.color = 'green'
    >>> d.a = a

    >>> d.a.report()
    green

    >>> try:
    ...     a.report()
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    The class 'A' inherits acquisition behavior from
    'Acquisition.Implicit'.  The object, 'a', "has" the color of
    objects 'c' and 'd' when it is accessed through them, but it
    has no color by itself.  The object 'a' obtains attributes
    from it's environment, where it's environment is defined by
    the access path used to reach 'a'.

    Acquisition wrappers

    When an object that supports acquisition is accessed through
    an extension class instance, a special object, called an
    acquisition wrapper, is returned.  In the example above, the
    expression 'c.a' returns an acquisition wrapper that
    contains references to both 'c' and 'a'.  It is this wrapper
    that performs attribute lookup in 'c' when an attribute
    cannot be found in 'a'.

    Aquisition wrappers provide access to the wrapped objects
    through the attributes 'aq_parent', 'aq_self', 'aq_base'.
    In the example above, the expressions:

    >>> c.a.aq_parent is c
    1

    and:

    >>> c.a.aq_self is a
    1

    both evaluate to true, but the expression:

    >>> c.a is a
    0

    evaluates to false, because the expression 'c.a' evaluates
    to an acquisition wrapper around 'c' and 'a', not 'a' itself.

    The attribute 'aq_base' is similar to 'aq_self'.  Wrappers may be
    nested and 'aq_self' may be a wrapped object.  The 'aq_base'
    attribute is the underlying object with all wrappers removed.

    Acquisition Control

    Two styles of acquisition are supported in the current
    ExtensionClass release, implicit and explicit aquisition.

    Implicit acquisition

    Implicit acquisition is so named because it searches for
    attributes from the environment automatically whenever an
    attribute cannot be obtained directly from an object or
    through inheritence.

    An attribute may be implicitly acquired if it's name does
    not begin with an underscore, '_'.

    To support implicit acquisition, an object should inherit
    from the mix-in class 'Acquisition.Implicit'.

    Explicit Acquisition

    When explicit acquisition is used, attributes are not
    automatically obtained from the environment.  Instead, the
    method 'aq_aquire' must be used, as in:

    print(c.a.aq_acquire('color'))

    To support explicit acquisition, an object should inherit
    from the mix-in class 'Acquisition.Explicit'.

    Controlled Acquisition

    A class (or instance) can provide attribute by attribute control
    over acquisition.  This is done by:

    - subclassing from 'Acquisition.Explicit', and

    - setting all attributes that should be acquired to the special
      value: 'Acquisition.Acquired'.  Setting an attribute to this
      value also allows inherited attributes to be overridden with
      acquired ones.

    For example, in:

    >>> class E(Acquisition.Explicit):
    ...    id = 1
    ...    secret = 2
    ...    color = Acquisition.Acquired
    ...    __roles__ = Acquisition.Acquired

    The *only* attributes that are automatically acquired from
    containing objects are 'color', and '__roles__'.

    >>> c = C()
    >>> c.foo = 'foo'
    >>> c.e = E()
    >>> c.e.color
    'red'
    >>> c.e.foo
    Traceback (most recent call last):
    ...
    AttributeError: foo

    Note also that the '__roles__' attribute is acquired even
    though it's name begins with an underscore:

    >>> c.__roles__ = 'Manager', 'Member'
    >>> c.e.__roles__
    ('Manager', 'Member')

    In fact, the special 'Acquisition.Acquired' value can be used
    in 'Acquisition.Implicit' objects to implicitly acquire
    selected objects that smell like private objects.

    >>> class I(Acquisition.Implicit):
    ...    __roles__ = Acquisition.Acquired

    >>> c.x = C()
    >>> try:
    ...     c.x.__roles__
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> c.x = I()
    >>> c.x.__roles__
    ('Manager', 'Member')

    Filtered Acquisition

    The acquisition method, 'aq_acquire', accepts two optional
    arguments. The first of the additional arguments is a
    "filtering" function that is used when considering whether to
    acquire an object.  The second of the additional arguments is an
    object that is passed as extra data when calling the filtering
    function and which defaults to 'None'.

    The filter function is called with five arguments:

    - The object that the 'aq_acquire' method was called on,

    - The object where an object was found,

    - The name of the object, as passed to 'aq_acquire',

    - The object found, and

    - The extra data passed to 'aq_acquire'.

    If the filter returns a true object that the object found is
    returned, otherwise, the acquisition search continues.

    For example, in:

    >>> from Acquisition import Explicit

    >>> class HandyForTesting:
    ...     def __init__(self, name): self.name=name
    ...     def __str__(self):
    ...       return "%s(%s)" % (self.name, self.__class__.__name__)
    ...     __repr__=__str__

    >>> class E(Explicit, HandyForTesting):
    ...     pass

    >>> class Nice(HandyForTesting):
    ...     isNice=1
    ...     def __str__(self):
    ...        return HandyForTesting.__str__(self)+' and I am nice!'
    ...     __repr__=__str__

    >>> a = E('a')
    >>> a.b = E('b')
    >>> a.b.c = E('c')
    >>> a.p = Nice('spam')
    >>> a.b.p = E('p')

    >>> def find_nice(self, ancestor, name, object, extra):
    ...     return hasattr(object,'isNice') and object.isNice

    >>> print(a.b.c.aq_acquire('p', find_nice))
    spam(Nice) and I am nice!

    The filtered acquisition in the last line skips over the first
    attribute it finds with the name 'p', because the attribute
    doesn't satisfy the condition given in the filter.

    Acquisition and methods

    Python methods of objects that support acquisition can use
    acquired attributes as in the 'report' method of the first example
    above.  When a Python method is called on an object that is
    wrapped by an acquisition wrapper, the wrapper is passed to the
    method as the first argument.  This rule also applies to
    user-defined method types and to C methods defined in pure mix-in
    classes.

    Unfortunately, C methods defined in extension base classes that
    define their own data structures, cannot use aquired attributes at
    this time.  This is because wrapper objects do not conform to the
    data structures expected by these methods.

    Acquiring Acquiring objects

    Consider the following example:

    >>> from Acquisition import Implicit

    >>> class C(Implicit):
    ...     def __init__(self, name): self.name=name
    ...     def __str__(self):
    ...         return "%s(%s)" % (self.name, self.__class__.__name__)
    ...     __repr__=__str__

    >>> a = C("a")
    >>> a.b = C("b")
    >>> a.b.pref = "spam"
    >>> a.b.c = C("c")
    >>> a.b.c.color = "red"
    >>> a.b.c.pref = "eggs"
    >>> a.x = C("x")

    >>> o = a.b.c.x

    The expression 'o.color' might be expected to return '"red"'. In
    earlier versions of ExtensionClass, however, this expression
    failed.  Acquired acquiring objects did not acquire from the
    environment they were accessed in, because objects were only
    wrapped when they were first found, and were not rewrapped as they
    were passed down the acquisition tree.

    In the current release of ExtensionClass, the expression "o.color"
    does indeed return '"red"'.

    >>> o.color
    'red'

    When searching for an attribute in 'o', objects are searched in
    the order 'x', 'a', 'b', 'c'. So, for example, the expression,
    'o.pref' returns '"spam"', not '"eggs"':

    >>> o.pref
    'spam'

    In earlier releases of ExtensionClass, the attempt to get the
    'pref' attribute from 'o' would have failed.

    If desired, the current rules for looking up attributes in complex
    expressions can best be understood through repeated application of
    the '__of__' method:

    'a.x' -- 'x.__of__(a)'

    'a.b' -- 'b.__of__(a)'

    'a.b.x' -- 'x.__of__(a).__of__(b.__of__(a))'

    'a.b.c' -- 'c.__of__(b.__of__(a))'

    'a.b.c.x' --
        'x.__of__(a).__of__(b.__of__(a)).__of__(c.__of__(b.__of__(a)))'

    and by keeping in mind that attribute lookup in a wrapper
    is done by trying to lookup the attribute in the wrapped object
    first and then in the parent object.  In the expressions above
    involving the '__of__' method, lookup proceeds from left to right.

    Note that heuristics are used to avoid most of the repeated
    lookups. For example, in the expression: 'a.b.c.x.foo', the object
    'a' is searched no more than once, even though it is wrapped three
    times.
"""


class I(Acquisition.Implicit):

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return self.id


class E(Acquisition.Explicit):

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return self.id


def test_unwrapped():
    """
    >>> c = I('unwrapped')
    >>> show(c)
    unwrapped

    >>> try:
    ...     c.aq_parent
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> try:
    ...     c.__parent__
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_acquire(c, 'id')
    'unwrapped'

    >>> try:
    ...     Acquisition.aq_acquire(c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_acquire(c, 'id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'unwrapped'

    >>> Acquisition.aq_base(c) is c
    1

    >>> Acquisition.aq_chain(c)
    [unwrapped]

    >>> Acquisition.aq_chain(c, 1)
    [unwrapped]

    >>> Acquisition.aq_get(c, 'id')
    'unwrapped'

    >>> try:
    ...     Acquisition.aq_get(c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_get(c, 'x', 'foo')
    'foo'
    >>> Acquisition.aq_get(c, 'x', 'foo', 1)
    'foo'

    >>> Acquisition.aq_inner(c) is c
    1

    >>> Acquisition.aq_parent(c)

    >>> Acquisition.aq_self(c) is c
    1

    """


def test_simple():
    """
    >>> a = I('a')
    >>> a.y = 42
    >>> a.b = I('b')
    >>> a.b.c = I('c')
    >>> show(a.b.c)
    c
    |
    b
    |
    a

    >>> show(a.b.c.aq_parent)
    b
    |
    a

    >>> show(a.b.c.aq_self)
    c

    >>> show(a.b.c.aq_base)
    c

    >>> show(a.b.c.aq_inner)
    c
    |
    b
    |
    a

    >>> a.b.c.y
    42

    >>> a.b.c.aq_chain
    [c, b, a]

    >>> a.b.c.aq_inContextOf(a)
    1
    >>> a.b.c.aq_inContextOf(a.b)
    1
    >>> a.b.c.aq_inContextOf(a.b.c)
    1

    >>> Acquisition.aq_inContextOf(a.b.c, a)
    1
    >>> Acquisition.aq_inContextOf(a.b.c, a.b)
    1
    >>> Acquisition.aq_inContextOf(a.b.c, a.b.c)
    1


    >>> a.b.c.aq_acquire('y')
    42

    >>> a.b.c.aq_acquire('id')
    'c'

    >>> try:
    ...     a.b.c.aq_acquire('x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> a.b.c.aq_acquire('id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'c'

    >>> Acquisition.aq_acquire(a.b.c, 'id')
    'c'

    >>> try:
    ...     Acquisition.aq_acquire(a.b.c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_acquire(a.b.c, 'y')
    42

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'c'

    >>> show(Acquisition.aq_base(a.b.c))
    c

    >>> Acquisition.aq_chain(a.b.c)
    [c, b, a]

    >>> Acquisition.aq_chain(a.b.c, 1)
    [c, b, a]

    >>> Acquisition.aq_get(a.b.c, 'id')
    'c'

    >>> try:
    ...     Acquisition.aq_get(a.b.c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_get(a.b.c, 'x', 'foo')
    'foo'
    >>> Acquisition.aq_get(a.b.c, 'x', 'foo', 1)
    'foo'

    >>> show(Acquisition.aq_inner(a.b.c))
    c
    |
    b
    |
    a

    >>> show(Acquisition.aq_parent(a.b.c))
    b
    |
    a

    >>> show(Acquisition.aq_self(a.b.c))
    c

    A wrapper's __parent__ attribute (which is equivalent to its
    aq_parent attribute) points to the Acquisition parent.

    >>> a.b.c.__parent__ == a.b.c.aq_parent
    True
    >>> a.b.c.__parent__ == a.b
    True
    """


def test__of__exception():
    """
    Wrapper_findattr did't check for an exception in a user defined
    __of__ method before passing the result to the filter. In this
    case the 'value' argument of the filter was NULL, which caused
    a segfault when being accessed.

    >>> class X(Acquisition.Implicit):
    ...     def __of__(self, parent):
    ...         if Acquisition.aq_base(parent) is not parent:
    ...             raise NotImplementedError('ack')
    ...         return X.inheritedAttribute('__of__')(self, parent)
    ...
    >>> a = I('a')
    >>> a.b = I('b')
    >>> a.b.x = X('x')
    >>> Acquisition.aq_acquire(a.b, 'x',
    ...     lambda self, object, name, value, extra: repr(value))
    Traceback (most recent call last):
    ...
    NotImplementedError: ack

    """


def test_muliple():
    r"""
    >>> a = I('a')
    >>> a.color = 'red'
    >>> a.a1 = I('a1')
    >>> a.a1.color = 'green'
    >>> a.a1.a11 = I('a11')
    >>> a.a2 = I('a2')
    >>> a.a2.a21 = I('a21')
    >>> show(a.a1.a11.a2.a21)
    a21
    |
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   a1
    |   |
    |   a
    |
    a11
    |
    a1
    |
    a

    >>> a.a1.a11.a2.a21.color
    'red'

    >>> show(a.a1.a11.a2.a21.aq_parent)
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   a1
    |   |
    |   a
    |
    a11
    |
    a1
    |
    a

    >>> show(a.a1.a11.a2.a21.aq_parent.aq_parent)
    a11
    |
    a1
    |
    a

    >>> show(a.a1.a11.a2.a21.aq_self)
    a21

    >>> show(a.a1.a11.a2.a21.aq_parent.aq_self)
    (a2)
    |  \
    |   a2
    |   |
    |   a
    |
    a1
    |
    a

    >>> show(a.a1.a11.a2.a21.aq_base)
    a21

    >>> show(a.a1.a11.a2.a21.aq_inner)
    a21
    |
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   a1
    |   |
    |   a
    |
    a11
    |
    a1
    |
    a

    >>> show(a.a1.a11.a2.a21.aq_inner.aq_parent.aq_inner)
    a2
    |
    a

    >>> show(a.a1.a11.a2.a21.aq_inner.aq_parent.aq_inner.aq_parent)
    a

    >>> a.a1.a11.a2.a21.aq_chain
    [a21, a2, a11, a1, a]

    >>> a.a1.a11.a2.a21.aq_inContextOf(a)
    1

    >>> a.a1.a11.a2.a21.aq_inContextOf(a.a2)
    1

    >>> a.a1.a11.a2.a21.aq_inContextOf(a.a1)
    0

    >>> a.a1.a11.a2.a21.aq_acquire('color')
    'red'
    >>> a.a1.a11.a2.a21.aq_acquire('id')
    'a21'

    >>> a.a1.a11.a2.a21.aq_acquire('color',
    ...     lambda ob, parent, name, v, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: color

    >>> a.a1.a11.a2.a21.aq_acquire('color',
    ...     lambda ob, parent, name, v, extra: extra, 1)
    'red'

    >>> a.a1.y = 42
    >>> a.a1.a11.a2.a21.aq_acquire('y')
    42

    >>> try:
    ...     a.a1.a11.a2.a21.aq_acquire('y', containment=1)
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    Much of the same, but with methods:

    >>> show(Acquisition.aq_parent(a.a1.a11.a2.a21))
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   a1
    |   |
    |   a
    |
    a11
    |
    a1
    |
    a

    >>> show(Acquisition.aq_parent(a.a1.a11.a2.a21.aq_parent))
    a11
    |
    a1
    |
    a

    >>> show(Acquisition.aq_self(a.a1.a11.a2.a21))
    a21

    >>> show(Acquisition.aq_self(a.a1.a11.a2.a21.aq_parent))
    (a2)
    |  \
    |   a2
    |   |
    |   a
    |
    a1
    |
    a

    >>> show(Acquisition.aq_base(a.a1.a11.a2.a21))
    a21

    >>> show(Acquisition.aq_inner(a.a1.a11.a2.a21))
    a21
    |
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   a1
    |   |
    |   a
    |
    a11
    |
    a1
    |
    a

    >>> show(Acquisition.aq_inner(a.a1.a11.a2.a21.aq_inner.aq_parent))
    a2
    |
    a

    >>> show(Acquisition.aq_parent(
    ...       a.a1.a11.a2.a21.aq_inner.aq_parent.aq_inner))
    a

    >>> Acquisition.aq_chain(a.a1.a11.a2.a21)
    [a21, a2, a11, a1, a]

    >>> Acquisition.aq_chain(a.a1.a11.a2.a21, 1)
    [a21, a2, a]

    >>> Acquisition.aq_acquire(a.a1.a11.a2.a21, 'color')
    'red'
    >>> Acquisition.aq_acquire(a.a1.a11.a2.a21, 'id')
    'a21'

    >>> Acquisition.aq_acquire(a.a1.a11.a2.a21, 'color',
    ...     lambda ob, parent, name, v, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: color

    >>> Acquisition.aq_acquire(a.a1.a11.a2.a21, 'color',
    ...     lambda ob, parent, name, v, extra: extra, 1)
    'red'

    >>> a.a1.y = 42
    >>> Acquisition.aq_acquire(a.a1.a11.a2.a21, 'y')
    42

    >>> try:
    ...     Acquisition.aq_acquire(a.a1.a11.a2.a21, 'y', containment=1)
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')
    """


def test_pinball():
    r"""
    >>> a = I('a')
    >>> a.a1 = I('a1')
    >>> a.a1.a11 = I('a11')
    >>> a.a1.a12 = I('a12')
    >>> a.a2 = I('a2')
    >>> a.a2.a21 = I('a21')
    >>> a.a2.a22 = I('a22')
    >>> show(a.a1.a11.a1.a12.a2.a21.a2.a22)
    a22
    |
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   (a2)
    |   |  \
    |   |   (a2)
    |   |   |  \
    |   |   |   a2
    |   |   |   |
    |   |   |   a
    |   |   |
    |   |   (a1)
    |   |   |  \
    |   |   |   (a1)
    |   |   |   |  \
    |   |   |   |   a1
    |   |   |   |   |
    |   |   |   |   a
    |   |   |   |
    |   |   |   a1
    |   |   |   |
    |   |   |   a
    |   |   |
    |   |   a11
    |   |   |
    |   |   a1
    |   |   |
    |   |   a
    |   |
    |   a12
    |   |
    |   (a1)
    |   |  \
    |   |   (a1)
    |   |   |  \
    |   |   |   a1
    |   |   |   |
    |   |   |   a
    |   |   |
    |   |   a1
    |   |   |
    |   |   a
    |   |
    |   a11
    |   |
    |   a1
    |   |
    |   a
    |
    a21
    |
    (a2)
    |  \
    |   (a2)
    |   |  \
    |   |   a2
    |   |   |
    |   |   a
    |   |
    |   (a1)
    |   |  \
    |   |   (a1)
    |   |   |  \
    |   |   |   a1
    |   |   |   |
    |   |   |   a
    |   |   |
    |   |   a1
    |   |   |
    |   |   a
    |   |
    |   a11
    |   |
    |   a1
    |   |
    |   a
    |
    a12
    |
    (a1)
    |  \
    |   (a1)
    |   |  \
    |   |   a1
    |   |   |
    |   |   a
    |   |
    |   a1
    |   |
    |   a
    |
    a11
    |
    a1
    |
    a

    """


def test_explicit():
    """
    >>> a = E('a')
    >>> a.y = 42
    >>> a.b = E('b')
    >>> a.b.c = E('c')
    >>> show(a.b.c)
    c
    |
    b
    |
    a

    >>> show(a.b.c.aq_parent)
    b
    |
    a

    >>> show(a.b.c.aq_self)
    c

    >>> show(a.b.c.aq_base)
    c

    >>> show(a.b.c.aq_inner)
    c
    |
    b
    |
    a

    >>> a.b.c.y
    Traceback (most recent call last):
    ...
    AttributeError: y

    >>> a.b.c.aq_chain
    [c, b, a]

    >>> a.b.c.aq_inContextOf(a)
    1
    >>> a.b.c.aq_inContextOf(a.b)
    1
    >>> a.b.c.aq_inContextOf(a.b.c)
    1


    >>> a.b.c.aq_acquire('y')
    42

    >>> a.b.c.aq_acquire('id')
    'c'

    >>> try:
    ...     a.b.c.aq_acquire('x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> a.b.c.aq_acquire('id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'c'

    >>> Acquisition.aq_acquire(a.b.c, 'id')
    'c'

    >>> try:
    ...     Acquisition.aq_acquire(a.b.c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_acquire(a.b.c, 'y')
    42

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'c'

    >>> show(Acquisition.aq_base(a.b.c))
    c

    >>> Acquisition.aq_chain(a.b.c)
    [c, b, a]

    >>> Acquisition.aq_chain(a.b.c, 1)
    [c, b, a]

    >>> Acquisition.aq_get(a.b.c, 'id')
    'c'

    >>> try:
    ...     Acquisition.aq_get(a.b.c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_get(a.b.c, 'y')
    42

    >>> Acquisition.aq_get(a.b.c, 'x', 'foo')
    'foo'
    >>> Acquisition.aq_get(a.b.c, 'x', 'foo', 1)
    'foo'

    >>> show(Acquisition.aq_inner(a.b.c))
    c
    |
    b
    |
    a

    >>> show(Acquisition.aq_parent(a.b.c))
    b
    |
    a

    >>> show(Acquisition.aq_self(a.b.c))
    c

    """


def test_mixed_explicit_and_explicit():
    """
    >>> a = I('a')
    >>> a.y = 42
    >>> a.b = E('b')
    >>> a.b.z = 3
    >>> a.b.c = I('c')
    >>> show(a.b.c)
    c
    |
    b
    |
    a

    >>> show(a.b.c.aq_parent)
    b
    |
    a

    >>> show(a.b.c.aq_self)
    c

    >>> show(a.b.c.aq_base)
    c

    >>> show(a.b.c.aq_inner)
    c
    |
    b
    |
    a

    >>> a.b.c.y
    42

    >>> a.b.c.z
    3

    >>> a.b.c.aq_chain
    [c, b, a]

    >>> a.b.c.aq_inContextOf(a)
    1
    >>> a.b.c.aq_inContextOf(a.b)
    1
    >>> a.b.c.aq_inContextOf(a.b.c)
    1

    >>> a.b.c.aq_acquire('y')
    42

    >>> a.b.c.aq_acquire('z')
    3

    >>> a.b.c.aq_acquire('id')
    'c'

    >>> try:
    ...     a.b.c.aq_acquire('x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> a.b.c.aq_acquire('id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'c'

    >>> Acquisition.aq_acquire(a.b.c, 'id')
    'c'

    >>> try:
    ...     Acquisition.aq_acquire(a.b.c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_acquire(a.b.c, 'y')
    42

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...  lambda searched, parent, name, ob, extra: extra)
    Traceback (most recent call last):
    ...
    AttributeError: id

    >>> Acquisition.aq_acquire(a.b.c, 'id',
    ...        lambda searched, parent, name, ob, extra: extra,
    ...        1)
    'c'

    >>> show(Acquisition.aq_base(a.b.c))
    c

    >>> Acquisition.aq_chain(a.b.c)
    [c, b, a]

    >>> Acquisition.aq_chain(a.b.c, 1)
    [c, b, a]

    >>> Acquisition.aq_get(a.b.c, 'id')
    'c'

    >>> try:
    ...     Acquisition.aq_get(a.b.c, 'x')
    ... except AttributeError:
    ...     pass
    ... else:
    ...     raise AssertionError('AttributeError not raised.')

    >>> Acquisition.aq_get(a.b.c, 'y')
    42

    >>> Acquisition.aq_get(a.b.c, 'x', 'foo')
    'foo'
    >>> Acquisition.aq_get(a.b.c, 'x', 'foo', 1)
    'foo'

    >>> show(Acquisition.aq_inner(a.b.c))
    c
    |
    b
    |
    a

    >>> show(Acquisition.aq_parent(a.b.c))
    b
    |
    a

    >>> show(Acquisition.aq_self(a.b.c))
    c

    """


def test_aq_inContextOf():
    """
    >>> from ExtensionClass import Base
    >>> import Acquisition

    >>> class B(Base):
    ...     color='red'

    >>> class A(Acquisition.Implicit):
    ...     def hi(self):
    ...         print(self.__class__.__name__)
    ...         print(self.color)

    >>> class Location(object):
    ...     __parent__ = None

    >>> b=B()
    >>> b.a=A()
    >>> b.a.hi()
    A
    red
    >>> b.a.color='green'
    >>> b.a.hi()
    A
    green
    >>> try:
    ...     A().hi()
    ...     raise RuntimeError( 'Program error', 'spam')
    ... except AttributeError: pass
    A

       New test for wrapper comparisons.

    >>> foo = b.a
    >>> bar = b.a
    >>> foo == bar
    1
    >>> c = A()
    >>> b.c = c
    >>> b.c.d = c
    >>> b.c.d == c
    1
    >>> b.c.d == b.c
    1
    >>> b.c == c
    1

    >>> l = Location()
    >>> l.__parent__ = b.c

    >>> def checkContext(self, o):
    ...     # Python equivalent to aq_inContextOf
    ...     from Acquisition import aq_base, aq_parent, aq_inner
    ...     next = self
    ...     o = aq_base(o)
    ...     while 1:
    ...         if aq_base(next) is o:
    ...             return 1
    ...         self = aq_inner(next)
    ...         if self is None:
    ...             break
    ...         next = aq_parent(self)
    ...         if next is None:
    ...             break
    ...     return 0


    >>> checkContext(b.c, b)
    1
    >>> not checkContext(b.c, b.a)
    1

    >>> checkContext(l, b)
    1
    >>> checkContext(l, b.c)
    1
    >>> not checkContext(l, b.a)
    1

    Acquisition.aq_inContextOf works the same way:

    >>> Acquisition.aq_inContextOf(b.c, b)
    1
    >>> Acquisition.aq_inContextOf(b.c, b.a)
    0

    >>> Acquisition.aq_inContextOf(l, b)
    1
    >>> Acquisition.aq_inContextOf(l, b.c)
    1
    >>> Acquisition.aq_inContextOf(l, b.a)
    0

    >>> b.a.aq_inContextOf(b)
    1
    >>> b.c.aq_inContextOf(b)
    1
    >>> b.c.d.aq_inContextOf(b)
    1
    >>> b.c.d.aq_inContextOf(c)
    1
    >>> b.c.d.aq_inContextOf(b.c)
    1
    >>> b.c.aq_inContextOf(foo)
    0
    >>> b.c.aq_inContextOf(b.a)
    0
    >>> b.a.aq_inContextOf('somestring')
    0
    """


def test_AqAlg():
    """
    >>> A=I('A')
    >>> A.B=I('B')
    >>> A.B.color='red'
    >>> A.C=I('C')
    >>> A.C.D=I('D')

    >>> A
    A
    >>> Acquisition.aq_chain(A)
    [A]
    >>> Acquisition.aq_chain(A, 1)
    [A]
    >>> list(map(Acquisition.aq_base, Acquisition.aq_chain(A, 1)))
    [A]
    >>> A.C
    C
    >>> Acquisition.aq_chain(A.C)
    [C, A]
    >>> Acquisition.aq_chain(A.C, 1)
    [C, A]
    >>> list(map(Acquisition.aq_base, Acquisition.aq_chain(A.C, 1)))
    [C, A]

    >>> A.C.D
    D
    >>> Acquisition.aq_chain(A.C.D)
    [D, C, A]
    >>> Acquisition.aq_chain(A.C.D, 1)
    [D, C, A]
    >>> list(map(Acquisition.aq_base, Acquisition.aq_chain(A.C.D, 1)))
    [D, C, A]

    >>> A.B.C
    C
    >>> Acquisition.aq_chain(A.B.C)
    [C, B, A]
    >>> Acquisition.aq_chain(A.B.C, 1)
    [C, A]
    >>> list(map(Acquisition.aq_base, Acquisition.aq_chain(A.B.C, 1)))
    [C, A]

    >>> A.B.C.D
    D
    >>> Acquisition.aq_chain(A.B.C.D)
    [D, C, B, A]
    >>> Acquisition.aq_chain(A.B.C.D, 1)
    [D, C, A]
    >>> list(map(Acquisition.aq_base, Acquisition.aq_chain(A.B.C.D, 1)))
    [D, C, A]


    >>> A.B.C.D.color
    'red'
    >>> Acquisition.aq_get(A.B.C.D, "color", None)
    'red'
    >>> Acquisition.aq_get(A.B.C.D, "color", None, 1)

    """


def test_explicit_acquisition():
    """
    >>> from ExtensionClass import Base
    >>> import Acquisition

    >>> class B(Base):
    ...     color='red'

    >>> class A(Acquisition.Explicit):
    ...     def hi(self):
    ...         print(self.__class__.__name__)
    ...         print(self.acquire('color'))

    >>> b=B()
    >>> b.a=A()
    >>> b.a.hi()
    A
    red
    >>> b.a.color='green'
    >>> b.a.hi()
    A
    green

    >>> try:
    ...     A().hi()
    ...     raise RuntimeError('Program error', 'spam')
    ... except AttributeError: pass
    A

    """


class TestCreatingWrappers(unittest.TestCase):

    def test_creating_wrappers_directly(self):
        from ExtensionClass import Base
        from Acquisition import ImplicitAcquisitionWrapper

        class B(Base):
            pass

        a = B()
        a.color = 'red'
        a.b = B()
        w = ImplicitAcquisitionWrapper(a.b, a)
        self.assertEqual(w.color, 'red')

        with self.assertRaises(TypeError):
            ImplicitAcquisitionWrapper(a.b)

        # We can reassign aq_parent / __parent__ on a wrapper:

        x = B()
        x.color = 'green'
        w.aq_parent = x
        self.assertEqual(w.color, 'green')

        y = B()
        y.color = 'blue'
        w.__parent__ = y
        self.assertEqual(w.color, 'blue')

        # Note that messing with the wrapper won't in any way affect the
        # wrapped object:

        with self.assertRaises(AttributeError):
            Acquisition.aq_base(w).__parent__

        with self.assertRaises(TypeError):
            ImplicitAcquisitionWrapper()

        with self.assertRaises(TypeError):
            ImplicitAcquisitionWrapper(obj=1)


class TestPickle(unittest.TestCase):

    def test_cant_pickle_acquisition_wrappers_classic(self):
        import pickle

        class X:
            def __getstate__(self):
                return 1

        # We shouldn't be able to pickle wrappers:

        from Acquisition import ImplicitAcquisitionWrapper
        w = ImplicitAcquisitionWrapper(X(), X())
        with self.assertRaises(TypeError):
            pickle.dumps(w)

        # But that's not enough. We need to defeat persistence as well. :)
        # This is tricky. We want to generate the error in __getstate__, not
        # in the attr access, as attribute errors are too-often hidden:

        getstate = w.__getstate__
        with self.assertRaises(TypeError):
            getstate()

        # We shouldn't be able to pickle wrappers:

        from Acquisition import ExplicitAcquisitionWrapper
        w = ExplicitAcquisitionWrapper(X(), X())
        with self.assertRaises(TypeError):
            pickle.dumps(w)

        # But that's not enough. We need to defeat persistence as well. :)
        # This is tricky. We want to generate the error in __getstate__, not
        # in the attr access, as attribute errors are too-often hidden:

        getstate = w.__getstate__
        with self.assertRaises(TypeError):
            getstate()

    def test_cant_pickle_acquisition_wrappers_newstyle(self):
        import pickle

        class X(object):
            def __getstate__(self):
                return 1

        # We shouldn't be able to pickle wrappers:

        from Acquisition import ImplicitAcquisitionWrapper
        w = ImplicitAcquisitionWrapper(X(), X())
        with self.assertRaises(TypeError):
            pickle.dumps(w)

        # But that's not enough. We need to defeat persistence as well. :)
        # This is tricky. We want to generate the error in __getstate__, not
        # in the attr access, as attribute errors are too-often hidden:

        getstate = w.__getstate__
        with self.assertRaises(TypeError):
            getstate()

        # We shouldn't be able to pickle wrappers:

        from Acquisition import ExplicitAcquisitionWrapper
        w = ExplicitAcquisitionWrapper(X(), X())
        with self.assertRaises(TypeError):
            pickle.dumps(w)

        # But that's not enough. We need to defeat persistence as well. :)
        # This is tricky. We want to generate the error in __getstate__, not
        # in the attr access, as attribute errors are too-often hidden:

        getstate = w.__getstate__
        with self.assertRaises(TypeError):
            getstate()

    def test_cant_persist_acquisition_wrappers_classic(self):
        try:
            import cPickle
        except ImportError:
            import pickle as cPickle

        class X:
            _p_oid = '1234'

            def __getstate__(self):
                return 1

        # We shouldn't be able to pickle wrappers:

        from Acquisition import ImplicitAcquisitionWrapper
        w = ImplicitAcquisitionWrapper(X(), X())
        with self.assertRaises(TypeError):
            cPickle.dumps(w)

        # Check for pickle protocol one:

        with self.assertRaises(TypeError):
            cPickle.dumps(w, 1)

        # Check custom pickler:

        from io import BytesIO
        file = BytesIO()
        pickler = cPickle.Pickler(file, 1)

        with self.assertRaises(TypeError):
            pickler.dump(w)

        # Check custom pickler with a persistent_id method matching
        # the semantics in ZODB.serialize.ObjectWriter.persistent_id:

        file = BytesIO()
        pickler = cPickle.Pickler(file, 1)

        def persistent_id(obj):
            if not hasattr(obj, '_p_oid'):
                return None
            klass = type(obj)
            oid = obj._p_oid
            if hasattr(klass, '__getnewargs__'):
                # Coverage, make sure it can be called
                assert klass.__getnewargs__(obj) == ()
                return oid
            return 'class_and_oid', klass

        try:
            pickler.inst_persistent_id = persistent_id
        except AttributeError:
            pass
        pickler.persistent_id = persistent_id  # PyPy and Py3k
        pickler.dump(w)
        state = file.getvalue()
        self.assertTrue(b'1234' in state)
        self.assertFalse(b'class_and_oid' in state)

    def test_cant_persist_acquisition_wrappers_newstyle(self):
        try:
            import cPickle
        except ImportError:
            import pickle as cPickle

        class X(object):
            _p_oid = '1234'

            def __getstate__(self):
                return 1

        # We shouldn't be able to pickle wrappers:

        from Acquisition import ImplicitAcquisitionWrapper
        w = ImplicitAcquisitionWrapper(X(), X())
        with self.assertRaises(TypeError):
            cPickle.dumps(w)

        # Check for pickle protocol one:

        with self.assertRaises(TypeError):
            cPickle.dumps(w, 1)

        # Check custom pickler:

        from io import BytesIO
        file = BytesIO()
        pickler = cPickle.Pickler(file, 1)

        with self.assertRaises(TypeError):
            pickler.dump(w)

        # Check custom pickler with a persistent_id method matching
        # the semantics in ZODB.serialize.ObjectWriter.persistent_id:

        file = BytesIO()
        pickler = cPickle.Pickler(file, 1)

        def persistent_id(obj):
            if not hasattr(obj, '_p_oid'):
                return None
            klass = type(obj)
            oid = obj._p_oid
            if hasattr(klass, '__getnewargs__'):
                return oid
            return 'class_and_oid', klass

        try:
            pickler.inst_persistent_id = persistent_id
        except AttributeError:
            pass

        pickler.persistent_id = persistent_id  # PyPy and Py3k
        pickler.dump(w)
        state = file.getvalue()
        self.assertTrue(b'1234' in state)
        self.assertFalse(b'class_and_oid' in state)


class TestInterfaces(unittest.TestCase):

    def test_interfaces(self):
        from zope.interface.verify import verifyClass

        # Explicit and Implicit implement IAcquirer:

        from Acquisition import Explicit
        from Acquisition import Implicit
        from Acquisition.interfaces import IAcquirer
        self.assertTrue(verifyClass(IAcquirer, Explicit))
        self.assertTrue(verifyClass(IAcquirer, Implicit))

        # ExplicitAcquisitionWrapper and ImplicitAcquisitionWrapper implement
        # IAcquisitionWrapper:

        from Acquisition import ExplicitAcquisitionWrapper
        from Acquisition import ImplicitAcquisitionWrapper
        from Acquisition.interfaces import IAcquisitionWrapper
        self.assertTrue(
            verifyClass(IAcquisitionWrapper, ExplicitAcquisitionWrapper))
        self.assertTrue(
            verifyClass(IAcquisitionWrapper, ImplicitAcquisitionWrapper))


try:
    class Plain(object):
        pass
    Plain.__bases__ = (ExtensionClass.Base,)
except TypeError:
    # Not supported
    pass
else:
    # Assigning to __bases__ is difficult under some versions of python.
    # PyPy usually lets it, but CPython (3 esp) may not.
    # In this example, you get:
    #   "TypeError: __bases__ assignment:
    #   'Base' deallocator differs from 'object'"
    # I don't know what the workaround is; the old one of using a dummy
    # superclass no longer works. See http://bugs.python.org/issue672115

    def test_mixin_post_class_definition():
        """
        Mixing in Base after class definition doesn't break anything,
        but also doesn't result in any wrappers.

        >>> from ExtensionClass import Base
        >>> class Plain(object):
        ...     pass
        >>> Plain.__bases__ == (object,)
        True
        >>> Plain.__bases__ = (Base,)
        >>> isinstance(Plain(), Base)
        True

        Even after mixing in that base, when we request such an object
        from an implicit acquiring base, it doesn't come out wrapped:

        >>> from Acquisition import Implicit
        >>> class I(Implicit):
        ...     pass
        >>> root = I()
        >>> root.a = I()
        >>> root.a.b = Plain()
        >>> type(root.a.b) is Plain
        True

        This is because after the mixin, even though Plain is-a Base,
        it's still not an Explicit/Implicit acquirer and provides
        neither the `__of__` nor `__get__` methods necessary.
        `__get__` is added as a consequence of
        `__of__` at class creation time):

        >>> hasattr(Plain, '__get__')
        False
        >>> hasattr(Plain, '__of__')
        False

        """


def test_mixin_base():
    """
    We can mix-in Base as part of multiple inheritance.

    >>> from ExtensionClass import Base
    >>> class MyBase(object):
    ...    pass
    >>> class MixedIn(Base,MyBase):
    ...     pass
    >>> MixedIn.__bases__ == (Base,MyBase)
    True
    >>> isinstance(MixedIn(), Base)
    True

    Because it's not an acquiring object and doesn't provide `__of__`
    or `__get__`, when accessed from implicit contexts it doesn't come
    out wrapped:

    >>> from Acquisition import Implicit
    >>> class I(Implicit):
    ...     pass
    >>> root = I()
    >>> root.a = I()
    >>> root.a.b = MixedIn()
    >>> type(root.a.b) is MixedIn
    True

    This is because after the mixin, even though Plain is-a Base,
    it doesn't provide the `__of__` method used for wrapping, and so
    the class definition code that would add the `__get__` method also
    doesn't run:

    >>> hasattr(MixedIn, '__of__')
    False
    >>> hasattr(MixedIn, '__get__')
    False

    """


def show(x):
    print(showaq(x).strip())


def showaq(m_self, indent=''):
    rval = ''
    obj = m_self
    base = getattr(obj, 'aq_base', obj)
    try:
        id = base.id
    except Exception:
        id = str(base)
    try:
        id = id()
    except Exception:
        pass

    if hasattr(obj, 'aq_self'):
        if hasattr(obj.aq_self, 'aq_self'):
            rval = rval + indent + "(" + id + ")\n"
            rval = rval + indent + "|  \\\n"
            rval = rval + showaq(obj.aq_self, '|   ' + indent)
            rval = rval + indent + "|\n"
            rval = rval + showaq(obj.aq_parent, indent)
        elif hasattr(obj, 'aq_parent'):
            rval = rval + indent + id + "\n"
            rval = rval + indent + "|\n"
            rval = rval + showaq(obj.aq_parent, indent)
    else:
        rval = rval + indent + id + "\n"
    return rval


def test_Basic_gc():
    """Test to make sure that EC instances participate in GC.
    Note that PyPy always reports 0 collected objects even
    though we can see its finalizers run.

    >>> from ExtensionClass import Base
    >>> import gc
    >>> thresholds = gc.get_threshold()
    >>> gc.set_threshold(0)

    >>> for B in I, E:
    ...     class C1(B):
    ...         pass
    ...
    ...     class C2(Base):
    ...         def __del__(self):
    ...             print('removed')
    ...
    ...     a=C1('a')
    ...     a.b = C1('a.b')
    ...     a.b.a = a
    ...     a.b.c = C2()
    ...     ignore = gc.collect()
    ...     del a
    ...     removed = gc.collect()
    ...     print(removed > 0 or IS_PYPY)
    removed
    True
    removed
    True

    >>> gc.set_threshold(*thresholds)

    """


def test_Wrapper_gc():
    """Test to make sure that EC instances participate in GC.
    Note that PyPy always reports 0 collected objects even
    though we can see its finalizers run.

    >>> import gc
    >>> thresholds = gc.get_threshold()
    >>> gc.set_threshold(0)

    >>> for B in I, E:
    ...     class C:
    ...         def __del__(self):
    ...             print('removed')
    ...
    ...     a=B('a')
    ...     a.b = B('b')
    ...     a.a_b = a.b # circ ref through wrapper
    ...     a.b.c = C()
    ...     ignored = gc.collect()
    ...     del a
    ...     removed = gc.collect()
    ...     removed > 0 or IS_PYPY
    removed
    True
    removed
    True

    >>> gc.set_threshold(*thresholds)

    """


def test_container_proxying():
    """Make sure that recent python container-related slots are proxied.

    >>> import sys
    >>> import Acquisition
    >>> class Impl(Acquisition.Implicit):
    ...     pass

    >>> class C(Acquisition.Implicit):
    ...     def __getitem__(self, key):
    ...         if isinstance(key, slice):
    ...             print('slicing...')
    ...             return (key.start,key.stop)
    ...         print('getitem', key)
    ...         if key == 4:
    ...             raise IndexError
    ...         return key
    ...     def __contains__(self, key):
    ...         print('contains', repr(key))
    ...         return key == 5
    ...     def __iter__(self):
    ...         print('iterating...')
    ...         return iter((42,))
    ...     def __getslice__(self, start, end):
    ...         print('slicing...')
    ...         return (start, end)

    The naked class behaves like this:

    >>> c = C()
    >>> 3 in c
    contains 3
    False
    >>> 5 in c
    contains 5
    True
    >>> list(c)
    iterating...
    [42]
    >>> c[5:10]
    slicing...
    (5, 10)
    >>> c[5:] == (5, sys.maxsize if PY2 else None)
    slicing...
    True

    Let's put c in the context of i:

    >>> i = Impl()
    >>> i.c = c

    Now check that __contains__ is properly used:

    >>> 3 in i.c # c.__of__(i)
    contains 3
    False
    >>> 5 in i.c
    contains 5
    True
    >>> list(i.c)
    iterating...
    [42]
    >>> i.c[5:10]
    slicing...
    (5, 10)
    >>> i.c[5:] == (5, sys.maxsize if PY2 else None)
    slicing...
    True

    Let's let's test the same again with an explicit wrapper:

    >>> import Acquisition
    >>> class Impl(Acquisition.Explicit):
    ...     pass

    >>> class C(Acquisition.Explicit):
    ...     def __getitem__(self, key):
    ...         if isinstance(key, slice):
    ...             print('slicing...')
    ...             return (key.start,key.stop)
    ...         print('getitem', key)
    ...         if key == 4:
    ...             raise IndexError
    ...         return key
    ...     def __contains__(self, key):
    ...         print('contains', repr(key))
    ...         return key == 5
    ...     def __iter__(self):
    ...         print('iterating...')
    ...         return iter((42,))
    ...     def __getslice__(self, start, end):
    ...         print('slicing...')
    ...         return (start, end)

    The naked class behaves like this:

    >>> c = C()
    >>> 3 in c
    contains 3
    False
    >>> 5 in c
    contains 5
    True
    >>> list(c)
    iterating...
    [42]
    >>> c[5:10]
    slicing...
    (5, 10)
    >>> c[5:] == (5, sys.maxsize if PY2 else None)
    slicing...
    True

    Let's put c in the context of i:

    >>> i = Impl()
    >>> i.c = c

    Now check that __contains__ is properly used:

    >>> 3 in i.c # c.__of__(i)
    contains 3
    False
    >>> 5 in i.c
    contains 5
    True
    >>> list(i.c)
    iterating...
    [42]
    >>> i.c[5:10]
    slicing...
    (5, 10)
    >>> i.c[5:] == (5, sys.maxsize if PY2 else None)
    slicing...
    True

    Next let's check that the wrapper's __iter__ proxy falls back
    to using the object's __getitem__ if it has no __iter__.  See
    https://bugs.launchpad.net/zope2/+bug/360761 .

    >>> class C(Acquisition.Implicit):
    ...     l=[1,2,3]
    ...     def __getitem__(self, i):
    ...         return self.l[i]

    >>> c1 = C()
    >>> type(iter(c1)) #doctest: +ELLIPSIS
    <... '...iterator'>
    >>> list(c1)
    [1, 2, 3]

    >>> c2 = C().__of__(c1)
    >>> type(iter(c2)) #doctest: +ELLIPSIS
    <... '...iterator'>
    >>> list(c2)
    [1, 2, 3]

    The __iter__proxy should also pass the wrapped object as self to
    the __iter__ of objects defining __iter__:

    >>> class C(Acquisition.Implicit):
    ...     def __iter__(self):
    ...         print('iterating...')
    ...         for i in range(5):
    ...             yield i, self.aq_parent.name
    >>> c = C()
    >>> i = Impl()
    >>> i.c = c
    >>> i.name = 'i'
    >>> list(i.c)
    iterating...
    [(0, 'i'), (1, 'i'), (2, 'i'), (3, 'i'), (4, 'i')]

    And it should pass the wrapped object as self to
    the __getitem__ of objects without an __iter__:

    >>> class C(Acquisition.Implicit):
    ...     def __getitem__(self, i):
    ...         return self.aq_parent.l[i]
    >>> c = C()
    >>> i = Impl()
    >>> i.c = c
    >>> i.l = range(5)
    >>> list(i.c)
    [0, 1, 2, 3, 4]

    Finally let's make sure errors are still correctly raised after having
    to use a modified version of `PyObject_GetIter` for iterator support:

    >>> class C(Acquisition.Implicit):
    ...     pass
    >>> c = C()
    >>> i = Impl()
    >>> i.c = c
    >>> list(i.c) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: ...iter...

    >>> class C(Acquisition.Implicit):
    ...     def __iter__(self):
    ...         return [42]
    >>> c = C()
    >>> i = Impl()
    >>> i.c = c
    >>> list(i.c) #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    TypeError: iter() returned non-iterator...

    """


class Location(object):
    __parent__ = None


class ECLocation(ExtensionClass.Base):
    __parent__ = None


def test___parent__no_wrappers():
    """
    Acquisition also works with objects that aren't wrappers, as long
    as they have __parent__ pointers.  Let's take a hierarchy like
    z --isParent--> y --isParent--> x:

      >>> x = Location()
      >>> y = Location()
      >>> z = Location()
      >>> x.__parent__ = y
      >>> y.__parent__ = z

    and some attributes that we want to acquire:

      >>> x.hello = 'world'
      >>> y.foo = 42
      >>> z.foo = 43  # this should not be found
      >>> z.bar = 3.145

    ``aq_acquire`` works as we know it from implicit/acquisition
    wrappers:

      >>> Acquisition.aq_acquire(x, 'hello')
      'world'
      >>> Acquisition.aq_acquire(x, 'foo')
      42
      >>> Acquisition.aq_acquire(x, 'bar')
      3.145

    as does ``aq_get``:

      >>> Acquisition.aq_get(x, 'hello')
      'world'
      >>> Acquisition.aq_get(x, 'foo')
      42
      >>> Acquisition.aq_get(x, 'bar')
      3.145

    and ``aq_parent``:

      >>> Acquisition.aq_parent(x) is y
      True
      >>> Acquisition.aq_parent(y) is z
      True

    as well as ``aq_chain``:

      >>> Acquisition.aq_chain(x) == [x, y, z]
      True
    """


def test_implicit_wrapper_as___parent__():
    """
    Let's do the same test again, only now not all objects are of the
    same kind and link to each other via __parent__ pointers.  The
    root is a stupid ExtensionClass object:

      >>> class Root(ExtensionClass.Base):
      ...     bar = 3.145
      >>> z = Root()

    The intermediate parent is an object that supports implicit
    acquisition.  We bind it to the root via the __of__ protocol:

      >>> class Impl(Acquisition.Implicit):
      ...     foo = 42
      >>> y = Impl().__of__(z)

    The child object is again a simple object with a simple __parent__
    pointer:

      >>> x = Location()
      >>> x.hello = 'world'
      >>> x.__parent__ = y

    ``aq_acquire`` works as expected from implicit/acquisition
    wrappers:

      >>> Acquisition.aq_acquire(x, 'hello')
      'world'
      >>> Acquisition.aq_acquire(x, 'foo')
      42
      >>> Acquisition.aq_acquire(x, 'bar')
      3.145

    as does ``aq_get``:

      >>> Acquisition.aq_get(x, 'hello')
      'world'
      >>> Acquisition.aq_get(x, 'foo')
      42
      >>> Acquisition.aq_get(x, 'bar')
      3.145

    and ``aq_parent``:

      >>> Acquisition.aq_parent(x) is y
      True
      >>> Acquisition.aq_parent(y) is z
      True

    as well as ``aq_chain``:

      >>> Acquisition.aq_chain(x) == [x, y, z]
      True

    Note that also the (implicit) acquisition wrapper has a __parent__
    pointer, which is automatically computed from the acquisition
    container (it's identical to aq_parent):

      >>> y.__parent__ is z
      True

    Just as much as you can assign to aq_parent, you can also assign
    to __parent__ to change the acquisition context of the wrapper:

      >>> newroot = Root()
      >>> y.__parent__ = newroot
      >>> y.__parent__ is z
      False
      >>> y.__parent__ is newroot
      True

    Note that messing with the wrapper won't in any way affect the
    wrapped object:

      >>> try:
      ...     Acquisition.aq_base(y).__parent__
      ... except AttributeError:
      ...     pass
      ... else:
      ...     raise AssertionError('AttributeError not raised.')
    """


def test_explicit_wrapper_as___parent__():
    """
    Let's do this test yet another time, with an explicit wrapper:

      >>> class Root(ExtensionClass.Base):
      ...     bar = 3.145
      >>> z = Root()

    The intermediate parent is an object that supports implicit
    acquisition.  We bind it to the root via the __of__ protocol:

      >>> class Expl(Acquisition.Explicit):
      ...     foo = 42
      >>> y = Expl().__of__(z)

    The child object is again a simple object with a simple __parent__
    pointer:

      >>> x = Location()
      >>> x.hello = 'world'
      >>> x.__parent__ = y

    ``aq_acquire`` works as expected from implicit/acquisition
    wrappers:

      >>> Acquisition.aq_acquire(x, 'hello')
      'world'
      >>> Acquisition.aq_acquire(x, 'foo')
      42
      >>> Acquisition.aq_acquire(x, 'bar')
      3.145

    as does ``aq_get``:

      >>> Acquisition.aq_get(x, 'hello')
      'world'
      >>> Acquisition.aq_get(x, 'foo')
      42
      >>> Acquisition.aq_get(x, 'bar')
      3.145

    and ``aq_parent``:

      >>> Acquisition.aq_parent(x) is y
      True
      >>> Acquisition.aq_parent(y) is z
      True

    as well as ``aq_chain``:

      >>> Acquisition.aq_chain(x) == [x, y, z]
      True

    Note that also the (explicit) acquisition wrapper has a __parent__
    pointer, which is automatically computed from the acquisition
    container (it's identical to aq_parent):

      >>> y.__parent__ is z
      True

    Just as much as you can assign to aq_parent, you can also assign
    to __parent__ to change the acquisition context of the wrapper:

      >>> newroot = Root()
      >>> y.__parent__ = newroot
      >>> y.__parent__ is z
      False
      >>> y.__parent__ is newroot
      True

    Note that messing with the wrapper won't in any way affect the
    wrapped object:

      >>> try:
      ...     Acquisition.aq_base(y).__parent__
      ... except AttributeError:
      ...     pass
      ... else:
      ...     raise AssertionError('AttributeError not raised.')
    """


def test_implicit_wrapper_has_nonwrapper_as_aq_parent():
    """Let's do this the other way around: The root and the
    intermediate parent is an object that doesn't support acquisition,

      >>> y = ECLocation()
      >>> z = Location()
      >>> y.__parent__ = z
      >>> y.foo = 42
      >>> z.foo = 43  # this should not be found
      >>> z.bar = 3.145

    only the outmost object does:

      >>> class Impl(Acquisition.Implicit):
      ...     hello = 'world'
      >>> x = Impl().__of__(y)

    Again, acquiring objects works as usual:

      >>> Acquisition.aq_acquire(x, 'hello')
      'world'
      >>> Acquisition.aq_acquire(x, 'foo')
      42
      >>> Acquisition.aq_acquire(x, 'bar')
      3.145

    as does ``aq_get``:

      >>> Acquisition.aq_get(x, 'hello')
      'world'
      >>> Acquisition.aq_get(x, 'foo')
      42
      >>> Acquisition.aq_get(x, 'bar')
      3.145

    and ``aq_parent``:

      >>> Acquisition.aq_parent(x) == y
      True
      >>> x.aq_parent == y
      True
      >>> x.aq_parent.aq_parent == z
      True
      >>> Acquisition.aq_parent(y) is z
      True

    as well as ``aq_chain``:

      >>> Acquisition.aq_chain(x) == [x, y, z]
      True
      >>> x.aq_chain == [x, y, z]
      True

    Because the outmost object, ``x``, is wrapped in an implicit
    acquisition wrapper, we can also use direct attribute access:

      >>> x.hello
      'world'
      >>> x.foo
      42
      >>> x.bar
      3.145
    """


def test_explicit_wrapper_has_nonwrapper_as_aq_parent():
    """Let's do this the other way around: The root and the
    intermediate parent is an object that doesn't support acquisition,

      >>> y = ECLocation()
      >>> z = Location()
      >>> y.__parent__ = z
      >>> y.foo = 42
      >>> z.foo = 43  # this should not be found
      >>> z.bar = 3.145

    only the outmost object does:

      >>> class Expl(Acquisition.Explicit):
      ...     hello = 'world'
      >>> x = Expl().__of__(y)

    Again, acquiring objects works as usual:

      >>> Acquisition.aq_acquire(x, 'hello')
      'world'
      >>> Acquisition.aq_acquire(x, 'foo')
      42
      >>> Acquisition.aq_acquire(x, 'bar')
      3.145

    as does ``aq_get``:

      >>> Acquisition.aq_get(x, 'hello')
      'world'
      >>> Acquisition.aq_get(x, 'foo')
      42
      >>> Acquisition.aq_get(x, 'bar')
      3.145

    and ``aq_parent``:

      >>> Acquisition.aq_parent(x) == y
      True
      >>> x.aq_parent == y
      True
      >>> x.aq_parent.aq_parent == z
      True
      >>> Acquisition.aq_parent(y) is z
      True

    as well as ``aq_chain``:

      >>> Acquisition.aq_chain(x) == [x, y, z]
      True
      >>> x.aq_chain == [x, y, z]
      True
    """


class TestParentCircles(unittest.TestCase):

    def test___parent__aq_parent_circles(self):
        # As a general safety belt, Acquisition won't follow a mixture of
        # circular __parent__ pointers and aq_parent wrappers.  These can
        # occurr when code that uses implicit acquisition wrappers meets
        # code that uses __parent__ pointers.

        class Impl(Acquisition.Implicit):
            hello = 'world'

        class Impl2(Acquisition.Implicit):
            hello = 'world2'
            only = 'here'

        x = Impl()
        y = Impl2().__of__(x)
        x.__parent__ = y

        self.assertTrue(x.__parent__.aq_base is y.aq_base)
        self.assertTrue(Acquisition.aq_parent(x) is y)
        self.assertTrue(x.__parent__.__parent__ is x)

        self.assertEqual(x.hello, 'world')
        self.assertEqual(Acquisition.aq_acquire(x, 'hello'), 'world')

        with self.assertRaises(AttributeError):
            x.only

        self.assertEqual(Acquisition.aq_acquire(x, 'only'), 'here')

        with self.assertRaises(AttributeError):
            Acquisition.aq_acquire(x, 'non_existant_attr')

        with self.assertRaises(RuntimeError):
            Acquisition.aq_acquire(y, 'non_existant_attr')

        with self.assertRaises(AttributeError):
            x.non_existant_attr

        with self.assertRaises(RuntimeError):
            y.non_existant_attr


if hasattr(Acquisition.ImplicitAcquisitionWrapper, '_obj'):
    def test_python_impl_cycle():
        """
        An extra safety belt, specific to the Python implementation
        because it's not clear how one could arrive in this situation
        naturally.

        >>> class Impl(Acquisition.Implicit):
        ...    pass
        >>> root = Impl()
        >>> root.child = Impl()
        >>> child_wrapper = root.child

        Now set up the python specific boo-boo:

        >>> child_wrapper._obj = child_wrapper

        Now nothing works:

        >>> child_wrapper.non_existant_attr
        Traceback (most recent call last):
        ...
        RuntimeError: Recursion detected in acquisition wrapper

        >>> Acquisition.aq_acquire(child_wrapper, 'non_existant_attr')
        Traceback (most recent call last):
        ...
        RuntimeError: Recursion detected in acquisition wrapper

        """


def test_unwrapped_implicit_acquirer_unwraps__parent__():
    """
    Set up an implicit acquirer with a parent:

    >>> class Impl(Acquisition.Implicit):
    ...     pass

    >>> y = Impl()
    >>> x = Impl()
    >>> x.__parent__ = y

    Now if we retrieve the parent from the (unwrapped) instance,
    the parent should not be wrapped in the instance's acquisition chain.

    >>> x.__parent__ is y
    True
    """


def test__iter__after_AttributeError():
    """ See https://bugs.launchpad.net/zope2/+bug/1155760

    >>> from Acquisition import Implicit
    >>> class C(Implicit):
    ...     l = [0, 1, 2, 3, 4]
    ...     def __getitem__(self, i):
    ...         return self.l[i]
    >>> a = C()
    >>> b = C().__of__(a)
    >>> import time
    >>> try:
    ...     for n in b:
    ...         t = time.gmtime()
    ... except AttributeError:
    ...     raise
    """


def test_special_names():
    """
    This test captures some aq_special names that are not otherwise
    tested for.

    >>> class Impl(Acquisition.Implicit):
    ...     pass

    >>> root = Impl()
    >>> root.child = Impl()

    First, the 'aq_explicit' name returns an explicit wrapper
    instead of an explicit wrapper:

    >>> ex_wrapper = root.child.aq_explicit
    >>> type(ex_wrapper) #doctest: +ELLIPSIS
    <... 'Acquisition.ExplicitAcquisitionWrapper'>

    If we ask an explicit wrapper to be explicit, we get back
    the same object:

    >>> ex_wrapper.aq_explicit is ex_wrapper.aq_explicit
    True

    These special names can also be filtered:

    >>> Acquisition.aq_acquire(root.child, 'aq_explicit',
    ...    lambda searched, parent, name, ob, extra: None,
    ...    default=None) is None
    True
    >>> Acquisition.aq_acquire(root.child, 'aq_explicit',
    ...    lambda searched, parent, name, ob, extra: True,
    ...    default=None) is None
    False


    Last, a value that can be used for testing that you have a wrapper:

    >>> root.child.aq_uncle
    'Bob'

    """


def test_deleting_parent_attrs():
    """
    We can detach a wrapper object from its chain by deleting its
    parent.

    >>> class Impl(Acquisition.Implicit):
    ...     pass

    >>> root = Impl()
    >>> root.a = 42
    >>> root.child = Impl()

    Initially, a wrapped object has the parent we expect:

    >>> child_wrapper = root.child
    >>> child_wrapper.aq_parent is child_wrapper.__parent__ is root
    True

    Even though we acquired the 'a' attribute, we can't delete it:

    >>> child_wrapper.a
    42
    >>> del child_wrapper.a #doctest: +ELLIPSIS
    Traceback (most recent call last):
      ...
    AttributeError: ...

    Now if we delete it (as many times as we want)
    we lose access to the parent and acquired attributes:

    >>> del child_wrapper.__parent__
    >>> del child_wrapper.aq_parent

    >>> child_wrapper.aq_parent is child_wrapper.__parent__ is None
    True
    >>> hasattr(child_wrapper, 'a')
    False

    """


def test__cmp__is_called_on_wrapped_object():
    """
    If we define an object that implements `__cmp__`:

    >>> class Impl(Acquisition.Implicit):
    ...     def __cmp__(self,other):
    ...         return self.a

    Then it gets called when a wrapper is compared (we call it
    directly to avoid any Python2/3 issues):

    >>> root = Impl()
    >>> root.a = 42
    >>> root.child = Impl()
    >>> root.child.a
    42

    >>> root.child.__cmp__(None)
    42

    """


def test_wrapped_methods_have_correct_self():
    """
    Getting a method from a wrapper returns an object that uses the
    wrapper as its `__self__`, no matter how many layers deep we go;
    this makes acquisition work in that code.

    >>> class Impl(Acquisition.Implicit):
    ...    def method(self):
    ...        return self.a

    >>> root = Impl()
    >>> root.a = 42
    >>> root.child = Impl()
    >>> root.child.child = Impl()

    We explicitly construct a wrapper to bypass some of the optimizations
    that remove redundant wrappers and thus get more full code coverage:

    >>> child_wrapper = Acquisition.ImplicitAcquisitionWrapper(
    ...     root.child.child, root.child)

    >>> method = child_wrapper.method
    >>> method.__self__ is child_wrapper
    True
    >>> method()
    42
    """


def test_cannot_set_attributes_on_empty_wrappers():
    """
    If a wrapper is around None, no attributes can be set on it:

    >>> wrapper = Acquisition.ImplicitAcquisitionWrapper(None,None)
    >>> wrapper.a = 42 #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    AttributeError: ...

    Likewise, we can't really get any attributes on such an empty wrapper

    >>> wrapper.a #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    AttributeError: ...

    """


def test_getitem_setitem_not_implemented():
    """
    If a wrapper wraps something that doesn't implement get/setitem,
    those failures propagate up.

    >>> class Impl(Acquisition.Implicit):
    ...     pass
    >>> root = Impl()
    >>> root.child = Impl()

    We can't set anything:

    >>> root.child['key'] = 42
    Traceback (most recent call last):
        ...
    AttributeError: __setitem__

    We can't get anything:

    >>> root.child['key']
    Traceback (most recent call last):
        ...
    AttributeError: __getitem__
    """


def test_getitem_setitem_implemented():
    """
    The wrapper delegates to get/set item.

    >>> class Root(Acquisition.Implicit):
    ...   pass
    >>> class Impl(Acquisition.Implicit):
    ...   def __getitem__(self, i):
    ...        return self.a
    ...   def __setitem__(self, key, value):
    ...        self.a[key] = value

    >>> root = Root()
    >>> root.a = dict()
    >>> root.child = Impl()

    >>> root.child[1]
    {}
    >>> root.child['a'] = 'b'
    >>> root.child[1]
    {'a': 'b'}
    """


def test_wrapped_objects_are_unwrapped_on_set():
    """
    A wrapper is not passed to the base object during `setattr`.

    >>> class Impl(Acquisition.Implicit):
    ...   pass

    Given two different wrappers:

    >>> root = Impl()
    >>> child = Impl()
    >>> child2 = Impl()
    >>> root.child = child
    >>> root.child2 = child

    If we pass one to the other as an attribute:

    >>> root.child.child2 = root.child2

    By the time it gets there, it's not wrapped:

    >>> type(child.__dict__['child2']) is Impl
    True
    """


def test_wrapper_calls_of_on_non_wrapper():
    """
    The ExtensionClass protocol is respected even for non-Acquisition
    objects.

    >>> class MyBase(ExtensionClass.Base):
    ...     def __of__(self, other):
    ...        print("Of called")
    ...        return 42

    >>> class Impl(Acquisition.Implicit):
    ...     pass

    If we have a wrapper around an object that is an extension class,
    but not an Acquisition wrapper:

    >>> root = Impl()
    >>> wrapper = Acquisition.ImplicitAcquisitionWrapper(MyBase(), root)

    And access that object itself through a wrapper:

    >>> root.child = Impl()
    >>> root.child.wrapper = wrapper

    The `__of__` protocol is respected implicitly:

    >>> root.child.wrapper
    Of called
    42

    Here it is explicitly:

    >>> wrapper.__of__(root.child)
    Of called
    42

    """


def test_aq_inContextOf_odd_cases():
    """
    The aq_inContextOf function still works in some
    artificial cases.

    >>> from Acquisition import aq_inContextOf, aq_inner

    >>> root = object()
    >>> wrapper_around_none = Acquisition.ImplicitAcquisitionWrapper(None,None)
    >>> aq_inContextOf(wrapper_around_none, root)
    0

    If we don't ask for inner objects, the same thing happens in this case:

    >>> aq_inContextOf(wrapper_around_none, root, False)
    0

    Somewhat surprisingly, the `aq_inner` of this wrapper is itself a wrapper:

    >>> aq_inner(wrapper_around_none) is None
    False

    If we manipulate the Python implementation to make this no longer true,
    nothing breaks:

    >>> if hasattr(wrapper_around_none, '_obj'):
    ...     setattr(wrapper_around_none, '_obj', None)

    >>> aq_inContextOf(wrapper_around_none, root)
    0
    >>> wrapper_around_none
    None

    Following parent pointers in weird circumstances works too:

    >>> class WithParent(object):
    ...    __parent__ = None
    >>> aq_inContextOf(WithParent(), root)
    0

    """


def test_search_repeated_objects():
    """
    If an acquisition wrapper object is wrapping another wrapper, and
    also has another wrapper as its parent, and both of *those*
    wrappers have the same object (one as its direct object, one as
    its parent), then acquisition proceeds as normal: we don't get
    into any cycles or fail to acquire expected attributes. In fact,
    we actually can optimize out a level of the search in that case.


    This is a bit of a convoluted scenario to set up when the code is
    written out all in one place, but it may occur organically when
    spread across a project.

    We begin with some simple setup, importing the objects we'll use
    and setting up the object that we'll repeat. This particular test
    is specific to the Python implementation, so we're using low-level
    functions from that module:

    >>> from Acquisition import _Wrapper as Wrapper
    >>> from Acquisition import _Wrapper_acquire
    >>> from Acquisition import aq_acquire

    >>> class Repeated(object):
    ...    hello = "world"
    ...    def __repr__(self):
    ...        return 'repeated'
    >>> repeated = Repeated()

    Now the tricky part, creating the repeating pattern. To rephrase
    the opening sentence, we need a wrapper whose object and parent
    (container) are themselves both wrappers, and the object's parent is
    the same object as the wrapper's parent's object. That might be a
    bit more clear in code:

    >>> wrappers_object = Wrapper('a', repeated)
    >>> wrappers_parent = Wrapper(repeated, 'b')
    >>> wrapper = Wrapper(wrappers_object, wrappers_parent)
    >>> wrapper._obj._container is wrapper._container._obj
    True

    Using the low-level function on the wrapper fails to find the
    desired attribute. This is because of the optimization that cuts
    out a level of the search (it is assumed that the higher level
    `_Wrapper_findattr` function is driving the search and will take
    the appropriate steps):

    >>> _Wrapper_acquire(wrapper, 'hello') #doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    AttributeError: ...


    In fact, if we go through the public interface of the high-level
    functions, we do find the attribute as expected:

    >>> aq_acquire(wrapper, 'hello')
    'world'
    """


class TestParent(unittest.TestCase):

    def test_parent_parent_circles(self):

        class Impl(Acquisition.Implicit):
            hello = 'world'

        class Impl2(Acquisition.Implicit):
            hello = 'world2'
            only = 'here'

        x = Impl()
        y = Impl2()
        x.__parent__ = y
        y.__parent__ = x

        self.assertTrue(x.__parent__.__parent__ is x)
        self.assertEqual(Acquisition.aq_acquire(x, 'hello'), 'world')
        self.assertEqual(Acquisition.aq_acquire(x, 'only'), 'here')

        self.assertRaises(AttributeError, Acquisition.aq_acquire,
                          x, 'non_existant_attr')
        self.assertRaises(AttributeError, Acquisition.aq_acquire,
                          y, 'non_existant_attr')

    def test_parent_parent_parent_circles(self):

        class Impl(Acquisition.Implicit):
            hello = 'world'

        class Impl2(Acquisition.Implicit):
            hello = 'world'

        class Impl3(Acquisition.Implicit):
            hello = 'world2'
            only = 'here'

        a = Impl()
        b = Impl2()
        c = Impl3()
        a.__parent__ = b
        b.__parent__ = c
        c.__parent__ = a

        self.assertTrue(a.__parent__.__parent__ is c)
        self.assertTrue(
            Acquisition.aq_base(a.__parent__.__parent__.__parent__) is a)
        self.assertTrue(b.__parent__.__parent__ is a)
        self.assertTrue(c.__parent__.__parent__ is b)

        self.assertEqual(Acquisition.aq_acquire(a, 'hello'), 'world')
        self.assertEqual(Acquisition.aq_acquire(b, 'hello'), 'world')
        self.assertEqual(Acquisition.aq_acquire(c, 'hello'), 'world2')

        self.assertEqual(Acquisition.aq_acquire(a, 'only'), 'here')
        self.assertEqual(Acquisition.aq_acquire(b, 'only'), 'here')
        self.assertEqual(Acquisition.aq_acquire(c, 'only'), 'here')

        self.assertRaises(AttributeError, getattr, a, 'non_existant_attr')
        self.assertRaises(AttributeError, getattr, b, 'non_existant_attr')
        self.assertRaises(AttributeError, getattr, c, 'non_existant_attr')


class TestAcquire(unittest.TestCase):

    def setUp(self):

        class Impl(Acquisition.Implicit):
            pass

        class Expl(Acquisition.Explicit):
            pass

        a = Impl('a')
        a.y = 42
        a.b = Expl('b')
        a.b.z = 3
        a.b.c = Impl('c')
        self.a = a
        self.acquire = Acquisition.aq_acquire

    def test_explicit_module_default(self):
        self.assertEqual(self.acquire(self.a.b.c, 'z'), 3)

    def test_explicit_module_true(self):
        self.assertEqual(self.acquire(self.a.b.c, 'z', explicit=True), 3)

    def test_explicit_module_false(self):
        self.assertEqual(self.acquire(self.a.b.c, 'z', explicit=False), 3)

    def test_explicit_wrapper_default(self):
        self.assertEqual(self.a.b.c.aq_acquire('z'), 3)

    def test_explicit_wrapper_true(self):
        self.assertEqual(self.a.b.c.aq_acquire('z', explicit=True), 3)

    def test_explicit_wrapper_false(self):
        self.assertEqual(self.a.b.c.aq_acquire('z', explicit=False), 3)

    def test_wrapper_falls_back_to_default(self):
        self.assertEqual(self.acquire(self.a.b.c, 'nonesuch', default=4), 4)

    def test_no_wrapper_but___parent___falls_back_to_default(self):
        class NotWrapped(object):
            pass
        child = NotWrapped()
        child.__parent__ = NotWrapped()
        self.assertEqual(self.acquire(child, 'nonesuch', default=4), 4)

    def test_unwrapped_falls_back_to_default(self):
        self.assertEqual(self.acquire(object(), 'nonesuch', default=4), 4)

    def test_w_unicode_attr_name(self):
        # See https://bugs.launchpad.net/acquisition/+bug/143358
        found = self.acquire(self.a.b.c, AQ_PARENT)
        self.assertTrue(found.aq_self is self.a.b.aq_self)


class TestCooperativeBase(unittest.TestCase):

    def _make_acquirer(self, kind):
        from ExtensionClass import Base

        class ExtendsBase(Base):
            def __getattribute__(self, name):
                if name == 'magic':
                    return 42
                return super(ExtendsBase, self).__getattribute__(name)

        class Acquirer(kind, ExtendsBase):
            pass

        return Acquirer()

    def _check___getattribute___is_cooperative(self, acquirer):
        self.assertEqual(getattr(acquirer, 'magic'), 42)

    def test_implicit___getattribute__is_cooperative(self):
        self._check___getattribute___is_cooperative(
            self._make_acquirer(Acquisition.Implicit))

    def test_explicit___getattribute__is_cooperative(self):
        self._check___getattribute___is_cooperative(
            self._make_acquirer(Acquisition.Explicit))


if 'Acquisition._Acquisition' not in sys.modules:
    # Implicitly wrapping an object that uses object.__getattribute__
    # in its implementation of __getattribute__ doesn't break.
    # This can arise with the `persistent` library or other
    # "base" classes.

    # The C implementation doesn't directly support this; however,
    # it is used heavily in the Python implementation of Persistent.

    class TestImplicitWrappingGetattribute(unittest.TestCase):

        def test_object_getattribute_in_rebound_method_with_slots(self):

            class Persistent(object):
                __slots__ = ('__flags',)

                def __init__(self):
                    self.__flags = 42

                def get_flags(self):
                    return object.__getattribute__(self, '_Persistent__flags')

            wrapped = Persistent()
            wrapper = Acquisition.ImplicitAcquisitionWrapper(wrapped, None)

            self.assertEqual(wrapped.get_flags(), wrapper.get_flags())

            # Changing it is not reflected in the wrapper's dict (this is an
            # implementation detail)
            wrapper._Persistent__flags = -1
            self.assertEqual(wrapped.get_flags(), -1)
            self.assertEqual(wrapped.get_flags(), wrapper.get_flags())

            wrapper_dict = object.__getattribute__(wrapper, '__dict__')
            self.assertFalse('_Persistent__flags' in wrapper_dict)

        def test_type_with_slots_reused(self):

            class Persistent(object):
                __slots__ = ('__flags',)

                def __init__(self):
                    self.__flags = 42

                def get_flags(self):
                    return object.__getattribute__(self, '_Persistent__flags')

            wrapped = Persistent()
            wrapper = Acquisition.ImplicitAcquisitionWrapper(wrapped, None)
            wrapper2 = Acquisition.ImplicitAcquisitionWrapper(wrapped, None)

            self.assertTrue(type(wrapper) is type(wrapper2))

        def test_object_getattribute_in_rebound_method_with_dict(self):

            class Persistent(object):
                def __init__(self):
                    self.__flags = 42

                def get_flags(self):
                    return object.__getattribute__(self, '_Persistent__flags')

            wrapped = Persistent()
            wrapper = Acquisition.ImplicitAcquisitionWrapper(wrapped, None)

            self.assertEqual(wrapped.get_flags(), wrapper.get_flags())

            # Changing it is also reflected in both dicts (this is an
            # implementation detail)
            wrapper._Persistent__flags = -1
            self.assertEqual(wrapped.get_flags(), -1)
            self.assertEqual(wrapped.get_flags(), wrapper.get_flags())

            wrapper_dict = object.__getattribute__(wrapper, '__dict__')
            self.assertTrue('_Persistent__flags' in wrapper_dict)

        def test_object_getattribute_in_rebound_method_with_slots_and_dict(self):  # NOQA

            class Persistent(object):
                __slots__ = ('__flags', '__dict__')

                def __init__(self):
                    self.__flags = 42
                    self.__oid = 'oid'

                def get_flags(self):
                    return object.__getattribute__(self, '_Persistent__flags')

                def get_oid(self):
                    return object.__getattribute__(self, '_Persistent__oid')

            wrapped = Persistent()
            wrapper = Acquisition.ImplicitAcquisitionWrapper(wrapped, None)

            self.assertEqual(wrapped.get_flags(), wrapper.get_flags())
            self.assertEqual(wrapped.get_oid(), wrapper.get_oid())


class TestUnicode(unittest.TestCase):

    def test_implicit_aq_unicode_should_be_called(self):
        class A(Acquisition.Implicit):
            def __unicode__(self):
                return UNICODE_WAS_CALLED
        wrapped = A().__of__(A())
        self.assertEqual(UNICODE_WAS_CALLED, unicode(wrapped))
        self.assertEqual(str(wrapped), repr(wrapped))

    def test_explicit_aq_unicode_should_be_called(self):
        class A(Acquisition.Explicit):
            def __unicode__(self):
                return UNICODE_WAS_CALLED
        wrapped = A().__of__(A())
        self.assertEqual(UNICODE_WAS_CALLED, unicode(wrapped))
        self.assertEqual(str(wrapped), repr(wrapped))

    def test_implicit_should_fall_back_to_str(self):
        class A(Acquisition.Implicit):
            def __str__(self):
                return 'str was called'
        wrapped = A().__of__(A())
        self.assertEqual(STR_WAS_CALLED, unicode(wrapped))
        self.assertEqual('str was called', str(wrapped))

    def test_explicit_should_fall_back_to_str(self):
        class A(Acquisition.Explicit):
            def __str__(self):
                return 'str was called'
        wrapped = A().__of__(A())
        self.assertEqual(STR_WAS_CALLED, unicode(wrapped))
        self.assertEqual('str was called', str(wrapped))

    def test_str_fallback_should_be_called_with_wrapped_self(self):
        class A(Acquisition.Implicit):
            def __str__(self):
                return str(self.aq_parent == outer)
        outer = A()
        inner = A().__of__(outer)
        self.assertEqual(TRUE, unicode(inner))

    def test_unicode_should_be_called_with_wrapped_self(self):
        class A(Acquisition.Implicit):
            def __unicode__(self):
                return str(self.aq_parent == outer)
        outer = A()
        inner = A().__of__(outer)
        self.assertEqual(TRUE, unicode(inner))


class TestProxying(unittest.TestCase):

    __binary_numeric_methods__ = [
        '__add__',
        '__sub__',
        '__mul__',
        # '__floordiv__',  # not implemented in C
        '__mod__',
        '__divmod__',
        '__pow__',
        '__lshift__',
        '__rshift__',
        '__and__',
        '__xor__',
        '__or__',
        # division
        '__truediv__',
        '__div__',
        # reflected
        '__radd__',
        '__rsub__',
        '__rmul__',
        '__rdiv__',
        '__rtruediv__',
        '__rfloordiv__',
        '__rmod__',
        '__rdivmod__',
        '__rpow__',
        '__rlshift__',
        '__rrshift__',
        '__rand__',
        '__rxor__',
        '__ror__',
        # in place
        '__iadd__',
        '__isub__',
        '__imul__',
        '__idiv__',
        '__itruediv__',
        '__ifloordiv__',
        '__imod__',
        '__idivmod__',
        '__ipow__',
        '__ilshift__',
        '__irshift__',
        '__iand__',
        '__ixor__',
        '__ior__',
        # conversion
        # implementing it messes up all the arithmetic tests
        # '__coerce__',
    ]

    if PY3 and sys.version_info.minor >= 5:
        __binary_numeric_methods__.extend([
            '__matmul__',
            '__imatmul__'
        ])

    __unary_special_methods__ = [
        # arithmetic
        '__neg__',
        '__pos__',
        '__abs__',
        '__invert__',
    ]

    __unary_conversion_methods__ = {
        # conversion
        '__complex__': complex,
        '__int__': int,
        '__long__': long,
        '__float__': float,
        '__oct__': oct,
        '__hex__': hex,
        '__len__': lambda o: o if isinstance(o, int) else len(o),
        # '__index__': operator.index, # not implemented in C
    }

    def _check_special_methods(self, base_class=Acquisition.Implicit):
        # Check that special methods are proxied
        # when called implicitly by the interpreter

        def binary_acquired_func(self, other, modulo=None):
            return self.value

        def unary_acquired_func(self):
            return self.value

        acquire_meths = {}
        for k in self.__binary_numeric_methods__:
            acquire_meths[k] = binary_acquired_func
        for k in self.__unary_special_methods__:
            acquire_meths[k] = unary_acquired_func

        def make_converter(f):
            def converter(self, *args):
                return f(self.value)
            return converter
        for k, convert in self.__unary_conversion_methods__.items():
            acquire_meths[k] = make_converter(convert)

        acquire_meths['__len__'] = lambda self: self.value

        if PY3:
            # Under Python 3, oct() and hex() call __index__ directly
            acquire_meths['__index__'] = acquire_meths['__int__']

        if base_class == Acquisition.Explicit:
            acquire_meths['value'] = Acquisition.Acquired
        AcquireValue = type('AcquireValue', (base_class,), acquire_meths)

        class B(Acquisition.Implicit):
            pass

        base = B()
        base.value = 42
        base.derived = AcquireValue()

        # one syntax check for the heck of it
        self.assertEqual(base.value, base.derived + 1)
        # divmod is not in the operator module
        self.assertEqual(base.value, divmod(base.derived, 1))

        _found_at_least_one_div = False

        for meth in self.__binary_numeric_methods__:
            op = getattr(operator, meth, None)
            if op is not None:
                # called on the instance
                self.assertEqual(base.value, op(base.derived, -1))

            # called on the type, as the interpreter does
            # Note that the C version can only implement either __truediv__
            # or __div__, not both
            op = getattr(operator, meth, None)
            if op is not None:
                try:
                    self.assertEqual(base.value,
                                     op(base.derived, 1))
                    if meth in ('__div__', '__truediv__'):
                        _found_at_least_one_div = True
                except TypeError:
                    if meth in ('__div__', '__truediv__'):
                        pass

        self.assertTrue(
            _found_at_least_one_div,
            "Must implement at least one of __div__ and __truediv__")

        # Unary methods
        for meth in self.__unary_special_methods__:
            self.assertEqual(base.value, getattr(base.derived, meth)())
            op = getattr(operator, meth)
            self.assertEqual(base.value, op(base.derived))

        # Conversion functions
        for meth, converter in self.__unary_conversion_methods__.items():
            if not converter:
                continue
            self.assertEqual(converter(base.value),
                             getattr(base.derived, meth)())

            self.assertEqual(converter(base.value),
                             converter(base.derived))

    def test_implicit_proxy_special_meths(self):
        self._check_special_methods()

    def test_explicit_proxy_special_meths(self):
        self._check_special_methods(base_class=Acquisition.Explicit)

    def _check_contains(self, base_class=Acquisition.Implicit):
        # Contains has lots of fallback behaviour
        class B(Acquisition.Implicit):
            pass
        base = B()
        base.value = 42

        # The simple case is if the object implements contains itself
        class ReallyContains(base_class):
            if base_class is Acquisition.Explicit:
                value = Acquisition.Acquired

            def __contains__(self, item):
                return self.value == item

        base.derived = ReallyContains()

        self.assertTrue(42 in base.derived)
        self.assertFalse(24 in base.derived)

        # Iterable objects are NOT iterated
        # XXX: Is this a bug in the C code? Shouldn't it do
        # what the interpreter does and fallback to iteration?
        class IterContains(base_class):
            if base_class is Acquisition.Explicit:
                value = Acquisition.Acquired

            def __iter__(self):
                return iter((42,))
        base.derived = IterContains()

        self.assertRaises(AttributeError, operator.contains, base.derived, 42)

    def test_implicit_proxy_contains(self):
        self._check_contains()

    def test_explicit_proxy_contains(self):
        self._check_contains(base_class=Acquisition.Explicit)

    def _check_call(self, base_class=Acquisition.Implicit):
        class B(Acquisition.Implicit):
            pass
        base = B()
        base.value = 42

        class Callable(base_class):
            if base_class is Acquisition.Explicit:
                value = Acquisition.Acquired

            def __call__(self, arg, k=None):
                return self.value, arg, k

        base.derived = Callable()

        self.assertEqual(base.derived(1, k=2), (42, 1, 2))

        if not IS_PYPY:
            # XXX: This test causes certain versions
            # of PyPy to segfault (at least 2.6.0-alpha1)
            class NotCallable(base_class):
                pass

            base.derived = NotCallable()
            try:
                base.derived()
                self.fail("Not callable")
            except (TypeError, AttributeError):
                pass

    def test_implicit_proxy_call(self):
        self._check_call()

    def test_explicit_proxy_call(self):
        self._check_call(base_class=Acquisition.Explicit)

    def _check_hash(self, base_class=Acquisition.Implicit):
        class B(Acquisition.Implicit):
            pass
        base = B()
        base.value = B()
        base.value.hash = 42

        class NoAcquired(base_class):
            def __hash__(self):
                return 1

        hashable = NoAcquired()
        base.derived = hashable
        self.assertEqual(1, hash(hashable))
        self.assertEqual(1, hash(base.derived))

        # cannot access acquired attributes during
        # __hash__

        class CannotAccessAcquiredAttributesAtHash(base_class):
            if base_class is Acquisition.Explicit:
                value = Acquisition.Acquired

            def __hash__(self):
                return self.value.hash

        hashable = CannotAccessAcquiredAttributesAtHash()
        base.derived = hashable
        self.assertRaises(AttributeError, hash, hashable)
        self.assertRaises(AttributeError, hash, base.derived)

    def test_implicit_proxy_hash(self):
        self._check_hash()

    def test_explicit_proxy_hash(self):
        self._check_hash(base_class=Acquisition.Explicit)

    def _check_comparison(self, base_class=Acquisition.Implicit):
        # Comparison behaviour is complex; see notes in _Wrapper
        class B(Acquisition.Implicit):
            pass
        base = B()
        base.value = 42

        rich_cmp_methods = ['__lt__', '__gt__', '__eq__',
                            '__ne__', '__ge__', '__le__']

        def _never_called(self, other):
            raise RuntimeError("This should never be called")

        class RichCmpNeverCalled(base_class):
            for _name in rich_cmp_methods:
                locals()[_name] = _never_called

        base.derived = RichCmpNeverCalled()
        base.derived2 = RichCmpNeverCalled()
        # We can access all of the operators, but only because
        # they are masked
        for name in rich_cmp_methods:
            getattr(operator, name)(base.derived, base.derived2)

        self.assertFalse(base.derived2 == base.derived)
        self.assertEquals(base.derived, base.derived)

    def test_implicit_proxy_comporison(self):
        self._check_comparison()

    def test_explicit_proxy_comporison(self):
        self._check_comparison(base_class=Acquisition.Explicit)

    def _check_bool(self, base_class=Acquisition.Implicit):
        class B(Acquisition.Implicit):
            pass
        base = B()
        base.value = 42

        class WithBool(base_class):
            if base_class is Acquisition.Explicit:
                value = Acquisition.Acquired

            def __nonzero__(self):
                return bool(self.value)
            __bool__ = __nonzero__

        class WithLen(base_class):
            if base_class is Acquisition.Explicit:
                value = Acquisition.Acquired

            def __len__(self):
                return self.value

        class WithNothing(base_class):
            pass

        base.wbool = WithBool()
        base.wlen = WithLen()
        base.wnothing = WithNothing()

        self.assertEqual(bool(base.wbool), True)
        self.assertEqual(bool(base.wlen), True)
        self.assertEqual(bool(base.wnothing), True)

        base.value = 0
        self.assertFalse(base.wbool)
        self.assertFalse(base.wlen)

    def test_implicit_proxy_bool(self):
        self._check_bool()

    def test_explicit_proxy_bool(self):
        self._check_bool(base_class=Acquisition.Explicit)


class TestCompilation(unittest.TestCase):

    def test_compile(self):
        if IS_PYPY or IS_PURE:
            with self.assertRaises((AttributeError, ImportError)):
                from Acquisition import _Acquisition
        else:
            from Acquisition import _Acquisition
            self.assertTrue(hasattr(_Acquisition, 'AcquisitionCAPI'))


def test_suite():
    import os.path
    here = os.path.dirname(__file__)
    root = os.path.join(here, os.pardir, os.pardir)
    readme = os.path.join(root, 'README.rst')

    suites = [
        DocTestSuite(),
        unittest.makeSuite(TestCreatingWrappers),
        unittest.makeSuite(TestPickle),
        unittest.makeSuite(TestInterfaces),
        unittest.makeSuite(TestParentCircles),
        unittest.makeSuite(TestParent),
        unittest.makeSuite(TestAcquire),
        unittest.makeSuite(TestUnicode),
        unittest.makeSuite(TestProxying),
        unittest.makeSuite(TestCooperativeBase),
        unittest.makeSuite(TestCompilation),
    ]

    # This file is only available in a source checkout, skip it
    # when tests are run for an installed version.
    if os.path.isfile(readme):
        suites.append(DocFileSuite(readme, module_relative=False))

    return unittest.TestSuite(suites)
