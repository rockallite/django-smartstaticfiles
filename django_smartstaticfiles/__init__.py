# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import VERSION as DJANGO_VERSION

PROPER_DJANGO_VERSION = (1, 11)

assert DJANGO_VERSION[0] == PROPER_DJANGO_VERSION[0] and \
    DJANGO_VERSION[1] == PROPER_DJANGO_VERSION[1], \
    '%s is only compatible with Django %s.%s' % (
        (__name__,) + PROPER_DJANGO_VERSION
    )

__version__ = '0.3.2'
