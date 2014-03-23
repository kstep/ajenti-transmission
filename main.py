# -*- encoding: utf-8 -*-
import q
from ajenti.api import *  # noqa
from ajenti.plugins import *  # noqa
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder
from ajenti.ui import on
from transmissionrpc import Client, Torrent

def torrent_get(self, key, default=None):
    return getattr(self, key, default)
Torrent.get = torrent_get
Torrent.__getitem__ = torrent_get

@plugin
class TransmissionPlugin (SectionPlugin):
    def init(self):
        # meta-data
        self.title = 'Transmission'
        self.icon = 'download'
        self.category = _("Software")

        self.append(self.ui.inflate('transmission:main'))

        self.torrents = []

        def post_item_bind(root, collection, value, ui):
            print (collection, value, ui)

        self.find('torrents').post_item_bind = post_item_bind
        self.binder = Binder(self, self.find('main'))

    def on_first_page_load(self):
        self._client = Client()
        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        #self.torrents = map(lambda t: {'name': t.name}, self._client.get_torrents())
        self.torrents = self._client.get_torrents()
        self.torrent = self.torrents[0]
        self.binder.populate()


