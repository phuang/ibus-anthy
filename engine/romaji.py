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

def romaji_correction_rule_get(k, d):
    return (u'ん', k[1:2]) if k[0:1] == u'n' and not k[1:2] in u"aiueony'" else d

class RomajiSegment(segment.Segment):
    def __init__(self, enchars=u"", jachars=u"", shift=False):
        if not jachars and not shift:
            jachars = romaji_typing_rule.get(enchars, None)
            if jachars == None:
                jachars = symbol_rule.get(enchars, u"")
        super(RomajiSegment, self).__init__(enchars, jachars)

    def is_finished(self):
        return self._jachars != u""

    def append(self, enchar, shift=False):
        if self.is_finished():
            if enchar == u"" and enchar == u"\0":
                return []
            return [RomajiSegment(enchar)]

        text = self._enchars + enchar
        if shift:
            self._enchars = text
            return []

        jachars = romaji_typing_rule.get(text, None)
        if jachars == None:
            jachars = symbol_rule.get(text, None)
        if jachars:
            self._enchars = text
            self._jachars = jachars
            return []

        jachars, c = romaji_double_consonat_typing_rule.get(text, (None, None))
        if jachars:
            self._enchars = text[0]
            self._jachars = jachars
            return [RomajiSegment(c)]

#        jachars, c = romaji_correction_rule.get(text, (None, None))
        jachars, c = romaji_correction_rule_get(text, (None, None))
        if jachars:
            self._enchars = text[0]
            self._jachars = jachars
            return [RomajiSegment(c)]

        for i in range(-min(4, len(text)), 0):
            enchars = text[i:]

            jachars = romaji_typing_rule.get(enchars, None)
            if jachars == None:
                jachars = symbol_rule.get(enchars, None)
            if jachars:
                jasegment = RomajiSegment(enchars, jachars)
                self._enchars = text[:i]
                return [jasegment]

            jachars, c = romaji_double_consonat_typing_rule.get(enchars, (None, None))
            if jachars:
                jasegment = RomajiSegment(enchars[:-len(c)], jachars)
                self._enchars = text[:i]
                if c:
                    return [jasegment, RomajiSegment(c)]
                return [jasegment]

#            jachars, c = romaji_correction_rule.get(enchars, (None, None))
            jachars, c = romaji_correction_rule_get(enchars, (None, None))
            if jachars:
                jasegment = RomajiSegment(enchars[:-len(c)], jachars)
                self._enchars = text[:i]
                if c:
                    return [jasegment, RomajiSegment(c)]
                return [jasegment]

        self._enchars = text
        return []

    def prepend(self, enchar, shift=False):
        if enchar == u"" or enchar == u"\0":
            return []

        if self.is_finished():
            return [RomajiSegment(enchar)]

        text = enchar + self._enchars
        if shift:
            self._enchars = text
            return []

        jachars = romaji_typing_rule.get(text, None)
        if jachars == None:
            jachars = symbol_rule.get(text, None)
        if jachars:
            self._enchars = text
            self._jachars = jachars
            return []

        jachars, c = romaji_double_consonat_typing_rule.get(text, (None, None))
        if jachars:
            self._enchars = c
            return [RomajiSegment(text[0], jachars)]

#        jachars, c = romaji_correction_rule.get(text, (None, None))
        jachars, c = romaji_correction_rule_get(text, (None, None))
        if jachars:
            self._enchars = c
            return [RomajiSegment(text[0], jachars)]

        for i in range(min(4, len(text)), 0, -1):
            enchars = text[:i]

            jachars = romaji_typing_rule.get(enchars, None)
            if jachars == None:
                jachars = symbol_rule.get(enchars, None)
            if jachars:
                jasegment = RomajiSegment(enchars, jachars)
                self._enchars = text[i:]
                return [jasegment]

            jachars, c = romaji_double_consonat_typing_rule.get(enchars, (None, None))
            if jachars:
                self._enchars = c + text[i:]
                return [RomajiSegment(enchars[:-len(c)], jachars)]

#            jachars, c = romaji_correction_rule.get(enchars, (None, None))
            jachars, c = romaji_correction_rule_get(enchars, (None, None))
            if jachars:
                self._enchars = c + text[i:]
                return [RomajiSegment(enchars[:-len(c)], jachars)]

        self._enchars = text
        return []

    def pop(self, index=-1):
        if index == -1:
            index = len(self._enchars) - 1
        if index < 0 or index >= len(self._enchars):
            raise IndexError("Out of bound")
        if self.is_finished():
            self._enchars = u""
            self._jachars = u""
        else:
            enchars = list(self._enchars)
            del enchars[index]
            self._enchars = u"".join(enchars)
            jachars = romaji_typing_rule.get(self._enchars, None)
            if jachars == None:
                jachars = symbol_rule.get(self._enchars, u"")
            self._jachars = jachars


