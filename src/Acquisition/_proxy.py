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
"""Taken from zope.proxy to support acquisition wrappers.
"""
import operator
import pickle
import sys

import ExtensionClass

_MARKER = object()

class PyProxyBase(ExtensionClass.Base):
    """Reference implementation.
    """
    __slots__ = ('_obj', )

    def __new__(cls, value):
        inst = super(PyProxyBase, cls).__new__(cls)
        inst._obj = value
        return inst

    def __init__(self, obj):
        self._obj = obj

    def __call__(self, *args, **kw):
        return self._obj(*args, **kw)

    def __repr__(self):
        return repr(self._obj)

    def __str__(self):
        return str(self._obj)

    def __unicode__(self):
        return unicode(self._obj)

    def __reduce__(self): #pragma NO COVER  (__reduce_ex__ prevents normal)
        raise pickle.PicklingError

    def __reduce_ex__(self, proto):
        raise pickle.PicklingError

    # Rich comparison protocol
    def __lt__(self, other):
        return self._obj < other

    def __le__(self, other):
        return self._obj <= other

    def __eq__(self, other):
        return self._obj == other

    def __ne__(self, other):
        return self._obj != other

    def __gt__(self, other):
        return self._obj > other

    def __ge__(self, other):
        return self._obj >= other

    def __nonzero__(self):
        return bool(self._obj)
    __bool__ = __nonzero__ # Python3 compat

    def __hash__(self):
        return hash(self._obj)

    # Attribute protocol
    # Left for the _Wrapper subclass

    # Container protocols

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, key):
        if isinstance(key, slice):
            if isinstance(self._obj, (list, tuple)):
                return self._obj[key]
            start, stop = key.start, key.stop
            if start is None:
                start = 0
            if start < 0:
                start += len(self._obj)
            if stop is None:
                stop = getattr(sys, 'maxint', None) # PY2
            elif stop < 0:
                stop += len(self._obj)
            if hasattr(operator, 'setslice'): # PY2
                return operator.getslice(self._obj, start, stop)
            return self._obj[start:stop]
        return self._obj[key]

    def __setitem__(self, key, value):
        self._obj[key] = value

    def __delitem__(self, key):
        del self._obj[key]

    def __iter__(self):
        # This handles a custom __iter__ and generator support at the same time.
        return iter(self._obj)

    def next(self):
        # Called when we wrap an iterator itself.
        return self._obj.next()

    def __next__(self): #pragma NO COVER Python3
        return self._obj.__next__()

    # Python 2.7 won't let the C wrapper support __reversed__ :(
    #def __reversed__(self):
    #    return reversed(self._obj)

    def __contains__(self, item):
        return item in self._obj

    # Numeric protocol:  unary operators
    def __neg__(self):
        return -self._obj

    def __pos__(self):
        return +self._obj

    def __abs__(self):
        return abs(self._obj)

    def __invert__(self):
        return ~self._obj

    # Numeric protocol:  unary conversions
    def __complex__(self):
        return complex(self._obj)

    def __int__(self):
        return int(self._obj)

    def __long__(self):
        return long(self._obj)

    def __float__(self):
        return float(self._obj)

    def __oct__(self):
        return oct(self._obj)

    def __hex__(self):
        return hex(self._obj)

    def __index__(self):
        return operator.index(self._obj)

    # Numeric protocol:  binary coercion
    def __coerce__(self, other):
        left, right = coerce(self._obj, other)
        if left == self._obj and type(left) is type(self._obj):
            left = self
        return left, right

    # Numeric protocol:  binary arithmetic operators
    def __add__(self, other):
        return self._obj + other

    def __sub__(self, other):
        return self._obj - other

    def __mul__(self, other):
        return self._obj * other

    def __floordiv__(self, other):
        return self._obj // other

    def __truediv__(self, other): #pragma NO COVER
        # Only one of __truediv__ and __div__ is meaningful at any one time.
        return self._obj / other

    def __div__(self, other): #pragma NO COVER
        # Only one of __truediv__ and __div__ is meaningful at any one time.
        return self._obj / other

    def __mod__(self, other):
        return self._obj % other

    def __divmod__(self, other):
        return divmod(self._obj, other)

    def __pow__(self, other, modulus=None):
        if modulus is None:
            return pow(self._obj, other)
        return pow(self._obj, other, modulus)

    def __radd__(self, other):
        return other + self._obj

    def __rsub__(self, other):
        return other - self._obj

    def __rmul__(self, other):
        return other * self._obj

    def __rfloordiv__(self, other):
        return other // self._obj

    def __rtruediv__(self, other): #pragma NO COVER
        # Only one of __rtruediv__ and __rdiv__ is meaningful at any one time.
        return other / self._obj

    def __rdiv__(self, other): #pragma NO COVER
        # Only one of __rtruediv__ and __rdiv__ is meaningful at any one time.
        return other / self._obj

    def __rmod__(self, other):
        return other % self._obj

    def __rdivmod__(self, other):
        return divmod(other, self._obj)

    def __rpow__(self, other, modulus=None):
        if modulus is None:
            return pow(other, self._obj)
        # We can't actually get here, because we can't lie about our type()
        return pow(other, self._obj, modulus) #pragma NO COVER

    # Numeric protocol:  binary bitwise operators
    def __lshift__(self, other):
        return self._obj << other

    def __rshift__(self, other):
        return self._obj >> other

    def __and__(self, other):
        return self._obj & other

    def __xor__(self, other):
        return self._obj ^ other

    def __or__(self, other):
        return self._obj | other

    def __rlshift__(self, other):
        return other << self._obj

    def __rrshift__(self, other):
        return other >> self._obj

    def __rand__(self, other):
        return other & self._obj

    def __rxor__(self, other):
        return other ^ self._obj

    def __ror__(self, other):
        return other | self._obj

    # Numeric protocol:  binary in-place operators
    def __iadd__(self, other):
        self._obj += other
        return self

    def __isub__(self, other):
        self._obj -= other
        return self

    def __imul__(self, other):
        self._obj *= other
        return self

    def __idiv__(self, other): #pragma NO COVER
        # Only one of __itruediv__ and __idiv__ is meaningful at any one time.
        self._obj /= other
        return self

    def __itruediv__(self, other): #pragma NO COVER
        # Only one of __itruediv__ and __idiv__ is meaningful at any one time.
        self._obj /= other
        return self

    def __ifloordiv__(self, other):
        self._obj //= other
        return self

    def __imod__(self, other):
        self._obj %= other
        return self

    def __ilshift__(self, other):
        self._obj <<= other
        return self

    def __irshift__(self, other):
        self._obj >>= other
        return self

    def __iand__(self, other):
        self._obj &= other
        return self

    def __ixor__(self, other):
        self._obj ^= other
        return self

    def __ior__(self, other):
        self._obj |= other
        return self

    def __ipow__(self, other, modulus=None):
        if modulus is None:
            self._obj **= other
        else: #pragma NO COVER
            # There is no syntax which triggers in-place pow w/ modulus
            self._obj = pow(self._obj, other, modulus)
        return self
