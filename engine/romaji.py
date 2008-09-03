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

class RomajiSegment:
    def __init__(self, enchars = u"", jachars = u""):
        self.__enchars = enchars
        if jachars:
            self.__jachars = jachars
        else:
            jachars = romaji_typing_rule.get(enchars, None)
            if jachars == None:
                jachars = half_symbol_rule.get(enchars, u"")
            self.__jachars = jachars

    def is_finished(self):
        return self.__jachars != u""

    def append(self, enchar):
        if self.is_finished():
            if enchar == u"" and enchar == u"\0":
                return []
            return [RomajiSegment(enchar)]

        text = self.__enchars + enchar

        jachars = romaji_typing_rule.get(text, None)
        if jachars == None:
            jachars = half_symbol_rule.get(text, None)
        if jachars:
            self.__enchars = text
            self.__jachars = jachars
            return []

        jachars, c = romaji_double_consonat_typing_rule.get(text, (None, None))
        if jachars:
            self.__enchars = text[0]
            self.__jachars = jachars
            return [RomajiSegment(c)]

        for i in range(-min(4, len(text)), 0):
            enchars = text[i:]

            jachars = romaji_typing_rule.get(enchars, None)
            if jachars == None:
                jachars = half_symbol_rule.get(enchars, None)
            if jachars:
                jasegment = RomajiSegment(enchars, jachars)
                self.__enchars = text[:i]
                return [jasegment]

            jachars, c = romaji_double_consonat_typing_rule.get(enchars, (None, None))
            if jachars:
                jasegment = RomajiSegment(enchars[:-len(c)], jachars)
                self.__enchars = text[:i]
                if c:
                    return [jasegment, RomajiSegment(c)]
                return [jasegment]

            jachars, c = romaji_correction_rule.get(enchars, (None, None))
            if jachars:
                jasegment = RomajiSegment(enchars[:-len(c)], jachars)
                self.__enchars = text[:i]
                if c:
                    return [jasegment, RomajiSegment(c)]
                return [jasegment]



        self.__enchars = text
        return []

    def prepend(self, enchar):
        if enchar == u"" or enchar == u"\0":
            return []

        if self.is_finished():
            return [RomajiSegment(enchar)]

        text = enchar + self.__enchars
        jachars = romaji_typing_rule.get(text, None)
        if not jachars:
            jachars = half_symbol_rule.get(text, None)
        if jachars:
            self.__enchars = text
            self.__jachars = jachars
            return []

        jachars, c = romaji_double_consonat_typing_rule.get(text, (None, None))
        if jachars:
            self.__enchars = c
            return [RomajiSegment(text[0], jachars)]

        for i in range(min(4, len(text)), 0, -1):
            enchars = text[:i]

            jachars = romaji_typing_rule.get(enchars, None)
            if not jachars:
                jachars = half_symbol_rule.get(enchars, None)
            if jachars:
                jasegment = RomajiSegment(enchars, jachars)
                self.__enchars = text[i:]
                return [jasegment]

            jachars, c = romaji_double_consonat_typing_rule.get(enchars, (None, None))
            if jachars:
                self.__enchars = c + text[i:]
                return [RomajiSegment(enchars[:-len(c)], jachars)]

            jachars, c = romaji_correction_rule.get(enchars, (None, None))
            if jachars:
                self.__enchars = c + text[i:]
                return [RomajiSegment(enchars[:-len(c)], jachars)]


        self.__enchars = text
        return []

    def set_enchars(self, enchars):
        self.__enchars = enchars

    def get_enchars(self):
        return self.__enchars

    def set_jachars(self, jachars):
        self.__jachars = jachars

    def get_jachars(self):
        return self.__jachars

    def to_hiragana(self):
        if self.__jachars:
            return self.__jachars
        return self.__enchars

    def to_katakana(self):
        if self.__jachars:
            return u"".join(map(lambda c: hiragana_katakana_table[c][0], self.__jachars))
        return self.__enchars

    def to_half_width_katakana(self):
        if self.__jachars:
            return u"".join(map(lambda c: hiragana_katakana_table[c][1], self.__jachars))
        return self.__enchars

    def to_latin(self):
        return self.__enchars

    def to_wide_latin(self):
        return u"".join(map(unichar_half_to_full, self.__enchars))

    def is_empty(self):
        if self.__enchars or self.__jachars:
            return False
        return True
