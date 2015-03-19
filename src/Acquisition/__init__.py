from __future__ import absolute_import, print_function

# pylint:disable=W0212,R0911,R0912

import os
import sys
import types

import ExtensionClass

from zope.interface import classImplements

from .interfaces import IAcquirer
from .interfaces import IAcquisitionWrapper
from ._proxy import PyProxyBase


class Acquired(object):
    "Marker for explicit acquisition"


_NOT_FOUND = object()  # marker

###
# Helper functions
###


def _has__of__(obj):
    """Check whether an object has an __of__ method for returning itself
    in the context of a container."""
    # Note specifically this is a type check, not duck typing, or
    # we get into cycles
    return isinstance(obj, ExtensionClass.Base)


def _apply_filter(predicate, inst, name, result, extra, orig):
    return predicate(orig, inst, name, result, extra)

if sys.version_info < (3,):
    def _rebound_method(method, wrapper):
        """Returns a version of the method with self bound to `wrapper`"""
        if isinstance(method, types.MethodType):
            method = types.MethodType(method.im_func, wrapper, method.im_class)
        return method
else:
    def _rebound_method(method, wrapper):
        """Returns a version of the method with self bound to `wrapper`"""
        if isinstance(method, types.MethodType):
            method = types.MethodType(method.__func__, wrapper)
        return method

###
# Wrapper object protocol, mostly ported from C directly
###


def _Wrapper_findspecial(wrapper, name):
    """
    Looks up the special acquisition attributes of an object.
    :param str name: The attribute to find, with 'aq' already stripped.
    """

    result = _NOT_FOUND

    if name == 'base':
        result = wrapper._obj
        while isinstance(result, _Wrapper) and result._obj is not None:
            result = result._obj
    elif name == 'parent':
        result = wrapper._container
    elif name == 'self':
        result = wrapper._obj
    elif name == 'explicit':
        if type(wrapper)._IS_IMPLICIT:
            result = ExplicitAcquisitionWrapper(wrapper._obj, wrapper._container)
        else:
            result = wrapper
    elif name == 'acquire':
        result = object.__getattribute__(wrapper, 'aq_acquire')
    elif name == 'chain':
        # XXX: C has a second implementation here
        result = aq_chain(wrapper)
    elif name == 'inContextOf':
        result = object.__getattribute__(wrapper, 'aq_inContextOf')
    elif name == 'inner':
        # XXX: C has a second implementation here
        result = aq_inner(wrapper)
    elif name == 'uncle':
        result = 'Bob'

    return result


def _Wrapper_acquire(wrapper, name,
                     predicate=None, predicate_extra=None,
                     orig_object=None,
                     explicit=True, containment=True):
    """
    Attempt to acquire the `name` from the parent of the wrapper.

    :raises AttributeError: If the wrapper has no parent or the attribute cannot
        be found.
    """

    if wrapper._container is None:
        raise AttributeError(name)

    search_self = True
    search_parent = True

    # If the container has an acquisition wrapper itself, we'll use
    # _Wrapper_findattr to progress further
    if isinstance(wrapper._container, _Wrapper):
        if isinstance(wrapper._obj, _Wrapper):
            # try to optimize search by recognizing repeated objects in path
            if wrapper._obj._container is wrapper._container._container:
                search_parent = False
            elif wrapper._obj._container is wrapper._container._obj:
                search_self = False

        # Don't search the container when the container of the container
        # is the same object as `wrapper`
        if wrapper._container._container is wrapper._obj:
            search_parent = False
            containment = True
        result = _Wrapper_findattr(wrapper._container, name,
                                   predicate=predicate, predicate_extra=predicate_extra,
                                   orig_object=orig_object,
                                   search_self=search_self,
                                   search_parent=search_parent,
                                   explicit=explicit, containment=containment)
        # XXX: Why does this branch of the C code check __of__, but the next one
        # doesn't?
        if _has__of__(result):
            result = result.__of__(wrapper)
        return result

    # If the container has a __parent__ pointer, we create an
    # acquisition wrapper for it accordingly.  Then we can proceed
    # with Wrapper_findattr, just as if the container had an
    # acquisition wrapper in the first place (see above).
    # NOTE: This mutates the wrapper
    elif hasattr(wrapper._container, '__parent__'):
        parent = wrapper._container.__parent__
        # Don't search the container when the parent of the parent
        # is the same object as 'self'
        if parent is wrapper._obj:
            search_parent = False
        elif isinstance(parent, _Wrapper) and parent._obj is wrapper._obj:
            # XXX: C code just does parent._obj, assumes its a wrapper
            search_parent = False

        wrapper._container = ImplicitAcquisitionWrapper(wrapper._container, parent)
        return _Wrapper_findattr(wrapper._container, name,
                                 predicate=predicate, predicate_extra=predicate_extra,
                                 orig_object=orig_object,
                                 search_self=search_self,
                                 search_parent=search_parent,
                                 explicit=explicit, containment=containment)
    else:
        # The container is the end of the acquisition chain; if we
        # can't look up the attributes here, we can't look it up at all
        result = getattr(wrapper._container, name)
        if result is not Acquired:
            if predicate:
                if _apply_filter(predicate, wrapper._container, name, result, predicate_extra, orig_object):
                    if _has__of__(result):
                        result = result.__of__(wrapper)
                    return result
                else:
                    raise AttributeError(name)
            else:
                if _has__of__(result):
                    result = result.__of__(wrapper)
                return result

    raise AttributeError(name)


def _Wrapper_findattr(wrapper, name,
                      predicate=None, predicate_extra=None,
                      orig_object=None,
                      search_self=True, search_parent=True,
                      explicit=True, containment=True):
    """
    Search the `wrapper` object for the attribute `name`.

    :param bool search_self: Search `wrapper.aq_self` for the attribute.
    :param bool search_parent: Search `wrapper.aq_parent` for the attribute.
    :param bool explicit: Explicitly acquire the attribute from the parent
        (should be assumed with implicit wrapper)
    :param bool containment: Use the innermost wrapper (`aq_inner`) for looking up
        the attribute.
    """
    orig_name = name
    if orig_object is None:
        orig_object = wrapper

    # Trivial port of the C function

    # First, special names
    if name.startswith('aq') or name == '__parent__':
        # __parent__ is an alias of aq_parent
        if name == '__parent__':
            name = 'parent'
        else:
            name = name[3:]

        result = _Wrapper_findspecial(wrapper, name)
        if result is not _NOT_FOUND:
            if predicate:
                return result if _apply_filter(predicate, wrapper, orig_name, result, predicate_extra, orig_object) else None
            return result
    elif name in ('__reduce__', '__reduce_ex__', '__getstate__', '__of__'):
        return object.__getattribute__(wrapper, orig_name)

    # If we're doing a containment search, replace the wrapper with aq_inner
    if containment:
        while wrapper._obj is not None and isinstance(wrapper._obj, _Wrapper):
            wrapper = wrapper._obj

    if search_self and wrapper._obj is not None:
        if isinstance(wrapper._obj, _Wrapper):
            if wrapper is wrapper._obj:
                raise RuntimeError("Recursion detected in acquisition wrapper")
            try:
                result = _Wrapper_findattr(wrapper._obj, orig_name,
                                           predicate=predicate, predicate_extra=predicate_extra,
                                           orig_object=orig_object,
                                           search_self=True,
                                           search_parent=explicit or isinstance(wrapper._obj, ImplicitAcquisitionWrapper),
                                           explicit=explicit, containment=containment)
                if isinstance(result, types.MethodType):
                    result = _rebound_method(result, wrapper)
                elif _has__of__(result):
                    result = result.__of__(wrapper)
                return result
            except AttributeError:
                pass

        # deal with mixed __parent__ / aq_parent circles
        elif (isinstance(wrapper._container, _Wrapper)
              and wrapper._container._container is wrapper):
            raise RuntimeError("Recursion detected in acquisition wrapper")
        else:
            # normal attribute lookup
            try:
                result = getattr(wrapper._obj, orig_name)
            except AttributeError:
                pass
            else:
                if result is Acquired:
                    return _Wrapper_acquire(wrapper, orig_name,
                                            predicate=predicate, predicate_extra=predicate_extra,
                                            orig_object=orig_object,
                                            explicit=True,
                                            containment=containment)

                if isinstance(result, types.MethodType):
                    result = _rebound_method(result, wrapper)
                elif _has__of__(result):
                    result = result.__of__(wrapper)

                if predicate:
                    if _apply_filter(predicate, wrapper, orig_name, result, predicate_extra, orig_object):
                        return result
                else:
                    return result

    # lookup has failed, acquire from the parent
    if search_parent and (not name.startswith('_') or explicit):
        return _Wrapper_acquire(wrapper, orig_name,
                                predicate=predicate, predicate_extra=predicate_extra,
                                orig_object=orig_object,
                                explicit=explicit,
                                containment=containment)

    raise AttributeError(orig_name)


_NOT_GIVEN = object()  # marker


class _Wrapper(PyProxyBase):
    __slots__ = ('_container',)
    _IS_IMPLICIT = None

    def __new__(cls, obj, container):
        inst = PyProxyBase.__new__(cls, obj)
        inst._container = container
        return inst

    def __init__(self, obj, container):
        PyProxyBase.__init__(self, obj)
        self._obj = obj
        self._container = container

    def __setattr__(self, name, value):
        if name == '__parent__' or name == 'aq_parent':
            object.__setattr__(self, '_container', value)
            return
        if name == '_obj' or name == '_container':  # should only happen at init time
            object.__setattr__(self, name, value)
            return

        # If we are wrapping something, unwrap passed in wrappers
        if self._obj is None:
            raise AttributeError("Attempt to set attribute on empty acquisition wrapper")

        while value is not None and isinstance(value, _Wrapper):
            value = value._obj

        setattr(self._obj, name, value)

    def __delattr__(self, name):
        if name == '__parent__' or name == 'aq_parent':
            self._container = None
        else:
            delattr(self._obj, name)

    def __getattribute__(self, name):
        if name in ('_obj', '_container'):
            return object.__getattribute__(self, name)
        if self._obj is not None or self._container is not None:
            return _Wrapper_findattr(self, name, None, None, None,
                                     True, type(self)._IS_IMPLICIT, False, False)
        return object.__getattribute__(self, name)

    def __of__(self, parent):
        # Based on __of__ in the C code;
        # simplify a layer of wrapping.

        # We have to call the raw __of__ method or we recurse on
        # our own lookup (the C code does not have this issue, it can use
        # the wrapped __of__ method because it gets here via the descriptor code
        # path)...
        wrapper = self._obj.__of__(parent)
        if not isinstance(wrapper, _Wrapper) or not isinstance(wrapper._container, _Wrapper):
            return wrapper
        # but the returned wrapper should be based on this object's
        # wrapping chain
        wrapper._obj = self

        while isinstance(wrapper._obj, _Wrapper) \
              and (wrapper._obj._container is wrapper._container._obj):
            # Since we mutate the wrapper as we walk up, we must copy
            wrapper = type(wrapper)(wrapper._obj, wrapper._container)
            wrapper._obj = wrapper._obj._obj
        return wrapper

    def aq_acquire(self, name,
                   filter=None, extra=None,
                   explicit=True,
                   default=_NOT_GIVEN,
                   containment=False):
        try:
            return _Wrapper_findattr(self, name,
                                     predicate=filter, predicate_extra=extra,
                                     orig_object=self,
                                     search_self=True,
                                     search_parent=explicit or type(self)._IS_IMPLICIT,
                                     explicit=explicit,
                                     containment=containment)
        except AttributeError:
            if default is _NOT_GIVEN:
                raise
            return default

    acquire = aq_acquire

    def aq_inContextOf(self, o, inner=True):
        return aq_inContextOf(self, o, inner=inner)

    # Wrappers themselves are not picklable, but if the underlying
    # object has a _p_oid, then the __getnewargs__ method is allowed
    def __reduce__(self, *args):
        raise TypeError("Can't pickle objects in acquisition wrappers.")
    __reduce_ex__ = __reduce__
    __getstate__ = __reduce__

    def __getnewargs__(self):
        return ()

    # Methods looked up by the type of self._obj
    # NOTE: This is probably incomplete

    def __unicode__(self):
        f = getattr(self.aq_self, '__unicode__',
                    getattr(self.aq_self, '__str__', object.__str__))
        return _rebound_method(f, self)()

    def __repr__(self):
        aq_self = self._obj
        return type(aq_self).__repr__(aq_self)

    def __str__(self):
        aq_self = self._obj
        return type(aq_self).__str__(aq_self)

    def __iter__(self):
        # For things that provide either __iter__ or just __getitem__,
        # we need to be sure that the wrapper is provided as self
        if hasattr(self._obj, '__iter__'):
            return _rebound_method(self._obj.__iter__, self)()
        if hasattr(self._obj, '__getitem__'):
            # Unfortunately we cannot simply call iter(self._obj)
            # and rebind im_self like we do above: the Python runtime
            # complains (TypeError: 'sequenceiterator' expected, got 'Wrapper' instead)

            class WrapperIter(object):
                __slots__ = ('_wrapper',)

                def __init__(self, o):
                    self._wrapper = o

                def __getitem__(self, i):
                    return self._wrapper.__getitem__(i)
            it = WrapperIter(self)
            return iter(it)

        return iter(self._obj)


class ImplicitAcquisitionWrapper(_Wrapper):
    _IS_IMPLICIT = True


class ExplicitAcquisitionWrapper(_Wrapper):
    _IS_IMPLICIT = False

    def __getattribute__(self, name):
        # Special case backwards-compatible acquire method
        if name == 'acquire':
            return object.__getattribute__(self, name)

        return _Wrapper.__getattribute__(self, name)


class _Acquirer(ExtensionClass.Base):

    def __getattribute__(self, name):
        try:
            return ExtensionClass.Base.__getattribute__(self, name)
        except AttributeError:
            # the doctests have very specific error message
            # requirements
            raise AttributeError(name)

    def __of__(self, context):
        # Workaround ExtensionClass bug #3
        try:
            if not isinstance(self, _Wrapper) \
               and self is object.__getattribute__(context, '__parent__'):
                return self
        except AttributeError:
            pass
        return type(self)._Wrapper(self, context)


class Implicit(_Acquirer):
    _Wrapper = ImplicitAcquisitionWrapper
ImplicitAcquisitionWrapper._Wrapper = ImplicitAcquisitionWrapper


class Explicit(_Acquirer):
    _Wrapper = ExplicitAcquisitionWrapper
ExplicitAcquisitionWrapper._Wrapper = ExplicitAcquisitionWrapper

###
# Exported module functions
###


def aq_acquire(obj, name,
               filter=None, extra=None,
               explicit=True,
               default=_NOT_GIVEN,
               containment=False):
    if isinstance(obj, _Wrapper):
        return obj.aq_acquire(name,
                              filter=filter, extra=extra,
                              default=default,
                              explicit=explicit or type(obj)._IS_IMPLICIT,
                              containment=containment)

    # Does it have a parent, or do we have a filter?
    # Then go through the acquisition code
    if hasattr(obj, '__parent__') or filter is not None:
        parent = getattr(obj, '__parent__', None)
        return aq_acquire(ImplicitAcquisitionWrapper(obj, parent),
                          name,
                          filter=filter, extra=extra,
                          default=default,
                          explicit=explicit,
                          containment=containment)

    # no parent and no filter, simple case
    try:
        return getattr(obj, name)
    except AttributeError:
        if default is _NOT_GIVEN:
            raise AttributeError(name)  # doctests are strict
        return default


def aq_parent(obj):
    # needs to be safe to call from __getattribute__ of a wrapper
    # and reasonably fast
    if isinstance(obj, _Wrapper):
        return object.__getattribute__(obj, '_container')
    # if not a wrapper, deal with the __parent__
    # XXX have to implement the mixed checking
    return getattr(obj, '__parent__', None)


def aq_chain(obj, containment=False):
    # This is a straight port of the C code,
    # but it doesn't work for the containment branch...
    # not that I really understand what that branch is supposed to do
    def isWrapper(self):
        return isinstance(self, _Wrapper)

    result = []

    while True:
        if isWrapper(obj):
            if obj._obj is not None:
                if containment:
                    while obj._obj is not None and isWrapper(obj._obj):
                        obj = obj._obj
                result.append(obj)
            if obj._container is not None:
                obj = obj._container
                continue
        else:
            result.append(obj)
            obj = getattr(obj, '__parent__', None)
            if obj is not None:
                continue

        break

    return result


def aq_base(obj):
    result = obj
    while isinstance(result, _Wrapper):
        result = result.aq_self
    return result


def aq_get(obj, name, default=_NOT_GIVEN, containment=False):

    # Not wrapped. If we have a __parent__ pointer, create a wrapper
    # and go as usual
    if not isinstance(obj, _Wrapper) and hasattr(obj, '__parent__'):
        obj = ImplicitAcquisitionWrapper(obj, obj.__parent__)

    try:
        # We got a wrapped object, business as usual
        return (_Wrapper_findattr(obj, name, None, None, obj,
                                  True, True, True, containment)
                if isinstance(obj, _Wrapper)
                # ok, plain getattr
                else getattr(obj, name))
    except AttributeError:
        if default is _NOT_GIVEN:
            raise
        return default


def aq_inner(obj):
    if not isinstance(obj, _Wrapper):
        return obj

    result = obj.aq_self
    while isinstance(result, _Wrapper):
        obj = result
        result = result.aq_self
    result = obj
    return result


def aq_self(obj):
    if isinstance(obj, _Wrapper):
        return obj.aq_self
    return obj


def aq_inContextOf(self, o, inner=True):
    next = self
    o = aq_base(o)

    while True:
        if aq_base(next) is o:
            return 1

        if inner:
            self = aq_inner(next)
            if self is None:
                break
        else:
            self = next

        next = aq_parent(self)
        if next is None:
            break

    return 0


if 'PURE_PYTHON' not in os.environ:  # pragma no cover
    try:
        from _Acquisition import *
    except ImportError:
        pass

classImplements(Explicit, IAcquirer)
classImplements(ExplicitAcquisitionWrapper, IAcquisitionWrapper)
classImplements(Implicit, IAcquirer)
classImplements(ImplicitAcquisitionWrapper, IAcquisitionWrapper)
