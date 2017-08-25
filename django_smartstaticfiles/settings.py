# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.utils.module_loading import import_string
from django.utils.six import iteritems, iterkeys

settings_attr = 'SMARTSTATICFILES_CONFIG'

settings_defaults = {
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
    # minification. The callable should accept a single argument of a string
    # of the content of original JavaScript, and return a string of minified
    # content. (Notice that loud comments such as /*! ... */ must be preserved
    # in the result so as to make JavaScript asset URLs replacement work.)
    # The result will be cached and reused when possible.
    'JS_MIN_FUNC': 'rjsmin.jsmin',

    # Extra keyword arguments which are sent to the callable for JavaScript
    # minification. They are sent after the argument of a string of the
    # content of original JavaScript. If no keyword arguments are sent, set it
    # to an empty dict ({}) or None.
    'JS_MIN_FUNC_KWARGS': {
        'keep_bang_comments': True,
    },

    # Dotted string of the module path and the callable for CSS
    # minification. The callable should accept a single argument of
    # string which contains the content of original CSS, and return a
    # string of minified content. The result will be cached and
    # reused when possible.
    'CSS_MIN_FUNC': 'rcssmin.cssmin',

    # Extra keyword arguments which are sent to the callable for CSS
    # minification. They are sent after the argument of a string of the
    # content of original CSS. If no keyword arguments are sent, set it
    # to an empty dict ({}) or None.
    'CSS_MIN_FUNC_KWARGS': {
        'keep_bang_comments': True,
    },

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
    'JS_ASSETS_REPL_TAG': 'rev',

    # Whether to remove one trailing newline (if presents) after each
    # replaced URL in JavaScript. This is effective only if "JS_MIN_ENABLED"
    # is set to True. This fixes the problems and annoyances caused by a
    # deliberately added newline at the end of each loud comment by certain
    # minification libraries (e.g. jsmin).
    'JS_ASSETS_REPL_TRAILING_FIX': False,
}

settings_cache = None


def setup_settings_cache():
    global settings_cache
    if settings_cache is None:
        try:
            _settings = getattr(settings, settings_attr)
        except AttributeError:
            settings_cache = {}
        else:
            try:
                settings_cache = dict(_settings)
            except (TypeError, ValueError):
                raise ImproperlyConfigured(
                    'setting "%s" must be a dict' % settings_attr
                )
        # Set default values
        for key, value in iteritems(settings_defaults):
            settings_cache.setdefault(key, value)
        # Import modules from dotted strings
        if settings_cache['JS_MIN_ENABLED']:
            settings_cache['JS_MIN_FUNC'] = \
                import_string(settings_cache['JS_MIN_FUNC'])
        if settings_cache['CSS_MIN_ENABLED']:
            settings_cache['CSS_MIN_FUNC'] = \
                import_string(settings_cache['CSS_MIN_FUNC'])
        # Compile possible regular expressions
        regex_keys_to_cache = ['RE_IGNORE_HASHING']
        if settings_cache['JS_MIN_ENABLED'] or settings_cache['CSS_MIN_ENABLED']:
            regex_keys_to_cache.append('RE_IGNORE_MIN')
        for key in regex_keys_to_cache:
            regex = settings_cache.get(key, None)
            if regex:
                try:
                    settings_cache[key] = re.compile(regex)
                except Exception as err:
                    raise ImproperlyConfigured(
                        'key "%s" in setting "%s" is not a valid regular '
                        'expression: %s' % (key, settings_attr, err)
                    )
            elif regex is not None:
                settings_cache[key] = None


def clear_settings_cache():
    global settings_cache
    settings_cache = None


def get_cached_setting_key(key):
    setup_settings_cache()
    return settings_cache[key]


def settings_changed_handler(setting, **kwargs):
    if setting == settings_attr:
        clear_settings_cache()


setting_changed.connect(settings_changed_handler)


class CachedSettingsMixin(object):
    def __init__(self, *args, **kwargs):
        self.update_patterns()
        super(CachedSettingsMixin, self).__init__(*args, **kwargs)

    def update_patterns(self):
        if not self.js_assets_repl_enabled:
            return

        esc_tag = re.escape(self.js_assets_repl_tag)
        self.patterns += (
            ("*.js", (
                (r"""(/\*!\s*%s(?:\((.*?)\))?\s*\*/\s*['"](.*?)['"]\s*/\*!\s*end%s\s*\*/(\n)?)"""
                    % (esc_tag, esc_tag),
                 """'%s'"""),
            )),
        )


class SettingProxy(object):
    def __init__(self, key):
        self.key = key

    def __call__(self, instance):
        return get_cached_setting_key(self.key)


# Dynamically create properties, whose names are lower-cased keys of
# settings_defaults
for key in iterkeys(settings_defaults):
    setattr(CachedSettingsMixin, key.lower(), property(SettingProxy(key)))
