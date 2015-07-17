#!/usr/bin/env python

from distutils.core import setup

setup(name='iresolve',
      version='0.1.3',
      description='Python Import Resolver',
      author='Mark Baas',
      author_email='mark.baas123@gmail.com',
      url='https://github.com/markbaas/python-iresolve',
      scripts=['iresolve'],
      install_requires = ['pyflakes>=0.8.1']
     )
