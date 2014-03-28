from __future__ import division
from ajenti.plugins.models.api import Model, unixtime, listof, sort, timedelta
import operator as op
import base64

priority = lambda v: {-1: 'low', 0: 'normal', 1: 'high'}.get(int(v))
mode = lambda v: ['global', 'single', 'unlimited'][int(v)]
eta = lambda v: 'unavailable' if v == -1 else 'unknown' if v == -2 else timedelta(v)

import re
upcase_re = re.compile(r'([A-Z])')


# Transmission RPC API: https://trac.transmissionbt.com/browser/branches/1.7x/doc/rpc-spec.txt

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

    def _init(self):
        self.progress = self.bytes_completed / self.length
        self.progress_str = '%0.2f%%' % (self.progress * 100)

class FileStat(TorrentModel):
    _casts = {
            #'bytesCompleted': int,
            #'wanted': bool,
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

class Tracker(TorrentModel):
    _casts = {
            #'announce': str,
            #'id': int,
            #'scrape': int,
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
            'bandwidthPriority': priority,
            #'comment': str,
            #'corruptEver': int,
            #'creator': str,
            'dateCreated': unixtime,
            #'desiredAvailable': int,
            #'doneDate': int,
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
            #'isFinished': bool,
            #'isPrivate': bool,
            #'isStalled': bool,
            #'leftUntilDone': int,
            #'magnetLink': int,
            #'manualAnnounceTime': int,
            #'maxConnectedPeers': int,
            #'metadataPercentComplete': float,
            #'name': str,
            #'peer-limit': int,
            'peers': listof(Peer),
            #'peersConnected': int,
            'peersFrom': PeersCount,
            #'peersGettingFromUs': int,
            #'peersSendingToUs': int,
            #'percentDone': float,
            'pieces': base64.decodestring,
            #'pieceCount': int,
            #'pieceSize': int,
            'priorities': listof(priority),
            #'queuePosition': int,
            #'rateDownload': int,
            #'rateUpload': int,
            #'recheckProgress': float,
            #'secondsDownloading': int,
            #'secondsSeeding': int,
            #'seedIdleLimit': int,
            #'seedIdleMode': int,
            #'seedRatioLimit': float,
            #'seedRatioMode': int,
            #'sizeWhenDone': int,
            #'startDate': int,
            #'status': int,
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

    def _init(self):
        if 'files' in self and 'file_stats' in self:
            for i, stats in enumerate(self.file_stats):
                self.files[i].update(stats.__dict__)

            self.files.sort(key=op.attrgetter('name'))

class SessionStat(TorrentModel):
    pass

class Session(TorrentModel):
    _casts = {
            #'activeTorrentCount': int,
            #'downloadSpeed': int,
            #'pausedTorrentCount': int,
            #'torrentCount': int,
            #'uploadSpeed': int,
            'cumulative-stats': SessionStat,
            'current-stats': SessionStat,
            }

class Result(TorrentModel):
    pass
