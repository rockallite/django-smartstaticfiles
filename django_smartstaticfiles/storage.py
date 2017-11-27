# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
import logging
import posixpath
import re
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.encoding import force_bytes, force_text
from django.utils.six import iteritems, itervalues, iterkeys
from django.contrib.staticfiles.utils import matches_patterns
from django.contrib.staticfiles.storage import (
    HashedFilesMixin, ManifestFilesMixin, StaticFilesStorage,
)

from .settings import CachedSettingsMixin

logger = logging.getLogger(__name__)


class DuckTypedMatchObj(object):
    def __init__(self, matched, url):
        self.matched = matched
        self.url = url

    def groups(self):
        return self.matched, self.url


class SmartManifestFilesMixin(CachedSettingsMixin, ManifestFilesMixin):
    def __init__(self, *args, **kwargs):
        super(SmartManifestFilesMixin, self).__init__(*args, **kwargs)
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

    def url_converter(self, name, hashed_files, template=None):
        # Overrides original verision from HashedFilesMixin of Django 1.11.
        # Add support for "new-style" pattern which accepts a parent directory
        # as the first match and a URL as the sencond match (mainly for loud
        # comments in JavaScript).
        if template is None:
            template = self.default_template

        def converter(matchobj):
            groups = matchobj.groups()
            if len(groups) == 2:
                # For "classic" pattern, use the original converter maker.
                # Then feed the converter with the original match object.
                return super(SmartManifestFilesMixin, self).url_converter(
                    name, hashed_files, template
                )(matchobj)

            # Add support for prefix path of "new-style" pattern
            matched = groups[0]
            vp_dir = groups[1]
            url = groups[2]
            if len(groups) > 3:
                # Remember trailing characters
                trailing_chars = groups[3] or ''
            else:
                trailing_chars = ''

            if vp_dir:
                if vp_dir in ('.', '..') \
                        or vp_dir.startswith('./') \
                        or vp_dir.startswith('../'):
                    # The parent directory is relative to the source name
                    source_name = name if os.sep == '/' else name.replace(os.sep, '/')
                    vp_dir = posixpath.normpath(
                        posixpath.join(posixpath.dirname(source_name), vp_dir)
                    )
                else:
                    # The parent directory is relative to root of static files
                    if vp_dir.startswith('/'):
                        vp_dir = vp_dir[1:]
                vname = posixpath.join(vp_dir, 'doesnotmatter')
            else:
                # Use the original name if parent directory is not given
                vname = name

            if not trailing_chars or \
                    self.js_min_enabled and self.js_assets_repl_trailing_fix:
                new_template = template
            else:
                new_template = '%s%s' % (template,
                                         trailing_chars.replace('%', '%%'))

            # Create a duck-typed match object for the convertor, of which
            # groups() method returns a tuple of two values.
            return super(SmartManifestFilesMixin, self).url_converter(
                vname, hashed_files, new_template
            )(DuckTypedMatchObj(matched, url))

        return converter

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
            min_func_kwargs = None
            if (self.css_min_enabled or self.js_min_enabled) and \
                    not (self.re_ignore_min and
                         self.re_ignore_min.search(cleaned_name)):
                # Minification mode is on and file isn't ignored
                if self.css_min_enabled and \
                        matches_patterns(cleaned_name, self.css_file_patterns):
                    # Minify CSS
                    min_func = self.css_min_func
                    min_func_kwargs = self.css_min_func_kwargs
                elif self.js_min_enabled and \
                        matches_patterns(cleaned_name, self.js_file_patterns):
                    # Minify JavaScript
                    min_func = self.js_min_func
                    min_func_kwargs = self.js_min_func_kwargs

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
                    # content_text = content.read().decode(settings.FILE_CHARSET)
                    content_text = content.read()
                finally:
                    if opened:
                        content.close()
                # Minify the content
                if min_func_kwargs is None:
                    min_func_kwargs = {}
                content_text = min_func(content_text, **min_func_kwargs)
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
            # Explicitly exclude manifest file caching
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
            # Ignore hashing by short-circuited the logic
            if cleaned_name in self.hashing_ignored_files:
                yield name, cleaned_name, False, False
                continue
            hash_key = self.hash_key(cleaned_name)            
            if self.re_ignore_hashing is not None and self.re_ignore_hashing.search(cleaned_name):
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
                        # The file didn't get substituted, thus didn't change.
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
