Changelog
=========

v0.3.1 (2017-08-25) Rockallite Wulf
-----------------------------------

- Change default CSS and JavaScript minifiers back to ``"rcssmin.cssmin"`` and
  ``"rjsmin.jsmin"``, and add new settings attribute "JS_MIN_FUNC_KWARGS" and
  "CSS_MIN_FUNC_KWARGS" to make them keep loud comments (``/*! ... */``),
  because there is a bug in ``"jsmin"`` libarary
  (https://github.com/tikitu/jsmin/issues/23)

v0.3.0 (2017-05-12) Rockallite Wulf
-----------------------------------

- New feature: removed one trailing new line (if presents) from each replaced
  URL in JavaScript if "JS_MIN_ENABLED" is set to True. This fixes the problems
  and annoyances caused by a deliberately added newline at the end of each loud
  comment by certain JavaScript minification libraries (such as jsmin). This
  behavior can be disabled by setting "JS_ASSETS_REPL_TRAILING_FIX" to False.

- Removed the character restrictions of tag name of loud comments in JavaScript
  asset URLs replacement. Previously, only alphabetic characters, numeric
  characters, underscores and dashes are allowed

- Fixed parsing of relative virtual parent paths in JavaScript asset URLs
  replacement. Previously, an absolute path with a leading dot
  (e.g. ``.some/path``) will be considered as a relative path

- Rewritten CachedSettingsMixin for performance and simplicity

- Clarified the documentation

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