# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2007-2010 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from ibus import unichar_half_to_full
from tables import *
import segment

_UNFINISHED_HIRAGANA = set(u"かきくけこさしすせそたちつてとはひふへほ")

class KanaSegment(segment.Segment):
    _prefs = None
    _kana_typing_rule_section = None
    
    def __init__(self, enchars=u"", jachars=u""):
        if not jachars:
            jachars = self.__get_kana_typing_rule(enchars, u"")
        super(KanaSegment, self).__init__(enchars, jachars)

    @classmethod
    def _init_kana_typing_rule(cls, prefs):
        cls._prefs = prefs
        if prefs == None:
            cls._kana_typing_rule_section = None
            return
        method = prefs.get_value('kana_typing_rule', 'method')
        if method == None:
            method = 'default'
        cls._kana_typing_rule_section = 'kana_typing_rule/' + method
        if cls._kana_typing_rule_section not in prefs.sections():
            cls._kana_typing_rule_section = None

    def __get_kana_typing_rule(self, enchars, retval=None):
        prefs = self._prefs
        value = None
        section = self._kana_typing_rule_section
        if section != None:
            if enchars in prefs.keys(section):
                value = unicode(str(prefs.get_value(section, enchars)))
            if value == '':
                value = None
            if value == None:
                value = retval 
        else:
            value = kana_typing_rule_static.get(enchars, retval)
        return value

    def is_finished(self):
        return not (self._jachars in _UNFINISHED_HIRAGANA)

    def append(self, enchar):
        if enchar == u"\0" or enchar == u"":
            return []
        if self._jachars:
            text = self._jachars + enchar
            jachars = kana_voiced_consonant_rule.get(text, None)
            if jachars:
                self._enchars = self._enchars + enchar
                self._jachars = jachars
                return []
            return [KanaSegment(enchar)]
        self._enchars = self._enchars + enchar
        self._jachars = self.__get_kana_typing_rule(self._enchars, u"")
        return []

    def prepend(self, enchar):
        if enchar == u"\0" or enchar == u"":
            return []
        if self._enchars == u"":
            self._enchars = enchar
            self._jachars = self.__get_kana_typing_rule(self._enchars, u"")
            return []
        return [KanaSegment(enchar)]

    def pop(self, index=-1):
        if index == -1:
            index = len(self._enchars) - 1
        if index < 0 or index >= len(self._enchars):
            raise IndexError("Out of bound")
        enchars = list(self._enchars)
        del enchars[index]
        self._enchars = u"".join(enchars)
        self._jachars = self.__get_kana_typing_rule(self._enchars, u"")
