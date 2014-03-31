# -*- encoding: utf-8 -*-
from __future__ import division
from ajenti.api import *  # noqa
from ajenti.api.http import HttpPlugin, url
from ajenti.plugins import *  # noqa
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder
from ajenti.ui import on
from ajenti.util import str_fsize, str_timedelta
from ajenti.plugins.transmission.client import Client
from ajenti.plugins.transmission.models import Torrent
from ajenti.plugins.models.api import Model
from datetime import datetime
import time
import base64
import gevent
import os

@plugin
class TransmissionPlugin (SectionPlugin):
    def init(self):
        # meta-data
        self.title = 'Transmission'
        self.icon = 'download-alt'
        self.category = _("Software")

        self.append(self.ui.inflate('transmission:main'))

        self.scope = Model(
                torrents=[],
                torrent=Torrent.EMPTY,
                peers=[],
                pieces=[],
                trackers=[],
                files=[])

        def post_item_bind(root, collection, value, ui):
            ui.find('priority_low').on('click', self.set_priority, value, -1)
            ui.find('priority_normal').on('click', self.set_priority, value, 0)
            ui.find('priority_high').on('click', self.set_priority, value, 1)
            ui.find('start').on('click', self.start, value)
            ui.find('stop').on('click', self.stop, value)
            ui.find('details').on('click', self.details, value)
            ui.find('recheck').on('click', self.recheck, value)

        self.find('torrents').post_item_bind = post_item_bind
        self.find('torrents').delete_item = self.remove


        def post_file_bind(root, collection, value, ui):
            ui.find('priority_low').on('click', self.set_file_priority, value, 'low')
            ui.find('priority_normal').on('click', self.set_file_priority, value, 'normal')
            ui.find('priority_high').on('click', self.set_file_priority, value, 'high')

        self.find('files').post_item_bind = post_file_bind

        self.find('add_dialog').find('target_dir').value = os.path.expanduser('~transmission/Downloads')

        self.binder = Binder(self.scope, self.find('main'))

    def on_first_page_load(self):
        self._client = Client()
        self.refresh()

    @on('apply', 'click')
    def apply(self):
        self.binder.update()

        files_wanted, files_unwanted = [], []
        priority_low, priority_normal, priority_high = [], [], []
        for file in self.scope.files:
            (files_wanted if file.wanted else files_unwanted).append(file.id)
            (priority_low if file.priority == 'low' else
             priority_high if file.priority == 'high' else
             priority_normal).append(file.id)

        ids = [self.scope.torrent.id]

        data = {}
        if files_wanted:
            data['files_wanted'] = files_wanted
        if files_unwanted:
            data['files_unwanted'] = files_unwanted
        if priority_low:
            data['priority_low'] = priority_low
        if priority_normal:
            data['priority_normal'] = priority_normal
        if priority_high:
            data['priority_high'] = priority_high

        self._client.torrent_set(ids=ids, **data)

        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        self.scope.torrents = self._client.torrent_get(fields=['id', 'name', 'sizeWhenDone', 'leftUntilDone',
            'percentDone', 'bandwidthPriority', 'totalSize', 'eta', 'status'])

        if self.scope.torrent:
            self.refresh_item(self.scope.torrent)
        else:
            self.binder.populate()

    def refresh_item(self, item):
        try:
            item.update(self._client.torrent_get(ids=[item.id], fields=['id', 'name', 'sizeWhenDone', 'leftUntilDone',
                'percentDone', 'bandwidthPriority', 'totalSize', 'eta', 'status'])[0].__dict__)
            self.binder.populate()

        except IndexError:
            pass

    def set_priority(self, item, value):
        self._client.torrent_set(ids=[item.id], bandwidthPriority=value)
        self.refresh_item(item)

    def set_file_priority(self, item, value):
        self.binder.update()
        item.priority = value
        self.binder.populate()

    def start(self, item):
        self._client.torrent_start(ids=[item.id])
        self.refresh_item(item)

    def stop(self, item):
        self._client.torrent_stop(ids=[item.id])
        self.refresh_item(item)

    @on('start_all', 'click')
    def start_all(self):
        self._client.start_all()
        self.refresh()

    @on('stop_all', 'click')
    def stop_all(self):
        self._client.stop_all()
        self.refresh()

    def recheck(self, item):
        self._client.torrent_verify(ids=[item.id])
        self.refresh_item(item)

    def details(self, item):
        self.scope.torrent = self._client.torrent_get(ids=[item.id], fields=[
            'id', 'files', 'fileStats', 'name', 'torrentFile', 'downloadDir',
            'peersSendingToUs', 'peersGettingFromUs', 'peersConnected',
            'bandwidthPriority', 'secondsDownloading', 'secondsSeeding',
            'downloadedEver', 'uploadedEver', 'uploadRatio', 'peers', 'pieces', 'pieceCount',
            'sizeWhenDone', 'totalSize', 'eta', 'rateUpload', 'rateDownload',
            'addedDate', 'dateCreated', 'startDate', 'doneDate',
            'trackers',  # 'trackerStats',
            #'lastAnnounceTime', 'lastScrapeTime', 'announceURL', 'scrapeURL',
            #'announceResponse', 'scrapeResponse'
            ])[0]

        self.scope.trackers, self.scope.files, self.scope.peers, self.scope.pieces = (
                self.scope.torrent.trackers,
                self.scope.torrent.files,
                self.scope.torrent.peers,
                self.scope.torrent.pieces)

        self.binder.populate()

    def remove(self, item, collection):
        self._client.torrent_remove(ids=[item.id], delete_local_data=False)

    def delete(self, item, collection):
        self._client.torrent_remove(ids=[item.id], delete_local_data=True)

    #@on('reannounce', 'click')
    def reannounce(self):
        self._client.torrent_reannounce(ids=[self.scope.torrent.id])

    @on('add', 'click')
    def open_add_dialog(self):
        self.find('add_dialog').visible = True

    @on('move', 'click')
    def open_move_dialog(self):
        dialog = self.find('move_dialog')
        dialog.find('target_dir').value = self.scope.torrent.download_dir
        dialog.visible = True

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
                if url.startswith(('file://', 'http://', 'https://', 'ftp://', 'ftps://', 'magnet:')):
                    options['filename'] = url

                else:
                    options['filename'] = 'file://' + url

            else:
                url = dialog.find('local_file').value.strip()
                if url:
                    options['filename'] = 'file://' + url

                elif self._torrent_data:
                    options['metainfo'] = self._torrent_data
                    self._torrent_data = None

                else:
                    return

            added_torrent = self._client.torrent_add(**options)
            self.details(added_torrent)
            self.refresh()

    @on('move', 'click')
    def move(self):
        self._client.torrent_set_location(ids=[self.scope.torrent.id],
                location=self.find('download_dir').value, move=True)
        self.refresh_item(self.scope.torrent)


@plugin
class UploadReceiver (HttpPlugin):
    @url('/ajenti:transmission-upload')
    def handle_upload(self, context):
        file = context.query['file']
        data = base64.encodestring(file.read()).replace('\n', '')
        context.session.endpoint.get_section(FileManager)._torrent_data = data
        context.respond_ok()
        return 'OK'

