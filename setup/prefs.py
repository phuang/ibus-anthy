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

from ibus import Bus


class Prefs(object):
    _prefix = 'engine/dummy'

    def __init__(self, bus=None, config=None):
        self.default = {}
        self.modified = {}
        self.new = {}

        self._config = config if config else \
                       bus.get_config() if bus else  \
                       Bus().get_config()

    def keys(self, section):
        return self.default[section].keys()

    def sections(self):
        return self.default.keys()

    def set_new_section(self, section):
        self.default.setdefault(section, {})

    def set_new_key(self, section, key):
        self.default[section].setdefault(key)

    def get_value(self, section, key):
        try:
            return self.new[section][key]
        except:
            try:
                return self.modified[section][key]
            except:
                return self.default[section][key]

    def set_value(self, section, key, value):
        if section not in self.sections():
            self.set_new_section(section)
        if key not in self.keys(section):
            self.set_new_key(section, key)
        self.default[section][key]
        self.new.setdefault(section, {})[key] = value

    def fetch_all(self):
        for s in self.sections():
            self.fetch_section(s)

    def fetch_section(self, section):
        for k in self.keys(section):
            self.fetch_item(section, k)

    def fetch_item(self, section, key, readonly=False):
        s = '/'.join(
            [s for s in '/'.join([self._prefix, section]).split('/') if s])
        v = self._config.get_value(s, key, None)
        if readonly:
            return v != None
        if v != None:
            self.modified.setdefault(section, {})[key] = v if v != [''] else []
        return True

    def commit_all(self):
        for s in self.new.keys():
            self.commit_section(s)

    def commit_section(self, section):
        if section in self.new:
            for k in self.new[section].keys():
                self.commit_item(section, k)

    def commit_item(self, section, key):
        if section in self.new and key in self.new[section]:
            s = '/'.join(
                [s for s in '/'.join([self._prefix, section]).split('/') if s])
            v = self.new[section][key]
            if v == []:
                v = ['']
            self._config.set_value(s, key, v)
            self.modified.setdefault(section, {})[key] = v
            del(self.new[section][key])

    def undo_all(self):
        self.new.clear()

    def undo_section(self, section):
        try:
            del(self.new[section])
        except:
            pass

    def undo_item(self, section, key):
        try:
            del(self.new[section][key])
        except:
            pass

    def set_default_all(self):
        for s in self.sections():
            self.set_default_section(s)

    def set_default_section(self, section):
        for k in self.keys(section):
            self.set_default_item(section, k)

    def set_default_item(self, section, key):
        try:
            if key in self.modified[section] or key in self.new[section]:
                self.new[section][key] = self.default[section][key]
        except:
            pass

