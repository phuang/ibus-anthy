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

import romaji

class JaString:
    def __init__(self):
        self.reset()

    def reset(self):
        self.__cursor = 0
        self.__segments = list()

    def insert(self, c):
        segment_before = None
        segment_after = None
        new_segments = None

        if self.__cursor >= 1:
            segment_before = self.__segments[self.__cursor - 1]
        if self.__cursor < len(self.__segments):
            segment_after = self.__segments[self.__cursor]
        if segment_before and not segment_before.is_finished():
            new_segments = segment_before.append(c)
        elif segment_after and not segment_after.is_finished():
            new_segments = segment_after.prepend(c)
        else:
            if c != u"\0" and c != u"":
                new_segments = [romaji.Segment(c)]
        if new_segments:
            self.__segments[self.__cursor:self.__cursor] = new_segments
            self.__cursor += len(new_segments)

    def remove_before(self):
        index = self.__cursor - 1
        if index >= 0:
            if self.__segments[index].is_finished():
                del self.__segments[index]
                self.__cursor = index
                return True

            enchars = self.__segments[index].get_enchars()
            enchars = enchars[:-1]
            if not enchars:
                del self.__segments[index]
                self.__cursor = index
                return True
            self.__segments[index].set_enchars(enchars)
            return True

        return False

    def remove_after(self):
        index = self.__cursor
        if index < len(self.__segments):
            if self.__segments[index].is_finished():
                del self.__segments[index]
                return True

            enchars = self.__segments[index].get_enchars()
            enchars = enchars[1:]
            if not enchars:
                del self.__segments[index]
                return True
            self.__segments[index].set_enchars(enchars)
            return True

        return False

    def get_string(self, type):
        pass

    def move_cursor(self, delta):
        self.__cursor += delta
        if self.__cursor < 0:
            self.__cursor = 0
        elif self.__cursor > len(self.__segments):
            self.__cursor = len(self.__segments)

    def get_hiragana(self):
        conv = lambda s: s.to_hiragana()
        text_before = u"".join(map(conv, self.__segments[:self.__cursor]))
        text_after = u"".join(map(conv, self.__segments[self.__cursor:]))
        return text_before + text_after, len(text_before)

    def get_katakana(self):
        conv = lambda s: s.to_katakana()
        text_before = u"".join(map(conv, self.__segments[:self.__cursor]))
        text_after = u"".join(map(conv, self.__segments[self.__cursor:]))
        return text_before + text_after, len(text_before)

    def get_half_width_katakana(self):
        conv = lambda s: s.to_half_width_katakana()
        text_before = u"".join(map(conv, self.__segments[:self.__cursor]))
        text_after = u"".join(map(conv, self.__segments[self.__cursor:]))
        return text_before + text_after, len(text_before)

    def get_latin(self):
        conv = lambda s: s.to_latin()
        text_before = u"".join(map(conv, self.__segments[:self.__cursor]))
        text_after = u"".join(map(conv, self.__segments[self.__cursor:]))
        return text_before + text_after, len(text_before)

    def get_wide_latin(self):
        conv = lambda s: s.to_wide_latin()
        text_before = u"".join(map(conv, self.__segments[:self.__cursor]))
        text_after = u"".join(map(conv, self.__segments[self.__cursor:]))
        return text_before + text_after, len(text_before)

    def is_empty(self):
        return all(map(lambda s: s.is_empty(), self.__segments))

