from ajenti.util import public
from datetime import datetime
from itertools import chain, imap
import operator as op
import chardet

__all__ = ['ident', 'intbool', 'time', 'unixtime', 'timedelta', 'listof']
ident = lambda x: x
intbool = lambda v: bool(int(v))
time = lambda t: '%2d:%02d' % (int(t or 0) / 60, int(t or 0) % 60)
unixtime = lambda t: datetime.fromtimestamp(int(t))
timedelta = lambda t: datetime.timedelta(int(t) // 86400, int(t) % 86400)
listof = lambda cast: lambda lst: map(cast, lst)
sort = lambda listcast, field: lambda v: sorted(listcast(v), key=op.attrgetter(field))

@public
def fixutf8(value):
    if not value:
        return u''

    try:
        utf8 = value.decode('utf-8')
        raw = utf8.encode('raw_unicode_escape')
        encoding = chardet.detect(raw)['encoding']

        return (utf8 if encoding == 'ascii' else
                raw.decode({
                    'MacCyrillic': 'windows-1251',
                    'ISO-8859-7': 'windows-1251',
                    }.get(encoding, encoding)))

    except (UnicodeDecodeError, UnicodeEncodeError):
        return value


@public
def timestamp(d):
    for pattern in (
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y',
            ):
        try:
            return datetime.strptime(d, pattern)
        except ValueError:
            continue
    return d

@public
def flatten(items):
    return (item
            for _ in items
            for item in _)


@public
def unique(items):
    last_item = next(items)
    yield last_item

    for item in items:
        if item != last_item:
            yield item
            last_item = item

@public
class Model(object):
    _casts = {}
    _defaults = {}
    _keymap = {}

    def __init__(self, items=(), **kwargs):
        self.load(items, kwargs)

    def _init(self):
        pass

    def _mapkey(self, key):
        return self._keymap.get(key, None) or key.replace('-', '_')

    def get(self, key, default=None):
        if default is None:
            default = self._defaults.get(key, None)

        return getattr(self, key, default)

    def load(self, *iters, **kwargs):
        if kwargs:
            iters = iters + (kwargs,)

        if iters:
            self.__dict__.update((self._mapkey(k),
                self._casts.get(k, ident)(v) if v is not None else None)
                for it in iters
                for k, v in (it.iteritems() if isinstance(it, dict) else it))

        self._init()

    def __getattr__(self, key):
        try:
            return self._defaults[key]
        except KeyError:
            raise AttributeError(key)

    def update(self, items=(), **kwargs):
        self.__dict__.update(items, **kwargs)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        try:
            delattr(self, key)
        except AttributeError:
            pass

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            return self._defaults[key]

    def __contains__(self, key):
        return hasattr(self, key)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, repr(self.__dict__))

    EMPTY = None
    class __metaclass__(type):
        def __init__(cls, name, bases, attrs):
            type.__init__(cls, name, bases, attrs)
            try:
                cls.EMPTY = cls()
            except AttributeError:
                pass

