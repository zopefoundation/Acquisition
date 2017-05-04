from __future__ import absolute_import, print_function

# pylint:disable=W0212,R0911,R0912


import os
import operator
import platform
import sys
import types
import weakref

import ExtensionClass

from zope.interface import classImplements

from .interfaces import IAcquirer
from .interfaces import IAcquisitionWrapper

IS_PYPY = getattr(platform, 'python_implementation', lambda: None)() == 'PyPy'
IS_PURE = 'PURE_PYTHON' in os.environ


class Acquired(object):
    "Marker for explicit acquisition"


_NOT_FOUND = object()  # marker

###
# Helper functions
###


def _has__of__(obj):
    """Check whether an object has an __of__ method for returning itself
    in the context of a container."""
    # It is necessary to check both the type (or we get into cycles)
    # as well as the presence of the method (or mixins of Base pre- or
    # post-class-creation as done in, e.g.,
    # zopefoundation/Persistence) can fail.
    return (isinstance(obj, ExtensionClass.Base) and
            hasattr(type(obj), '__of__'))


def _apply_filter(predicate, inst, name, result, extra, orig):
    return predicate(orig, inst, name, result, extra)


if sys.version_info < (3,):
    import copy_reg

    def _rebound_method(method, wrapper):
        """Returns a version of the method with self bound to `wrapper`"""
        if isinstance(method, types.MethodType):
            method = types.MethodType(method.im_func, wrapper, method.im_class)
        return method
    exec("""def _reraise(tp, value, tb=None):
    raise tp, value, tb
""")
else:  # pragma: no cover (python 2 is currently our reference)
    import copyreg as copy_reg

    def _rebound_method(method, wrapper):
        """Returns a version of the method with self bound to `wrapper`"""
        if isinstance(method, types.MethodType):
            method = types.MethodType(method.__func__, wrapper)
        return method

    def _reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

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
            result = ExplicitAcquisitionWrapper(
                wrapper._obj, wrapper._container)
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

    :raises AttributeError: If the wrapper has no parent or the
        attribute cannot be found.
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
                                   predicate=predicate,
                                   predicate_extra=predicate_extra,
                                   orig_object=orig_object,
                                   search_self=search_self,
                                   search_parent=search_parent,
                                   explicit=explicit,
                                   containment=containment)
        # XXX: Why does this branch of the C code check __of__,
        # but the next one doesn't?
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

        wrapper._container = ImplicitAcquisitionWrapper(
            wrapper._container, parent)
        return _Wrapper_findattr(wrapper._container, name,
                                 predicate=predicate,
                                 predicate_extra=predicate_extra,
                                 orig_object=orig_object,
                                 search_self=search_self,
                                 search_parent=search_parent,
                                 explicit=explicit,
                                 containment=containment)
    else:
        # The container is the end of the acquisition chain; if we
        # can't look up the attributes here, we can't look it up at all
        result = getattr(wrapper._container, name)
        if result is not Acquired:
            if predicate:
                if _apply_filter(predicate, wrapper._container, name,
                                 result, predicate_extra, orig_object):
                    return (result.__of__(wrapper)
                            if _has__of__(result) else result)
                else:
                    raise AttributeError(name)
            else:
                if _has__of__(result):
                    result = result.__of__(wrapper)
                return result

    # this line cannot be reached
    raise AttributeError(name)  # pragma: no cover


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
    :param bool containment: Use the innermost wrapper (`aq_inner`)
        for looking up the attribute.
    """

    orig_name = name
    if orig_object is None:
        orig_object = wrapper

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
                if _apply_filter(predicate, wrapper, orig_name,
                                 result, predicate_extra, orig_object):
                    return result
                else:
                    raise AttributeError(orig_name)
            return result
    elif name in ('__reduce__', '__reduce_ex__', '__getstate__',
                  '__of__', '__cmp__', '__eq__', '__ne__', '__lt__',
                  '__le__', '__gt__', '__ge__'):
        return object.__getattribute__(wrapper, orig_name)

    # If we're doing a containment search, replace the wrapper with aq_inner
    if containment:
        while isinstance(wrapper._obj, _Wrapper):
            wrapper = wrapper._obj

    if search_self and wrapper._obj is not None:
        if isinstance(wrapper._obj, _Wrapper):
            if wrapper is wrapper._obj:
                raise RuntimeError("Recursion detected in acquisition wrapper")
            try:
                result = _Wrapper_findattr(wrapper._obj, orig_name,
                                           predicate=predicate,
                                           predicate_extra=predicate_extra,
                                           orig_object=orig_object,
                                           search_self=True,
                                           search_parent=explicit or isinstance(wrapper._obj, ImplicitAcquisitionWrapper),  # NOQA
                                           explicit=explicit,
                                           containment=containment)
                if isinstance(result, types.MethodType):
                    result = _rebound_method(result, wrapper)
                elif _has__of__(result):
                    result = result.__of__(wrapper)
                return result
            except AttributeError:
                pass

        # deal with mixed __parent__ / aq_parent circles
        elif (isinstance(wrapper._container, _Wrapper) and
              wrapper._container._container is wrapper):
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
                                            predicate=predicate,
                                            predicate_extra=predicate_extra,
                                            orig_object=orig_object,
                                            explicit=True,
                                            containment=containment)

                if isinstance(result, types.MethodType):
                    result = _rebound_method(result, wrapper)
                elif _has__of__(result):
                    result = result.__of__(wrapper)

                if predicate:
                    if _apply_filter(predicate, wrapper, orig_name,
                                     result, predicate_extra, orig_object):
                        return result
                else:
                    return result

    # lookup has failed, acquire from the parent
    if search_parent and (not name.startswith('_') or explicit):
        return _Wrapper_acquire(wrapper, orig_name,
                                predicate=predicate,
                                predicate_extra=predicate_extra,
                                orig_object=orig_object,
                                explicit=explicit,
                                containment=containment)

    raise AttributeError(orig_name)


_NOT_GIVEN = object()  # marker
_OGA = object.__getattribute__

# Map from object types with slots to their generated, derived
# types (or None if no derived type is needed)
_wrapper_subclass_cache = weakref.WeakKeyDictionary()


def _make_wrapper_subclass_if_needed(cls, obj, container):
    # If the type of an object to be wrapped has __slots__, then we
    # must create a wrapper subclass that has descriptors for those
    # same slots. In this way, its methods that use object.__getattribute__
    # directly will continue to work, even when given an instance of _Wrapper
    if getattr(cls, '_Wrapper__DERIVED', False):
        return None
    type_obj = type(obj)
    wrapper_subclass = _wrapper_subclass_cache.get(type_obj, _NOT_GIVEN)
    if wrapper_subclass is _NOT_GIVEN:
        slotnames = copy_reg._slotnames(type_obj)
        if slotnames and not isinstance(obj, _Wrapper):
            new_type_dict = {'_Wrapper__DERIVED': True}

            def _make_property(slotname):
                return property(lambda s: getattr(s._obj, slotname),
                                lambda s, v: setattr(s._obj, slotname, v),
                                lambda s: delattr(s._obj, slotname))
            for slotname in slotnames:
                new_type_dict[slotname] = _make_property(slotname)
            new_type = type(cls.__name__ + '_' + type_obj.__name__,
                            (cls,),
                            new_type_dict)
        else:
            new_type = None
        wrapper_subclass = _wrapper_subclass_cache[type_obj] = new_type

    return wrapper_subclass


class _Wrapper(ExtensionClass.Base):
    __slots__ = ('_obj', '_container', '__dict__')
    _IS_IMPLICIT = None

    def __new__(cls, obj, container):
        wrapper_subclass = _make_wrapper_subclass_if_needed(cls, obj, container)  # NOQA
        if wrapper_subclass:
            inst = wrapper_subclass(obj, container)
        else:
            inst = super(_Wrapper, cls).__new__(cls)
        inst._obj = obj
        inst._container = container
        if hasattr(obj, '__dict__') and not isinstance(obj, _Wrapper):
            # Make our __dict__ refer to the same dict as the other object,
            # so that if it has methods that use `object.__getattribute__`
            # they still work. Note that because we have slots,
            # we won't interfere with the contents of that dict.
            object.__setattr__(inst, '__dict__', obj.__dict__)
        return inst

    def __init__(self, obj, container):
        super(_Wrapper, self).__init__()
        self._obj = obj
        self._container = container

    def __setattr__(self, name, value):
        if name == '__parent__' or name == 'aq_parent':
            object.__setattr__(self, '_container', value)
            return
        if name == '_obj' or name == '_container':
            # should only happen at init time
            object.__setattr__(self, name, value)
            return

        # If we are wrapping something, unwrap passed in wrappers
        if self._obj is None:
            raise AttributeError(
                'Attempt to set attribute on empty acquisition wrapper')

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
            return _OGA(self, name)
        if (_OGA(self, '_obj') is not None or
                _OGA(self, '_container') is not None):
            return _Wrapper_findattr(self, name, None, None, None, True,
                                     type(self)._IS_IMPLICIT, False, False)
        return _OGA(self, name)

    def __of__(self, parent):
        # Based on __of__ in the C code;
        # simplify a layer of wrapping.

        # We have to call the raw __of__ method or we recurse on our
        # own lookup (the C code does not have this issue, it can use
        # the wrapped __of__ method because it gets here via the
        # descriptor code path)...
        wrapper = self._obj.__of__(parent)
        if (not isinstance(wrapper, _Wrapper) or
                not isinstance(wrapper._container, _Wrapper)):
            return wrapper
        # but the returned wrapper should be based on this object's
        # wrapping chain
        wrapper._obj = self

        while (isinstance(wrapper._obj, _Wrapper) and
               (wrapper._obj._container is wrapper._container._obj)):
            # Since we mutate the wrapper as we walk up, we must copy
            # XXX: This comes from the C implementation. Do we really need to
            # copy?
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
                                     predicate=filter,
                                     predicate_extra=extra,
                                     orig_object=self,
                                     search_self=True,
                                     search_parent=explicit or type(self)._IS_IMPLICIT,  # NOQA
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

    # Equality and comparisons

    def __hash__(self):
        # The C implementation doesn't pass the wrapper
        # to any __hash__ that the object implements,
        # so it can't access derived attributes.
        # (If that changes, just add this to __unary_special_methods__
        # and remove this method)
        return hash(self._obj)

    # The C implementation forces all comparisons through the
    # __cmp__ method, if it's implemented. If it's not implemented,
    # then comparisons are based strictly on the memory addresses
    # of the underlying object (aq_base). We could mostly emulate
    # this behaviour on Python 2, but on Python 3 __cmp__ is gone,
    # so users won't have an expectation to write it.
    # Because users have never had an expectation that the rich comparison
    # methods would be called on their wrapped objects (and so would not be
    # accessing acquired attributes there), we can't/don't want to start
    # proxying to them?
    # For the moment, we settle for an emulation of the C behaviour:
    # define __cmp__ the same way, and redirect the rich comparison operators
    # to it. (Note that these attributes are also hardcoded in getattribute)
    def __cmp__(self, other):
        aq_self = self._obj
        if hasattr(type(aq_self), '__cmp__'):
            return _rebound_method(aq_self.__cmp__, self)(other)

        my_base = aq_base(self)
        other_base = aq_base(other)
        if my_base is other_base:
            return 0
        return -1 if id(my_base) < id(other_base) else 1

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    # Special methods looked up by the type of self._obj,
    # but which must have the wrapper as self when called

    def __nonzero__(self):
        aq_self = self._obj
        type_aq_self = type(aq_self)
        nonzero = getattr(type_aq_self, '__nonzero__', None)
        if nonzero is None:
            # Py3 bool?
            nonzero = getattr(type_aq_self, '__bool__', None)
        if nonzero is None:
            # a len?
            nonzero = getattr(type_aq_self, '__len__', None)
        if nonzero:
            return bool(nonzero(self))  # Py3 is strict about the return type
        # If nothing was defined, then it's true
        return True
    __bool__ = __nonzero__

    def __unicode__(self):
        f = getattr(self.aq_self, '__unicode__',
                    getattr(self.aq_self, '__str__', object.__str__))
        return _rebound_method(f, self)()

    def __repr__(self):
        aq_self = self._obj
        try:
            return _rebound_method(aq_self.__repr__, self)()
        except (AttributeError, TypeError):
            return repr(aq_self)

    def __str__(self):
        aq_self = self._obj
        try:
            return _rebound_method(aq_self.__str__, self)()
        except (AttributeError, TypeError):  # pragma: no cover (Only Py3)
            return str(aq_self)

    __binary_special_methods__ = [
        # general numeric
        '__add__',
        '__sub__',
        '__mul__',
        '__matmul__',
        '__floordiv__',  # not implemented in C
        '__mod__',
        '__divmod__',
        '__pow__',
        '__lshift__',
        '__rshift__',
        '__and__',
        '__xor__',
        '__or__',

        # division; only one of these will be used at any one time
        '__truediv__',
        '__div__',

        # reflected numeric
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

        # in place numeric
        '__iadd__',
        '__isub__',
        '__imul__',
        '__imatmul__',
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
        '__coerce__',

        # container
        '__delitem__',
    ]

    __unary_special_methods__ = [
        # arithmetic
        '__neg__',
        '__pos__',
        '__abs__',
        '__invert__',

        # conversion
        '__complex__',
        '__int__',
        '__long__',
        '__float__',
        '__oct__',
        '__hex__',
        '__index__',
        # '__len__',

        # strings are special
        # '__repr__',
        # '__str__',
    ]

    for _name in __binary_special_methods__:
        def _make_op(_name):
            def op(self, other):
                aq_self = self._obj
                return getattr(type(aq_self), _name)(self, other)
            return op
        locals()[_name] = _make_op(_name)

    for _name in __unary_special_methods__:
        def _make_op(_name):
            def op(self):
                aq_self = self._obj
                return getattr(type(aq_self), _name)(self)
            return op
        locals()[_name] = _make_op(_name)

    del _make_op
    del _name

    # Container protocol

    def __len__(self):
        # if len is missing, it should raise TypeError
        # (AttributeError is acceptable under Py2, but Py3
        # breaks list conversion if AttributeError is raised)
        try:
            l = getattr(type(self._obj), '__len__')
        except AttributeError:
            raise TypeError('object has no len()')
        else:
            return l(self)

    def __iter__(self):
        # For things that provide either __iter__ or just __getitem__,
        # we need to be sure that the wrapper is provided as self
        if hasattr(self._obj, '__iter__'):
            return _rebound_method(self._obj.__iter__, self)()
        if hasattr(self._obj, '__getitem__'):
            # Unfortunately we cannot simply call iter(self._obj)
            # and rebind im_self like we do above: the Python runtime
            # complains:
            # (TypeError: 'sequenceiterator' expected, got 'Wrapper' instead)

            class WrapperIter(object):
                __slots__ = ('_wrapper',)

                def __init__(self, o):
                    self._wrapper = o

                def __getitem__(self, i):
                    return self._wrapper.__getitem__(i)
            it = WrapperIter(self)
            return iter(it)

        return iter(self._obj)

    def __contains__(self, item):
        # First, if the type of the object defines __contains__ then
        # use it
        aq_self = self._obj
        aq_contains = getattr(type(aq_self), '__contains__', None)
        if aq_contains:
            return aq_contains(self, item)
        # Next, we should attempt to iterate like the interpreter;
        # but the C code doesn't do this, so we don't either.
        # return item in iter(self)
        raise AttributeError('__contains__')

    def __setitem__(self, key, value):
        aq_self = self._obj
        try:
            setter = type(aq_self).__setitem__
        except AttributeError:
            raise AttributeError("__setitem__")  # doctests care about the name
        else:
            setter(self, key, value)

    def __getitem__(self, key):
        if isinstance(key, slice) and hasattr(operator, 'getslice'):
            # Only on Python 2
            # XXX: This is probably not proxying correctly, but the existing
            # tests pass with this behaviour
            return operator.getslice(
                self._obj,
                key.start if key.start is not None else 0,
                key.stop if key.stop is not None else sys.maxint)

        aq_self = self._obj
        try:
            getter = type(aq_self).__getitem__
        except AttributeError:
            raise AttributeError("__getitem__")  # doctests care about the name
        else:
            return getter(self, key)

    def __call__(self, *args, **kwargs):
        try:
            # Note we look this up on the completely unwrapped
            # object, so as not to get a class
            call = getattr(self.aq_base, '__call__')
        except AttributeError:  # pragma: no cover
            # A TypeError is what the interpreter raises;
            # AttributeError is allowed to percolate through the
            # C proxy
            raise TypeError('object is not callable')
        else:
            return _rebound_method(call, self)(*args, **kwargs)


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
            return super(_Acquirer, self).__getattribute__(name)
        except AttributeError:
            # the doctests have very specific error message
            # requirements (but at least we can preserve the traceback)
            _, _, tb = sys.exc_info()
            try:
                _reraise(AttributeError, AttributeError(name), tb)
            finally:
                del tb

    def __of__(self, context):
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
    return getattr(obj, '__parent__', None)


def aq_chain(obj, containment=False):
    result = []

    while True:
        if isinstance(obj, _Wrapper):
            if obj._obj is not None:
                if containment:
                    while isinstance(obj._obj, _Wrapper):
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
        result = result._obj
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

    result = obj._obj
    while isinstance(result, _Wrapper):
        obj = result
        result = result._obj
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
            return True

        if inner:
            self = aq_inner(next)
            if self is None:  # pragma: no cover
                # This branch is normally impossible to hit,
                # it just mirrors a check in C
                break
        else:
            self = next

        next = aq_parent(self)
        if next is None:
            break

    return False


if not (IS_PYPY or IS_PURE):  # pragma: no cover
    # Make sure we can import the C extension of our dependency.
    from ExtensionClass import _ExtensionClass  # NOQA
    from ._Acquisition import *  # NOQA

classImplements(Explicit, IAcquirer)
classImplements(ExplicitAcquisitionWrapper, IAcquisitionWrapper)
classImplements(Implicit, IAcquirer)
classImplements(ImplicitAcquisitionWrapper, IAcquisitionWrapper)
