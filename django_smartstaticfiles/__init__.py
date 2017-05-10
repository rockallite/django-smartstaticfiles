# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django import VERSION

PROPER_VERSION = (1, 11)
assert VERSION[0] == PROPER_VERSION[0] and VERSION[1] == PROPER_VERSION[1], \
    '%s is only compatible with Django %s.%s' % ((__name__,) + PROPER_VERSION)
