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
- Optionally replace JavaScript asset URLs with hashed versions using
  *loud comments* markup. *(New in v0.2.0)*
- Optimizes hashing process with fewer I/O and less calculation.

Quick Start
-----------

1. Install the stable version from PyPI:

   .. code:: bash

       pip install django-smartstaticfiles

   Or install the stable version with extras for JavaScript and CSS minification
   (will also install |jsmin|_ and |csscompressor|_):

   .. code:: bash

       pip install django-smartstaticfiles[jsmin,cssmin]

   Or install the latest version from GitHub:

   .. code:: bash

       pip install git+https://github.com/rockallite/django-smartstaticfiles.git

2. Add the following lines to the project's Django settings module:

   .. code:: python

       STATIC_ROOT = '/path/for/collecting/static/files'

       STATICFILES_STORAGE = 'django_smartstaticfiles.storage.SmartManifestStaticFilesStorage'

       # Remove this if you don't need to minify JavaScript and CSS
       SMARTSTATICFILES_CONFIG = {
           'JS_MIN_ENABLED': True,
           'CSS_MIN_ENABLED': True,
       }

3. In the project directory, collect static files by running the following
   command:

   .. code:: bash

       python manage.py collectstatic --clear --no-input

JavaScript Asset URLs Replacement
---------------------------------

*(New in v0.2.0)*

By default, URLs of referenced assets (images, fonts, etc) in CSS
files will be replaced with hashed versions during processing. The
``SmartManifestStaticFilesStorage`` storage backend of
**django-smartstaticfiles** extends this feature to JavaScript files by
using special *loud comments* (``/*! */``) markup.

Simple use case
~~~~~~~~~~~~~~~

The feature is disabled by default. To enable it, add the following setting
to Django settings module:

.. code:: python

    SMARTSTATICFILES_CONFIG = {
        # Enable JavaScript asset URLs replacement
        'JS_ASSETS_REPL_ENABLED': True,
    }

To replace an asset URL with the hashed version, surround the URL string with
a pair of ``/*! rev */`` and ``/*! endrev */``:

.. code:: javascript

    var imageURL = /*! rev */ '../img/welcome.jpg' /*! endrev */;

Supposed that the file hash is ``welcome.ac99c750806a.jpg``, the processing
result will be:

.. code:: javascript

    var imageURL = '../img/welcome.ac99c750806a.jpg';

Using a different parent directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, relative asset URLs are considered to be relative to the
referencing JavaScript file, just the same rule for a CSS file. However,
since JavaScript runs in global scope of a browser, the path of a
JavaScript file is sometimes not useful for locating relative assets.

Therefore, the markup accepts a parameter as *virtual parent path*.
During processing, it will be considered as if it were the parent path
of the asset. For example:

.. code:: javascript

    /*
     * Supposed there are following files:
     *     STATIC_URL/helloworld/img/welcome.jpg
     *     STATIC_URL/helloworld/js/main.js
     *
     * Then in the main.js:
     */

    var imageURLs = [
        // *** Absolute reference ***
        // (STATIC_URL as the root path)

        // Leading and trailing slashes are optional
        /*! rev(helloworld/img) */ 'welcome.jpg' /*! endrev */,
        /*! rev(/helloworld/img/) */ 'welcome.jpg' /*! endrev */,

        // A single leading slash is OK
        /*! rev(/helloworld/img) */ 'welcome.jpg' /*! endrev */,

        // A single trailing slash is OK
        /*! rev(helloworld/img/) */ 'welcome.jpg' /*! endrev */,

        // Different path portion
        /*! rev(helloworld) */ 'img/welcome.jpg' /*! endrev */,

        // A single slash for the root path
        /*! rev(/) */ 'helloworld/img/welcome.jpg' /*! endrev */,

        // *** Relative reference ***
        // (Relative to the JavaScript file)

        // A leading dot slash (./) or dot-dot slash (../) indicates a relative reference
        /*! rev(../img) */ 'welcome.jpg' /*! endrev */,
        /*! rev(..) */ 'img/welcome.jpg' /*! endrev */,
        /*! rev(../..) */ 'helloworld/img/welcome.jpg' /*! endrev */
    ];

The processing result:

.. code:: javascript

    /*
     * Supposed there are following files:
     *     STATIC_URL/helloworld/img/welcome.jpg
     *     STATIC_URL/helloworld/js/main.js
     *
     * Then in the main.js:
     */

    var imageURLs = [
        // *** Absolute reference ***
        // (STATIC_URL as the root path)

        // Leading and trailing slashes are optional
        'welcome.ac99c750806a.jpg',
        'welcome.ac99c750806a.jpg',

        // A single leading slash is OK
        'welcome.ac99c750806a.jpg',

        // A single trailing slash is OK
        'welcome.ac99c750806a.jpg',

        // Different path portion
        'img/welcome.ac99c750806a.jpg',

        // A single slash for the root path
        'helloworld/img/welcome.ac99c750806a.jpg',

        // *** Relative reference ***
        // (Relative to the JavaScript file)

        // A leading dot slash (./) or dot-dot slash (../) indicates a relative reference
        'welcome.ac99c750806a.jpg',
        'img/welcome.ac99c750806a.jpg',
        'helloworld/img/welcome.ac99c750806a.jpg'
    ];

Notice that ``STATIC_URL`` **WILL NOT be prepended to the final URL**. You
have to manually pass the value of ``STATIC_URL`` to the browser, e.g. in a
Django template via dynamic generated JavaScript code. Then, concatenate the two values in JavaScript.

Customize the tag name
~~~~~~~~~~~~~~~~~~~~~~

You can also use a custom tag name in loud comments markup via the following
setting in Django settings module:

.. code:: python

    SMARTSTATICFILES_CONFIG = {
        # ...
        # Tag name of loud comments used in JavaScript asset URLs replacement
        'JS_ASSETS_REPL_TAG': 'hash-it',
    }

Then the corresponding JavaScript code should be written as:

.. code:: javascript

    var imageURL = /*! hash-it */ '../img/welcome.jpg' /*! endhash-it */;


Configurations
--------------
All configurations of **django-smartstaticfiles** are in the ``SMARTSTATICFILES_CONFIG`` property of
Django settings module, a dict containing configuration keys. All
keys are optional, which means you don't even need a ``SMARTSTATICFILES_CONFIG``
property at all if the default values meet your needs.

Possible keys and default values are listed below:

.. code:: python

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
        # a unicode string of minified content. (Notice that loud comments
        # such as /*! ... */ must be preserved in the result so as to make
        # JavaScript asset URLs replacement work.) The result will be cached and
        # reused when possible.
        'JS_MIN_FUNC': 'jsmin.jsmin',

        # Dotted string of the module path and the callable for CSS
        # minification. The callable should accept a single argument of unicode
        # string which contains the content of original CSS, and return a
        # unicode string of minified content. The result will be cached and
        # reused when possible.
        'CSS_MIN_FUNC': 'csscompressor.compress',

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

        # Whether to enable JavaScript asset URLs replacement.
        'JS_ASSETS_REPL_ENABLED': False,

        # Tag name of loud comments used in JavaScript asset URLs replacement.
        # Only alphabetic characters, numeric characters, underscores (_) and
        # dashes (-) can be used in the tag name.
        'JS_ASSETS_REPL_TAG': 'rev',
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

.. |jsmin| replace:: ``jsmin``
.. _jsmin: https://github.com/tikitu/jsmin/

.. |csscompressor| replace:: ``csscompressor``
.. _csscompressor: https://github.com/sprymix/csscompressor

.. _django-s3-storage: https://github.com/etianen/django-s3-storage

.. _a broken implementation: https://docs.djangoproject.com/en/1.11/ref/contrib/staticfiles/#django.contrib.staticfiles.storage.ManifestStaticFilesStorage.max_post_process_passes
