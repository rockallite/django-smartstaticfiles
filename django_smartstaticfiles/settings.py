# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.six import iteritems

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

settings_cache = None
settings_imports = ['JS_MIN_FUNC', 'CSS_MIN_FUNC']
settings_re_keys = ['RE_IGNORE_MIN', 'RE_IGNORE_HASHING']


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
        for key in settings_imports:
            settings_cache[key] = import_string(settings_cache[key])
        # Compile possible regular expressions
        for key in settings_re_keys:
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


class CachedSettingsMixin(object):
    def __init__(self, *args, **kwargs):
        super(CachedSettingsMixin, self).__init__(*args, **kwargs)
        setting_changed.connect(self._clear_cached_props)

    def _clear_cached_props(self, setting, **kwargs):
        if setting == settings_attr:
            self.__dict__.pop('js_min_enabled', None)
            self.__dict__.pop('css_min_enabled', None)
            self.__dict__.pop('js_file_patterns', None)
            self.__dict__.pop('css_file_patterns', None)
            self.__dict__.pop('js_min_func', None)
            self.__dict__.pop('css_min_func', None)
            self.__dict__.pop('re_ignore_min', None)
            self.__dict__.pop('delete_unhashed_enabled', None)
            self.__dict__.pop('delete_intermediate_enabled', None)
            self.__dict__.pop('re_ignore_hashing', None)

    def _cached_setting_key(self, key):
        setup_settings_cache()
        return settings_cache[key]

    @cached_property
    def js_min_enabled(self):
        return self._cached_setting_key('JS_MIN_ENABLED')

    @cached_property
    def css_min_enabled(self):
        return self._cached_setting_key('CSS_MIN_ENABLED')

    @cached_property
    def js_file_patterns(self):
        return self._cached_setting_key('JS_FILE_PATTERNS')

    @cached_property
    def css_file_patterns(self):
        return self._cached_setting_key('CSS_FILE_PATTERNS')

    @cached_property
    def js_min_func(self):
        return self._cached_setting_key('JS_MIN_FUNC')

    @cached_property
    def css_min_func(self):
        return self._cached_setting_key('CSS_MIN_FUNC')

    @cached_property
    def re_ignore_min(self):
        return self._cached_setting_key('RE_IGNORE_MIN')

    @cached_property
    def delete_unhashed_enabled(self):
        return self._cached_setting_key('DELETE_UNHASHED_ENABLED')

    @cached_property
    def delete_intermediate_enabled(self):
        return self._cached_setting_key('DELETE_INTERMEDIATE_ENABLED')

    @cached_property
    def re_ignore_hashing(self):
        return self._cached_setting_key('RE_IGNORE_HASHING')
