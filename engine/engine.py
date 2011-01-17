# vim:set et sts=4 sw=4:
# -*- coding: utf-8 -*-
#
# ibus-anthy - The Anthy engine for IBus
#
# Copyright (c) 2007-2008 Peng Huang <shawn.p.huang@gmail.com>
# Copyright (c) 2007-2011 Red Hat, Inc.
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

import os
from os import environ, path
from locale import getpreferredencoding
import signal
import sys
import gobject
import ibus
import anthy
from anthy import NTH_UNCONVERTED_CANDIDATE
from anthy import NTH_KATAKANA_CANDIDATE
from anthy import NTH_HIRAGANA_CANDIDATE
from anthy import NTH_HALFKANA_CANDIDATE
from tables import *
from ibus import keysyms
from ibus import modifier
import jastring
from segment import unichar_half_to_full

try:
    from gtk import clipboard_get
except ImportError:
    clipboard_get = lambda a : None

sys.path.append(path.join(os.getenv('IBUS_ANTHY_PKGDATADIR'), 'setup'))
from anthyprefs import AnthyPrefs

from gettext import dgettext
_  = lambda a : dgettext("ibus-anthy", a)
N_ = lambda a : a
UN = lambda a : unicode(a)

INPUT_MODE_HIRAGANA, \
INPUT_MODE_KATAKANA, \
INPUT_MODE_HALF_WIDTH_KATAKANA, \
INPUT_MODE_LATIN, \
INPUT_MODE_WIDE_LATIN = range(5)

CONV_MODE_OFF, \
CONV_MODE_ANTHY, \
CONV_MODE_HIRAGANA, \
CONV_MODE_KATAKANA, \
CONV_MODE_HALF_WIDTH_KATAKANA, \
CONV_MODE_LATIN_0, \
CONV_MODE_LATIN_1, \
CONV_MODE_LATIN_2, \
CONV_MODE_LATIN_3, \
CONV_MODE_WIDE_LATIN_0, \
CONV_MODE_WIDE_LATIN_1, \
CONV_MODE_WIDE_LATIN_2, \
CONV_MODE_WIDE_LATIN_3, \
CONV_MODE_PREDICTION = range(14)

SEGMENT_DEFAULT         = 0
SEGMENT_SINGLE          = 1 << 0
SEGMENT_IMMEDIATE       = 1 << 1

CLIPBOARD_RECONVERT = range(1)

LINK_DICT_EMBEDDED, \
LINK_DICT_SINGLE = range(2)

IMPORTED_EMBEDDED_DICT_DIR = "imported_words_default.d"
IMPORTED_EMBEDDED_DICT_PREFIX = "ibus__"
IMPORTED_SINGLE_DICT_PREFIX = "imported_words_ibus__"

KP_Table = {}
for s in dir(keysyms):
    if s.startswith('KP_'):
        v = keysyms.name_to_keycode(s[3:])
        if v:
            KP_Table[keysyms.name_to_keycode(s)] = v
for k, v in zip(['KP_Add', 'KP_Decimal', 'KP_Divide', 'KP_Enter', 'KP_Equal',
                 'KP_Multiply', 'KP_Separator', 'KP_Space', 'KP_Subtract'],
                ['plus', 'period', 'slash', 'Return', 'equal',
                 'asterisk', 'comma', 'space', 'minus']):
    KP_Table[keysyms.__getattribute__(k)] = keysyms.__getattribute__(v)

class Engine(ibus.EngineBase):
    __typing_mode = jastring.TYPING_MODE_ROMAJI

    __setup_pid = 0
    __prefs = None
    __keybind = {}
    __thumb = None

    def __init__(self, bus, object_path):
        super(Engine, self).__init__(bus, object_path)

        # create anthy context
        self.__context = anthy.anthy_context()
        self.__context._set_encoding(anthy.ANTHY_UTF8_ENCODING)

        # init state
        self.__idle_id = 0
        self.__input_mode = INPUT_MODE_HIRAGANA
        self.__segment_mode = SEGMENT_DEFAULT
        self.__dict_mode = 0
        self.__prop_dict = {}
        self.__is_utf8 = (getpreferredencoding().lower() == "utf-8")
        self.__ibus_version = 0

#        self.__lookup_table = ibus.LookupTable(page_size=9, round=True)
        size = self.__prefs.get_value('common', 'page_size')
        self.__lookup_table = ibus.LookupTable(page_size=size, round=True)
        self.__prop_list = self.__init_props()

        mode = self.__prefs.get_value('common', 'input_mode')
        mode = 'InputMode.' + ['Hiragana', 'Katakana', 'HalfWidthKatakana',
                               'Latin', 'WideLatin'][mode]
        self.__input_mode_activate(mode, ibus.PROP_STATE_CHECKED)

        mode = self.__prefs.get_value('common', 'typing_method')
        mode = 'TypingMode.' + ['Romaji', 'Kana', 'ThumbShift'][mode]
        self.__typing_mode_activate(mode, ibus.PROP_STATE_CHECKED)

        mode = self.__prefs.get_value('common', 'conversion_segment_mode')
        mode = 'SegmentMode.' + ['Multi', 'Single',
                                 'ImmediateMulti', 'ImmediateSingle'][mode]
        self.__segment_mode_activate(mode, ibus.PROP_STATE_CHECKED)

        self.__init_ibus_version()

        # use reset to init values
        self.__reset()

    def __init_ibus_version(self):
        version_str = ibus.get_version()
        if version_str == None:
            return
        versions = version_str.split('.')
        if len(versions) < 3:
            print >> sys.stderr, \
                "ibus.get_version returns incorrect str \"" + \
                version_str + "\""
            return
        version_str = "%03d%03d%03d" % \
            (int(versions[0]), int(versions[1]), int(versions[2]))
        self.__ibus_version = long(version_str)

    # reset values of engine
    def __reset(self):
        self.__preedit_ja_string = jastring.JaString(Engine.__typing_mode)
        self.__convert_chars = u""
        self.__cursor_pos = 0
        self.__convert_mode = CONV_MODE_OFF
        self.__segments = list()
        self.__lookup_table.clean()
        self.__lookup_table_visible = False
        self._MM = 0
        self._SS = 0
        self._H = 0
        self._RMM = 0
        self._RSS = 0
        if self.__idle_id != 0:
            gobject.source_remove(self.__idle_id)
            self.__idle_id = 0

    def __init_props(self):
        anthy_props = ibus.PropList()

        # init input mode properties
        input_mode_prop = ibus.Property(key=u"InputMode",
                                        type=ibus.PROP_TYPE_MENU,
                                        label=u"あ",
                                        tooltip=UN(_("Switch input mode")))
        self.__prop_dict[u"InputMode"] = input_mode_prop

        props = ibus.PropList()
        props.append(ibus.Property(key=u"InputMode.Hiragana",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Hiragana"))))
        props.append(ibus.Property(key=u"InputMode.Katakana",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Katakana"))))
        props.append(ibus.Property(key=u"InputMode.HalfWidthKatakana",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Half width katakana"))))
        props.append(ibus.Property(key=u"InputMode.Latin",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Latin"))))
        props.append(ibus.Property(key=u"InputMode.WideLatin",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Wide Latin"))))

        props[self.__input_mode].set_state(ibus.PROP_STATE_CHECKED)

        for prop in props:
            self.__prop_dict[prop.key] = prop

        input_mode_prop.set_sub_props(props)
        anthy_props.append(input_mode_prop)

        # typing input mode properties
        typing_mode_prop = ibus.Property(key=u"TypingMode",
                                         type=ibus.PROP_TYPE_MENU,
                                         label=u"R",
                                         tooltip=UN(_("Switch typing mode")))
        self.__prop_dict[u"TypingMode"] = typing_mode_prop

        props = ibus.PropList()
        props.append(ibus.Property(key=u"TypingMode.Romaji",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Romaji"))))
        props.append(ibus.Property(key=u"TypingMode.Kana",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Kana"))))
        props.append(ibus.Property(key=u"TypingMode.ThumbShift",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Thumb shift"))))
        props[Engine.__typing_mode].set_state(ibus.PROP_STATE_CHECKED)

        for prop in props:
            self.__prop_dict[prop.key] = prop

        typing_mode_prop.set_sub_props(props)
        anthy_props.append(typing_mode_prop)

        self.__set_segment_mode_props(anthy_props)
        self.__set_dict_mode_props(anthy_props)
        self.__set_dict_config_props(anthy_props)
        anthy_props.append(ibus.Property(key=u"setup",
                                         label=UN(_("Preferences - Anthy")),
                                         icon=u"gtk-preferences",
                                         tooltip=UN(_("Configure Anthy"))))

        return anthy_props

    def __init_signal(self):
        signal.signal(signal.SIGHUP, self.__signal_cb)
        signal.signal(signal.SIGINT, self.__signal_cb)
        signal.signal(signal.SIGQUIT, self.__signal_cb)
        signal.signal(signal.SIGABRT, self.__signal_cb)
        signal.signal(signal.SIGTERM, self.__signal_cb)

    def __signal_cb(self, signum, object):
        self.__remove_dict_files()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    def __set_segment_mode_props(self, anthy_props):
        segment_mode_prop = ibus.Property(key=u"SegmentMode",
                                          type=ibus.PROP_TYPE_MENU,
                                          label=u"連",
                                          tooltip=UN(_("Switch conversion mode")))
        self.__prop_dict[u"SegmentMode"] = segment_mode_prop

        props = ibus.PropList()
        props.append(ibus.Property(key=u"SegmentMode.Multi",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Multiple segment"))))
        props.append(ibus.Property(key=u"SegmentMode.Single",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Single segment"))))
        props.append(ibus.Property(key=u"SegmentMode.ImmediateMulti",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Immediate conversion (Multiple segment)"))))
        props.append(ibus.Property(key=u"SegmentMode.ImmediateSingle",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_("Immediate conversion (Single segment)"))))
        props[self.__segment_mode].set_state(ibus.PROP_STATE_CHECKED)

        for prop in props:
            self.__prop_dict[prop.key] = prop

        segment_mode_prop.set_sub_props(props)
        anthy_props.append(segment_mode_prop)

    def __set_dict_mode_props(self, anthy_props):
        short_label = self.__prefs.get_value('dict/file/embedded',
                                             'short_label')
        dict_mode_prop = ibus.Property(key=u"DictMode",
                                       type=ibus.PROP_TYPE_MENU,
                                       label=UN(short_label),
                                       tooltip=UN(_("Switch Dictionary")))
        self.__prop_dict[u"DictMode"] = dict_mode_prop
        props = ibus.PropList()

        long_label = self.__prefs.get_value('dict/file/embedded',
                                            'long_label')
        props.append(ibus.Property(key=u"DictMode.embedded",
                                   type=ibus.PROP_TYPE_RADIO,
                                   label=UN(_(long_label))))

        for file in self.__prefs.get_value('dict', 'files'):
            self._link_dict_file(file)
            id = self._get_dict_id_from_file(file)
            if id == None:
                continue
            section = 'dict/file/' + id
            if not self.__prefs.get_value(section, 'single'):
                continue
            key = "DictMode." + id
            long_label = self.__prefs.get_value(section, 'long_label')
            if 'is_system' in self.__prefs.keys(section) and \
               self.__prefs.get_value(section, 'is_system'):
                uni_long_label = UN(_(long_label))
            else:
                uni_long_label = UN(long_label)
            props.append(ibus.Property(key=UN(key),
                                       type=ibus.PROP_TYPE_RADIO,
                                       label=uni_long_label))

        props[self.__dict_mode].set_state(ibus.PROP_STATE_CHECKED)
        for prop in props:
            self.__prop_dict[prop.key] = prop
        dict_mode_prop.set_sub_props(props)
        anthy_props.append(dict_mode_prop)
        self.__init_signal()

    def __set_dict_config_props(self, anthy_props):
        admin_command = self.__prefs.get_value('common', 'dict_admin_command')
        icon_path = self.__prefs.get_value('common', 'dict_config_icon')

        if not path.exists(admin_command[0]):
            return
        label = UN(_("Dictionary - Anthy"))
        if icon_path and path.exists(icon_path):
            icon = unicode(icon_path)
        else:
            # Translators: "Dic" means 'dictionary', One kanji may be good.
            label = UN(_("Dic"))
            icon = u""

        dict_prop = ibus.Property(key=u"setup-dict-kasumi",
                                  type=ibus.PROP_TYPE_MENU,
                                  label=label,
                                  icon=icon,
                                  tooltip=UN(_("Configure dictionaries")))

        props = ibus.PropList()
        props.append(ibus.Property(key=u"setup-dict-kasumi-admin",
                                   type=ibus.PROP_TYPE_NORMAL,
                                   label=UN(_("Edit dictionaries")),
                                   icon=icon,
                                   tooltip=UN(_("Launch the dictionary tool"))))
        props.append(ibus.Property(key=u"setup-dict-kasumi-word",
                                   type=ibus.PROP_TYPE_NORMAL,
                                   label=UN(_("Add words")),
                                   icon=icon,
                                   tooltip=UN(_("Add words in the dictionary"))))

        dict_prop.set_sub_props(props)
        anthy_props.append(dict_prop)

    def __get_clipboard(self, clipboard, text, data):
        clipboard_text = clipboard.wait_for_text ()

        if data == CLIPBOARD_RECONVERT:
            self.__update_reconvert(clipboard_text)

        return clipboard_text

    def __get_single_dict_files(self):
        files = self.__prefs.get_value('dict', 'files')
        single_files = []
        for file in files:
            id = self._get_dict_id_from_file(file)
            if id == None:
                continue
            section = 'dict/file/' + id
            if self.__prefs.get_value(section, 'single'):
                single_files.append(file)
        return single_files

    def __remove_dict_files(self):
        for file in self.__prefs.get_value('dict', 'files'):
            self._remove_dict_file(file)

    def update_preedit(self, string, attrs, cursor_pos, visible):
        mode = self.__prefs.get_value('common', 'behavior_on_focus_out')
        if self.__ibus_version >= 1003000 and mode == 1:
            self.update_preedit_text(ibus.Text(string, attrs),
                                     cursor_pos, visible,
                                     ibus.common.IBUS_ENGINE_PREEDIT_COMMIT)
        else:
            self.update_preedit_text(ibus.Text(string, attrs),
                                     cursor_pos, visible)

    def update_aux_string(self, string, attrs, visible):
        self.update_auxiliary_text(ibus.Text(string, attrs), visible)

    def page_up(self):
        # only process cursor down in convert mode
        if self.__convert_mode != CONV_MODE_ANTHY:
            return False

        if not self.__lookup_table.page_up():
            return False

        candidate = self.__lookup_table.get_current_candidate().text
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

        candidate = self.__lookup_table.get_current_candidate().text
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def cursor_up(self):
        # only process cursor down in convert mode
        # if self.__convert_mode != CONV_MODE_ANTHY:
        if self.__convert_mode != CONV_MODE_ANTHY and self.__convert_mode != CONV_MODE_PREDICTION:
            return False

        if not self.__lookup_table.cursor_up():
            return False

        candidate = self.__lookup_table.get_current_candidate().text
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def cursor_down(self):
        # only process cursor down in convert mode
        # if self.__convert_mode != CONV_MODE_ANTHY:
        if self.__convert_mode != CONV_MODE_ANTHY and self.__convert_mode != CONV_MODE_PREDICTION:
            return False

        if not self.__lookup_table.cursor_down():
            return False

        candidate = self.__lookup_table.get_current_candidate().text
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def candidate_clicked(self, index, button, state):
        if index == 9:
            keyval = keysyms._0
        else:
            keyval = keysyms._1 + index
        self.__on_key_number(keyval)

    def __commit_string(self, text):
        self.__reset()
        self.commit_text(ibus.Text(text))
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

    if ibus.get_version() >= '1.2.0':
        def process_key_event(self, keyval, keycode, state):
            try:
                return self.process_key_event_internal2(keyval, keycode, state)
            except:
                import traceback
                traceback.print_exc()
                return False
    else:
        def process_key_event(self, keyval, state):
            try:
                return self.process_key_event_internal2(keyval, 0, state)
            except:
                import traceback
                traceback.print_exc()
                return False

    '''def process_key_event_internal(self, keyval, state):
        is_press = (state & modifier.RELEASE_MASK) == 0

        state = state & (modifier.SHIFT_MASK |
                modifier.CONTROL_MASK |
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
        elif keyval == keysyms.Hiragana_Katakana: # or keyval == keysyms.F11:
            return self.__on_key_hiragana_katakana()
        elif keyval == keysyms.Muhenkan: # or keyval == keysyms.F11:
            return self.__on_key_muhenka()
        elif keyval == keysyms.Henkan: # or keyval == keysyms.F11:
            return self.__on_key_henkan()
        elif keyval >= keysyms.F6 and keyval <= keysyms.F9:
            return self.__on_key_conv(keyval - keysyms.F6)
        elif keyval >= keysyms.exclam and keyval <= keysyms.asciitilde:
            return self.__on_key_common(keyval)
        elif keyval == keysyms.yen:
            return self.__on_key_common(keyval)
        else:
            if not self.__preedit_ja_string.is_empty():
                return True
            return False'''

    def property_activate(self, prop_name, state):

        if state == ibus.PROP_STATE_CHECKED:
            if prop_name == None:
                return
            elif prop_name.startswith(u"InputMode."):
                self.__input_mode_activate(prop_name, state)
                return
            elif prop_name.startswith(u"TypingMode."):
                self.__typing_mode_activate(prop_name, state)
                return
            elif prop_name.startswith(u"SegmentMode."):
                self.__segment_mode_activate(prop_name, state)
                return
            elif prop_name.startswith(u"DictMode."):
                self.__dict_mode_activate(prop_name, state)
                return
        else:
            if prop_name == 'setup':
                self.__start_setup()
            elif prop_name == 'setup-dict-kasumi-admin':
                self.__start_dict_admin()
            elif prop_name == 'setup-dict-kasumi-word':
                self.__start_add_word()
            else:
                self.__prop_dict[prop_name].set_state(state)
                if prop_name == "DictMode":
                    sub_name = self.__dict_mode_get_prop_name(self.__dict_mode)
                    if sub_name == None:
                        return
                    self.__dict_mode_activate(sub_name,
                                              ibus.PROP_STATE_CHECKED)

    def __input_mode_activate(self, prop_name, state):
        input_modes = {
            u"InputMode.Hiragana" : (INPUT_MODE_HIRAGANA, u"あ"),
            u"InputMode.Katakana" : (INPUT_MODE_KATAKANA, u"ア"),
            u"InputMode.HalfWidthKatakana" : (INPUT_MODE_HALF_WIDTH_KATAKANA, u"_ｱ"),
            u"InputMode.Latin" : (INPUT_MODE_LATIN, u"_A"),
            u"InputMode.WideLatin" : (INPUT_MODE_WIDE_LATIN, u"Ａ"),
        }

        if prop_name not in input_modes:
            print >> sys.stderr, "Unknow prop_name = %s" % prop_name
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])

        mode, label = input_modes[prop_name]
        if self.__input_mode == mode:
            return

        self.__input_mode = mode
        prop = self.__prop_dict[u"InputMode"]
        prop.label = label
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __typing_mode_activate(self, prop_name, state):
        typing_modes = {
            u"TypingMode.Romaji" : (jastring.TYPING_MODE_ROMAJI, u"R"),
            u"TypingMode.Kana" : (jastring.TYPING_MODE_KANA, u"か"),
            u"TypingMode.ThumbShift" : (jastring.TYPING_MODE_THUMB_SHIFT, u"親"),
        }

        if prop_name not in typing_modes:
            print >> sys.stderr, "Unknow prop_name = %s" % prop_name
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])
        if prop_name == u"TypingMode.ThumbShift":
            self._reset_thumb()

        mode, label = typing_modes[prop_name]

        Engine.__typing_mode = mode
        prop = self.__prop_dict[u"TypingMode"]
        prop.label = label
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __refresh_typing_mode_property(self):
        prop = self.__prop_dict[u"TypingMode"]
        modes = {
            jastring.TYPING_MODE_ROMAJI : (u"TypingMode.Romaji", u"R"),
            jastring.TYPING_MODE_KANA : (u"TypingMode.Kana", u"か"),
            jastring.TYPING_MODE_THUMB_SHIFT : (u"TypingMode.ThumbShift", u"親"),
        }
        prop_name, label = modes.get(Engine.__typing_mode, (None, None))
        if prop_name == None or label == None:
            return
        _prop = self.__prop_dict[prop_name]
        _prop.set_state(ibus.PROP_STATE_CHECKED)
        self.update_property(_prop)
        prop.label = label
        self.update_property(prop)

    def __segment_mode_activate(self, prop_name, state):
        segment_modes = {
            u"SegmentMode.Multi" : (SEGMENT_DEFAULT, u"連"),
            u"SegmentMode.Single" : (SEGMENT_SINGLE, u"単"),
            u"SegmentMode.ImmediateMulti" : (SEGMENT_IMMEDIATE, u"逐|連"),
            u"SegmentMode.ImmediateSingle" :
                (SEGMENT_IMMEDIATE | SEGMENT_SINGLE, u"逐|単"),
        }

        if prop_name not in segment_modes:
            print >> sys.stderr, "Unknow prop_name = %s" % prop_name
            return
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])

        mode, label = segment_modes[prop_name]

        self.__segment_mode = mode
        prop = self.__prop_dict[u"SegmentMode"]
        prop.label = label
        self.update_property(prop)

        self.__reset()
        self.__invalidate()

    def __dict_mode_get_prop_name(self, mode):
        if mode == 0:
            id = 'embedded'
        else:
            single_files = self.__get_single_dict_files()
            file = single_files[mode - 1]
            id = self._get_dict_id_from_file(file)
        if id == None:
            return None
        return 'DictMode.' + id

    def __dict_mode_activate(self, prop_name, state):
        if prop_name not in self.__prop_dict.keys():
            # The prop_name is added. Need to restart.
            return
        i = prop_name.find('.')
        if i < 0:
            return
        id = prop_name[i + 1:].encode('utf-8')

        file = None
        files = self.__prefs.get_value('dict', 'files')
        if id == 'embedded':
            pass
        elif id == 'anthy_zipcode' or id == 'ibus_symbol':
            file = self.__prefs.get_value('dict', id)[0]
        else:
            found = False
            for file in files:
                if id == self._get_quoted_id(file):
                    found = True
                    break
            if found == False:
                return

        if id == 'embedded':
            dict_name = 'default'
            self.__dict_mode = 0
        else:
            dict_name = 'ibus__' + id
            self.__dict_mode = files.index(file) + 1
        self.__prop_dict[prop_name].set_state(state)
        self.update_property(self.__prop_dict[prop_name])
        self.__context.init_personality()
        self.__context.do_set_personality(dict_name)

        prop = self.__prop_dict[u"DictMode"]
        section = 'dict/file/' + id
        prop.label = self.__prefs.get_value(section, 'short_label')
        self.update_property(prop)

    def focus_in(self):
        self.register_properties(self.__prop_list)
        self.__refresh_typing_mode_property()
        mode = self.__prefs.get_value('common', 'behavior_on_focus_out')
        if mode == 2:
            self.__update_input_chars()
#        self.__reset()
#        self.__invalidate()
        size = self.__prefs.get_value('common', 'page_size')
        if size != self.__lookup_table.get_page_size():
            self.__lookup_table.set_page_size(size)

    def focus_out(self):
        mode = self.__prefs.get_value('common', 'behavior_on_focus_out')
        if mode == 0 or mode == 1:
            self.__reset()
            self.__invalidate()

    def disable(self):
        self.__reset()
        self.__invalidate()

    def reset(self):
        self.__reset()
        self.__invalidate()

    def do_destroy(self):
        if self.__idle_id != 0:
            gobject.source_remove(self.__idle_id)
            self.__idle_id = 0
        self.__remove_dict_files()
        super(Engine,self).do_destroy()

    def __join_all_segments(self):
        while True:
            conv_stat = anthy.anthy_conv_stat()
            self.__context.get_stat(conv_stat)
            seg = conv_stat.nr_segment - self.__cursor_pos

            if seg > 1:
                self.__context.resize_segment(self.__cursor_pos, 1)
            else:
                break

    # begine convert
    def __begin_anthy_convert(self):
        if self.__segment_mode & SEGMENT_IMMEDIATE:
            self.__end_anthy_convert()
        if self.__convert_mode == CONV_MODE_ANTHY:
            return
        self.__convert_mode = CONV_MODE_ANTHY

#        text, cursor = self.__preedit_ja_string.get_hiragana()
        text, cursor = self.__preedit_ja_string.get_hiragana(True)

        self.__context.set_string(text.encode("utf8"))
        if self.__segment_mode & SEGMENT_SINGLE:
            self.__join_all_segments()
        conv_stat = anthy.anthy_conv_stat()
        self.__context.get_stat(conv_stat)

        for i in xrange(0, conv_stat.nr_segment):
            buf = self.__context.get_segment(i, 0)
            text = unicode(buf, "utf-8")
            self.__segments.append((0, text))

        if self.__segment_mode & SEGMENT_IMMEDIATE:
            self.__cursor_pos = conv_stat.nr_segment - 1
        else:
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

    def __candidate_cb(self, candidate):
        if not self.__is_utf8:
            return
        for key in romaji_utf8_rule.keys():
            if candidate.find(key) >= 0:
                for value in romaji_utf8_rule[key]:
                    candidate = candidate.replace(key, value)
                    self.__lookup_table.append_candidate(ibus.Text(candidate))

    def __fill_anthy_zipcode_strip(self, dict_file, id):
        import re
        text = self.__preedit_ja_string.get_latin()[0]
        if text.find('-') < 0:
            return
        text = text.replace('-', '')
        section = 'dict/file/' + id
        if 'encoding' not in self.__prefs.keys(section):
            section = 'dict/file/default'
        encoding = self.__prefs.get_value(section, 'encoding')
        contents = unicode(open(dict_file).read(), encoding)
        expression = re.compile("^" + text + "[ \t]")

        found = False
        dict_dest = None
        for line in contents.split('\n'):
            matched = expression.search(line)
            if matched:
                found = True
                dict_dest = unicode(matched.string).split(' ')[2]
                break
        if found:
            self.__lookup_table.append_candidate(ibus.Text(dict_dest))

    def __fill_lookup_table_dict_mode(self):
        if self.__dict_mode <= 0:
            return
        single_files = self.__get_single_dict_files()
        file = single_files[self.__dict_mode - 1]
        if file == None:
            return
        id = self._get_dict_id_from_file(file)
        if id == None:
            return
        if id == 'anthy_zipcode':
            self.__fill_anthy_zipcode_strip(file, id)

    def __fill_lookup_table(self):
        if self.__convert_mode == CONV_MODE_PREDICTION:
            seg_stat = anthy.anthy_prediction_stat()
            self.__context.get_prediction_stat(seg_stat)

            # fill lookup_table
            self.__lookup_table.clean()
            for i in xrange(0, seg_stat.nr_prediction):
                buf = self.__context.get_prediction(i)
                candidate = unicode(buf, "utf-8")
                self.__lookup_table.append_candidate(ibus.Text(candidate))
                self.__candidate_cb(candidate)
            return

        # get segment stat
        seg_stat = anthy.anthy_segment_stat()
        self.__context.get_segment_stat(self.__cursor_pos, seg_stat)

        # fill lookup_table
        self.__lookup_table.clean()
        for i in xrange(0, seg_stat.nr_candidate):
            buf = self.__context.get_segment(self.__cursor_pos, i)
            candidate = unicode(buf, "utf-8")
            self.__lookup_table.append_candidate(ibus.Text(candidate))
            self.__candidate_cb(candidate)
        self.__fill_lookup_table_dict_mode()


    def __invalidate(self):
        if self.__idle_id != 0:
            return
        self.__idle_id = gobject.idle_add(self.__update,
                                          priority = gobject.PRIORITY_LOW)

#    def __get_preedit(self):
    def __get_preedit(self, commit=False):
        if self.__input_mode == INPUT_MODE_HIRAGANA:
#            text, cursor = self.__preedit_ja_string.get_hiragana()
            text, cursor = self.__preedit_ja_string.get_hiragana(commit)
        elif self.__input_mode == INPUT_MODE_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_katakana()
            text, cursor = self.__preedit_ja_string.get_katakana(commit)
        elif self.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
            text, cursor = self.__preedit_ja_string.get_half_width_katakana(commit)
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
#        if self.__convert_mode == CONV_MODE_ANTHY:
        if self.__convert_mode == CONV_MODE_ANTHY or self.__convert_mode == CONV_MODE_PREDICTION:
            self.__update_anthy_convert_chars()
            return
        if self.__convert_mode == CONV_MODE_HIRAGANA:
#            text, cursor = self.__preedit_ja_string.get_hiragana()
            text, cursor = self.__preedit_ja_string.get_hiragana(True)
        elif self.__convert_mode == CONV_MODE_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_katakana()
            text, cursor = self.__preedit_ja_string.get_katakana(True)
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
#            text, cursor = self.__preedit_ja_string.get_half_width_katakana()
            text, cursor = self.__preedit_ja_string.get_half_width_katakana(True)
        elif self.__convert_mode == CONV_MODE_LATIN_0:
            text, cursor = self.__preedit_ja_string.get_latin()
            if text == text.lower():
                self.__convert_mode = CONV_MODE_LATIN_1
        elif self.__convert_mode == CONV_MODE_LATIN_1:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.lower()
        elif self.__convert_mode == CONV_MODE_LATIN_2:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.upper()
        elif self.__convert_mode == CONV_MODE_LATIN_3:
            text, cursor = self.__preedit_ja_string.get_latin()
            text = text.capitalize()
        elif self.__convert_mode == CONV_MODE_WIDE_LATIN_0:
            text, cursor = self.__preedit_ja_string.get_wide_latin()
            if text == text.lower():
                self.__convert_mode = CONV_MODE_WIDE_LATIN_1
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
        for i, (seg_index, text) in enumerate(self.__segments):
            self.__convert_chars += text
            if i < self.__cursor_pos:
                pos += len(text)
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
        if self.__convert_mode == CONV_MODE_OFF:
            self.__update_input_chars()
        else:
            self.__update_convert_chars()
        self.__idle_id = 0

    def __on_key_return(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_OFF:
#            text, cursor = self.__get_preedit()
            text, cursor = self.__get_preedit(True)
            self.__commit_string(text)
        elif self.__convert_mode == CONV_MODE_ANTHY:
            for i, (seg_index, text) in enumerate(self.__segments):
                self.__context.commit_segment(i, seg_index)
            self.__commit_string(self.__convert_chars)
        elif self.__convert_mode == CONV_MODE_PREDICTION:
            self.__context.commit_prediction(self.__segments[0][0])
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

    '''def __on_key_hiragana_katakana(self):
        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__end_anthy_convert()

        if self.__input_mode >= INPUT_MODE_HIRAGANA and \
           self.__input_mode < INPUT_MODE_HALF_WIDTH_KATAKANA:
            self.__input_mode += 1
        else:
            self.__input_mode = INPUT_MODE_HIRAGANA

        modes = { INPUT_MODE_HIRAGANA: u"あ",
                  INPUT_MODE_KATAKANA: u"ア",
                  INPUT_MODE_HALF_WIDTH_KATAKANA: u"_ｱ" }

        prop = self.__prop_dict[u"InputMode"]
        prop.label = modes[self.__input_mode]
        self.update_property(prop)

        self.__invalidate()
        return True'''

    '''def __on_key_muhenka(self):
        if self.__preedit_ja_string.is_empty():
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__end_anthy_convert()

        new_mode = CONV_MODE_HIRAGANA
        if self.__convert_mode < CONV_MODE_WIDE_LATIN_3 and \
           self.__convert_mode >= CONV_MODE_HIRAGANA :
            self.__convert_mode += 1
        else:
            self.__convert_mode = CONV_MODE_HIRAGANA

        self.__invalidate()

        return True'''

    '''def __on_key_henkan(self):
        if self.__preedit_ja_string.is_empty():
            return False
        if self.__convert_mode != CONV_MODE_ANTHY:
            self.__begin_anthy_convert()
            self.__invalidate()
        elif self.__convert_mode == CONV_MODE_ANTHY:
            self.__lookup_table_visible = True
            self.cursor_down()
        return True'''

    '''def __on_key_space(self, wide=False):
        if self.__input_mode == INPUT_MODE_WIDE_LATIN or wide:
            # Input Wide space U+3000
            wide_char = symbol_rule[unichr(keysyms.space)]
            self.__commit_string(wide_char)
            return True

        if self.__preedit_ja_string.is_empty():
            if self.__input_mode in (INPUT_MODE_HIRAGANA, INPUT_MODE_KATAKANA):
                # Input Wide space U+3000
                wide_char = symbol_rule[unichr(keysyms.space)]
                self.__commit_string(wide_char)
                return True
            else:
                # Input Half space U+0020
                self.__commit_string(unichr(keysyms.space))
                return True

        if self.__convert_mode != CONV_MODE_ANTHY:
            self.__begin_anthy_convert()
            self.__invalidate()
        elif self.__convert_mode == CONV_MODE_ANTHY:
            self.__lookup_table_visible = True
            self.cursor_down()
        return True'''

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

    '''def __on_key_left(self):
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
        return True'''

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
            keyval = keysyms._9 + 1
        index = keyval - keysyms._1

        candidates = self.__lookup_table.get_candidates_in_current_page()
        if self.__lookup_table.set_cursor_pos_in_current_page(index):
            index = self.__lookup_table.get_cursor_pos()
            candidate = self.__lookup_table.get_current_candidate().text
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
            self.__convert_mode = CONV_MODE_HALF_WIDTH_KATAKANA
        elif mode == 3:
            if CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode <= CONV_MODE_WIDE_LATIN_3:
                self.__convert_mode += 1
                if self.__convert_mode > CONV_MODE_WIDE_LATIN_3:
                    self.__convert_mode = CONV_MODE_WIDE_LATIN_1
            else:
                self.__convert_mode = CONV_MODE_WIDE_LATIN_0
        elif mode == 4:
            if CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
                self.__convert_mode += 1
                if self.__convert_mode > CONV_MODE_LATIN_3:
                    self.__convert_mode = CONV_MODE_LATIN_1
            else:
                self.__convert_mode = CONV_MODE_LATIN_0
        else:
            print >> sys.stderr, "Unkown convert mode (%d)!" % mode
            return False
        self.__invalidate()
        return True

    def __on_key_common(self, keyval, state=0):

        if self.__input_mode == INPUT_MODE_LATIN:
            # Input Latin chars
            char = unichr(keyval)
            self.__commit_string(char)
            return True

        elif self.__input_mode == INPUT_MODE_WIDE_LATIN:
            #  Input Wide Latin chars
            char = unichr(keyval)
            wide_char = None#symbol_rule.get(char, None)
            if wide_char == None:
                wide_char = unichar_half_to_full(char)
            self.__commit_string(wide_char)
            return True

        # Input Japanese
        if self.__segment_mode & SEGMENT_IMMEDIATE:
            # Commit nothing
            pass
        elif self.__convert_mode == CONV_MODE_ANTHY:
            for i, (seg_index, text) in enumerate(self.__segments):
                self.__context.commit_segment(i, seg_index)
            self.__commit_string(self.__convert_chars)
        elif self.__convert_mode != CONV_MODE_OFF:
            self.__commit_string(self.__convert_chars)

        # "n" + "'" == "nn" in romaji
        if (keyval >= ord('A') and keyval <= ord('Z')) or \
           (keyval >= ord('a') and keyval <= ord('z')):
            shift = (state & modifier.SHIFT_MASK) != 0
        else:
            shift = False
        self.__preedit_ja_string.set_shift(shift)
        self.__preedit_ja_string.insert(unichr(keyval))
        if self.__segment_mode & SEGMENT_IMMEDIATE:
            self.__begin_anthy_convert()
        self.__invalidate()
        return True

#=======================================================================
    @classmethod
    def CONFIG_RELOADED(cls, bus):
        print 'RELOADED'
        if not cls.__prefs:
            cls.__prefs = AnthyPrefs(bus)

        cls.__keybind = cls._mk_keybind()

        jastring.JaString._prefs = cls.__prefs

    @classmethod
    def CONFIG_VALUE_CHANGED(cls, bus, section, name, value):
        print 'VALUE_CHAMGED =', section, name, value

        if not section.startswith("engine/anthy"):
            # This value is used for ibus.config.set_value only.
            return

        base_sec = section[len(cls.__prefs._prefix) + 1:]
        sec = cls._get_shortcut_type()
        if base_sec == sec:
            cmd = '_Engine__cmd_' + name
            old = cls.__prefs.get_value(sec, name)
            value = value if value != [''] else []
            for s in set(old).difference(value):
                cls.__keybind.get(cls._s_to_key(s), []).remove(cmd)

            keys = cls.__prefs.keys(sec)
            for s in set(value).difference(old):
                cls.__keybind.setdefault(cls._s_to_key(s), []).append(cmd)
                cls.__keybind.get(cls._s_to_key(s)).sort(
                    lambda a, b: cmp(keys.index(a[13:]), keys.index(b[13:])))

            cls.__prefs.set_value(sec, name, value)
        elif base_sec == 'common':
            cls.__prefs.set_value(base_sec, name, value)
            if name == 'shortcut_type':
                cls.__keybind = cls._mk_keybind()
        elif base_sec == 'thumb':
            cls.__prefs.set_value(base_sec, name, value)
            cls._reset_thumb()
        elif base_sec == 'dict':
            cls._set_dict_files_value(base_sec, name, value)
        elif base_sec.startswith('dict/file/'):
            if base_sec not in cls.__prefs.sections():
                cls._fetch_dict_values(base_sec)
            cls.__prefs.set_value(base_sec, name, value)
        elif base_sec:
            cls.__prefs.set_value(base_sec, name, value)
        else:
            cls.__prefs.set_value(section, name, value)

    @classmethod
    def _mk_keybind(cls):
        keybind = {}
        sec = cls._get_shortcut_type()
        for k in cls.__prefs.keys(sec):
            cmd = '_Engine__cmd_' + k
            for s in cls.__prefs.get_value(sec, k):
                keybind.setdefault(cls._s_to_key(s), []).append(cmd)
        return keybind

    @classmethod
    def _get_shortcut_type(cls):
        try:
            t = 'shortcut/' + cls.__prefs.get_value('common', 'shortcut_type')
        except:
            t = 'shortcut/default'
        return t

    @classmethod
    def _s_to_key(cls, s):
        keyval = keysyms.name_to_keycode(s.split('+')[-1])
        s = s.lower()
        state = ('shift+' in s and modifier.SHIFT_MASK or 0) | (
                 'ctrl+' in s and modifier.CONTROL_MASK or 0) | (
                 'alt+' in s and modifier.MOD1_MASK or 0)
        return cls._mk_key(keyval, state)

    @classmethod
    def _reset_thumb(cls):
        if cls.__thumb == None:
            import thumb
            cls.__thumb = thumb.ThumbShiftKeyboard(cls.__prefs)

        else:
            cls.__thumb.reset()

    @classmethod
    def _get_userhome(cls):
        if 'HOME' not in environ:
            import pwd
            userhome = pwd.getpwuid(getuid()).pw_dir
        else:
            userhome = environ['HOME']
        userhome = userhome.rstrip('/')
        return userhome

    @classmethod
    def _get_quoted_id(cls, file):
        id = file
        has_mbcs = False

        for i in xrange(0, len(id)):
            if ord(id[i]) >= 0x7f:
                    has_mbcs = True
                    break
        if has_mbcs:
            import urllib
            id = urllib.quote(id)

        if id.find('/') >=0:
            id = id[id.rindex('/') + 1:]
        if id.find('.') >=0:
            id = id[:id.rindex('.')]
        return id

    @classmethod
    def _get_dict_id_from_file(cls, file):
        if file in cls.__prefs.get_value('dict', 'anthy_zipcode'):
            id = 'anthy_zipcode'
        elif file in cls.__prefs.get_value('dict', 'ibus_symbol'):
            id = 'ibus_symbol'
        else:
            id = cls._get_quoted_id(file)
        return id

    @classmethod
    def _link_dict_file_with_id(cls, file, id, link_mode):
        if not path.exists(file):
            print >> sys.stderr, file + " does not exist"
            return
        if id == None:
            return
        if link_mode == LINK_DICT_EMBEDDED:
            directory = cls._get_userhome() + "/.anthy/" + IMPORTED_EMBEDDED_DICT_DIR
            name = IMPORTED_EMBEDDED_DICT_PREFIX + id
        elif link_mode == LINK_DICT_SINGLE:
            directory = cls._get_userhome() + "/.anthy"
            name = IMPORTED_SINGLE_DICT_PREFIX + id
        else:
            return
        if path.exists(directory):
            if not path.isdir(directory):
                print >> sys.stderr, directory + " is not a directory"
                return
        else:
            os.makedirs(directory, 0700)
        backup_dir = os.getcwd()
        os.chdir(directory)
        if path.lexists(directory + '/' + name):
            if path.islink(directory + '/' + name):
                print >> sys.stderr, "Removing " + name
                os.unlink(directory + '/' + name)
            else:
                alternate = name + str(os.getpid())
                print >> sys.stderr, "Moving " + name + " to " + alternate
                os.rename(name, alternate)
        os.symlink(file, directory + '/' + name)
        if backup_dir != None:
            os.chdir(backup_dir)

    @classmethod
    def _remove_dict_file_with_id(cls, file, id, link_mode):
        if id == None:
            return
        if link_mode == LINK_DICT_EMBEDDED:
            directory = cls._get_userhome() + "/.anthy/" + IMPORTED_EMBEDDED_DICT_DIR
            name = IMPORTED_EMBEDDED_DICT_PREFIX + id
        elif link_mode == LINK_DICT_SINGLE:
            directory = cls._get_userhome() + "/.anthy"
            name = IMPORTED_SINGLE_DICT_PREFIX + id
        else:
            return
        if path.exists(directory):
            if not path.isdir(directory):
                print >> sys.stderr, directory + " is not a directory"
                return
        backup_dir = os.getcwd()
        os.chdir(directory)
        if path.lexists(directory + '/' + name):
            os.unlink(directory + '/' + name)
        if backup_dir != None:
            os.chdir(backup_dir)

    @classmethod
    def _link_dict_file(cls, file):
        id = cls._get_dict_id_from_file(file)
        if id == None:
            return
        section = 'dict/file/' + id
        if section not in cls.__prefs.sections():
            cls._fetch_dict_values(section)
        if cls.__prefs.get_value(section, 'embed'):
            cls._link_dict_file_with_id(file, id, LINK_DICT_EMBEDDED)
        if cls.__prefs.get_value(section, 'single'):
            cls._link_dict_file_with_id(file, id, LINK_DICT_SINGLE)

    @classmethod
    def _remove_dict_file(cls, file):
        id = cls._get_dict_id_from_file(file)
        if id == None:
            return
        section = 'dict/file/' + id
        if section not in cls.__prefs.sections():
            cls._fetch_dict_values(section)
        if cls.__prefs.get_value(section, 'embed'):
            cls._remove_dict_file_with_id(file, id, LINK_DICT_EMBEDDED)
        if cls.__prefs.get_value(section, 'single'):
            cls._remove_dict_file_with_id(file, id, LINK_DICT_SINGLE)

    @classmethod
    def _set_dict_files_value(cls, base_sec, name, value):
        if name == 'files':
            str_list = []
            for file in value:
                str_list.append(str(file))
            old_files = cls.__prefs.get_value(base_sec, name)
            for file in old_files:
                if file in str_list:
                    continue
                cls._remove_dict_file(file)
            for file in str_list:
                if file in old_files:
                    continue
                cls._link_dict_file(file)
            cls.__prefs.set_value(base_sec, name, str_list)
        else:
            cls.__prefs.set_value(base_sec, name, value)

    @classmethod
    def _fetch_dict_values(cls, section):
        cls.__prefs.set_new_section(section)
        cls.__prefs.set_new_key(section, 'short_label')
        cls.__prefs.fetch_item(section, 'short_label')
        cls.__prefs.set_value(section, 'short_label',
                              str(cls.__prefs.get_value(section, 'short_label')))
        cls.__prefs.set_new_key(section, 'long_label')
        cls.__prefs.fetch_item(section, 'long_label')
        cls.__prefs.set_value(section, 'long_label',
                              str(cls.__prefs.get_value(section, 'long_label')))
        cls.__prefs.set_new_key(section, 'embed')
        cls.__prefs.fetch_item(section, 'embed')
        cls.__prefs.set_new_key(section, 'single')
        cls.__prefs.fetch_item(section, 'single')
        cls.__prefs.set_new_key(section, 'reverse')
        cls.__prefs.fetch_item(section, 'reverse')

    @staticmethod
    def _mk_key(keyval, state):
        if state & (modifier.CONTROL_MASK | modifier.MOD1_MASK):
            if unichr(keyval) in u'!"#$%^\'()*+,-./:;<=>?@[\]^_`{|}~':
                state |= modifier.SHIFT_MASK
            elif keysyms.a <= keyval <= keysyms.z:
                keyval -= (keysyms.a - keysyms.A)

        return repr([int(state), int(keyval)])

    def process_key_event_thumb(self, keyval, keycode, state):
        if self.__thumb == None:
            self._reset_thumb()

        def on_timeout(keyval):
            if self._MM:
                insert(self.__thumb.get_char(self._MM)[self._SS])
            else:
                cmd_exec([0, RS(), LS()][self._SS])
            self._H = None

        def start(t):
            self._H = gobject.timeout_add(t, on_timeout, keyval)

        def stop():
            if self._H:
                gobject.source_remove(self._H)
                self._H = None
                return True
            return False

        def insert(keyval):
            try:
                self._MM = self._SS = 0
                ret = self.__on_key_common(ord(keyval))
                if (keyval in u',.、。' and
                    self.__prefs.get_value('common', 'behavior_on_period')):
                    return self.__cmd_convert(keyval, state)
                return ret
            except:
                pass

        def cmd_exec(keyval, state=0):
            key = self._mk_key(keyval, state)
            for cmd in self.__keybind.get(key, []):
                print 'cmd =', cmd
                try:
                    if getattr(self, cmd)(keyval, state):
                        return True
                except:
                    print >> sys.stderr, 'Unknow command = %s' % cmd
            return False

        def RS():
            return self.__thumb.get_rs()

        def LS():
            return self.__thumb.get_ls()

        def T1():
            return self.__thumb.get_t1()

        def T2():
            return self.__thumb.get_t2()

        state = state & (modifier.SHIFT_MASK |
                         modifier.CONTROL_MASK |
                         modifier.MOD1_MASK |
                         modifier.RELEASE_MASK)

        if keyval in KP_Table and self.__prefs.get_value('common',
                                                         'ten_key_mode'):
            keyval = KP_Table[keyval]

        if state & modifier.RELEASE_MASK:
            if keyval == self._MM:
                if stop():
                    insert(self.__thumb.get_char(self._MM)[self._SS])
                self._MM = 0
            elif (1 if keyval == RS() else 2) == self._SS:
                if stop():
                    cmd_exec([0, RS(), LS()][self._SS])
                self._SS = 0
            if keyval in [RS(), LS()]:
                self._RSS = 0
            elif keyval == self._RMM:
                self._RMM = 0
        else:
            if keyval in [LS(), RS()] and state == 0:
                if self._SS:
                    stop()
                    cmd_exec([0, RS(), LS()][self._SS])
                    self._SS = 1 if keyval == RS() else 2
                    start(T1())
                elif self._MM:
                    stop()
                    self._RMM = self._MM
                    self._RSS = 1 if keyval == RS() else 2
                    insert(self.__thumb.get_char(self._MM)[1 if keyval == RS() else 2])
                else:
                    if self._RSS == (1 if keyval == RS() else 2):
                        if self._RMM:
                            insert(self.__thumb.get_char(self._RMM)[self._RSS])
                    else:
                        self._SS = 1 if keyval == RS() else 2
                        start(T1())
            elif keyval in self.__thumb.get_chars() and state == 0:
                if self._MM:
                    stop()
                    insert(self.__thumb.get_char(self._MM)[self._SS])
                    start(T2())
                    self._MM = keyval
                elif self._SS:
                    stop()
                    self._RMM = keyval
                    self._RSS = self._SS
                    insert(self.__thumb.get_char(keyval)[self._SS])
                else:
                    if self._RMM  == keyval:
                        if self._RSS:
                            insert(self.__thumb.get_char(self._RMM)[self._RSS])
                    else:
                        if cmd_exec(keyval, state):
                            return True
                        start(T2())
                        self._MM = keyval
            else:
                if self._MM:
                    stop()
                    insert(self.__thumb.get_char(self._MM)[self._SS])
                elif self._SS:
                    stop()
                    cmd_exec([0, RS(), LS()][self._SS])
                if cmd_exec(keyval, state):
                    return True
                elif 0x21 <= keyval <= 0x7e and state & (modifier.CONTROL_MASK | modifier.MOD1_MASK) == 0:
                    if state & modifier.SHIFT_MASK:
                        insert(self.__thumb.get_shift_char(keyval, unichr(keyval)))
                    elif self._SS == 0:
                        insert(unichr(keyval))
                else:
                    if not self.__preedit_ja_string.is_empty():
                        return True
                    return False
        return True

    def process_key_event_internal2(self, keyval, keycode, state):
        if self.__typing_mode == jastring.TYPING_MODE_THUMB_SHIFT and \
           self.__input_mode not in [INPUT_MODE_LATIN, INPUT_MODE_WIDE_LATIN]:
            return self.process_key_event_thumb(keyval, keycode, state)

        is_press = (state & modifier.RELEASE_MASK) == 0

        state = state & (modifier.SHIFT_MASK |
                         modifier.CONTROL_MASK |
                         modifier.MOD1_MASK)

        # ignore key release events
        if not is_press:
            return False

        if keyval in KP_Table and self.__prefs.get_value('common',
                                                         'ten_key_mode'):
            keyval = KP_Table[keyval]

        key = self._mk_key(keyval, state)
        for cmd in self.__keybind.get(key, []):
            print 'cmd =', cmd
            try:
                if getattr(self, cmd)(keyval, state):
                    return True
            except:
                print >> sys.stderr, 'Unknow command = %s' % cmd

        if state & (modifier.CONTROL_MASK | modifier.MOD1_MASK):
            return False

        if (keysyms.exclam <= keyval <= keysyms.asciitilde or
            keyval == keysyms.yen):
            if self.__typing_mode == jastring.TYPING_MODE_KANA:
                if keyval == keysyms._0 and state == modifier.SHIFT_MASK:
                    keyval = keysyms.asciitilde
                elif keyval == keysyms.backslash and keycode in [132-8, 133-8]:
                    keyval = keysyms.yen
            ret = self.__on_key_common(keyval, state)
            if (unichr(keyval) in u',.' and
                self.__prefs.get_value('common', 'behavior_on_period')):
                return self.__cmd_convert(keyval, state)
            return ret
        else:
            if not self.__preedit_ja_string.is_empty():
                return True
            return False

    def _chk_mode(self, mode):
        if '0' in mode and self.__preedit_ja_string.is_empty():
            return True

        if self.__convert_mode == CONV_MODE_OFF:
            if '1' in mode and not self.__preedit_ja_string.is_empty():
                return True
        elif self.__convert_mode == CONV_MODE_ANTHY:
            if '2' in mode and not self.__lookup_table_visible:
                return True
        elif self.__convert_mode == CONV_MODE_PREDICTION:
            if '3' in mode and not self.__lookup_table_visible:
                return True
        else:
            if '4' in mode:
                return True

        if '5' in mode and self.__lookup_table_visible:
            return True

        return False

    #mod_keys
    def __set_input_mode(self, mode):
        if not self._chk_mode('0'):
            return False

        self.__input_mode_activate(mode, ibus.PROP_STATE_CHECKED)

        return True

    def __cmd_on_off(self, keyval, state):
        if self.__input_mode == INPUT_MODE_LATIN:
            return self.__set_input_mode(u'InputMode.Hiragana')
        else:
            return self.__set_input_mode(u'InputMode.Latin')

    def __cmd_circle_input_mode(self, keyval, state):
        modes = {
            INPUT_MODE_HIRAGANA: u"InputMode.Katakana",
            INPUT_MODE_KATAKANA: u"InputMode.HalfWidthKatakana",
            INPUT_MODE_HALF_WIDTH_KATAKANA: u"InputMode.Latin",
            INPUT_MODE_LATIN: u"InputMode.WideLatin",
            INPUT_MODE_WIDE_LATIN: u"InputMode.Hiragana"
        }
        return self.__set_input_mode(modes[self.__input_mode])

    def __cmd_circle_kana_mode(self, keyval, state):
        modes = {
            INPUT_MODE_HIRAGANA: u"InputMode.Katakana",
            INPUT_MODE_KATAKANA: u"InputMode.HalfWidthKatakana",
            INPUT_MODE_HALF_WIDTH_KATAKANA: u"InputMode.Hiragana",
            INPUT_MODE_LATIN: u"InputMode.Hiragana",
            INPUT_MODE_WIDE_LATIN: u"InputMode.Hiragana"
        }
        return self.__set_input_mode(modes[self.__input_mode])

    def __cmd_latin_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.Latin')

    def __cmd_wide_latin_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.WideLatin')

    def __cmd_hiragana_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.Hiragana')

    def __cmd_katakana_mode(self, keyval, state):
        return self.__set_input_mode(u'InputMode.Katakana')

    def __cmd_half_katakana(self, keyval, state):
        return self.__set_input_mode(u'InputMode.HalfWidthKatakana')

#    def __cmd_cancel_pseudo_ascii_mode_key(self, keyval, state):
#        pass

    def __cmd_circle_typing_method(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        modes = {
            jastring.TYPING_MODE_THUMB_SHIFT: u"TypingMode.Romaji",
            jastring.TYPING_MODE_KANA: u"TypingMode.ThumbShift",
            jastring.TYPING_MODE_ROMAJI: u"TypingMode.Kana",
        }
        self.__typing_mode_activate(modes[self.__typing_mode],
                                    ibus.PROP_STATE_CHECKED)
        return True

    def __cmd_circle_dict_method(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        single_files = self.__get_single_dict_files()
        new_mode = self.__dict_mode + 1
        if new_mode > len(single_files):
            new_mode = 0
        self.__dict_mode = new_mode
        prop_name = self.__dict_mode_get_prop_name(self.__dict_mode)
        if prop_name == None:
            return False
        self.__dict_mode_activate(prop_name,
                                  ibus.PROP_STATE_CHECKED)
        return True

    #edit_keys
    def __cmd_insert_space(self, keyval, state):
        if (self.__prefs.get_value('common', 'half_width_space') or
            self.__input_mode in [INPUT_MODE_LATIN,
                                  INPUT_MODE_HALF_WIDTH_KATAKANA]):
            return self.__cmd_insert_half_space(keyval, state)
        else:
            return self.__cmd_insert_wide_space(keyval, state)

    def __cmd_insert_alternate_space(self, keyval, state):
        if (self.__prefs.get_value('common', 'half_width_space') or
            self.__input_mode in [INPUT_MODE_LATIN,
                                  INPUT_MODE_HALF_WIDTH_KATAKANA]):
            return self.__cmd_insert_wide_space(keyval, state)
        else:
            return self.__cmd_insert_half_space(keyval, state)

    def __cmd_insert_half_space(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        if not self.__preedit_ja_string.is_empty():
            return False
        self.__commit_string(unichr(keysyms.space))
        return True

    def __cmd_insert_wide_space(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        if not self.__preedit_ja_string.is_empty():
            return False
        char = unichr(keysyms.space)
        wide_char = symbol_rule.get(char, None)
        if wide_char == None:
            wide_char = unichar_half_to_full(char)
        self.__commit_string(wide_char)
        return True

    def __cmd_backspace(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        return self.__on_key_back_space()

    def __cmd_delete(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        return self.__on_key_delete()

    def __cmd_commit(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        return self.__on_key_return()

    def __cmd_convert(self, keyval, state):
        if not self._chk_mode('14'):
            return False

        self.__begin_anthy_convert()
        self.__invalidate()

        return True

    def __cmd_predict(self, keyval, state):
        if not self._chk_mode('14'):
            return False

        text, cursor = self.__preedit_ja_string.get_hiragana(True)

        self.__context.set_prediction_string(text.encode("utf8"))
        ps = anthy.anthy_prediction_stat()
        self.__context.get_prediction_stat(ps)

#        for i in range(ps.nr_prediction):
#            print self.__context.get_prediction(i)

        buf = self.__context.get_prediction(0)
        if not buf:
            return False

        text = unicode(buf, "utf-8")
        self.__segments.append((0, text))

        self.__convert_mode = CONV_MODE_PREDICTION
        self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False
        self.__invalidate()

        return True

    def __cmd_cancel(self, keyval, state):
        return self.__cmd_cancel_all(keyval, state)

    def __cmd_cancel_all(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            return self.__on_key_escape()
        else:
            self.__end_convert()
            self.__invalidate()
            return True

    def __cmd_reconvert(self, keyval, state):
        if not self.__preedit_ja_string.is_empty():
            # if user has inputed some chars
            return False

        # Use gtk.Clipboard.request_text() instead of
        # gtk.Clipboard.wait_for_text() because DBus is timed out.
        clipboard = clipboard_get ("PRIMARY")
        if clipboard:
            clipboard.request_text (self.__get_clipboard, CLIPBOARD_RECONVERT)

        return True

    def __update_reconvert(self, clipboard_text):
        if clipboard_text == None:
            return False

        self.__convert_chars = unicode (clipboard_text, "utf-8")
        for i in xrange(0, len(self.__convert_chars)):
            keyval = self.__convert_chars[i]
            self.__preedit_ja_string.insert(unichr(ord (keyval)))

        self.__context.set_string(self.__convert_chars.encode("utf-8"))
        conv_stat = anthy.anthy_conv_stat()
        self.__context.get_stat(conv_stat)

        for i in xrange(0, conv_stat.nr_segment):
            buf = self.__context.get_segment(i, 0)
            text = unicode(buf, "utf-8")
            self.__segments.append((0, text))

        self.__convert_mode = CONV_MODE_ANTHY
        self.__cursor_pos = 0
        self.__fill_lookup_table()
        self.__lookup_table_visible = False
        self.__invalidate()

        return True

#    def __cmd_do_nothing(self, keyval, state):
#        return True

    #caret_keys
    def __move_caret(self, i):
        if not self._chk_mode('1'):
            return False

        if self.__convert_mode == CONV_MODE_OFF:
            self.__preedit_ja_string.move_cursor(
                -len(self.__preedit_ja_string.get_latin()[0]) if i == 0 else
                i if i in [-1, 1] else
                len(self.__preedit_ja_string.get_latin()[0]))
            self.__invalidate()
            return True

        return False

    def __cmd_move_caret_first(self, keyval, state):
        return self.__move_caret(0)

    def __cmd_move_caret_last(self, keyval, state):
        return self.__move_caret(2)

    def __cmd_move_caret_forward(self, keyval, state):
        return self.__move_caret(1)

    def __cmd_move_caret_backward(self, keyval, state):
        return self.__move_caret(-1)

    #segments_keys
    def __select_segment(self, i):
        if not self._chk_mode('25'):
            return False

        pos = 0 if i == 0 else \
              self.__cursor_pos + i if i in [-1, 1] else \
              len(self.__segments) - 1

        if 0 <= pos < len(self.__segments) and pos != self.__cursor_pos:
            self.__cursor_pos = pos
            self.__lookup_table_visible = False
            self.__fill_lookup_table()
            self.__invalidate()

        return True

    def __cmd_select_first_segment(self, keyval, state):
        return self.__select_segment(0)

    def __cmd_select_last_segment(self, keyval, state):
        return self.__select_segment(2)

    def __cmd_select_next_segment(self, keyval, state):
        return self.__select_segment(1)

    def __cmd_select_prev_segment(self, keyval, state):
        return self.__select_segment(-1)

    def __cmd_shrink_segment(self, keyval, state):
        if not self._chk_mode('25'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__shrink_segment(-1)
            return True

    def __cmd_expand_segment(self, keyval, state):
        if not self._chk_mode('25'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            self.__shrink_segment(1)
            return True

    def __move_cursor_char_length(self, length):
        if self.__input_mode == INPUT_MODE_HIRAGANA:
            self.__preedit_ja_string.move_cursor_hiragana_length(length)
        elif self.__input_mode == INPUT_MODE_KATAKANA:
            self.__preedit_ja_string.move_cursor_katakana_length(length)
        elif self.__input_mode == INPUT_MODE_HALF_WIDTH_KATAKANA:
            self.__preedit_ja_string.move_cursor_half_with_katakana_length(length)
        else:
            self.__preedit_ja_string.move_cursor(length)

    def __commit_nth_segment(self, commit_index, keyval, state):

        if commit_index >= len(self.__segments):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            for i in xrange(0, commit_index + 1):
                (seg_index, text) = self.__segments[i]
                self.commit_text(ibus.Text(text))

            text, cursor = self.__get_preedit()
            commit_length = 0
            for i in xrange(0, commit_index + 1):
                buf = self.__context.get_segment(i, NTH_UNCONVERTED_CANDIDATE)
                commit_length += len(unicode(buf, "utf-8"))
            self.__move_cursor_char_length(commit_length - cursor)
            for i in xrange(0, commit_length):
                self.__preedit_ja_string.remove_before()
            self.__move_cursor_char_length(cursor - commit_length)

            del self.__segments[0:commit_index + 1]

        if len(self.__segments) == 0:
            self.__reset()
        else:
            if self.__cursor_pos > commit_index:
                self.__cursor_pos -= (commit_index + 1)
            else:
                self.__cursor_pos = 0
            text, cursor = self.__get_preedit()
            self.__convert_chars = text
            self.__context.set_string(text.encode ("utf-8"))

        self.__lookup_table.clean()
        self.__lookup_table.show_cursor (False)
        self.__lookup_table_visible = False
        self.update_aux_string(u"", ibus.AttrList(),
            self.__lookup_table_visible)
        self.__fill_lookup_table()
        self.__invalidate()
        self.__update_input_chars()

        return True

    def __cmd_commit_first_segment(self, keyval, state):
        return self.__commit_nth_segment(0, keyval, state)

    def __cmd_commit_selected_segment(self, keyval, state):
        return self.__commit_nth_segment(self.__cursor_pos, keyval, state)

    #candidates_keys
    def __select_candidate(self, pos):
        if not self._chk_mode('5'):
            return False

        if not self.__lookup_table.set_cursor_pos_in_current_page(pos):
            return False

        candidate = self.__lookup_table.get_current_candidate().text
        index = self.__lookup_table.get_cursor_pos()
        self.__segments[self.__cursor_pos] = index, candidate
        self.__invalidate()
        return True

    def __cmd_select_first_candidate(self, keyval, state):
        return self.__select_candidate(0)

    def __cmd_select_last_candidate(self, keyval, state):
        return self.__select_candidate(self.__lookup_table.get_page_size() - 1)

    def __cmd_select_next_candidate(self, keyval, state):
        if not self._chk_mode('235'):
            return False

        return self.__on_key_down()

    def __cmd_select_prev_candidate(self, keyval, state):
        if not self._chk_mode('235'):
            return False

        return self.__on_key_up()

    def __cmd_candidates_page_up(self, keyval, state):
        if not self._chk_mode('5'):
            return False

        return self.__on_key_page_up()

    def __cmd_candidates_page_down(self, keyval, state):
        if not self._chk_mode('5'):
            return False

        return self.__on_key_page_down()

    #direct_select_keys
    def __select_candidates(self, keyval):
        if not self._chk_mode('5'):
            return False

        return self.__on_key_number(keyval)

    def __cmd_select_candidates_1(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_2(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_3(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_4(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_5(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_6(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_7(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_8(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_9(self, keyval, state):
        return self.__select_candidates(keyval)

    def __cmd_select_candidates_0(self, keyval, state):
        return self.__select_candidates(keyval)

    #convert_keys
    def __cmd_convert_to_char_type_forward(self, keyval, state):
        if self.__convert_mode == CONV_MODE_ANTHY:
            n = self.__segments[self.__cursor_pos][0]
            if n == NTH_HIRAGANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)
            elif n == NTH_KATAKANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)
            elif n == NTH_HALFKANA_CANDIDATE:
                return self.__convert_segment_to_latin(-100)
            elif n == -100:
                return self.__convert_segment_to_latin(-101)
            else:
                return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)

        if self.__convert_mode == CONV_MODE_KATAKANA:
            return self.__cmd_convert_to_half_katakana(keyval, state)
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
            return self.__cmd_convert_to_latin(keyval, state)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__cmd_convert_to_wide_latin(keyval, state)
        elif (CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode
                                     <= CONV_MODE_WIDE_LATIN_3):
            return self.__cmd_convert_to_hiragana(keyval, state)
        else:
            return self.__cmd_convert_to_katakana(keyval, state)

    def __cmd_convert_to_char_type_backward(self, keyval, state):
        if self.__convert_mode == CONV_MODE_ANTHY:
            n = self.__segments[self.__cursor_pos][0]
            if n == NTH_KATAKANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)
            elif n == NTH_HALFKANA_CANDIDATE:
                return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)
            elif n == -100:
                return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)
            elif n == -101:
                return self.__convert_segment_to_latin(-100)
            else:
                return self.__convert_segment_to_latin(-101)

        if self.__convert_mode == CONV_MODE_KATAKANA:
            return self.__cmd_convert_to_hiragana(keyval, state)
        elif self.__convert_mode == CONV_MODE_HALF_WIDTH_KATAKANA:
            return self.__cmd_convert_to_katakana(keyval, state)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__cmd_convert_to_half_katakana(keyval, state)
        elif (CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode
                                     <= CONV_MODE_WIDE_LATIN_3):
            return self.__cmd_convert_to_latin(keyval, state)
        else:
            return self.__cmd_convert_to_wide_latin(keyval, state)

    def __convert_segment_to_kana(self, n):
        if self.__convert_mode == CONV_MODE_ANTHY and -4 <= n <= -2:
            buf = self.__context.get_segment(self.__cursor_pos, n)
            self.__segments[self.__cursor_pos] = n, unicode(buf, "utf-8")
            self.__lookup_table_visible = False
            self.__invalidate()
            return True

        return False

    def __cmd_convert_to_hiragana(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            return self.__convert_segment_to_kana(NTH_HIRAGANA_CANDIDATE)

        return self.__on_key_conv(0)

    def __cmd_convert_to_katakana(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            return self.__convert_segment_to_kana(NTH_KATAKANA_CANDIDATE)

        return self.__on_key_conv(1)

    def __cmd_convert_to_half(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            i, s = self.__segments[self.__cursor_pos]
            if i == -101:
                return self.__convert_segment_to_latin(-100)
            elif i == -100:
                return self.__convert_segment_to_latin(-100)
            return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)

        elif CONV_MODE_WIDE_LATIN_0 <= self.__convert_mode <= CONV_MODE_WIDE_LATIN_3:
            return self.__on_key_conv(4)
        elif CONV_MODE_LATIN_0 <= self.__convert_mode <= CONV_MODE_LATIN_3:
            return self.__on_key_conv(4)
        return self.__on_key_conv(2)

    def __cmd_convert_to_half_katakana(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
            return self.__convert_segment_to_kana(NTH_HALFKANA_CANDIDATE)

        return self.__on_key_conv(2)

    def __convert_segment_to_latin(self, n):
        if self.__convert_mode == CONV_MODE_ANTHY and n in [-100, -101]:
            start = 0
            for i in range(self.__cursor_pos):
                start += len(unicode(self.__context.get_segment(i, NTH_UNCONVERTED_CANDIDATE), 'utf-8'))
            end = start + len(unicode(self.__context.get_segment(self.__cursor_pos, NTH_UNCONVERTED_CANDIDATE), 'utf-8'))
            i, s = self.__segments[self.__cursor_pos]
            s2 = self.__preedit_ja_string.get_raw(start, end)
            if n == -101:
                s2 = u''.join([unichar_half_to_full(c) for c in s2])
            if i == n:
                if s == s2.lower():
                    s2 = s2.upper()
                elif s == s2.upper():
                    s2 = s2.capitalize()
                elif s == s2 or s == s2.capitalize():
                    s2 = s2.lower()
            self.__segments[self.__cursor_pos] = n, s2
            self.__lookup_table_visible = False
            self.__invalidate()
            return True

        return False

    def __cmd_convert_to_wide_latin(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
           return self.__convert_segment_to_latin(-101)

        return self.__on_key_conv(3)

    def __cmd_convert_to_latin(self, keyval, state):
        if not self._chk_mode('12345'):
            return False

        if self.__convert_mode == CONV_MODE_ANTHY:
           return self.__convert_segment_to_latin(-100)

        return self.__on_key_conv(4)

    #dictonary_keys
    def __cmd_dict_admin(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        self.__start_dict_admin()
        return True

    def __cmd_add_word(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        self.__start_add_word()
        return True

    def __cmd_start_setup(self, keyval, state):
        if not self._chk_mode('0'):
            return False

        self.__start_setup()
        return True

    def __start_dict_admin(self):
        command = self.__prefs.get_value('common', 'dict_admin_command')
        os.spawnl(os.P_NOWAIT, *command)

    def __start_add_word(self):
        command = self.__prefs.get_value('common', 'add_word_command')
        os.spawnl(os.P_NOWAIT, *command)

    def __start_setup(self):
        if Engine.__setup_pid != 0:
            pid, state = os.waitpid(Engine.__setup_pid, os.P_NOWAIT)
            if pid != Engine.__setup_pid:
                return
            Engine.__setup_pid = 0
        setup_cmd = path.join(os.getenv('LIBEXECDIR'), "ibus-setup-anthy")
        Engine.__setup_pid = os.spawnl(os.P_NOWAIT, setup_cmd, "ibus-setup-anthy")

