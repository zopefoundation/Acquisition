##############################################################################
#
# Copyright (c) 2007 Zope Foundation and Contributors.
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
"""Setup for the Acquisition distribution
"""
import os
import platform

from setuptools import Extension
from setuptools import setup


# PyPy won't build the extension.
py_impl = getattr(platform, 'python_implementation', lambda: None)
is_pypy = py_impl() == 'PyPy'
if is_pypy:
    ext_modules = []
else:
    ext_modules = [
        Extension("Acquisition._Acquisition",
                  [os.path.join('src', 'Acquisition', '_Acquisition.c')],
                  include_dirs=['include', 'src']),
    ]


setup(ext_modules=ext_modules)
