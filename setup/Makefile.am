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

BUILT_SOURCES = anthyprefs.py

libexec_SCRIPTS = ibus-setup-anthy

setup_anthy_PYTHON = \
	anthyprefs.py \
	main.py \
	prefs.py \
	setup.glade \
	$(NULL)

setup_anthy_built_files = \
	$(BUILT_SOURCES) \
	$(libexec_SCRIPTS) \
	$(NULL)

setup_anthy_built_in_files = $(addsuffix .in, $(setup_anthy_built_files))

setup_anthydir = $(datadir)/ibus-anthy/setup

CONFIG_CLEAN_FILES = \
	$(BUILT_SOURCES) \
	$(libexec_SCRIPTS) \
	$(NULL)

CLEANFILES = \
	$(BUILT_SOURCES) \
	*.pyc \
	$(NULL)

EXTRA_DIST = \
	$(setup_anthy_built_in_files) \
	$(NULL)

anthyprefs.py: anthyprefs.py.in
	sed -e "s|\@ANTHY_ZIPCODE_FILE\@|$(ANTHY_ZIPCODE_FILE)|g" \
	    -e "s|\@KASUMI_EXEC_FILE\@|$(KASUMI_EXEC_FILE)|g" \
	    -e "s|\@KASUMI_ICON_FILE\@|$(KASUMI_ICON_FILE)|g" \
	    -e "s|\@VERSION\@|$(VERSION)|g" \
	    -e "s|\@pkgdatadir\@|$(pkgdatadir)|g" \
	$< > $@

# Need a time lag between .py and .py.in files to build .py files
# because *_PYTHON valuables are installed in the tarball.
dist-hook:
	@sleep 1; \
	for in_file in $(setup_anthy_built_in_files) ; do \
	    if [ -f $(distdir)/$(srcdir)/$$in_file ] ; then \
	        touch $(distdir)/$(srcdir)/$$in_file; \
	    fi; \
	done;

test:
	$(ENV_IBUS_TEST) DBUS_DEBUG=true \
		   LANG=en_US \
		   PYTHONPATH=$(abs_top_srcdir):$(pyexecdir) \
		   IBUS_LOCALEDIR=@localedir@ \
		   $(PYTHON) $(srcdir)/main.py

