# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Huang Peng <shawn.p.huang@gmail.com>
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
    
    def __init__(self, enchars=u"", jachars=u""):
        if not jachars:
            jachars = kana_typing_rule.get(enchars, u"")
        super(KanaSegment, self).__init__(enchars, jachars)

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
        self._jachars = kana_typing_rule.get(self._enchars, u"")
        return []

    def prepend(self, enchar):
        if enchar == u"\0" or enchar == u"":
            return []
        if self._enchars == u"":
            self._enchars = enchar
            self._jachars = kana_typing_rule.get(self._enchars, u"")
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
        self._jachars = kana_typing_rule.get(self._enchars, u"")
