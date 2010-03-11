# vim:set noet ts=4:
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

from os import environ, getenv, getuid, path
import os
import gtk
import pango
from gtk import glade
from ibus import keysyms, modifier, Bus
from gettext import dgettext, bindtextdomain

from anthyprefs import AnthyPrefs


_ = lambda a : dgettext('ibus-anthy', a)

def l_to_s(l):
    return str(sorted([str(s) for s in l])).replace("'", '')

def s_to_l(s):
    return [] if s == '[]' else s[1:-1].replace(' ', '').split(',')


class AnthySetup(object):
    def __init__(self):
        self.__config = Bus().get_config()
        self.__thumb_kb_layout_mode = None
        self.__thumb_kb_layout = None
        self.prefs = prefs = AnthyPrefs(None, self.__config)

        localedir = getenv("IBUS_LOCALEDIR")
        bindtextdomain("ibus-anthy", localedir)
        glade.bindtextdomain("ibus-anthy", localedir)
        glade.textdomain("ibus-anthy")
        glade_file = path.join(path.dirname(__file__), "setup.glade")
        self.xml = xml = glade.XML(glade_file)

        # glade "icon_name" property has a custom scaling and it seems
        # to be difficult to show the complicated small icon in metacity.
        # This can add the pixbuf without scaling.
        anthydir = path.dirname(path.dirname(__file__))
        if not anthydir:
            anthydir = "/usr/share/ibus-anthy"
        icon_path = path.join(anthydir, "icons", "ibus-anthy.png")
        if path.exists(icon_path):
            xml.get_widget('main').set_icon_from_file(icon_path)

        for name in ['input_mode', 'typing_method', 'conversion_segment_mode',
                     'period_style', 'symbol_style', 'ten_key_mode',
                     'behavior_on_focus_out', 'behavior_on_period',
                     'half_width_symbol', 'half_width_number', 'half_width_space',
                     'thumb:keyboard_layout_mode', 'thumb:keyboard_layout',
                     'thumb:fmv_extension', 'thumb:handakuten']:
            section, key = self.__get_section_key(name)
            xml.get_widget(name).set_active(prefs.get_value(section, key))

        l = ['default', 'atok', 'wnn']
        s_type = prefs.get_value('common', 'shortcut_type')
        s_type = s_type if s_type in l else 'default'
        xml.get_widget('shortcut_type').set_active(l.index(s_type))

        xml.get_widget('page_size').set_value(prefs.get_value('common',
                                                              'page_size'))

        tv = xml.get_widget('shortcut')
        tv.append_column(gtk.TreeViewColumn(_("Command"),
                                             gtk.CellRendererText(), text=0))
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        tv.append_column(gtk.TreeViewColumn(_("Shortcut"),
                                             renderer, text=1))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 0)
        ls = gtk.ListStore(str, str)
        sec = 'shortcut/' + s_type
        for k in self.prefs.keys(sec):
            ls.append([k, l_to_s(self.prefs.get_value(sec, k))])
        tv.set_model(ls)

        self.__thumb_kb_layout_mode = xml.get_widget('thumb:keyboard_layout_mode')
        self.__thumb_kb_layout = xml.get_widget('thumb:keyboard_layout')
        self.__set_thumb_kb_label()

        for name in ['thumb:ls', 'thumb:rs']:
            section, key = self.__get_section_key(name)
            xml.get_widget(name).set_text(prefs.get_value(section, key))

        tv = xml.get_widget('treeview2')
        tv.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), text=0))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 1)
        tv.set_model(gtk.ListStore(str))

        key = 'dict_admin_command'
        cli = self.__get_dict_cli_from_list(prefs.get_value('common', key))
        name = 'dict:entry_edit_dict_command'
        xml.get_widget(name).set_text(cli)
        key = 'add_word_command'
        cli = self.__get_dict_cli_from_list(prefs.get_value('common', key))
        name = 'dict:entry_add_word_command'
        xml.get_widget(name).set_text(cli)

        tv = xml.get_widget('dict:view')

        column = gtk.TreeViewColumn((" "))
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__text_cell_data_cb, 1)
        tv.append_column(column)

        column = gtk.TreeViewColumn(_("Description"))
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__text_cell_data_cb, 2)
        column.set_max_width(300)
        tv.append_column(column)

        # Translators: "Embd" means a short word of 'embedded'.
        column = gtk.TreeViewColumn(_("Embd"))
        renderer = gtk.CellRendererToggle()
        renderer.set_radio(False)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__toggle_cell_data_cb, 3)
        tv.append_column(column)

        # Translators: "Sgl" means a short word of 'single'.
        column = gtk.TreeViewColumn(_("Sgl"))
        renderer = gtk.CellRendererToggle()
        renderer.set_radio(False)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__toggle_cell_data_cb, 4)
        tv.append_column(column)

        '''
        Unfortunatelly reverse conversion is too slow.
        # Translators: "Rev" means a short word of 'reverse'.
        column = gtk.TreeViewColumn(_("Rev"))
        renderer = gtk.CellRendererToggle()
        renderer.set_radio(False)
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.__toggle_cell_data_cb, 5)
        tv.append_column(column)
        '''

        ls = gtk.ListStore(str, str, str, bool, bool, bool)
        tv.set_model(ls)
        self.__append_dicts_in_model()

        xml.signal_autoconnect(self)

    def __get_userhome(self):
        if 'HOME' not in environ:
            import pwd
            userhome = pwd.getpwuid(getuid()).pw_dir
        else:
            userhome = environ['HOME']
        userhome = userhome.rstrip('/')
        return userhome

    def __get_section_key(self, name):
        i = name.find(':')
        if i > 0:
            section = name[:i]
            key = name[i + 1:]
        else:
            section = 'common'
            key = name
        return (section, key)

    def __run_message_dialog(self, message, type=gtk.MESSAGE_INFO):
        label = gtk.Label(message)
        dlg = gtk.MessageDialog(parent=self.xml.get_widget('main'),
                                flags='modal',
                                type=type,
                                buttons=gtk.BUTTONS_OK,
                                message_format=message)
        dlg.run()
        dlg.destroy()

    def __set_thumb_kb_label(self):
        if self.__thumb_kb_layout_mode == None or \
           self.__thumb_kb_layout == None:
            return
        section, key = self.__get_section_key(self.__thumb_kb_layout_mode.name)
        layout_mode = self.prefs.get_value(section, key)
        if layout_mode:
            self.__thumb_kb_layout.set_sensitive(False)
        else:
            self.__thumb_kb_layout.set_sensitive(True)
        if layout_mode and \
           not self.__config.get_value('general', 'use_system_keyboard_layout', True):
            self.xml.get_widget('thumb:warning_hbox').show()
        else:
            self.xml.get_widget('thumb:warning_hbox').hide()

    def __get_dict_cli_from_list(self, cli_list):
            cli_str = cli_list[0]
            if len(cli_list) <= 2:
                return cli_str
            cli_str = cli_str + ' ' + ' '.join(cli_list[2:])
            return cli_str

    def __get_quoted_id(self, file):
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

    def __get_dict_file_from_id(self, selected_id):
        found = False
        files = self.prefs.get_value('dict', 'files')

        if selected_id == 'anthy_zipcode':
            return self.prefs.get_value('dict', 'anthy_zipcode')[0]
        elif selected_id == 'ibus_symbol':
            return self.prefs.get_value('dict', 'ibus_symbol')[0]
        for file in files:
            id = self.__get_quoted_id(file)
            if selected_id == id:
                found = True
                break
        if found:
            return file
        return None

    def __is_system_dict_file_from_id(self, selected_id):
        prefs = self.prefs
        section = 'dict/file/' + selected_id
        key = 'is_system'

        if key not in prefs.keys(section):
            return False
        return prefs.get_value(section, key)

    def __append_dict_id_in_model(self, id, is_gettext):
        prefs = self.prefs
        section = 'dict/file/' + id
        short_label = prefs.get_value(section, 'short_label')
        long_label = prefs.get_value(section, 'long_label')
        embed = prefs.get_value(section, 'embed')
        single = prefs.get_value(section, 'single')
        reverse = prefs.get_value(section, 'reverse')
        if is_gettext:
            long_label = _(long_label)
        l = self.xml.get_widget('dict:view').get_model()
        l.append([id, short_label, long_label, embed, single, reverse])

    def __append_dicts_in_model(self):
        prefs = self.prefs
        for file in prefs.get_value('dict', 'files'):
            if not path.exists(file):
                continue
            if file in prefs.get_value('dict', 'anthy_zipcode'):
                id = 'anthy_zipcode'
            elif file in prefs.get_value('dict', 'ibus_symbol'):
                id = 'ibus_symbol'
            else:
                id = self.__get_quoted_id(file)
                section = 'dict/file/' + id
                if section not in prefs.sections():
                    self.__fetch_dict_values(section)
            is_system_dict = self.__is_system_dict_file_from_id(id)
            self.__append_dict_id_in_model(id, is_system_dict)

    def __append_user_dict_from_dialog(self, file, id, new):
        files = self.prefs.get_value('dict', 'files')

        if new:
            if file in files:
                self.__run_message_dialog(_("Your choosed file has already been added: ") + file,
                                          gtk.MESSAGE_ERROR)
                return
            if not path.exists(file):
                self.__run_message_dialog(_("Your choosed file does not exist: ") + file,
                                          gtk.MESSAGE_ERROR)
                return
            if path.isdir(file):
                self.__run_message_dialog(_("Your choosed file is a directory: " + file),
                                          gtk.MESSAGE_ERROR)
                return
            if file.startswith(self.__get_userhome() + "/.anthy"):
                self.__run_message_dialog(_("You cannot add dictionaries in the anthy private directory: " + file),
                                          gtk.MESSAGE_ERROR)
                return

        if new:
            id = self.__get_quoted_id(file)
        if id == None or id == "":
            self.__run_message_dialog(_("Your file path is not good: ") + file,
                                      gtk.MESSAGE_ERROR)
            return

        single = self.xml.get_widget('dict:single').get_active()
        embed = self.xml.get_widget('dict:embed').get_active()
        reverse = self.xml.get_widget('dict:reverse').get_active()
        short_label = self.xml.get_widget('dict:short_entry').get_text()
        if len(unicode(short_label, "utf-8")) > 1:
            short_label = unicode(short_label, "utf-8")[0].encode("utf-8")
        long_label = self.xml.get_widget('dict:long_entry').get_text()

        if new:
            files.append(file)
            self.prefs.set_value('dict', 'files', files)

        if short_label == None or short_label == "":
                short_label = id[0]
        if long_label == None or long_label == "":
                long_label = id
        self.__update_dict_values(new, id, short_label, long_label, embed, single, reverse)
        self.xml.get_widget('btn_apply').set_sensitive(True)
        files = []

    def __init_dict_chooser_dialog(self):
        self.xml.get_widget('dict:single').set_active(True)
        self.xml.get_widget('dict:embed').set_active(False)
        self.xml.get_widget('dict:reverse').set_active(False)
        short_entry = self.xml.get_widget('dict:short_entry')
        short_entry.set_text('')
        short_entry.set_editable(True)
        long_entry = self.xml.get_widget('dict:long_entry')
        long_entry.set_text('')
        long_entry.set_editable(True)

    def __get_selected_dict_id(self):
        l, it = self.xml.get_widget('dict:view').get_selection().get_selected()

        if not it:
            return None
        return l.get_value(it, 0)

    def __set_selected_dict_to_dialog(self):
        selected_id = self.__get_selected_dict_id()
        if selected_id == None:
            return None

        is_system_dict = self.__is_system_dict_file_from_id(selected_id)

        prefs = self.prefs
        section = 'dict/file/' + selected_id
        short_label = prefs.get_value(section, 'short_label')
        long_label = prefs.get_value(section, 'long_label')
        embed = prefs.get_value(section, 'embed')
        single = prefs.get_value(section, 'single')
        reverse = prefs.get_value(section, 'reverse')

        if len(unicode(short_label, "utf-8")) > 1:
            short_label = unicode(short_label, "utf-8")[0].encode("utf-8")
        self.xml.get_widget('dict:single').set_active(single)
        self.xml.get_widget('dict:embed').set_active(embed)
        self.xml.get_widget('dict:reverse').set_active(reverse)
        short_entry = self.xml.get_widget('dict:short_entry')
        short_entry.set_text(short_label)
        long_entry = self.xml.get_widget('dict:long_entry')
        long_entry.set_text(long_label)
        if is_system_dict:
            short_entry.set_editable(False)
            long_entry.set_editable(False)
        else:
            short_entry.set_editable(True)
            long_entry.set_editable(True)

        return selected_id

    def __fetch_dict_values(self, section):
        prefs = self.prefs
        prefs.set_new_section(section)
        prefs.set_new_key(section, 'short_label')
        prefs.fetch_item(section, 'short_label')
        prefs.set_value(section, 'short_label',
                        str(prefs.get_value(section, 'short_label')))
        prefs.set_new_key(section, 'long_label')
        prefs.fetch_item(section, 'long_label')
        prefs.set_value(section, 'long_label',
                        str(prefs.get_value(section, 'long_label')))
        prefs.set_new_key(section, 'embed')
        prefs.fetch_item(section, 'embed')
        prefs.set_new_key(section, 'single')
        prefs.fetch_item(section, 'single')
        prefs.set_new_key(section, 'reverse')
        prefs.fetch_item(section, 'reverse')

    def __update_dict_values(self, new, id, short_label, long_label, embed, single, reverse):
        prefs = self.prefs
        section = 'dict/file/' + id
        if section not in prefs.sections():
            prefs.set_new_section(section)

        is_system_dict = self.__is_system_dict_file_from_id(id)
        if is_system_dict:
            if 'short_label' in prefs.keys(section):
                short_label = prefs.get_value(section, 'short_label')
            if 'long_label' in prefs.keys(section):
                long_label = prefs.get_value(section, 'long_label')

        if new:
            l = self.xml.get_widget('dict:view').get_model()
            l.append([id, short_label, long_label, embed, single, reverse])
        else:
            l, i = self.xml.get_widget('dict:view').get_selection().get_selected()
            if i :
                l[i] = [id, short_label, long_label, embed, single, reverse]

        key = 'short_label'
        if key not in prefs.keys(section):
            prefs.set_new_key(section, key)
        prefs.set_value(section, key, short_label)
        key = 'long_label'
        if key not in prefs.keys(section):
            prefs.set_new_key(section, key)
        prefs.set_value(section, key, long_label)
        key = 'embed'
        if key not in prefs.keys(section):
            prefs.set_new_key(section, key)
        prefs.set_value(section, key, embed)
        key = 'single'
        if key not in prefs.keys(section):
            prefs.set_new_key(section, key)
        prefs.set_value(section, key, single)
        key = 'reverse'
        if key not in prefs.keys(section):
            prefs.set_new_key(section, key)
        prefs.set_value(section, key, reverse)

    def __text_cell_data_cb(self, layout, renderer, model, iter, id):
        l = self.xml.get_widget('dict:view').get_model()
        text = l.get_value(iter, id)
        renderer.set_property('text', text)

    def __toggle_cell_data_cb(self, layout, renderer, model, iter, id):
        l = self.xml.get_widget('dict:view').get_model()
        active = l.get_value(iter, id)
        renderer.set_property('active', active)

    def on_selection_changed(self, widget, id):
        set_sensitive = lambda a, b: self.xml.get_widget(a).set_sensitive(b)
        flg = True if widget.get_selected()[1] else False
        for name in [['btn_default', 'btn_edit'], ['button5', 'button6']][id]:
            set_sensitive(name, flg)

    def on_main_delete(self, widget, event):
        self.on_btn_cancel_clicked(widget)
        return True

    def on_btn_ok_clicked(self, widget):
        if self.xml.get_widget('btn_apply').state == gtk.STATE_INSENSITIVE:
            gtk.main_quit()
            return True
        dlg = self.xml.get_widget('quit_check')
        dlg.set_markup('<big><b>%s</b></big>' % _('Confirm'))
        dlg.format_secondary_text(_('Are you sure to close Setup?'))
        id = dlg.run()
        dlg.hide()
        if id == gtk.RESPONSE_OK:
            self.prefs.commit_all()
            gtk.main_quit()
            return True

    def on_btn_cancel_clicked(self, widget):
        if self.xml.get_widget('btn_apply').state == gtk.STATE_INSENSITIVE:
            gtk.main_quit()
            return True
        dlg = self.xml.get_widget('quit_check_without_save')
        dlg.set_markup('<big><b>%s</b></big>' % _('Notice!'))
        dlg.format_secondary_text(_('Are you sure to close Setup without save configure?'))
        id = dlg.run()
        dlg.hide()
        if id == gtk.RESPONSE_OK:
            gtk.main_quit()
            return True

    def on_btn_apply_clicked(self, widget):
        self.prefs.commit_all()
        widget.set_sensitive(False)

    def on_cb_changed(self, widget):
        section, key = self.__get_section_key(widget.name)
        self.prefs.set_value(section, key, widget.get_active())
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_sb_changed(self, widget):
        section, key = self.__get_section_key(widget.name)
        self.prefs.set_value(section, key, widget.get_value_as_int())
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_ck_toggled(self, widget):
        section, key = self.__get_section_key(widget.name)
        self.prefs.set_value(section, key, widget.get_active())
        self.xml.get_widget('btn_apply').set_sensitive(True)
        if self.__thumb_kb_layout_mode and \
           widget.name == self.__thumb_kb_layout_mode.name:
            self.__set_thumb_kb_label()

    def on_btn_edit_clicked(self, widget):
        ls, it = self.xml.get_widget('shortcut').get_selection().get_selected()
        m = self.xml.get_widget('treeview2').get_model()
        m.clear()
        for s in s_to_l(ls.get(it, 1)[0]):
            m.append([s])
        self.xml.get_widget('entry2').set_text('')
        for w in ['checkbutton6', 'checkbutton7', 'checkbutton8']:
            self.xml.get_widget(w).set_active(False)
        dlg = self.xml.get_widget('edit_shortcut')
        id = dlg.run()
        dlg.hide()
        if id == gtk.RESPONSE_OK:
            new = l_to_s([m[i][0] for i in range(len(m))])
            if new != ls.get(it, 1)[0]:
                sec = self._get_shortcut_sec()
                self.prefs.set_value(sec, ls.get(it, 0)[0], s_to_l(new))
                ls.set(it, 1, new)
                self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_btn_default_clicked(self, widget):
        ls, it = self.xml.get_widget('shortcut').get_selection().get_selected()
        sec = self._get_shortcut_sec()
        new = l_to_s(self.prefs.default[sec][ls.get(it, 0)[0]])
        if new != ls.get(it, 1)[0]:
            self.prefs.set_value(sec, ls.get(it, 0)[0], s_to_l(new))
            ls.set(it, 1, new)
            self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_btn_thumb_key_clicked(self, widget):
        if widget.name == 'thumb:button_ls':
            entry = 'thumb:ls'
        elif widget.name == 'thumb:button_rs':
            entry = 'thumb:rs'
        else:
            return
        text = self.xml.get_widget(entry).get_text()
        m = self.xml.get_widget('treeview2').get_model()
        m.clear()
        if text != None:
            m.append([text])
            i = m.get_iter_first()
            self.xml.get_widget('treeview2').get_selection().select_iter(i)
        self.xml.get_widget('entry2').set_text('')
        self.xml.get_widget('button4').hide()
        self.xml.get_widget('button5').show()
        self.xml.get_widget('button6').hide()
        for w in ['checkbutton6', 'checkbutton7', 'checkbutton8']:
            self.xml.get_widget(w).set_active(False)
        dlg = self.xml.get_widget('edit_shortcut')
        id = dlg.run()
        dlg.hide()
        self.xml.get_widget('button4').show()
        self.xml.get_widget('button5').hide()
        self.xml.get_widget('button6').show()
        if id == gtk.RESPONSE_OK:
            l, i = self.xml.get_widget('treeview2').get_selection().get_selected()
            new = l[i][0]
            if new != text:
                section, key = self.__get_section_key(entry)
                self.prefs.set_value(section, key, new)
                self.xml.get_widget(entry).set_text(new)
                self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_btn_dict_command_clicked(self, widget):
        if widget.name == 'dict:btn_edit_dict_command':
            key = 'dict_admin_command'
        elif widget.name == 'dict:btn_add_word_command':
            key = 'add_word_command'
        else:
            return
        command = self.prefs.get_value('common', key)
        if not path.exists(command[0]):
            self.__run_message_dialog(_("Your file does not exist: ") + command[0],
                                      gtk.MESSAGE_ERROR)
            return
        os.spawnl(os.P_NOWAIT, *command)

    def on_btn_dict_add_clicked(self, widget):
        file = None
        id = None

        if widget.name == "dict:btn_add":
            dlg = gtk.FileChooserDialog(title=_("Open Dictionary File"),
                                        parent=self.xml.get_widget('main'),
                                        action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        if widget.name == "dict:btn_edit":
            dlg = gtk.Dialog(title=_("Edit Dictionary File"),
                             parent=self.xml.get_widget('main'),
                             flags='modal',
                             buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                      gtk.STOCK_OK, gtk.RESPONSE_OK))

        vbox = self.xml.get_widget('dict:add_extra_vbox')
        if widget.name == "dict:btn_add":
            # Need to init for the second time
            self.__init_dict_chooser_dialog()
            dlg.set_extra_widget(vbox)
        if widget.name == "dict:btn_edit":
            id = self.__set_selected_dict_to_dialog()
            if id == None:
                self.__run_message_dialog(_("Your choosed file is not correct."),
                                          gtk.MESSAGE_ERROR)
                return
            parent_vbox = dlg.vbox
            parent_vbox.add(vbox)
        vbox.show_all()

        if dlg.run() == gtk.RESPONSE_OK:
            if widget.name == "dict:btn_add":
                file = dlg.get_filename()
                if file[0] != '/':
                    dir = dlg.get_current_folder()
                    file = dir + "/" + file
                self.__append_user_dict_from_dialog(file, None, True)
            elif widget.name == "dict:btn_edit":
                self.__append_user_dict_from_dialog(None, id, False)
        dlg.hide()
        vbox.unparent()

    def on_btn_dict_delete_clicked(self, widget):
        l, i = self.xml.get_widget('dict:view').get_selection().get_selected()

        if not i:
            return
        selected_id = l.get_value(i, 0)

        if selected_id == None:
            return
        if self.__is_system_dict_file_from_id(selected_id):
            self.__run_message_dialog(_("You cannot delete the system dictionary."),
                                      gtk.MESSAGE_ERROR)
            return

        file = self.__get_dict_file_from_id(selected_id)
        if file != None:
            files = self.prefs.get_value('dict', 'files')
            files.remove(file)
            self.prefs.set_value('dict', 'files', files)
            self.xml.get_widget('btn_apply').set_sensitive(True)
            l.remove(i)
            return

        l.remove(i)

    def on_btn_dict_view_clicked(self, widget):
        dict_file = None
        selected_id = self.__get_selected_dict_id()
        if selected_id == None:
            return

        dict_file = self.__get_dict_file_from_id(selected_id)
        if dict_file == None:
            self.__run_message_dialog(_("Your file is not good."),
                                      gtk.MESSAGE_ERROR)
            return
        if not path.exists(dict_file):
            self.__run_message_dialog(_("Your file does not exist: ") + dict_file,
                                      gtk.MESSAGE_ERROR)
            return

        if dict_file == None:
            return

        section = 'dict/file/' + selected_id
        if 'preview_lines' not in self.prefs.keys(section):
            section = 'dict/file/default'
        nline = self.prefs.get_value(section, 'preview_lines')

        section = 'dict/file/' + selected_id
        if 'encoding' not in self.prefs.keys(section):
            section = 'dict/file/default'
        encoding = self.prefs.get_value(section, 'encoding')

        lines = "";
        for i, line in enumerate(file(dict_file)):
            if nline >= 0 and i >= nline:
                break;
            lines = lines + line
        if encoding != None and encoding != 'utf-8':
            lines = unicode(lines, encoding).encode('utf-8')

        dlg = gtk.Dialog(title=_("View Dictionary File"),
                         parent=self.xml.get_widget('main'),
                         flags='modal',
                         buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK))
        buffer = gtk.TextBuffer()
        buffer.set_text (lines)
        text_view = gtk.TextView(buffer)
        text_view.set_editable(False)
        sw = gtk.ScrolledWindow()
        sw.add(text_view)
        parent_vbox = dlg.vbox
        parent_vbox.add(sw)
        sw.show_all()
        dlg.set_default_size(500, 500)
        dlg.run()
        dlg.destroy()

    def on_btn_dict_order_clicked(self, widget):
        dict_file = None
        l, it = self.xml.get_widget('dict:view').get_selection().get_selected()

        if not it:
            return
        selected_path = l.get_path(it)
        selected_id = l.get_value(it, 0)

        if widget.name == "dict:btn_up":
            if selected_path[0] <= 0:
                return
            next_path = (selected_path[0] - 1, )
        elif widget.name == "dict:btn_down":
            if selected_path[0] + 1 >= len(l):
                return
            next_path = (selected_path[0] + 1, )
        next_it = l.get_iter(next_path)
        if next_it:
            l.swap(it, next_it)

        dict_file = self.__get_dict_file_from_id(selected_id)
        files = self.prefs.get_value('dict', 'files')

        if dict_file == None:
            return

        i = files.index(dict_file)
        if widget.name == "dict:btn_up":
            if i <= 0:
                return
            next_i = i - 1
        elif widget.name == "dict:btn_down":
            if i + 1 >= len(dict_file):
                return
            next_i = i + 1
        f = files[i]
        files[i] = files[next_i]
        files[next_i] = f
        self.prefs.set_value('dict', 'files', files)
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def _get_shortcut_sec(self):
        l = ['default', 'atok', 'wnn']
        s_type = self.xml.get_widget('shortcut_type').get_active_text().lower()
        return 'shortcut/' + (s_type if s_type in l else 'default')

    def on_shortcut_type_changed(self, widget):
        ls = self.xml.get_widget('shortcut').get_model()
        ls.clear()

        for a in widget.get_model():
            print a[0]

        sec = self._get_shortcut_sec()
        for k in self.prefs.keys(sec):
            ls.append([k, l_to_s(self.prefs.get_value(sec, k))])

        section, key = self.__get_section_key(widget.name)
        self.prefs.set_value(section, key, sec[len('shortcut/'):])
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_shortcut_key_release_event(self, widget, event):
        if event.hardware_keycode in [36, 65]:
            self.on_btn_edit_clicked(None)

    def on_shortcut_click_event(self, widget, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            widget.dc = True
        elif event.type == gtk.gdk.BUTTON_RELEASE:
            if hasattr(widget, 'dc') and widget.dc:
                self.on_btn_edit_clicked(None)
                widget.dc = False

    def on_key_input_dialog_key_press_event(self, widget, event):
        return True

    def on_key_input_dialog_key_release_event(self, widget, event):
        widget.e = (event.keyval, event.state)
        widget.response(gtk.RESPONSE_OK)
        return True

    def on_entry_dict_command_changed(self, widget):
        if not widget.get_text():
            return
        list = widget.get_text().split()
        if list[0][0] == '/':
            if len(list) == 1:
                list.append(list[0][list[0].rfind('/') + 1:])
            else:
                list.insert(1, list[0][list[0].rfind('/') + 1:])
        else:
            if len(list) == 1:
                list[0] = '/usr/bin/' + list[0]
            else:
                list.insert(0, '/usr/bin/' + list[0])
                list[1] = list[1][list[1].rfind('/') + 1:]
        if widget.name == 'dict:entry_edit_dict_command':
            key = 'dict_admin_command'
        elif widget.name == 'dict:entry_add_word_command':
            key = 'add_word_command'
        else:
            return
        self.prefs.set_value('common', key, list)
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_entry2_changed(self, widget):
        if not widget.get_text():
            self.xml.get_widget('button4').set_sensitive(False)
        else:
            self.xml.get_widget('button4').set_sensitive(True)

    def on_button7_clicked(self, widget):
        dlg = self.xml.get_widget('key_input_dialog')
        dlg.set_markup('<big><b>%s</b></big>' % _('Please press a key (or a key combination)'))
        dlg.format_secondary_text(_('The dialog will be closed when the key is released'))
        id = dlg.run()
        dlg.hide()
        if id == gtk.RESPONSE_OK:
            key, state = dlg.e
            if (state & (modifier.CONTROL_MASK | modifier.ALT_MASK) and
                    ord('a') <= key <= ord('z')):
                key = ord(chr(key).upper())
            self.xml.get_widget('entry2').set_text(keysyms.keycode_to_name(key))

            for w, i in [('checkbutton6', modifier.CONTROL_MASK),
                         ('checkbutton7', modifier.ALT_MASK),
                         ('checkbutton8', modifier.SHIFT_MASK)]:
                self.xml.get_widget(w).set_active(True if state & i else False)

    def on_button4_clicked(self, widget):
        s = self.xml.get_widget('entry2').get_text()
        if not s or not keysyms.name_to_keycode(s):
            dlg = self.xml.get_widget('invalid_keysym')
            dlg.set_markup('<big><b>%s</b></big>' % _('Invalid keysym'))
            dlg.format_secondary_text(_('This keysym is not valid'))
            dlg.run()
            dlg.hide()
            return True
        for w, m in [('checkbutton6', 'Ctrl+'),
                     ('checkbutton7', 'Alt+'),
                     ('checkbutton8', 'Shift+')]:
            if self.xml.get_widget(w).get_active():
                s = m + s
        l = self.xml.get_widget('treeview2').get_model()
        for i in range(len(l)):
            if l[i][0] == s:
                return True
        l.append([s])

    def on_button5_clicked(self, widget):
        s = self.xml.get_widget('entry2').get_text()
        if not s or not keysyms.name_to_keycode(s):
            dlg = self.xml.get_widget('invalid_keysym')
            dlg.set_markup('<big><b>%s</b></big>' % _('Invalid keysym'))
            dlg.format_secondary_text(_('This keysym is not valid'))
            dlg.run()
            dlg.hide()
            return True
        for w, m in [('checkbutton6', 'Ctrl+'),
                     ('checkbutton7', 'Alt+'),
                     ('checkbutton8', 'Shift+')]:
            if self.xml.get_widget(w).get_active():
                s = m + s
        l, i = self.xml.get_widget('treeview2').get_selection().get_selected()
        l[i][0] = s
        return True

    def on_button6_clicked(self, widget):
        l, i = self.xml.get_widget('treeview2').get_selection().get_selected()
        if i:
            l.remove(i)

    def run(self):
        gtk.main()


if __name__ == "__main__":
    AnthySetup().run()

