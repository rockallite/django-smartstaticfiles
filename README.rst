=======================
django-smartstaticfiles
=======================

**django-smartstaticfiles** enhances the functionalities of |collectstatic|_
management command of Django **1.11.x**, allows for finer-grained control
over serving static files in production.

Under the hood, it provides a file storage backend for use with
|STATICFILES_STORAGE|_ setting, which inherits and improves Django's
|ManifestStaticFilesStorage|_ storage backend.

Features
--------

- Deletes unhashed files and intermediate files by default.
- Optionally ignores hashing of specific files.
- Optionally minifies JavaScript and CSS files.
- Optimizes hashing process with fewer I/O and less calculation.

Quick start
-----------

1. Install the stable version from PyPI:

   .. code:: bash

       pip install django-smartstaticfiles

   Or install the latest version from GitHub:

   .. code:: bash

       pip install git+https://github.com/rockallite/django-smartstaticfiles.git

2. Optionally install |rjsmin|_ and |rcssmin|_ for JavaScript and CSS
   minification (skip this step if you don't need this):

   .. code:: bash

       pip install rjsmin rcssmin

3. In the Django project, add the following lines to the settings module:

   .. code:: python

       STATIC_ROOT = '/path/for/collecting/static/files'

       STATICFILES_STORAGE = 'django_smartstaticfiles.storage.SmartManifestStaticFilesStorage'

       # Remove this if you don't need to minify JavaScript and CSS
       SMARTSTATICFILES_CONFIG = {
           'JS_MIN_ENABLED': True,
           'CSS_MIN_ENABLED': True,
       }

4. In the project directory, run ``collectstatic`` management command:

   .. code:: bash

       python manage.py collectstatic --clear --no-input

Configurations
--------------
All configurations of **django-smartstaticfiles** are in the ``SMARTSTATICFILES_CONFIG`` property of
Django settings module, a dict containing configuration keys. All
keys are optional, which means you don't even need a ``SMARTSTATICFILES_CONFIG``
property at all if the default values meet your needs.

Possible keys and default values are listed below:

.. code:: python

    # your_project/settings.py

    SMARTSTATICFILES_CONFIG = {
        # Whether to enable JavaScript minification.
        'JS_MIN_ENABLED': False,

        # Whether to enable CSS minification.
        'CSS_MIN_ENABLED': False,

        # File patterns for matching JavaScript assets (in relative URL without
        # STATIC_URL prefix)
        'JS_FILE_PATTERNS': ['*.js'],

        # File patterns for matching CSS assets (in relative URL without
        # STATIC_URL prefix)
        'CSS_FILE_PATTERNS': ['*.css'],

        # Dotted string of the module path and the callable for JavaScript
        # minification. The callable should accept a single argument of unicode
        # string which contains the content of original JavaScript, and return
        # a unicode string of minified content. The result will be cached and
        # reused when possible.
        'JS_MIN_FUNC': 'rjsmin.jsmin',

        # Dotted string of the module path and the callable for CSS
        # minification. The callable should accept a single argument of unicode
        # string which contains the content of original CSS, and return a
        # unicode string of minified content. The result will be cached and
        # reused when possible.
        'CSS_MIN_FUNC': 'rcssmin.cssmin',

        # A regular expression (case-sensitive by default) which is used to
        # search against assets (in relative URL without STATIC_URL prefix). The
        # mathced assets won't be minified. Set it to None to ignore no assets.
        # (Assets with .min.js or .min.css extensions are always ignored.)
        'RE_IGNORE_MIN': None,

        # Whether to enable deletion of unhashed files.
        'DELETE_UNHASHED_ENABLED': True,

        # Whether to enable deletion of intermediate hashed files.
        'DELETE_INTERMEDIATE_ENABLED': True,

        # A regular expression (case-sensitive by default) which is used to
        # search against assets (in relative URL without STATIC_URL prefix). The
        # matched assets won't be hashed. Set it to None to ignore no assets.
        'RE_IGNORE_HASHING': None,
    }


Extensibility
-------------

The ``SmartManifestStaticFilesStorage`` storage backend provided by **django-smartstaticfiles** inherits two parent
classes:

.. code:: python

    class SmartManifestStaticFilesStorage(SmartManifestFilesMixin, StaticFilesStorage):
        pass

The main logic is implemented in ``SmartManifestFilesMixin``,
which is similar to Django's ``ManifestStaticFilesStorage``:

.. code:: python

    class ManifestStaticFilesStorage(ManifestFilesMixin, StaticFilesStorage):
        pass

The goal of this project is to make ``SmartManifestFilesMixin``
a drop-in replacement for ``ManifestFilesMixin``, without sacrificing
functionalities or performance. So you can combine
``SmartManifestFilesMixin`` with other storage class that is compatible with
``ManifestFilesMixin``.

For example, django-s3-storage_ provides a storage backend which utilizes
Django's ``ManifestFilesMixin``:

.. code:: python

    # django_s3_storage/storage.py
    from django.contrib.staticfiles.storage import ManifestFilesMixin

    # ...

    class ManifestStaticS3Storage(ManifestFilesMixin, StaticS3Storage):
        pass

You can make a similar but enhanced storage backend by replacing it with
``SmartManifestFilesMixin``:

.. code:: python

    from django_s3_storage.storage import StaticS3Storage
    from django_smartstaticfiles.storage import SmartManifestFilesMixin


    class SmartManifestStaticS3Storage(SmartManifestFilesMixin, StaticS3Storage):
        pass

Why Django 1.11.x only?
-----------------------

Until version 1.11, Django shipped with a ``ManifestStaticFilesStorage`` storage
backend that had `a broken implementation`_. In other words, content changes in
referenced files (images, fonts, etc) aren't represented in hashes of
referencing files (CSS files, specifically). This breaks the foundation of
cache-busting mechanism.

Then, there are significant code changes in Django 1.11 in order to fix the
behavior of that storage backend. So it becomes impractical to maintain compatibility
of **django-smartstaticfiles** with older Django code. Therefore, only Django
1.11 is supported (the latest version at the time of writing).


.. |collectstatic| replace:: ``collectstatic``
.. _collectstatic: https://docs.djangoproject.com/en/1.11/ref/contrib/staticfiles/#django-admin-collectstatic

.. |STATICFILES_STORAGE| replace:: ``STATICFILES_STORAGE``
.. _STATICFILES_STORAGE: https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-STATICFILES_STORAGE

.. |ManifestStaticFilesStorage| replace:: ``ManifestStaticFilesStorage``
.. _ManifestStaticFilesStorage: https://docs.djangoproject.com/en/1.11/ref/contrib/staticfiles/#manifeststaticfilesstorage

.. |rjsmin| replace:: ``rjsmin``
.. _rjsmin: http://opensource.perlig.de/rjsmin/

.. |rcssmin| replace:: ``rcssmin``
.. _rcssmin: http://opensource.perlig.de/rcssmin/

.. _django-s3-storage: https://github.com/etianen/django-s3-storage

.. _a broken implementation: https://docs.djangoproject.com/en/1.11/ref/contrib/staticfiles/#django.contrib.staticfiles.storage.ManifestStaticFilesStorage.max_post_process_passes
