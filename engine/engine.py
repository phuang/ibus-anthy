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

import gobject
import ibus
import anthy
from tables import *
from ibus import keysyms
from ibus import modifier
import jastring

from gettext import dgettext
_  = lambda a : dgettext("ibus-anthy", a)
N_ = lambda a : a

INPUT_MODE_HIRAGANA, \
INPUT_MODE_KATAKANA, \
INPUT_MODE_HALF_WIDTH_KATAKANA, \
INPUT_MODE_LATIN, \
INPUT_MODE_WIDE_LATIN = range(5)

TYPING_MODE_ROMAJI, \
TYPING_MODE_KANA, \
TYPING_MODE_THUMB_SHIFT = range(3)

CONV_MODE_OFF, \
CONV_MODE_ANTHY, \
CONV_MODE_HIRAGANA, \
CONV_MODE_KATAKANA, \
CONV_MODE_HALF_WIDTH_KATAKANA, \
CONV_MODE_LATIN_1, \
CONV_MODE_LATIN_2, \
CONV_MODE_LATIN_3, \
CONV_MODE_WIDE_LATIN_1, \
CONV_MODE_WIDE_LATIN_2, \
CONV_MODE_WIDE_LATIN_3 = range(11)

class Engine(ibus.EngineBase):
    def __init__(self, bus, object_path):
        super(Engine, self).__init__(bus, object_path)

        # create anthy context
        self.__context = anthy.anthy_context()
        self.__context._set_encoding(anthy.ANTHY_UTF8_ENCODING)

        # init state
        self.__input_mode = INPUT_MODE_HIRAGANA
        self.__typing_method = TYPING_MODE_ROMAJI
        self.__prop_dict = {}

        self.__lookup_table = ibus.LookupTable(page_size=9)
        self.__prop_list = self.__init_props()

        # use reset to init values
        self.__reset()

    # reset values of engine
    def __reset(self):
        self.__preedit_ja_string = jastring.JaString()
        self.__convert_chars = u""
        self.__cursor_pos = 0
        self.__need_update = False
        self.__convert_mode = CONV_MODE_OFF
        self.__segments = list()
        self.__lookup_table.clean()
        self.__lookup_table_visible = False

    def __init_props(self):
        props = ibus.PropList()

        # init input mode properties
        mode_prop = ibus.Property(name = u"InputMode",
                            type = ibus.PROP_TYPE_MENU,
                            label = u"あ",
                            tooltip = _(u"Switch input mode"))
        self.__prop_dict[u"InputMode"] = mode_prop

        mode_props = ibus.PropList()
        mode_props.append(ibus.Property(name = u"InputMode.Hiragana",
                                        type = ibus.PROP_TYPE_RADIO,
                                        label = _(u"Hiragana")))
        mode_props.append(ibus.Property(name = u"InputMode.Katakana",
                                        type = ibus.PROP_TYPE_RADIO,
                                        label = _(u"Katakana")))
        mode_props.append(ibus.Property(name = u"InputMode.HalfWidthKatakana",
                                        type = ibus.PROP_TYPE_RADIO,
                                        label = _(u"Half width katakana")))
        mode_props.append(ibus.Property(name = u"InputMode.Latin",
                                        type = ibus.PROP_TYPE_RADIO,
                                        label = _(u"Latin")))
        mode_props.append(ibus.Property(name = u"InputMode.WideLatin",
                                        type = ibus.PROP_TYPE_RADIO,
                                        label = _(u"Wide Latin")))

        mode_props[self.__input_mode].set_state(ibus.PROP_STATE_CHECKED)

        for prop in mode_props:
            self.__prop_dict[prop.name] = prop

        mode_prop.set_sub_props(mode_props)
        props.append(mode_prop)

        return props

    def page_up(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_up():
            return False

        candidate = self.__lookup_table.get_current_candidate()[0]
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def page_down(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_down():
            return False

        candidate = self.__lookup_table.get_current_candidate()[0]
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def cursor_up(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.cursor_up():
            return False

        candidate = self.__lookup_table.get_current_candidate()[0]
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def cursor_down(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.cursor_down():
            return False

        candidate = self.__lookup_table.get_current_candidate()[0]
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def __commit_string(self, text):
        self.__reset()
        self.commit_string(text)
        self.__invalidate()

    def __shrink_segment(self, relative_size):
        self.__context.resize_segment(self.__cursor_pos, relative_size)
        conv_stat = anthy.anthy_conv_stat()
        self.__context.get_stat(conv_stat)
        del self.__segments[self.__cursor_pos:]
        for i in xrange(self.__cursor_pos, conv_stat.nr_segment):
            buf = self.__context.get_segment(i, 0)
            text = unicode(buf, "utf-8")
            self.__segments.append((0, text))
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def process_key_event(self, keyval, is_press, state):

        state = state & (modifier.SHIFT_MASK | \
                modifier.CONTROL_MASK | \
                modifier.MOD1_MASK)

        # ignore key release events
        if not is_press:
            return False

        if state == modifier.SHIFT_MASK:
            if self.__convert_mode == CONV_MODE_ANTHY:
                if keyval == keysyms.Left:
                    self.__shrink_segment(-1)
                    return True
                elif keyval == keysyms.Right:
                    self.__shrink_segment(1)
                    return True

        if state & (modifier.CONTROL_MASK | modifier.MOD1_MASK) != 0:
            if not self.__preedit_ja_string.is_empty():
                # if user has inputed some chars
                return True
            return False

        if keyval == keysyms.Return:
            return self.__on_key_return()
        elif keyval == keysyms.Escape:
            return self.__on_key_escape()
        elif keyval == keysyms.BackSpace:
            return self.__on_key_back_space()
        elif keyval == keysyms.Delete or keyval == keysyms.KP_Delete:
            return self.__on_key_delete()
        elif keyval == keysyms.space:
            return self.__on_key_space()
        elif keyval >= keysyms._0 and keyval <= keysyms._9:
            if self.__on_key_number(keyval):
                return True
            return self.__on_key_common(keyval)
        elif keyval == keysyms.Page_Up or keyval == keysyms.KP_Page_Up:
            return self.__on_key_page_up()
        elif keyval == keysyms.Page_Down or keyval == keysyms.KP_Page_Down:
            return self.__on_key_page_down()
        elif keyval == keysyms.Up:
            return self.__on_key_up()
        elif keyval == keysyms.Down:
            return self.__on_key_down()
        elif keyval == keysyms.Left:
            return self.__on_key_left()
        elif keyval == keysyms.Right:
            return self.__on_key_right()
        elif keyval >= keysyms.F6 and keyval <= keysyms.F9:
            return self.__on_key_conv(keyval - keysyms.F6)
        elif keyval >= keysyms.exclam and keyval <= keysyms.asciitilde:
            return self.__on_key_common(keyval)
        else:
            if not self.__preedit_ja_string.is_empty():
                return True
            return False

    def property_activate(self, prop_name, state):
        prop = self.__prop_dict[prop_name]
        prop.set_state(state)

        if state == ibus.PROP_STATE_CHECKED:
            if prop_name == u"InputMode.Hiragana":
                prop = self.__prop_dict[u"InputMode"]
                prop.label = u"あ"
                self.__input_mode = INPUT_MODE_HIRAGANA
                self.update_property(prop)
                self.__reset()
                self.__invalidate()
            elif prop_name == u"InputMode.Katakana":
                prop = self.__prop_dict[u"InputMode"]
                prop.label = u"ア"
                self.__input_mode = INPUT_MODE_KATAKANA
                self.update_property(prop)
                self.__reset()
                self.__invalidate()
            elif prop_name == u"InputMode.HalfWidthKatakana":
                prop = self.__prop_dict[u"InputMode"]
                prop.label = u"_ｱ"
                self.__input_mode = INPUT_MODE_HALF_WIDTH_KATAKANA
                self.update_property(prop)
                self.__reset()
                self.__invalidate()
            elif prop_name == u"InputMode.Latin":
                prop = self.__prop_dict[u"InputMode"]
                self.__input_mode = INPUT_MODE_LATIN
                prop.label = u"_A"
                self.update_property(prop)
                self.__reset()
                self.__invalidate()
            elif prop_name == u"InputMode.WideLatin":
                prop = self.__prop_dict[u"InputMode"]
                prop.label = u"Ａ"
                self.__input_mode = INPUT_MODE_WIDE_LATIN
                self.update_property(prop)
                self.__reset()
                self.__invalidate()

    def focus_in(self):
        self.register_properties(self.__prop_list)

    def focus_out(self):
        pass

    # begine convert
    def __begin_anthy_convert(self):
        if self.__convert_mode == CONV_MODE_ANTHY:
            return
        self.__convert_mode = CONV_MODE_ANTHY

        self.__preedit_ja_string.insert(u"\0")

        text, cursor = self.__preedit_ja_string.get_hiragana()

        self.__context.set_string(text.encode("utf8"))
        conv_stat = anthy.anthy_conv_stat()
        self.__context.get_stat(conv_stat)

        for i in xrange(0, conv_stat.nr_segment):
            buf = self.__context.get_segment(i, 0)
            text = unicode(buf, "utf-8")
            self.__segments.append((0, text))

        self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False

    def __end_anthy_convert(self):
        if self.__convert_mode == CONV_MODE_OFF:
            return

        self.__convert_mode = CONV_MODE_OFF
        self.__convert_chars = u""
        self.__segments = list()
        self.__cursor_pos = 0
        self.__lookup_table.clean()
        self.__lookup_table_visible = False

    def __end_convert(self):
        self.__end_anthy_convert()

    def __fill_lookup_table(self):
        # get segment stat
        seg_stat = anthy.anthy_segment_stat()
        self.__context.get_segment_stat(self.__cursor_pos, seg_stat)

        # fill lookup_table
        self.__lookup_table.clean()
        for i in xrange(0, seg_stat.nr_candidate):
            buf = self.__context.get_segment(self.__cursor_pos, i)
            candidate = unicode(buf, "utf-8")
            self.__lookup_table.append_candidate(candidate)


    def __invalidate(self):
        if self.__need_update:
            return
        self.__need_update = True
        gobject.idle_add(self.__update, priority = gobject.PRIORITY_LOW)

    def __get_preedit(self):
        if self.__input_mode == INPUT_MODE_HIRAGANA:
            text, cursor = self.__preedit_ja_string.get_hiragana()
        elif self.__input_mode == INPUT_MODE_KATAKANA:
            text, cursor = self.__preedit_ja_string.get_katakana()
        elif self.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
        else:
            text, cursor = u"", 0
        return text, cursor

    def __update_input_chars(self):
        text, cursor = self.__get_preedit()
        attrs = ibus.AttrList()
        attrs.append(ibus.AttributeUnderline(
            ibus.ATTR_UNDERLINE_SINGLE, 0,
            len(text)))

        self.update_preedit(text,
            attrs, cursor, not self.__preedit_ja_string.is_empty())
        self.update_aux_string(u"", ibus.AttrList(), False)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update_convert_chars(self):
        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__update_anthy_convert_chars()
            return
        if self.__convert_mode == CONV_MODE_HIRAGANA:
            text, cursor = self.__preedit_ja_string.get_hiragana()
        elif self.__convert_mode == CONV_MODE_KATAKANA:
            text, cursor = self.__preedit_ja_string.get_katakana()
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
        elif self.__convert_mode == CONV_MODE_LATIN_1:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.lower()
        elif self.__convert_mode == CONV_MODE_LATIN_2:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.upper()
        elif self.__convert_mode == CONV_MODE_LATIN_3:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.capitalize()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_1:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            text = text.lower()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_2:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            text = text.upper()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_3:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            text = text.capitalize()
        self.__convert_chars = text
        attrs = ibus.AttrList()
        attrs.append(ibus.AttributeUnderline(
            ibus.ATTR_UNDERLINE_SINGLE, 0, len(text)))
        attrs.append(ibus.AttributeBackground(ibus.RGB(200, 200, 240),
            0, len(text)))
        attrs.append(ibus.AttributeForeground(ibus.RGB(0, 0, 0),
            0, len(text)))
        self.update_preedit(text, attrs, len(text), True)

        self.update_aux_string(u"",
            ibus.AttrList(), self.__lookup_table_visible)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update_anthy_convert_chars(self):
        self.__convert_chars = u""
        pos = 0
        i = 0
        for seg_index, text in self.__segments:
            self.__convert_chars += text
            if i < self.__cursor_pos:
                pos += len(text)
            i += 1
        attrs = ibus.AttrList()
        attrs.append(ibus.AttributeUnderline(
            ibus.ATTR_UNDERLINE_SINGLE, 0, len(self.__convert_chars)))
        attrs.append(ibus.AttributeBackground(ibus.RGB(200, 200, 240),
                pos, pos + len(self.__segments[self.__cursor_pos][1])))
        attrs.append(ibus.AttributeForeground(ibus.RGB(0, 0, 0),
                pos, pos + len(self.__segments[self.__cursor_pos][1])))
        self.update_preedit(self.__convert_chars, attrs, pos, True)
        aux_string = u"( %d / %d )" % (self.__lookup_table.get_cursor_pos() + 1, self.__lookup_table.get_number_of_candidates())
        self.update_aux_string(aux_string,
            ibus.AttrList(), self.__lookup_table_visible)
        self.update_lookup_table(self.__lookup_table,
            self.__lookup_table_visible)

    def __update(self):
        self.__need_update = False
        if self.__convert_mode == CONV_MODE_OFF:
            self.__update_input_chars()
        else:
            self.__update_convert_chars()

    def __on_key_return(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            text, cursor = self.__get_preedit()
            self.__commit_string(text)
        elif self.__convert_mode == CONV_MODE_ANTHY:
            i = 0
            for seg_index, text in self.__segments:
                self.__context.commit_segment(i, seg_index)
            self.__commit_string(self.__convert_chars)
        else:
            self.__commit_string(self.__convert_chars)

        return True

    def __on_key_escape(self):
        if self.__preedit_ja_string.is_empty():
            return False
        self.__reset()
        self.__invalidate()
        return True

    def __on_key_back_space(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode != CONV_MODE_OFF:
            self.__end_convert()
        else:
            self.__preedit_ja_string.remove_before()

        self.__invalidate()
        return True

    def __on_key_delete(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode != CONV_MODE_OFF:
            self.__end_convert()
        else:
            self.__preedit_ja_string.remove_after()

        self.__invalidate()
        return True

    def __on_key_space(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode != CONV_MODE_ANTHY:
            self.__begin_anthy_convert()
            self.__invalidate()
        elif self.__convert_mode == CONV_MODE_ANTHY:
            self.__lookup_table_visible = True
            self.cursor_down()
        return True

    def __on_key_up(self):
        if self.__preedit_ja_string.is_empty():
            return False
        self.__lookup_table_visible = True
        self.cursor_up()
        return True

    def __on_key_down(self):
        if self.__preedit_ja_string.is_empty():
            return False
        self.__lookup_table_visible = True
        self.cursor_down()
        return True

    def __on_key_page_up(self):
        if self.__preedit_ja_string.is_empty():
            return False
        if self.__lookup_table_visible == True:
            self.page_up()
        return True

    def __on_key_page_down(self):
        if self.__preedit_ja_string.is_empty():
            return False
        if self.__lookup_table_visible == True:
            self.page_down()
        return True

    def __on_key_left(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            self.__preedit_ja_string.move_cursor(-1)
            self.__invalidate()
            return True

        if self.__convert_mode != CONV_MODE_ANTHY:
            return True

        if self.__cursor_pos == 0:
            return True
        self.__cursor_pos -= 1
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def __on_key_right(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            self.__preedit_ja_string.move_cursor(1)
            self.__invalidate()
            return True

        if self.__convert_mode != CONV_MODE_ANTHY:
            return True

        if self.__cursor_pos + 1 >= len(self.__segments):
            return True

        self.__cursor_pos += 1
        self.__lookup_table_visible = False
        self.__fill_lookup_table()
        self.__invalidate()
        return True

    def __on_key_number(self, keyval):
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False
        if not self.__lookup_table_visible:
            return False

        if keyval == keysyms._0:
            return True
        index = keyval - keysyms._1

        candidates = self.__lookup_table.get_canidates_in_current_page()
        if self.__lookup_table.set_cursor_pos_in_current_page(index):
            index = self.__lookup_table.get_cursor_pos()
            candidate = self.__lookup_table.get_current_candidate()[0]
            self.__segments[self.__cursor_pos] = index, candidate
            self.__lookup_table_visible = False
            self.__on_key_right()
            self.__invalidate()
        return True

    def __on_key_conv(self, mode):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__end_anthy_convert()

        if mode == 0 or mode == 1:
            if self.__convert_mode == CONV_MODE_HIRAGANA + mode:
                return True
            self.__convert_mode = CONV_MODE_HIRAGANA + mode
        elif mode == 2:
            if self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
                return True
            if self.__convert_mode == CONV_MODE_HIRAGANA or \
                self.__convert_mode == CONV_MODE_KATAKANA or \
                self.__convert_mode == CONV_MODE_OFF or \
                self.__convert_mode == CONV_MODE_ANTHY:
                self.__convert_mode = CONV_MODE_HALF_WIDTH_KATAKANA
            else:
                if self.__convert_mode >= CONV_MODE_LATIN_1 and self.__convert_mode <= CONV_MODE_LATIN_3:
                    self.__convert_mode += 1
                    if self.__convert_mode > CONV_MODE_LATIN_3:
                        self.__convert_mode = CONV_MODE_LATIN_1
                else:
                    self.__convert_mode = CONV_MODE_LATIN_1
        elif mode == 3:
            if self.__convert_mode >= CONV_MODE_WIDE_LATIN_1 and self.__convert_mode <= CONV_MODE_WIDE_LATIN_3:
                self.__convert_mode += 1
                if self.__convert_mode > CONV_MODE_WIDE_LATIN_3:
                    self.__convert_mode = CONV_MODE_WIDE_LATIN_1
            else:
                self.__convert_mode = CONV_MODE_WIDE_LATIN_1
        else:
            print >> sys.stderr, "Unkown convert mode (%d)!" % mode
            return False
        self.__invalidate()
        return True

    def __on_key_common(self, keyval):

        if self.__input_mode == INPUT_MODE_LATIN:
            # Input Latin chars
            char = unichr(keyval)
            self.__commit_string(char)
            return True

        elif self.__input_mode == INPUT_MODE_WIDE_LATIN:
            #  Input Wide Latin chars
            char = unichr(keyval)
            wide_char = symbol_rule.get(char, None)
            if wide_char == None:
                wide_char = ibus.unichar_half_to_full(char)
            self.__commit_string(wide_char)
            return True

        # Input Japanese
        if self.__convert_mode == CONV_MODE_ANTHY:
            i = 0
            for seg_index, text in self.__segments:
                self.__context.commit_segment(i, seg_index)
            self.__commit_string(self.__convert_chars)
        elif self.__convert_mode != CONV_MODE_OFF:
            self.__commit_string(self.__convert_chars)

        self.__preedit_ja_string.insert(unichr(keyval))
        self.__invalidate()
        return True

