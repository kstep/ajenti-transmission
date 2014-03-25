# -*- encoding: utf-8 -*-
from ajenti.api import *  # noqa
from ajenti.plugins import *  # noqa
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder
from ajenti.ui import on
from ajenti.util import str_fsize, str_timedelta
from transmissionrpc import torrent, client

TransmissionTorrent = torrent.Torrent
class Torrent(TransmissionTorrent):
    @property
    def is_priority_high(self):
        return self.priority == 'high'

    @property
    def is_priority_low(self):
        return self.priority == 'low'

    @property
    def is_priority_normal(self):
        return self.priority == 'normal'

    @property
    def total_size(self):
        return str_fsize(self.totalSize)

    @property
    def size_when_done(self):
        return str_fsize(self.sizeWhenDone)

    @property
    def uploaded_ever(self):
        return str_fsize(self.uploadedEver)

    @property
    def downloaded_ever(self):
        return str_fsize(self.downloadedEver)

    @property
    def is_started(self):
        return self.status != 'stopped'

    @property
    def is_stopped(self):
        return self.status == 'stopped'

    @property
    def icon(self):
        return {
            'check pending': 'ellipsis-horizontal',
            'checking': 'dashboard',
            'downloading': 'download-alt',
            'seeding': 'upload-alt',
            'stopped': 'pause'
            }.get(self.status, 'question')

    @property
    def time_left(self):
        try:
            return str_timedelta(self.eta)
        except ValueError:
            return 'unknown time'

    @property
    def progress_str(self):
        return '%0.2f%%' % self.progress

torrent.Torrent = client.Torrent = Torrent

@plugin
class TransmissionPlugin (SectionPlugin):
    def init(self):
        # meta-data
        self.title = 'Transmission'
        self.icon = 'download-alt'
        self.category = _("Software")

        self.append(self.ui.inflate('transmission:main'))

        self.torrents = []

        def post_item_bind(root, collection, value, ui):
            ui.find('priority_low').on('click', self.set_priority_low, value)
            ui.find('priority_normal').on('click', self.set_priority_normal, value)
            ui.find('priority_high').on('click', self.set_priority_high, value)
            ui.find('start').on('click', self.start, value)
            ui.find('stop').on('click', self.stop, value)

        self.find('torrents').post_item_bind = post_item_bind
        self.find('torrents').delete_item = self.remove
        self.binder = Binder(self, self.find('main'))

    def on_first_page_load(self):
        self._client = client.Client()
        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        #self.torrents = map(lambda t: {'name': t.name}, self._client.get_torrents())
        self.torrents = self._client.get_torrents()
        self.torrent = self.torrents[0]
        self.binder.populate()

    def refresh_item(self, item):
        item.update()
        self.binder.populate()

    def set_priority_low(self, item):
        item.priority = 'low'
        self.refresh_item(item)

    def set_priority_normal(self, item):
        item.priority = 'normal'
        self.refresh_item(item)

    def set_priority_high(self, item):
        item.priority = 'high'
        self.refresh_item(item)

    def start(self, item):
        item.start()
        self.refresh_item(item)

    def stop(self, item):
        item.stop()
        self.refresh_item(item)

    def remove(self, item, collection):
        self._client.remove_torrent([item.id], delete_data=False)

    def delete(self, item, collection):
        self._client.remove_torrent([item.id], delete_item=True)

    @on('add', 'click')
    def open_add_dialog(self):
        self.find('add_dialog').visible = True

    @on('add_dialog', 'button')
    def submit_add_dialog(self, button):
        dialog = self.find('add_dialog')
        dialog.visible = False

        if button == 'add':
            options = {
                    'paused': dialog.find('add_paused').value,
                    'download_dir': dialog.find('target_dir').value,
                    }

            urls = dialog.find('new_url').value.strip().splitlines()
            for url in urls:
                url = url.strip()

                if not url.startswith(('file://', 'http://', 'https://', 'ftp://', 'ftps://')):
                    url = 'file://' + url

                self._client.add_torrent(url, **options)

            self.refresh()

