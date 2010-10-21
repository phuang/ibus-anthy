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

__all__ = (
        "ThumbShiftKeyboard",
        "ThumbShiftSegment",
    )

from ibus import keysyms
from ibus import modifier
import segment

try:
    from gtk.gdk import get_default_root_window
except ImportError:
    get_default_root_window = lambda : None

_THUMB_BASIC_METHOD = 'base'

_table_static = {
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
    '\\': [u'￥', u'',  u''],
}

_nicola_j_table_static = {
    ':': [u'：', u'',   u''],
    '@': [u'、', u'',   u''],
    '[': [u'゛', u'゜', u''],
    ']': [u'」', u'',   u''],
    '8': [u'8',  u'（', u''],
    '9': [u'9',  u'）', u''],
    '0': [u'0',  u'',   u''],
}

_nicola_a_table_static = {
    ':': [u'：', u'',   u''],
    '@': [u'＠', u'',   u''],
    '[': [u'、', u'',   u''],
    ']': [u'゛', u'゜', u''],
    '8': [u'8',  u'',   u''],
    '9': [u'9',  u'（', u''],
    '0': [u'0',  u'）', u''],
}

_nicola_f_table_static = {
    ':': [u'、', u'',   u''],
    '@': [u'＠', u'',   u''],
    '[': [u'゛', u'゜', u''],
    ']': [u'」', u'',   u''],
    '8': [u'8',  u'（', u''],
    '9': [u'9',  u'）', u''],
    '0': [u'0',  u'',   u''],
}

_kb231_j_fmv_table_static = {
    '3': [u'3',  u'',   u'～'],
    '0': [u'0',  u'『', u''],
    '-': [u'-',  u'』', u''],
    '=': [u'=',  u'',   u''],
}

_kb231_a_fmv_table_static = {
    '3': [u'3',  u'',   u'～'],
    '0': [u'0',  u'）', u''],
    '-': [u'-',  u'『', u''],
    '=': [u'=',  u'』', u''],
}

_kb231_f_fmv_table_static = {
    '3': [u'3',  u'',   u'～'],
    '0': [u'0',  u'『', u''],
    '-': [u'-',  u'』', u''],
    '=': [u'=',  u'',   u''],
}

_kb611_j_fmv_table_static = {
    '`':  [u'‘', u'',   u''],
    '^':  [u'々', u'£',  u''],
    ':':  [u'：', u'',   u''],
    '@':  [u'、', u'¢',  u''],
    '[':  [u'゛', u'゜', u''],
    # keysyms are same and keycodes depend on the platforms.
    #'￥': [u'￥', u'¬',  u''],
    '\\': [u'￥', u'¦',  u''],
}

_kb611_a_fmv_table_static = {
    '`':  [u'々', u'',   u'£'],
    ':':  [u'：', u'',   u''],
    '@':  [u'＠', u'',   u''],
    '[':  [u'、', u'¢',  u''],
    #'￥': [u'￥', u'¬',  u''],
    '\\': [u'￥', u'¦',  u''],
}

_kb611_f_fmv_table_static = {
    '`':  [u'‘', u'',   u''],
    '^':  [u'々', u'£',  u''],
    ':':  [u'、', u'¢',  u''],
    '@':  [u'＠', u'',   u''],
    '[':  [u'゛', u'゜', u''],
    #'￥': [u'￥', u'¬',  u''],
    '\\': [u'￥', u'¦',  u''],
}

_shift_table = {
    'H': u'ぱ',
    'X': u'ぴ',
    'V': u'ぷ',
    'B': u'ぺ',
    '>': u'ぽ',
}

table_static = {}
r_table_static = {}

for k in _table_static.keys():
    table_static[ord(k)] = _table_static[k]
    for c in _table_static[k]:
        r_table_static[c] = k

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

class ThumbShiftKeyboard:
    def __init__(self, prefs=None):
        self.__prefs = prefs
        self.__table = table_static
        self.__r_table = r_table_static
        self.__shift_table = {}
        self.__ls = 0
        self.__rs = 0
        self.__t1 = 0
        self.__t2 = 0
        self.__layout = 0
        self.__fmv_extension = 2
        self.__handakuten = False
        self.__thumb_typing_rule_section = None
        self.__init_thumb_typing_rule()
        self.__init_layout_table()
        if self.__prefs != None:
            self.reset()
            self.__reset_shift_table(False)

    def __init_thumb_typing_rule(self):
        prefs = self.__prefs
        if prefs == None:
            self.__thumb_typing_rule_section = None
            return
        method = prefs.get_value('thumb_typing_rule', 'method')
        if method == None:
            method = _THUMB_BASIC_METHOD
        self.__thumb_typing_rule_section = 'thumb_typing_rule/' + method
        if self.__thumb_typing_rule_section not in prefs.sections():
            self.__thumb_typing_rule_section = None

    def __init_layout_table(self):
        if self.__table != {}:
            self.__table.clear()
        if self.__r_table != {}:
            self.__r_table.clear()
        section = self.__thumb_typing_rule_section
        if section != None:
            prefs = self.__prefs
            for k in prefs.keys(section):
                value = prefs.get_value(section, k)
                if value == None or len(value) != 3 or \
                   (str(value[0]) == '' and \
                    str(value[1]) == '' and str(value[2]) == ''):
                    continue
                value = [unicode(str(value[0])),
                         unicode(str(value[1])),
                         unicode(str(value[2]))]
                self.__table[ord(k)] = value
                for c in value:
                    self.__r_table[c] = k
        else:
            for k in _table.keys():
                self.__table[ord(k)] = _table_static[k]
                for c in _table_static[k]:
                    self.__r_table[c] = k

    def __reset_layout_table(self, init,
                             j_table_label, j_table,
                             a_table_label, a_table,
                             f_table_label, f_table):
        if init:
            self.__init_layout_table()
        method = None
        sub_table = None
        if self.__layout == 0:
            method = j_table_label
            sub_table = j_table
        elif self.__layout == 1:
            method = a_table_label
            sub_table = a_table
        elif self.__layout == 2:
            method = f_table_label
            sub_table = f_table
        if method == None or sub_table == None:
            return
        base_section = self.__thumb_typing_rule_section
        sub_section = 'thumb_typing_rule/' + method
        if base_section != None:
            prefs = self.__prefs
            for k in prefs.keys(sub_section):
                value = prefs.get_value(sub_section, k)
                if len(value) == 3 and value[0] == '' and \
                    value[1] == '' and value[2] == '':
                    continue
                self.__table[ord(k)] = value
                for c in value:
                    self.__r_table[c] = k
        else:
            for k in sub_table.keys():
                self.__table[ord(unicode(k))] = sub_table[k]
                for c in sub_table[k]:
                    self.__r_table[c] = k

    def __reset_extension_table(self, init):
        self.__reset_layout_table(init,
                                  "nicola_j_table",
                                  _nicola_j_table_static,
                                  "nicola_a_table",
                                  _nicola_a_table_static,
                                  "nicola_f_table",
                                  _nicola_f_table_static)
        if self.__fmv_extension == 0:
            return
        if self.__fmv_extension >= 1:
            self.__reset_layout_table(False,
                                      "kb231_j_fmv_table",
                                      _kb231_j_fmv_table_static,
                                      "kb231_a_fmv_table",
                                      _kb231_a_fmv_table_static,
                                      "kb231_f_fmv_table",
                                      _kb231_f_fmv_table_static)
        if self.__fmv_extension >= 2:
            self.__reset_layout_table(False,
                                      "kb611_j_fmv_table",
                                      _kb611_j_fmv_table_static,
                                      "kb611_a_fmv_table",
                                      _kb611_a_fmv_table_static,
                                      "kb611_f_fmv_table",
                                      _kb611_f_fmv_table_static)

    def __reset_shift_table(self, init):
        self.__reset_extension_table(init)
        if self.__handakuten:
            for k in _shift_table.keys():
                self.__shift_table[ord(k)] = _shift_table[k]
                self.__r_table[_shift_table[k]] = k
        elif self.__shift_table != {}:
            for k in _shift_table.keys():
                if ord(k) in self.__shift_table:
                    del self.__shift_table[ord(k)]
                if _shift_table[k] in self.__r_table:
                    del self.__r_table[_shift_table[k]]

    def __s_to_key_raw(self, s):
        keyval = keysyms.name_to_keycode(s.split('+')[-1])
        s = s.lower()
        state = ('shift+' in s and modifier.SHIFT_MASK or 0) | (
                 'ctrl+' in s and modifier.CONTROL_MASK or 0) | (
                 'alt+' in s and modifier.MOD1_MASK or 0)
        return (keyval, state)

    def __get_xkb_layout(self):
        root_window = get_default_root_window()
        if not root_window:
            return 0
        prop = root_window.property_get("_XKB_RULES_NAMES")[2]
        list = prop.split('\0')
        layout = 0
        for data in list:
            if data == "jp":
                layout = 0
            elif data == "us":
                layout = 1
            elif data.find("japan:nicola_f_bs") >= 0:
                layout = 2
            elif data.find("japan:") >= 0:
                layout = 0
        return layout

    def reset(self):
        s = self.__prefs.get_value('thumb', 'ls')
        ls, state = self.__s_to_key_raw(s)
        if ls == 0xffffff:
            ls = keysyms.Muhenkan
        self.set_ls(ls)

        s = self.__prefs.get_value('thumb', 'rs')
        rs, state = self.__s_to_key_raw(s)
        if rs == 0xffffff:
            rs = keysyms.Henkan
        self.set_rs(rs)

        t1 = self.__prefs.get_value('thumb', 't1')
        t2 = self.__prefs.get_value('thumb', 't2')
        self.set_t1(t1)
        self.set_t2(t2)

        mode = self.__prefs.get_value('thumb', 'keyboard_layout_mode')
        layout = 0
        if mode == 1:
            layout = self.__get_xkb_layout()
        else:
            layout = self.__prefs.get_value('thumb', 'keyboard_layout')
        self.set_layout(layout)

        fmv_extension = self.__prefs.get_value('thumb', 'fmv_extension')
        self.set_fmv_extension(fmv_extension)
        handakuten = self.__prefs.get_value('thumb', 'handakuten')
        self.set_handakuten(handakuten)

    def get_ls(self):
        return self.__ls

    def set_ls(self, ls):
        self.__ls = ls

    def get_rs(self):
        return self.__rs

    def set_rs(self, rs):
        self.__rs = rs

    def get_t1(self):
        return self.__t1

    def set_t1(self, t1):
        self.__t1 = t1

    def get_t2(self):
        return self.__t2

    def set_t2(self, t2):
        self.__t2 = t2

    def get_layout(self):
        return self.__layout

    def set_layout(self, layout):
        if self.__layout == layout:
            return
        self.__layout = layout
        self.__reset_shift_table(True)

    def get_fmv_extension (self):
        return self.__fmv_extension

    def set_fmv_extension (self, fmv_extension):
        if self.__fmv_extension == fmv_extension:
            return
        self.__fmv_extension = fmv_extension
        self.__reset_shift_table(True)

    def get_handakuten(self):
        return self.__handakuten

    def set_handakuten(self, handakuten):
        if self.__handakuten == handakuten:
            return
        self.__handakuten = handakuten
        self.__reset_shift_table(True)

    def get_char(self, key, fallback=None):
        return self.__table.get(key, fallback)

    def get_chars(self):
        return self.__table.keys()

    def get_r_char(self, key, fallback=None):
        return self.__r_table.get(key, fallback)

    def get_r_chars(self):
        return self.__r_table.keys()

    def get_shift_char(self, key, fallback=None):
        return self.__shift_table.get(key, fallback)

    def get_shift_chars(self):
        return self.__shift_table.keys()


class ThumbShiftSegment(segment.Segment):
    _prefs = None
    _thumb_typing_rule_section = None
    _r_table = {}

    def __init__(self, enchars=u"", jachars=u""):
        if not jachars:
            if u'!' <= enchars <= u'~':
                jachars = segment.unichar_half_to_full(enchars)
            else:
                jachars = enchars
                enchars = self._r_table.get(jachars, u'')
        super(ThumbShiftSegment, self).__init__(enchars, jachars)

    @classmethod
    def _init_thumb_typing_rule(cls, prefs):
        cls._prefs = prefs
        if prefs == None:
            cls._thumb_typing_rule_section = None
            return
        method = prefs.get_value('thumb_typing_rule', 'method')
        if method == None:
            method = _THUMB_BASIC_METHOD
        cls._thumb_typing_rule_section = 'thumb_typing_rule/' + method
        if cls._thumb_typing_rule_section not in prefs.sections():
            cls._thumb_typing_rule_section = None
        cls._init_layout_table()

    @classmethod
    def _init_layout_table(cls):
        if cls._r_table != {}:
            cls._r_table.clear()
        section = cls._thumb_typing_rule_section
        if section != None:
            prefs = cls._prefs
            for k in prefs.keys(section):
                value = prefs.get_value(section, k)
                if value == None or len(value) != 3 or \
                   (str(value[0]) == '' and \
                    str(value[1]) == '' and str(value[2]) == ''):
                    continue
                value = [unicode(str(value[0])),
                         unicode(str(value[1])),
                         unicode(str(value[2]))]
                for c in value:
                    cls._r_table[c] = k
        else:
            for k in _table.keys():
                for c in _table_static[k]:
                    cls._r_table[c] = k

    def is_finished(self):
        return not (self._jachars in _UNFINISHED_HIRAGANA)

    def append(self, enchar):
        if enchar == u"\0" or enchar == u"":
            return []
        text = self._jachars + enchar
        jachars = kana_voiced_consonant_rule.get(text, None)
        if jachars:
            self._enchars = self._enchars + self._r_table.get(enchar, u'')
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
                self._enchars = self._r_table.get(enchar, u'')
                self._jachars = enchar
            return []
        return [ThumbShiftSegment(enchar)]

    def pop(self, index=-1):
        self._enchars = u''
        self._jachars = u''
        return

