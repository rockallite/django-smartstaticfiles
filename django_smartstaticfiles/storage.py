# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging
import re
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.signals import setting_changed
from django.utils.encoding import force_bytes, force_text
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.six import iteritems, itervalues, iterkeys
from django.contrib.staticfiles.utils import matches_patterns
from django.contrib.staticfiles.storage import (
    ManifestFilesMixin, StaticFilesStorage,
)

logger = logging.getLogger(__name__)

settings_attr = 'SMART_STATICFILES_CONFIG'

settings_defaults = {
    # Enable JavaScript minification.
    'JS_MIN_ENABLED': True,

    # Enable CSS minification.
    'CSS_MIN_ENABLED': True,

    # File patterns for matching relative JavaScript URL (without STATIC_URL
    # prefix)
    'JS_FILE_PATTERNS': ['*.js'],

    # File patterns for matching relative CSS URL (without STATIC_URL
    # prefix)
    'CSS_FILE_PATTERNS': ['*.css'],

    # Dotted string of the module path and the callable for JavaScript
    # minification. The callable should accept a single argument of unicode
    # string which contains the content of original JavaScript, and return a
    # unicode string of minified content.
    'JS_MIN_FUNC': 'rjsmin.jsmin',

    # Dotted string of the module path and the callable for CSS minification.
    # The callable should accept a single argument of unicode string which
    # contains the content of original CSS, and return a unicode string of
    # minified content.
    'CSS_MIN_FUNC': 'rcssmin.cssmin',

    # A regular expression (case-sensitive by default) which is used to search
    # against relative paths of assets URL (without STATIC_URL prefix). The
    # mathced assets won't be minified. Set it to None to ignore no assets.
    # (Assets with .min.js or .min.css extensions are always ignored.)
    'RE_IGNORE_MIN': None,

    # Enable deletion of unhashed files.
    'DELETE_UNHASHED_ENABLED': True,

    # Enable deletion of intermediate hashed files.
    'DELETE_INTERMEDIATE_ENABLED': True,

    # A regular expression (case-sensitive by default) which is used to search
    # against relative paths of assets URL (without STATIC_URL prefix). The
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


class SmartManifestFilesMixin(ManifestFilesMixin):
    def __init__(self, *args, **kwargs):
        super(SmartManifestFilesMixin, self).__init__(*args, **kwargs)
        setting_changed.connect(self._clear_cached_properties)
        if not settings.DEBUG:
            logger.info('Manifest file: %s',
                        self.path(self.manifest_name))
            if self.hashed_files:
                logger.info('Manifest loaded, number of files: %s',
                            len(self.hashed_files))
            else:
                logger.warning('Manifest contains no files.')
        self.intermediate_files = set()
        self.hashing_ignored_files = set()
        self.minified_files = {}

    def _clear_cached_properties(self, setting, **kwargs):
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

    def get_pre_minified_name(self, path):
        fn, ext = os.path.splitext(path)
        if not fn.endswith('.min'):
            return '%s.min%s' % (fn, ext)

    def get_minified_content_file(self, name, content=None, paths=None):
        if settings.DEBUG:
            # Return no cached minifiable file when debug mode is on
            return

        cleaned_name = self.clean_name(name)
        if cleaned_name in self.minified_files:
            # There is cached minified file. Return it
            return File(open(self.minified_files[cleaned_name], 'rb'))
        else:
            # No cached minified content. Check whether we should minify the
            # file content.
            pm_name = self.get_pre_minified_name(cleaned_name)
            if pm_name is None:
                # File already minified
                return

            min_func = None
            if (self.css_min_enabled or self.js_min_enabled) and \
                    not (self.re_ignore_min and
                         self.re_ignore_min.search(cleaned_name)):
                # Minification mode is on and file isn't ignored
                if self.css_min_enabled and \
                        matches_patterns(cleaned_name, self.css_file_patterns):
                    # Minify CSS
                    min_func = self.css_min_func
                elif self.js_min_enabled and \
                        matches_patterns(cleaned_name, self.js_file_patterns):
                    # Minify JavaScript
                    min_func = self.js_min_func

            if min_func:
                # File content needs to be minified
                assert content is not None or paths is not None, \
                    '"content" and "paths" argument can\'t be both None'
                opened = False
                if content is None:
                    storage, path = paths[name]
                    content = storage.open(path)
                    opened = True
                try:
                    content_text = content.read().decode(settings.FILE_CHARSET)
                finally:
                    if opened:
                        content.close()
                # Minify the content
                content_text = min_func(content_text)
                # Convert to bytes and save it to a temporary file
                with NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(force_bytes(content_text))
                # Cache the temp file path
                temp_file_path = temp_file.name
                self.minified_files[cleaned_name] = temp_file_path
                # Return minified file
                return File(open(temp_file_path, 'rb'))

    def _save(self, name, content, disable_minified_cache=False):
        if not disable_minified_cache and name != self.manifest_name:
            # Explicitly exclude manifiest caching
            cached_content = self.get_minified_content_file(name, content)
            if cached_content is not None:
                # Save the cached or newly processed minfiable content
                try:
                    return super(SmartManifestFilesMixin,
                                 self)._save(name, cached_content)
                finally:
                    cached_content.close()
        return super(SmartManifestFilesMixin, self)._save(name, content)

    # Comment by Rockallite: below is a modified copy of _post_process() of
    # HashedFilesMixin in Django 1.11. Changes are noted with "by Rockallite".
    def _post_process(self, paths, adjustable_paths, hashed_files):
        # Sort the files by directory level
        def path_level(name):
            return len(name.split(os.sep))

        for name in sorted(paths.keys(), key=path_level, reverse=True):
            # Added by Rockallite: check whether hashing should be ignored
            cleaned_name = self.clean_name(name)
            hash_key = self.hash_key(cleaned_name)
            if (self.re_ignore_hashing is not None
                    and cleaned_name not in self.hashing_ignored_files
                    and self.re_ignore_hashing.search(cleaned_name)):
                # Ignore hashing by short-circuited the logic
                hashed_files[hash_key] = cleaned_name
                self.hashing_ignored_files.add(cleaned_name)
                yield name, cleaned_name, False, False
                continue

            substitutions = True

            # Commented out by Rockallite: old code always use original file
            # # use the original, local file, not the copied-but-unprocessed
            # # file, which might be somewhere far away, like S3
            # storage, path = paths[name]
            # with storage.open(path) as original_file:

            # Added by Rockallite: new code which checks whether we should use
            # cached minified content
            storage, path = paths[name]
            cached_content = self.get_minified_content_file(name, paths=paths)
            if cached_content is None:
                # use the original, local file, not the copied-but-unprocessed
                # file, which might be somewhere far away, like S3
                open_original_file = lambda: storage.open(path)
            else:
                # Use the cached and minified content
                open_original_file = lambda: cached_content

            with open_original_file() as original_file:
            # Added by Rockallite: end of new code

                # Commited out by Rockallite: cleaned name and hash key already
                # generated
                # cleaned_name = self.clean_name(name)
                # hash_key = self.hash_key(cleaned_name)

                # generate the hash with the original content, even for
                # adjustable files.
                if hash_key not in hashed_files:
                    # Modified by Rockallite: use cleaned name (with backslashes
                    # replaced by slashes) instead of "raw" name for hashing.
                    # hashed_name = self.hashed_name(name, original_file)
                    hashed_name = self.hashed_name(cleaned_name, original_file)
                else:
                    hashed_name = hashed_files[hash_key]

                # then get the original's file content..
                if hasattr(original_file, 'seek'):
                    original_file.seek(0)

                hashed_file_exists = self.exists(hashed_name)
                processed = False

                # ..to apply each replacement pattern to the content
                if name in adjustable_paths:
                    old_hashed_name = hashed_name
                    content = original_file.read().decode(settings.FILE_CHARSET)
                    # Added by Rockallite: flag indicating content substitution
                    content_sub = False
                    for extension, patterns in iteritems(self._patterns):
                        if matches_patterns(path, (extension,)):
                            for pattern, template in patterns:
                                converter = self.url_converter(name, hashed_files, template)
                                try:
                                    # Modified by Rockallite: get number of sub
                                    # content = pattern.sub(converter, content)
                                    content, num_sub = pattern.subn(converter, content)
                                except ValueError as exc:
                                    yield name, None, exc, False
                                # Added by Rockallite: check content subsitution
                                else:
                                    if num_sub > 0:
                                        content_sub = True
                    # Commented out by Rockallite: original code is a bit messy
                    # if hashed_file_exists:
                    #     self.delete(hashed_name)
                    # # then save the processed result
                    # content_file = ContentFile(force_bytes(content))
                    # # Save intermediate file for reference
                    # saved_name = self._save(hashed_name, content_file)
                    # hashed_name = self.hashed_name(name, content_file)
                    #
                    # if self.exists(hashed_name):
                    #     self.delete(hashed_name)
                    #
                    # saved_name = self._save(hashed_name, content_file)
                    # hashed_name = force_text(self.clean_name(saved_name))
                    # # If the file hash stayed the same, this file didn't change
                    # if old_hashed_name == hashed_name:
                    #     substitutions = False
                    #
                    # processed = True

                    # Added by Rockallite: new code begins here
                    if content_sub:
                        # Content is substituted. Re-calculate file hash
                        content_file = ContentFile(force_bytes(content))
                        hashed_name = self.hashed_name(cleaned_name, content_file)
                        if hashed_name == old_hashed_name:
                            # The file didn't change
                            substitutions = False
                        else:
                            # The file changed
                            if not self.exists(hashed_name):
                                # Save the file only if it doesn't exist
                                saved_name = self._save(hashed_name, content_file,
                                                        disable_minified_cache=True)
                                hashed_name = force_text(self.clean_name(saved_name))
                            processed = True
                    else:
                        # The file didn't get substitued, thus didn't change.
                        # Avoid unnecessary hashing calculation.
                        substitutions = False
                    # Comment by Rockallite: end of new code

                if not processed:
                    # or handle the case in which neither processing nor
                    # a change to the original file happened
                    if not hashed_file_exists:
                        processed = True
                        saved_name = self._save(hashed_name, original_file,
                                                disable_minified_cache=True)
                        hashed_name = force_text(self.clean_name(saved_name))

                # Added by Rockallite: remember intermediate file
                if hash_key in hashed_files:
                    old_hashed_name = hashed_files[hash_key]
                    if old_hashed_name != hashed_name:
                        self.intermediate_files.add(old_hashed_name)

                # and then set the cache accordingly
                hashed_files[hash_key] = hashed_name

                yield name, hashed_name, processed, substitutions

    def post_process(self, paths, *args, **kwargs):
        all_post_processed = super(SmartManifestFilesMixin,
                                   self).post_process(paths, *args, **kwargs)

        try:
            for post_processed in all_post_processed:
                yield post_processed
        finally:
            temp_file_set = set(itervalues(self.minified_files))
            for f in temp_file_set:
                try:
                    os.remove(f)
                except OSError as err:
                    pass
            for f in temp_file_set:
                yield f, '<temp file deleted>', True

        if self.delete_unhashed_enabled:
            # Delete unhashed files from target storage
            if self.hashing_ignored_files:
                # Prevent hashing ignored files from being deleted
                unhashed_files = (set(iterkeys(self.hashed_files)) -
                                  self.hashing_ignored_files)
            else:
                unhashed_files = iterkeys(self.hashed_files)
            for f in unhashed_files:
                self.delete(f)
                yield f, '<unhashed file deleted>', True

        if self.delete_intermediate_enabled:
            # Delete intermediate files from target storage
            for f in self.intermediate_files:
                self.delete(f)
                yield f, '<intermediate file deleted>', True


class SmartManifestStaticFilesStorage(SmartManifestFilesMixin,
                                      StaticFilesStorage):
    pass
