##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Filesystem Page Template module

Zope object encapsulating a Page Template from the filesystem.
"""

__all__ = ("PageTemplateFile",)

import os
import sys
import re
import logging

import six
from zope.pagetemplate.pagetemplate import PageTemplate

DEFAULT_ENCODING = "utf-8"

meta_pattern = re.compile(
    br'\s*<meta\s+http-equiv=["\']?Content-Type["\']?'
    br'\s+content=["\']?([^;]+);\s*charset=([^"\']+)["\']?\s*/?\s*>\s*',
    re.IGNORECASE)

def package_home(gdict):
    filename = gdict["__file__"]
    return os.path.dirname(filename)

class PageTemplateFile(PageTemplate):
    "Zope wrapper for filesystem Page Template using TAL, TALES, and METAL"

    _v_last_read = 0

    #_error_start = b'<!-- Page Template Diagnostics'
    #_error_end = b'-->'
    #_newline = b'\n'

    def __init__(self, filename, _prefix=None):
        path = self.get_path_from_prefix(_prefix)
        self.filename = os.path.join(path, filename)
        if not os.path.isfile(self.filename):
            raise ValueError("No such file", self.filename)

    def get_path_from_prefix(self, _prefix):
        if isinstance(_prefix, str):
            path = _prefix
        else:
            if _prefix is None:
                _prefix = sys._getframe(2).f_globals
            path = package_home(_prefix)
        return path

    def _prepare_html(self, text):
        match = meta_pattern.search(text)
        if match is not None:
            type_, encoding = (x.decode('utf-8') for x in match.groups())
            # TODO: Shouldn't <meta>/<?xml?> stripping
            # be in PageTemplate.__call__()?
            text = meta_pattern.sub(b"", text)
        else:
            type_ = None
            encoding = DEFAULT_ENCODING
        text = text.decode(encoding)
        return text, type_

    def _read_file(self):
        __traceback_info__ = self.filename
        f = open(self.filename, "rb")
        try:
            text = f.read(XML_PREFIX_MAX_LENGTH)
        except:
            f.close()
            raise
        type_ = sniff_type(text)
        text += f.read()
        if type_ != "text/xml":
            text, type_ = self._prepare_html(text)
        f.close()
        return text, type_

    def _cook_check(self):
        if self._v_last_read and not __debug__:
            return
        __traceback_info__ = self.filename
        try:
            mtime = os.path.getmtime(self.filename)
        except OSError:
            mtime = 0
        if self._v_program is not None and mtime == self._v_last_read:
            return
        text, type_ = self._read_file()
        self.pt_edit(text, type_)
        assert self._v_cooked
        if self._v_errors:
            logging.error('PageTemplateFile: Error in template %s: %s',
                    self.filename, '\n'.join(self._v_errors))
            return
        self._v_last_read = mtime

    def pt_source_file(self):
        return self.filename

    def __getstate__(self):
        raise TypeError("non-picklable object")

XML_PREFIXES = [
    b"<?xml",                      # ascii, utf-8
    b"\xef\xbb\xbf<?xml",          # utf-8 w/ byte order mark
    b"\0<\0?\0x\0m\0l",            # utf-16 big endian
    b"<\0?\0x\0m\0l\0",            # utf-16 little endian
    b"\xfe\xff\0<\0?\0x\0m\0l",    # utf-16 big endian w/ byte order mark
    b"\xff\xfe<\0?\0x\0m\0l\0",    # utf-16 little endian w/ byte order mark
    ]

XML_PREFIX_MAX_LENGTH = max(map(len, XML_PREFIXES))

def sniff_type(text):
    """Return 'text/xml' if text appears to be XML, otherwise return None."""
    for prefix in XML_PREFIXES:
        if text.startswith(prefix):
            return "text/xml"
    return None
