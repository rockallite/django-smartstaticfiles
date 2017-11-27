# -*- coding: utf-8 -*-
import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-smartstaticfiles',
    version='0.3.2',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License',
    description='Provides enhanced static files storage backend for Django 1.11',
    long_description=README,
    url='https://github.com/rockallite/django-smartstaticfiles',
    author='Rockallite Wulf',
    author_email='rockallite.wulf@gmail.com',
    install_requires=[
        'Django>=1.11,<1.12',
    ],
    extras_require={
        'jsmin': ['rjsmin'],
        'cssmin': ['rcssmin'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
