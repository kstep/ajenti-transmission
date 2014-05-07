from ajenti.plugins.transmission.models import *
import operator as op
import random
import requests
import json
import itertools

class TransmissionError(RuntimeError):
    pass

class CommandError(TransmissionError):
    def __init__(self, message, args):
        super(CommandError, self).__init__(message)
        self.__args = args

    @property
    def arguments(self):
        return self.__args

class ProtocolError(TransmissionError):
    pass


class Client(object):
    _commands = {
            'torrent-start': None,
            'torrent-start-now': None,
            'torrent-stop': None,
            'torrent-verify': None,
            'torrent-reannounce': None,

            'torrent-set': None,
            'torrent-get': lambda r: map(Torrent, r['torrents']),
            'torrent-add': lambda r: Torrent(r.get('torrent-added') or r['torrent-duplicate']),
            'torrent-remove': None,
            'torrent-set-location': None,
            'torrent-rename-path': None,

            'session-set': None,
            'session-get': Session,
            'session-stats': SessionStat,
            'session-close': None,

            'blocklist-update': lambda r: r['blocklist-size'],

            'port-test': lambda r: r['port-is-open'],
            'free-space': lambda r: r['size-bytes'],

            'queue-move-up': None,
            'queue-move-down': None,
            'queue-move-top': None,
            'queue-move-bottom': None,
            }

    def __init__(self, host='127.0.0.1', port=9091, path="transmission/rpc"):
        self._session = requests.session()
        self._base_url = 'http://%s:%s/%s' % (host, port, path)
        self._token = ''
        self._tag = itertools.count(random.randint(0, 1000))

    def __getattr__(self, name):
        name = name.replace('_', '-')
        if name not in self._commands:
            raise AttributeError(name)

        method = (lambda self, **kwargs: self._do_request(name, self._fix_arg_keys(kwargs))).__get__(self, self.__class__)
        setattr(self, name, method)
        return method

    @staticmethod
    def _fix_arg_keys(args):
        for key, value in args.iteritems():
            if '_' in key:
                del args[key]
                args[key.replace('_', '-')] = value
        return args

    def _do_request(self, name, args):
        tag = self._tag.next()

        data = {
                'tag': tag,
                'method': name,
                'arguments': args
                }

        headers = {
                'X-Transmission-Session-Id': self._token
                }

        result = self._session.post(self._base_url, data=json.dumps(data), headers=headers)
        if result.status_code == 200:
            result = json.loads(result.content)
            if result['result'] != 'success':
                raise CommandError(result['result'], result.get('arguments'))

            if result['tag'] != tag:
                raise ProtocolError('unexpected tag %s instead of %s' % (result['tag'], tag))

            if result.get('arguments'):
                return self._commands.get(name, Result)(result['arguments'])

        elif result.status_code == 409:
            self._token = result.headers['X-Transmission-Session-Id']
            return self._do_request(name, args)

        else:
            raise ProtocolError('unexpected status code %s' % result.status_code)

    def start_all(self):
        self.torrent_start(ids=map(op.attrgetter('id'), self.torrent_get(fields=['id'])))

    def stop_all(self):
        self.torrent_stop(ids=map(op.attrgetter('id'), self.torrent_get(fields=['id'])))

