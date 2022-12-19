##############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Acquisition interfaces.

For details, see
`README.rst <https://github.com/zopefoundation/Acquisition#readme>`_
"""

from zope.interface import Attribute
from zope.interface import Interface


class IAcquirer(Interface):

    """Acquire attributes from containers.
    """

    def __of__(context):
        """Get the object in a context.
        """


class IAcquisitionWrapper(Interface):

    """Wrapper object for acquisition.

    A wrapper encapsulates an object, ``aq_self``, and a parent ``aq_parent``.
    Both of them can in turn be wrappers.

    Informally, the wrapper indicates that the object has been
    accessed via the parent.

    The wrapper essentially behaves like the object but may (in
    some cases) also show behavior of the parent.

    A wrapper is called an "inner wrapper" if its object is not
    itself a wrapper. In this case, the parent is called the object's
    container.

    There are 2 kinds of wrappers - implicit and explicit wrappers:
    Implicit wrappers search attributes in the parent by default
    in contrast to explicit wrappers.
    """

    def aq_acquire(name, filter=None, extra=None, explicit=True, default=0,
                   containment=False):
        """Get an attribute, acquiring it if necessary.

        The search first searches in the object and if this search
        is unsuccessful, it may continue the search in the parent.

        When the attribute is found and *filter* is not None,
        *filter* is called with the following parameters:

          self
            the object ``aq_acquire`` was called on

          container
            the container the attribute was found in

          *name*
            ``aq_acquire`` parameter

          value
            the attribute value
            
          *extra*
            ``aq_acquire`` parameter

        If the call returns ``True``, *value* is returned,
        otherwise the search continues.

        *explicit* controls whether the attribute is also searched
        in the parent. This is always the case for implicit
        wrappers. For explicit wrappers, the parent
        is only searched if *explicit* is true.

        *default* controls what happens when the attribute was not found.
        In this case, *default* is returned when it was passed;
        otherwise, ``AttributeError`` is raised.
        (Note: in contradiction to the signature above, *default* has
        actually a "not given" marker as default, not ``0``).

        *containment* controls whether the search is restricted
        to the "containment hierarchy". In the corresponding search,
        the parent of a wrapper *w* is only searched if *w* is an inner
        wrapper, i.e. if the object of *w* is not a wrapper and the parent
        is the object's container.
        """

    def aq_inContextOf(obj, inner=1):
        """Test whether the object is currently in the context of the argument.
        """

    aq_base = Attribute(
        """Get the object unwrapped.""")

    aq_parent = Attribute(
        """Get the parent of an object.""")

    aq_self = Attribute(
        """Get the object with the outermost wrapper removed.""")

    aq_inner = Attribute(
        """Get the object with all but the innermost wrapper removed.""")

    aq_chain = Attribute(
        """Get a list of objects in the acquisition environment.""")

    aq_explicit = Attribute(
        """Get the object with an explicit acquisition wrapper.""")
