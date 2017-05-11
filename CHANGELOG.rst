Changelog
=========

v0.2.0 (2017-05-11) Rockallite Wulf
-----------------------------------

- Add support for replacing assets URLs with hashed versions in JavaScript.
  Use a special loud comment to accomplish this, for example:
  ``/*! rev */ "path/to/asset.jpg" /*! endrev */``, or with virtual parent
  directory: ``/*! rev(parent/dir/to) */ "asset.jpg" /*! endrev */``

- Change default CSS and JavaScript minifiers from ``"rcssmin.cssmin"`` and
  ``"rjsmin.jsmin"`` to ``"csscompressor.compress"`` and ``"jsmin.jsmin"``,
  because the latter two would keep loud comments (``/*! ... */``)

- Rename setuptools extras from ``"rjsmin"`` and ``"rcssmin"`` to ``"jsmin"``
  and ``"cssmin"``, and update corresponding dependencies to the new
  minification libraries


v0.1.0 (2017-05-10) Rockallite Wulf
-----------------------------------

- Initial release