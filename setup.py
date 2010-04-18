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
from setuptools import setup, find_packages, Extension

setup(name='Acquisition',
      version = '2.13.3',
      url='http://pypi.python.org/pypi/Acquisition',
      license='ZPL 2.1',
      description="Acquisition is a mechanism that allows objects to obtain "
      "attributes from the containment hierarchy they're in.",
      author='Zope Foundation and Contributors',
      author_email='zope-dev@zope.org',
      long_description=open(
          os.path.join('src', 'Acquisition', 'README.txt')).read() + '\n' +
          open('CHANGES.txt').read(),

      packages=find_packages('src'),
      package_dir={'': 'src'},

      ext_modules=[Extension("Acquisition._Acquisition",
                             [os.path.join('src', 'Acquisition',
                                           '_Acquisition.c')],
                             include_dirs=['include', 'src']),
                   ],
      install_requires=['ExtensionClass', 'zope.interface'],
      include_package_data=True,
      zip_safe=False,
      )
