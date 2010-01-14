# -*- coding: utf-8 -*-
# vim:set et sts=4 sw=4:
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2009 Hideaki ABE <abe.sendai@gmail.com>
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

import gtk
import gobject
import time

import segment


_table = {
    'q': [u'。', u'',   u'ぁ'],
    'w': [u'か', u'が', u'え'],
    'e': [u'た', u'だ', u'り'],
    'r': [u'こ', u'ご', u'ゃ'],
    't': [u'さ', u'ざ', u'れ'],

    'y': [u'ら', u'よ', u'ぱ'],
    'u': [u'ち', u'に', u'ぢ'],
    'i': [u'く', u'る', u'ぐ'],
    'o': [u'つ', u'ま', u'づ'],
    'p': [u'，',  u'ぇ', u'ぴ'],
    '@': [u'、', u'',   u''],
    '[': [u'゛', u'゜', u''],

    'a': [u'う', u'',   u'を'],
    's': [u'し', u'じ', u'あ'],
    'd': [u'て', u'で', u'な'],
    'f': [u'け', u'げ', u'ゅ'],
    'g': [u'せ', u'ぜ', u'も'],

    'h': [u'は', u'み', u'ば'],
    'j': [u'と', u'お', u'ど'],
    'k': [u'き', u'の', u'ぎ'],
    'l': [u'い', u'ょ', u'ぽ'],
    ';': [u'ん', u'っ', u''],

    'z': [u'．',  u'',   u'ぅ'],
    'x': [u'ひ', u'び', u'ー'],
    'c': [u'す', u'ず', u'ろ'],
    'v': [u'ふ', u'ぶ', u'や'],
    'b': [u'へ', u'べ', u'ぃ'],

    'n': [u'め', u'ぬ', u'ぷ'],
    'm': [u'そ', u'ゆ', u'ぞ'],
    ',': [u'ね', u'む', u'ぺ'],
    '.': [u'ほ', u'わ', u'ぼ'],
    '/': [u'・', u'ぉ', u''],

    '1': [u'1',  u'',   u'？'],
    '2': [u'2',  u'',   u'／'],
    '4': [u'4',  u'',   u'「'],
    '5': [u'5',  u'',   u'」'],

    '6': [u'6',  u'［',  u''],
    '7': [u'7',  u'］',  u''],
    '8': [u'8',  u'（',  u''],
    '9': [u'9',  u'）',  u''],
}

_shift_table = {
    'H': u'ぱ',
    'X': u'ぴ',
    'V': u'ぷ',
    'B': u'ぺ',
    '>': u'ぽ',
}

table = {}
shift_table = {}
r_table = {}

for k in _table.keys():
    table[ord(k)] = _table[k]
    for c in _table[k]:
        r_table[c] = k

for k in _shift_table.keys():
    shift_table[ord(k)] = _shift_table[k]
    r_table[_shift_table[k]] = k

kana_voiced_consonant_rule = {
    u"か゛" : u"が",
    u"き゛" : u"ぎ",
    u"く゛" : u"ぐ",
    u"け゛" : u"げ",
    u"こ゛" : u"ご",
    u"さ゛" : u"ざ",
    u"し゛" : u"じ",
    u"す゛" : u"ず",
    u"せ゛" : u"ぜ",
    u"そ゛" : u"ぞ",
    u"た゛" : u"だ",
    u"ち゛" : u"ぢ",
    u"つ゛" : u"づ",
    u"て゛" : u"で",
    u"と゛" : u"ど",
    u"は゛" : u"ば",
    u"ひ゛" : u"び",
    u"ふ゛" : u"ぶ",
    u"へ゛" : u"べ",
    u"ほ゛" : u"ぼ",
    u"は゜" : u"ぱ",
    u"ひ゜" : u"ぴ",
    u"ふ゜" : u"ぷ",
    u"へ゜" : u"ぺ",
    u"ほ゜" : u"ぽ",
}

_UNFINISHED_HIRAGANA = set(u"かきくけこさしすせそたちつてとはひふへほ")

class ThumbShiftSegment(segment.Segment):
    
    def __init__(self, enchars=u"", jachars=u""):
        if not jachars:
            if u'!' <= enchars <= u'~':
                jachars = segment.unichar_half_to_full(enchars)
            else:
                jachars = enchars
                enchars = r_table.get(jachars, u'')
        super(ThumbShiftSegment, self).__init__(enchars, jachars)

    def is_finished(self):
        return not (self._jachars in _UNFINISHED_HIRAGANA)

    def append(self, enchar):
        if enchar == u"\0" or enchar == u"":
            return []
        text = self._jachars + enchar
        jachars = kana_voiced_consonant_rule.get(text, None)
        if jachars:
            self._enchars = self._enchars + r_table.get(enchar, u'')
            self._jachars = jachars
            return []
        return [ThumbShiftSegment(enchar)]

    def prepend(self, enchar):
        if enchar == u"\0" or enchar == u"":
            return []
        if self._jachars == u"":
            if 0x21 <= enchars <= 0x7e:
                self._enchars = enchar
                self._jachars = segment.unichar_half_to_full(enchars)
            else:
                self._enchars = r_table.get(enchar, u'')
                self._jachars = enchar
            return []
        return [ThumbShiftSegment(enchar)]

    def pop(self, index=-1):
        self._enchars = u''
        self._jachars = u''
        return

