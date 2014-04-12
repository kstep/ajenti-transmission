# -*- encoding: utf-8 -*-
from __future__ import division
from ajenti.plugins.models.api import Model, unixtime, listof, timedelta
import operator as op
import itertools as it
import base64

priority = {-1: 'low', 0: 'normal', 1: 'high'}.get
mode = ['global', 'single', 'unlimited'].__getitem__
eta = lambda v: 'unavailable' if v == -1 else 'unknown' if v == -2 else timedelta(v)
intpriority = {'low': -1, 'normal': 0, 'high': 0}.get

status = {
        # modern values compatible with old api
        0: 'stopped',
        1: 'check pending',
        2: 'checking',
        3: 'download pending',
        4: 'downloading',
        5: 'seed pending',
        6: 'seeding',

        # deprecated api values
        8:  'seeding',
        16: 'stopped',
        }.get

icon = {
        'stopped': 'pause',
        'check pending': 'stethoscope',
        'checking': 'stethoscope',
        'download pending': 'download-alt',
        'downloading': 'download-alt',
        'seed pending': 'upload-alt',
        'seeding': 'upload-alt',
        }.get


import re
upcase_re = re.compile(r'([A-Z])')


# Transmission RPC API: https://trac.transmissionbt.com/browser/branches/1.7x/doc/rpc-spec.txt


class bitfield(object):
    __slots__ = ('value', 'bitlen')

    def __init__(self, value, bitlen=None):
        if type(value) is not bytearray:
            raise TypeError('bytearray expected, got %s' % type(value).__name__)

        self.value = value
        self.bitlen = int(bitlen) if bitlen else len(value) * 8

        assert (len(self.value) - self.bitlen) < 8

    def __len__(self):
        return self.bitlen

    @staticmethod
    def bitcount(byte):
        byte = (byte & (0x55)) + ((byte >> 1) & (0x55));
        byte = (byte & (0x33)) + ((byte >> 2) & (0x33));
        byte = (byte & (0x0f)) + ((byte >> 4) & (0x0f));
        return byte

    def count(self, value):
        ones = sum(it.imap(self.bitcount, self.value))
        return ones if value else len(self) - ones

    def __getitem__(self, bitn):
        place = bitn >> 3  # quick bitn // 8
        bitn &= 7  # quick bitn % 8
        return bit.one if self.value[place] & (0b10000000 >> bitn) else bit.zero

    def __setitem__(self, bitn, value):
        place = bitn >> 3
        bitn = 0b10000000 >> (bitn & 7)
        if value:
            self.value[place] |= bitn
        else:
            self.value[place] &= ~bitn

    def __delitem__(self, bitn):
        place = bitn >> 3
        bitn &= 7
        self.value[place] &= ~(0b10000000 >> bitn)

    def __repr__(self):
        return '<bits:[%s]>' % ' '.join(it.imap(lambda n: ('0000000' + bin(n)[2:])[-8:], self.value))

    def __iter__(self):
        length = self.bitlen

        for byte in self.value:
            m = 0b10000000
            while m and length > 0:
                yield 1 if byte & m else 0
                m >>= 1
                length -= 1

    def __str__(self):
        return ''.join('■' if b else '□' for b in self)


class TorrentModel(Model):
    _backmap = {}
    def _mapkey(self, key):
         newkey = upcase_re.sub(lambda m: '_' + m.group(1).lower(), key.replace('-', '_'))
         self._backmap[newkey] = key
         return newkey

    def gather(self):
         return dict(
                 (oldkey, getattr(self, newkey, None))
                 for newkey, oldkey in self._backmap.iteritems()
                 )

class File(TorrentModel):
    _casts = {
            #'bytesCompleted': int,
            #'length': int,
            #'name': str,
            }

    _defaults = {
            'bytes_completed': 0,
            'length': 0,
            }

    def _init(self):
        try:
            self.percent_done = self.bytes_completed / self.length
        except ZeroDivisionError:
            self.percent_done = 0.0

class FileStat(TorrentModel):
    _casts = {
            #'bytesCompleted': int,
            'wanted': bool,
            'priority': priority,
            }

class PeersCount(TorrentModel):
    _casts = {
            #'fromCache': int,
            #'fromDht': int,
            #'fromIncoming': int,
            #'fromLpd': int,
            #'fromPex': int,
            #'fromTracker': int,
            }

class Peer(TorrentModel):
    _casts = {
            #'address': str,
            #'clientName': str,
            #'clientIsChoked': bool,
            #'clientIsInterested': bool,
            #'flagStr': str,
            #'isDownloadingFrom': bool,
            #'isEncrypted': bool,
            #'isIncoming': bool,
            #'isUploadingTo': bool,
            #'isUTP': bool,
            #'peerIsChoked': bool,
            #'peerIsInterested': bool,
            #'port': int,
            #'progress': float,
            #'rateToClient': int,
            #'rateToPeer': int,
            }

    _defaults = {
            'rate_to_client': 0,
            'rate_to_peer': 0,
            }

class Tracker(TorrentModel):
    _casts = {
            #'announce': str,
            #'id': int,
            #'scrape': str,
            #'tier': int,
            }

class TrackerStat(TorrentModel):
    _casts = {
            #'announce': str,
            #'announceState': int,
            #'downloadCount': int,
            #'hasAnnounced': bool,
            #'hasScraped': bool,
            #'host': str,
            #'id': int,
            #'isBackup': bool,
            #'lastAnnouncePeerCount': int,
            #'lastAnnounceResult': str,
            'lastAnnounceStartTime': unixtime,
            #'lastAnnounceSucceeded': bool,
            'lastAnnounceTime': unixtime,
            #'lastAnnounceTimedOut': bool,
            #'lastScrapeResult': str,
            'lastScrapeStartTime': unixtime,
            #'lastScrapeSucceeded': bool,
            'lastScrapeTime': unixtime,
            #'lastScrapeTimedOut': bool,
            #'leecherCount': int,
            'nextAnnounceTime': unixtime,
            'nextScrapeTime': unixtime,
            #'scrape': str,
            #'scrapeState': int,
            #'seederCount': int,
            #'tier': int,
            }

class Torrent(TorrentModel):
    _casts = {
            'activityDate': unixtime,
            'addedDate': unixtime,
            #'announceResponse': str,
            #'announceURL': str,
            'bandwidthPriority': priority,
            #'comment': str,
            #'corruptEver': int,
            #'creator': str,
            'dateCreated': unixtime,
            #'desiredAvailable': int,
            'doneDate': unixtime,
            #'downloadDir': str,
            #'downloadedEver': int,
            #'downloadLimit': int,
            #'downloadLimited': bool,
            #'error': int,
            #'errorString': str,
            'eta': eta,
            'etaIdle': eta,
            'files': listof(File),
            'fileStats': listof(FileStat),
            #'hashString': str,
            #'haveUnchecked': int,
            #'haveValid': int,
            #'honorsSessionLimits': bool,
            #'id': int,
            #'isPrivate': bool,
            'lastAnnounceTime': unixtime,
            'lastScrapeTime': unixtime,
            #'leftUntilDone': int,
            #'magnetLink': int,
            #'manualAnnounceTime': int,
            #'maxConnectedPeers': int,
            #'metadataPercentComplete': float,
            #'name': str,
            'nextAnnounceTime': unixtime,
            'nextScrapeTime': unixtime,
            #'peer-limit': int,
            'peers': listof(Peer),
            #'peersConnected': int,
            'peersFrom': PeersCount,
            #'peersGettingFromUs': int,
            #'peersSendingToUs': int,
            #'percentDone': float,
            'pieces': lambda v: bitfield(bytearray(base64.decodestring(v))),
            #'pieceCount': int,
            #'pieceSize': int,
            'priorities': listof(priority),
            #'queuePosition': int,
            #'rateDownload': int,
            #'rateUpload': int,
            #'recheckProgress': float,
            #'scrapeResponse': str,
            #'scrapeURL': str,
            'secondsDownloading': timedelta,
            'secondsSeeding': timedelta,
            #'seedIdleLimit': int,
            'seedIdleMode': mode,
            #'seedRatioLimit': float,
            'seedRatioMode': mode,
            #'sizeWhenDone': int,
            'startDate': unixtime,
            'status': status,
            'trackers': listof(Tracker),
            'trackerStats': listof(TrackerStat),
            #'totalSize': int,
            #'torrentFile': str,
            #'uploadedEver': int,
            #'uploadLimit': int,
            #'uploadLimited': bool,
            #'uploadRatio': float,
            #'wanted': listof(bool),
            #'webseeds': listof(str),
            #'webseedsSendingToUs': int,
            }

    _defaults = {
            'files': [],
            'peers': [],
            'trackers': [],
            'tracker_stats': [],
            'piece_count': 0,
            'piece_size': 0,
            'downloaded_ever': 0,
            'uploaded_ever': 0,
            'size_now': 0,
            'size_when_done': 0,
            'total_size': 0,
            'rate_download': 0,
            'rate_upload': 0,
            'id': None,
            'error': 0,
            'errorString': '',
            }

    def _init(self):
        if 'files' in self and 'file_stats' in self:
            for i, stats in enumerate(self.file_stats):
                self.files[i].update(stats.__dict__, id=i)

            self.files.sort(key=op.attrgetter('name'))

        if 'left_until_done' in self and 'size_when_done' in self:
            self.size_now = self.size_when_done - self.left_until_done

        if 'status' in self:
            self.icon = icon(self.status)

        if 'pieces' in self and 'piece_count' in self:
            self.pieces.bitlen = self.piece_count

class WeekDays(object):
    MASKS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

    def __init__(self, bits=127):
        self.value = bits

    def __getitem__(self, name):
        try:
            return (self.value & (1 << self.MASKS.index(name))) != 0
        except ValueError:
            raise KeyError(name)

    def __setitem__(self, name, value):
        value = -int(bool(value))

        try:
            mask = 1 << self.MASKS.index(name)
        except ValueError:
            raise KeyError(name)

        self.value = (self.value & ~mask) | (mask & value)

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def __int__(self):
        return self.value

    def __str__(self):
        return ', '.join(dow for mask, dow in enumerate(self.MASKS) if self.value & (1 << mask) != 0)

    def __repr__(self):
        return '<WeekDays: [%s]>' % str(self)

class Session(TorrentModel):
    _casts = {
            #'alt-speed-down': int,
            #'alt-speed-enabled': bool,
            'alt-speed-time-begin': lambda t: '%02d:%02d' % divmod(t, 60),
            #'alt-speed-time-enabled': bool,
            'alt-speed-time-end': lambda t: '%02d:%02d' % divmod(t, 60),
            'alt-speed-time-day': WeekDays,
            #'alt-speed-up': int,
            #'blocklist-enabled': bool,
            #'blocklist-size': int,
            #'dht-enabled': bool,
            #'encryption': str,
            #'download-dir': str,
            #'peer-limit-global': int,
            #'peer-limit-per-torrent': int,
            #'pex-enabled': bool,
            #'peer-port': int,
            #'peer-port-random-on-start': bool,
            #'port-forwarding-enabled': bool,
            #'rpc-version': int,
            #'rpc-version-minimum': int,
            #'seedRatioLimit': float,
            #'seedRatioLimited': bool,
            #'speed-limit-down': int,
            #'speed-limit-down-enabled': bool,
            #'speed-limit-up': int,
            #'speed-limit-up-enabled': bool,
            #'version': str,
        }

class SessionStat(TorrentModel):
    class Stats(TorrentModel):
        _casts = {
            #'uploadedBytes': int,
            #'downloadedBytes': int,
            #'filesAdded': int,
            #'sessionCount': int,
            'secondsActive': timedelta,
            }

    _casts = {
            #'activeTorrentCount': int,
            #'downloadSpeed': int,
            #'pausedTorrentCount': int,
            #'torrentCount': int,
            #'uploadSpeed': int,
            'cumulative-stats': Stats,
            'current-stats': Stats,
            }

class Result(TorrentModel):
    pass
