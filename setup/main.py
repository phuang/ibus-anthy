from os import path, getenv
import gtk
import pango
from gtk import glade
from ibus import keysyms, modifier
from gettext import dgettext, bindtextdomain

from anthyprefs import AnthyPrefs


_ = lambda a : dgettext('ibus-anthy', a)

def l_to_s(l):
    return str(sorted([str(s) for s in l])).replace("'", '')

def s_to_l(s):
    return [] if s == '[]' else s[1:-1].replace(' ', '').split(',')


class AnthySetup(object):
    def __init__(self):
        self.prefs = prefs = AnthyPrefs()

        localedir = getenv("IBUS_LOCALEDIR")
        bindtextdomain("ibus-anthy", localedir)
        glade.bindtextdomain("ibus-anthy", localedir)
        glade.textdomain("ibus-anthy")
        glade_file = path.join(path.dirname(__file__), "setup.glade")
        self.xml = xml = glade.XML(glade_file)

        for name in ['input_mode', 'typing_method',
                     'period_style', 'ten_key_mode',
                     'behivior_on_focus_out', 'behivior_on_period',
                     'half_width_symbol', 'half_width_number']:
            xml.get_widget(name).set_active(prefs.get_value('common', name))

        l = ['default', 'atok', 'wnn']
        s_type = prefs.get_value('common', 'shortcut_type')
        s_type = s_type if s_type in l else 'default'
        xml.get_widget('shortcut_type').set_active(l.index(s_type))

        xml.get_widget('page_size').set_value(prefs.get_value('common',
                                                              'page_size'))

        tv = xml.get_widget('shortcut')
        tv.append_column(gtk.TreeViewColumn('Command',
                                             gtk.CellRendererText(), text=0))
        renderer = gtk.CellRendererText()
        renderer.set_property("ellipsize", pango.ELLIPSIZE_END)
        tv.append_column(gtk.TreeViewColumn('Shortcut',
                                             renderer, text=1))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 0)
        ls = gtk.ListStore(str, str)
        sec = 'shortcut/' + s_type
        for k in self.prefs.keys(sec):
            ls.append([k, l_to_s(self.prefs.get_value(sec, k))])
        tv.set_model(ls)

        tv = xml.get_widget('treeview2')
        tv.append_column(gtk.TreeViewColumn('', gtk.CellRendererText(), text=0))
        tv.get_selection().connect_after('changed',
                                          self.on_selection_changed, 1)
        tv.set_model(gtk.ListStore(str))

        xml.signal_autoconnect(self)

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
        self.prefs.set_value('common', widget.name, widget.get_active())
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_sb_changed(self, widget):
        self.prefs.set_value('common', widget.name, widget.get_value_as_int())
        self.xml.get_widget('btn_apply').set_sensitive(True)

    def on_ck_toggled(self, widget):
        self.prefs.set_value('common', widget.name, widget.get_active())
        self.xml.get_widget('btn_apply').set_sensitive(True)

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

    def _get_shortcut_sec(self):
        l = ['default', 'atok', 'wnn']
        s_type = self.xml.get_widget('shortcut_type').get_active_text().lower()
        return 'shortcut/' + s_type if s_type in l else 'default'

    def on_shortcut_type_changed(self, widget):
        ls = self.xml.get_widget('shortcut').get_model()
        ls.clear()

        for a in widget.get_model():
            print a[0]

        sec = self._get_shortcut_sec()
        for k in self.prefs.keys(sec):
            ls.append([k, l_to_s(self.prefs.get_value(sec, k))])

        self.prefs.set_value('common', widget.name, sec[len('shortcut/'):])
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

    def on_entry2_changed(self, widget):
        if not widget.get_text():
            self.xml.get_widget('button4').set_sensitive(False)
        else:
            self.xml.get_widget('button4').set_sensitive(True)

    def on_button7_clicked(self, widget):
        dlg = self.xml.get_widget('key_input_dialog')
        dlg.set_markup('<big><b>%s</b></big>' % _('Please press a key (or a key combination)'))
        dlg.format_secondary_text(_('The dialog willbe closed when the key is released'))
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

    def on_button6_clicked(self, widget):
        l, i = self.xml.get_widget('treeview2').get_selection().get_selected()
        if i:
            l.remove(i)

    def run(self):
        gtk.main()


if __name__ == "__main__":
    AnthySetup().run()

