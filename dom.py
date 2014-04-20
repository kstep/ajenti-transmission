from ajenti.api import *
from ajenti.ui import p, UIElement

@p('width', default=None)
@p('height', default=None)
@p('text', default='', bindtypes=[str, unicode, int, long])
@plugin
class ContentBox (UIElement):
    typeid = 'contentbox'


@p('value', default='', bindtypes=[str, unicode, int, long])
@p('readonly', type=bool, default=False)
@p('lines', default=10, bindtypes=[int])
@p('type', default='text')
@plugin
class BigTextBox (UIElement):
    typeid = 'bigtextbox'


@p('value', default=0, bindtypes=[int, long])
@p('minvalue', default=0, type=int)
@p('maxvalue', default=10, type=int)
@p('width', default=None, type=int)
@plugin
class Slider (UIElement):
    typeid = 'slider'
