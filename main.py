# -*- encoding: utf-8 -*-
from __future__ import division
from ajenti.api import *  # noqa
from ajenti.api.http import HttpPlugin, url
from ajenti.plugins import *  # noqa
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder
from ajenti.ui import on
from ajenti.util import str_fsize, str_timedelta
from transmissionrpc import torrent, client
from datetime import datetime
import time
import base64
import gevent
import os

class TorrentFile(object):
    id = None
    _data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(key)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __init__(self, kv):
        self.id, self._data = kv

        self.is_priority_low = self.priority == 'low'
        self.is_priority_normal = self.priority == 'normal'
        self.is_priority_high = self.priority == 'high'

        self.percentDone = done = self.completed / self.size
        self.progress = progress = done * 100
        self.progress_str = '%0.2f%%' % progress

        self.completed_str = str_fsize(self.completed)
        self.size_str = str_fsize(self.size)

        self.icon = 'play' if self.selected else 'pause'
        self.is_started = self.selected
        self.is_stopped = not self.selected

    def set_priority(self, priority):
        assert priority in ('low', 'normal', 'high')
        self._data['priority'] = priority
        self.is_priority_low = self.priority == 'low'
        self.is_priority_normal = self.priority == 'normal'
        self.is_priority_high = self.priority == 'high'

TransmissionTorrent = torrent.Torrent
class Torrent(TransmissionTorrent):
    def get(self, key, default=None):
        return getattr(self, key, default)

    def __setitem__(self, key, value):
        try:
            setattr(self, key, value)
        except AttributeError:
            pass

    @property
    def last_scrape_time(self):
        pass

    @property
    def seconds_seeding(self):
        return str_timedelta(self.secondsSeeding)

    @property
    def seconds_downloading(self):
        return str_timedelta(self.secondsDownloading)

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
    def rate_download(self):
        return str_fsize(self.rateDownload)

    @property
    def rate_upload(self):
        return str_fsize(self.rateUpload)

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

    @property
    def content(self):
        try:
            return map(TorrentFile, sorted(self.files().items(), key=lambda kv: kv[0]))
        except:
            return []

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
        self.torrent = {}
        self.show_details = False
        self.files = []

        def post_item_bind(root, collection, value, ui):
            ui.find('priority_low').on('click', self.set_priority, value, 'low')
            ui.find('priority_normal').on('click', self.set_priority, value, 'normal')
            ui.find('priority_high').on('click', self.set_priority, value, 'high')
            ui.find('start').on('click', self.start, value)
            ui.find('stop').on('click', self.stop, value)
            ui.find('details').on('click', self.details, value)

        self.find('torrents').post_item_bind = post_item_bind
        self.find('torrents').delete_item = self.remove


        def post_file_bind(root, collection, value, ui):
            ui.find('priority_low').on('click', self.set_file_priority, value, 'low')
            ui.find('priority_normal').on('click', self.set_file_priority, value, 'normal')
            ui.find('priority_high').on('click', self.set_file_priority, value, 'high')

        self.find('files').post_item_bind = post_file_bind

        self.find('add_dialog').find('target_dir').value = os.path.expanduser('~transmission/Downloads')

        self.binder = Binder(self, self.find('main'))

    def on_first_page_load(self):
        self._client = client.Client()
        self.refresh()

    @on('apply', 'click')
    def apply(self):
        self.binder.update()
        self._client.set_files({
            self.torrent.id: dict(
                map(lambda f: (f.id, {'priority': f.priority, 'selected': f.selected}),
                    self.files))
            })
        self.torrent.update()
        self.refresh()

    @on('refresh', 'click')
    @profile
    def refresh(self):
        self.torrents = self._client.get_torrents()

        if self.torrent:
            #if self.torrent in self.torrents:
            self.torrent.update()
            self.files = self.torrent.content
            #else:
                #self.torrent = {}
                #self.show_details = False

        self.binder.populate()

    def refresh_item(self, item):
        item.update()
        self.binder.populate()

    def set_priority(self, item, value):
        item.priority = value
        self.refresh_item(item)

    def set_file_priority(self, item, value):
        item.set_priority(value)
        self.binder.populate()

    def start(self, item):
        item.start()
        self.refresh_item(item)

    def stop(self, item):
        item.stop()
        self.refresh_item(item)

    @on('start_all', 'click')
    def start_all(self):
        self._client.start_all()

    def details(self, item):
        item.update()
        self.torrent = item
        self.files = item.content
        self.show_details = True
        self.binder.populate()

    def remove(self, item, collection):
        self._client.remove_torrent([item.id], delete_data=False)

    def delete(self, item, collection):
        self._client.remove_torrent([item.id], delete_item=True)

    @on('add', 'click')
    def open_add_dialog(self):
        self.find('add_dialog').visible = True

    _torrent_data = None
    @on('add_dialog', 'button')
    def submit_add_dialog(self, button):
        dialog = self.find('add_dialog')
        dialog.visible = False

        if button == 'add':
            options = {
                    'paused': dialog.find('add_paused').value,
                    'download_dir': dialog.find('target_dir').value,
                    }

            url = dialog.find('url').value.strip()
            if url:
                torrent = url
                if not url.startswith(('file://', 'http://', 'https://', 'ftp://', 'ftps://', 'magnet:')):
                    torrent = 'file://' + url

            else:
                url = dialog.find('local_file').value.strip()
                if url:
                    torrent = 'file://' + url

                elif self._torrent_data:
                    torrent = self._torrent_data
                    self._torrent_data = None

                else:
                    return

            added_torrent = self._client.add_torrent(torrent, **options)
            self.details(added_torrent)
            self.refresh()

@plugin
class UploadReceiver (HttpPlugin):
    @url('/ajenti:transmission-upload')
    def handle_upload(self, context):
        file = context.query['file']
        data = base64.encodestring(file.read())
        context.session.endpoint.get_section(FileManager)._torrent_data = data
        context.respond_ok()
        return 'OK'

