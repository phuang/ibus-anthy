import sys
from gtk import gdk


class ComposeKey(object):
    def __init__(self, fn='/usr/share/X11/locale/en_US.UTF-8/Compose'):
        self._table = {}
        self._comments = {}

        fp = file(fn, 'r')
        for s in fp.readlines():
            if not s.startswith('<'):
                continue
            s = unicode(s, 'utf-8')
            a, b = s.strip().replace('\t', ' ').split(':')
            a = [gdk.keyval_from_name(i[1:-1]) for i in a.split(' ') if i]
            if a.count(0):
#                print s,
                continue
            b = [i for i in b.split(' ') if i]
            try:
                c = ord(b[0][1:-1] if b[0].find('\\') < 0 else b[0][2:-1])
            except:
#                print ' '.join(b[3:])
                continue
            d = self._table
            for i in a[:-1]:
                d = d.setdefault(i, {})
            d[a[-1]] = c
            self._comments[c] = ' '.join(b[3:])
        fp.close()

    def get(self, *l):
        d = self._table
        for i in l:
            d = d[gdk.keyval_from_name(i) if isinstance(i, str) else i]
        if isinstance(d, dict):
            raise IndexError('NOTEND')
        return d

    def get_comment(self, c):
        return self._comments[c]


_c = ComposeKey()

def get(l):
    d = _c._table
    for i in l:
        d = d[gdk.keyval_from_name(i) if isinstance(i, str) else i]
    if isinstance(d, dict):
        raise IndexError('NOTEND')
    return d

