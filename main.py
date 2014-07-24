# -*- encoding: utf-8 -*-
from __future__ import division, with_statement
from ajenti.api import *  # noqa
from ajenti.api.http import HttpPlugin, url
from ajenti.plugins import *  # noqa
from ajenti.plugins.main.api import SectionPlugin
from ajenti.ui.binder import Binder
from ajenti.ui import on
from ajenti.util import str_fsize, str_timedelta
from ajenti.plugins.transmission.client import Client
from ajenti.plugins.transmission.models import Torrent, Session, SessionStat
from ajenti.plugins.models.api import Model
from ajenti.plugins.configurator.api import ClassConfigEditor
from datetime import datetime
from requests import ConnectionError
from contextlib import contextmanager
import time
import base64
import gevent
import os


@plugin
class TransmissionPluginConfigurator(ClassConfigEditor):
    title = 'Transmission'
    icon = 'download-alt'

    def init(self):
        self.append(self.ui.inflate('transmission:config'))

class Scope(Model):
    _defaults = {
        'torrents': [],
        'session': Session.EMPTY,
        'torrent': Torrent.EMPTY,
        'session_stats': SessionStat.EMPTY,
        }

@plugin
class TransmissionPlugin (SectionPlugin):
    default_classconfig = {'host': '127.0.0.1', 'port': 9091, 'path': 'transmission/rpc'}
    classconfig_editor = TransmissionPluginConfigurator

    TORRENT_FIELDS = ['id', 'name', 'sizeWhenDone', 'leftUntilDone',
            'percentDone', 'bandwidthPriority', 'totalSize', 'eta', 'status', 'error', 'errorString',
            'peersSendingToUs', 'peersGettingFromUs', 'uploadRatio', 'rateDownload', 'rateUpload', 'recheckProgress']
    TORRENT_FIELDS_DETAILED = ['id', 'files', 'fileStats', 'name', 'torrentFile', 'downloadDir',
            'peersSendingToUs', 'peersGettingFromUs', 'peersConnected',
            'bandwidthPriority', 'secondsDownloading', 'secondsSeeding',
            'downloadedEver', 'uploadedEver', 'uploadRatio', 'peers', 'pieces', 'pieceCount',
            'pieceSize', 'sizeWhenDone', 'leftUntilDone', 'totalSize', 'eta', 'rateUpload', 'rateDownload',
            'addedDate', 'dateCreated', 'startDate', 'doneDate',
            'trackers',  # 'trackerStats',
            #'lastAnnounceTime', 'lastScrapeTime', 'announceURL', 'scrapeURL',
            #'announceResponse', 'scrapeResponse'
            'honorsSessionLimits', 'peer-limit', 'downloadLimit', 'downloadLimited',
            'seedRatioLimit', 'seedRationMode', 'uploadLimit', 'uploadLimited']
        
    @contextmanager    
    def configure_on_error(self):
        try:
            yield
        except ConnectionError, e:
            self.context.notify('error', str(e))
            self.context.launch('configure-plugin', plugin=self)

    def init(self):
        # meta-data
        self.title = 'Transmission'
        self.icon = 'download-alt'
        self.category = _("Software")

        self.append(self.ui.inflate('transmission:main'))
        self.scope = Scope()

        def post_item_bind(root, collection, value, ui):
            ui.find('set_priority').on('change', self.set_priority, value)
            ui.find('start').on('click', self.start, value)
            ui.find('stop').on('click', self.stop, value)
            ui.find('details').on('click', self.details, value)
            ui.find('recheck').on('click', self.recheck, value)

        self.find('torrents').post_item_bind = post_item_bind
        self.find('torrents').delete_item = self.remove

        self.find('add_dialog').find('target_dir').value = os.path.expanduser('~transmission/Downloads')
        self.find('add_dialog').find('priority').value = 0

    def on_first_page_load(self):
        self._client = Client(**self.classconfig)

        with self.configure_on_error():
            self.scope.session = self._client.session_get()
            self.scope.session.port_is_open = self._client.port_test()
            self.scope.session_stats = self._client.session_stats()
            self.scope.torrents = self._client.torrent_get(fields=self.TORRENT_FIELDS)
            self.scope.torrent = self._client.torrent_get(fields=self.TORRENT_FIELDS_DETAILED)[0]
            self.binder = Binder(self.scope, self.find('main'))
            self.binder.populate()

            if not self.scope.session.port_is_open:
                self.context.notify('error', 'Peer port %s is closed' % self.scope.session.peer_port)

    @on('status_filter', 'switch')
    def set_filter(self):
        tab = self.find('status_filter').active
        status = ['all', 'downloading', 'seeding', 'stopped'][tab]
        self.find('torrents').filter = (lambda t: t.status == status) if tab else (lambda t: True)
        self.binder.populate()

    @on('apply_limits', 'click')
    def apply_limits(self):
        self.binder.update()

        with self.configure_on_error():
            self._client.torrent_set(ids=[self.scope.torrent.id],
                    downloadLimit=self.scope.torrent.download_limit,
                    downloadLimited=self.scope.torrent.download_limited,
                    uploadLimit=self.scope.torrent.upload_limit,
                    uploadLimited=self.scope.torrent.upload_limited,
                    seedRatioLimit=self.scope.torrent.seed_ratio_limit,
                    seedRatioMode={'global': 0, 'single': 1, 'unlimited': 2}.get(self.scope.torrent.seed_ratio_mode),
                    honorsSessionLimits=self.scope.torrent.honors_session_limits)

        self.refresh()

    @on('apply_files', 'click')
    def apply_files(self):
        self.binder.update()

        files_wanted, files_unwanted = [], []
        priority_low, priority_normal, priority_high = [], [], []
        for file in self.scope.torrent.files:
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

        with self.configure_on_error():
            self._client.torrent_set(ids=ids, **data)

        self.refresh()

    @on('refresh', 'click')
    def refresh(self):
        with self.configure_on_error():
            self.scope.torrents[:] = self._client.torrent_get(fields=self.TORRENT_FIELDS)
            self.scope.session.update(self._client.session_get())
            self.scope.session.port_is_open = self._client.port_test()

        for t in self.scope.torrents:
            if t.error:
                self.context.notify('error', 'Torrent #%s (%s): %s' % (t.id, t.name, t.error_string))

        if self.scope.torrent:
            self.refresh_item(self.scope.torrent)
        else:
            self.binder.populate()

    def refresh_item(self, item):
        with self.configure_on_error():
            try:
                item.update(self._client.torrent_get(ids=[item.id], fields=self.TORRENT_FIELDS)[0])
                if item.error:
                    self.context.notify('error', 'Torrent #%s (%s): %s' % (item.id, item.name, item.error_string))
                self.binder.populate()
    
            except IndexError:
                pass

    @on('set_torrent_priority', 'change')
    def set_priority(self, item=None, priority=0):
        if not item:
            item = self.scope.torrent

        with self.configure_on_error():
            self._client.torrent_set(ids=[item.id], bandwidthPriority=priority)

        self.refresh_item(item)

    def start(self, item):
        with self.configure_on_error():
            self._client.torrent_start(ids=[item.id])
        self.refresh_item(item)

    def stop(self, item):
        with self.configure_on_error():
            self._client.torrent_stop(ids=[item.id])
        self.refresh_item(item)

    @on('start_all', 'click')
    def start_all(self):
        with self.configure_on_error():
            self._client.start_all()
        self.refresh()

    @on('stop_all', 'click')
    def stop_all(self):
        with self.configure_on_error():
            self._client.stop_all()
        self.refresh()

    def recheck(self, item):
        with self.configure_on_error():
            self._client.torrent_verify(ids=[item.id])
        self.refresh_item(item)

    def details(self, item):
        with self.configure_on_error():
            self.scope.torrent.update(self._client.torrent_get(ids=[item.id], fields=self.TORRENT_FIELDS_DETAILED)[0])
        self.binder.populate()

    def remove(self, item, collection):
        with self.configure_on_error():
            self._client.torrent_remove(ids=[item.id], delete_local_data=False)

    def delete(self, item, collection):
        with self.configure_on_error():
            self._client.torrent_remove(ids=[item.id], delete_local_data=True)

    #@on('reannounce', 'click')
    def reannounce(self):
        with self.configure_on_error():
            self._client.torrent_reannounce(ids=[self.scope.torrent.id])

    @on('stats', 'click')
    def open_stats_dialog(self):
        with self.configure_on_error():
            self.scope.session_stats.update(self._client.session_stats())
        self.find('stats_dialog').visible = True

    @on('stats_dialog', 'button')
    def submit_stats_dialog(self, button):
        self.find('stats_dialog').visible = False

    @on('config', 'click')
    def open_config_dialog(self):
        self.find('config_dialog').visible = True

    @on('alt_speed', 'click')
    def toggle_alt_speed(self):
        alt_speed = self.scope.session.alt_speed_enabled = not self.scope.session.alt_speed_enabled
        with self.configure_on_error():
            self._client.session_set(alt_speed_enabled=alt_speed)
        self.binder.populate()

    @on('config_dialog', 'button')
    def submit_config_dialog(self, button):
        dialog = self.find('config_dialog')
        dialog.visible = False

        if button == 'apply':
            self.binder.update()
            with self.configure_on_error():
                self._client.session_set(
                        alt_speed_down=self.scope.session.alt_speed_down,
                        alt_speed_up=self.scope.session.alt_speed_up,
                        alt_speed_enabled=self.scope.session.alt_speed_enabled,
                        alt_speed_time_begin=reduce(lambda a, t: a * 60 + int(t), self.scope.session.alt_speed_time_begin.split(':', 1), 0),
                        alt_speed_time_end=reduce(lambda a, t: a * 60 + int(t), self.scope.session.alt_speed_time_end.split(':', 1), 0),
                        alt_speed_time_day=int(self.scope.session.alt_speed_time_day),
                        dht_enabled=self.scope.session.dht_enabled,
                        pex_enabled=self.scope.session.pex_enabled,
                        encryption=self.scope.session.encryption,
                        download_dir=self.scope.session.download_dir,
    
                        peer_limit_global=self.scope.session.peer_limit_global,
                        peer_limit_per_torrent=self.scope.session.peer_limit_per_torrent,
                        peer_port=self.scope.session.peer_port,
                        peer_port_random_on_start=self.scope.session.peer_port_random_on_start,
                        port_forwarding_enabled=self.scope.session.port_forwarding_enabled,
    
                        seedRatioLimit=self.scope.session.seed_ratio_limit,
                        seedRatioLimited=self.scope.session.seed_ratio_limited,
                        speed_limit_down=self.scope.session.speed_limit_down,
                        speed_limit_up=self.scope.session.speed_limit_up,
                        speed_limit_down_enabled=self.scope.session.speed_limit_down_enabled,
                        speed_limit_up_enabled=self.scope.session.speed_limit_up_enabled,
                        )

    @on('add', 'click')
    def open_add_dialog(self):
        dialog = self.find('add_dialog')
        dialog.find('url').value = ''
        dialog.find('local_file').value = ''
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
                    'bandwidthPriority': dialog.find('priority').value,
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

            with self.configure_on_error():
                added_torrent = self._client.torrent_add(**options)

            self.details(added_torrent)
            self.refresh()

    @on('move', 'click')
    def move(self):
        with self.configure_on_error():
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

