from ajenti.plugins.transmission.client.models import *
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


class Connection(object):
    _commands = {
            'torrent-start': None,
            'torrent-stop': None,
            'torrent-verify': None,
            'torrent-reannounce': None,

            'torrent-set': None,
            'torrent-get': lambda r: map(Torrent, r['torrents']),
            'torrent-add': lambda r: Torrent(r['torrent-added']),
            'torrent-remove': None,
            'torrent-set-location': None,

            'session-set': None,
            'session-get': Session,
            'session-stats': SessionStat,

            'blocklist-update': lambda r: r['blocklist-size'],

            'port-test': lambda r: r['port-is-open'],
            }

    def __init__(self, host='127.0.0.1', port=9091, path="transmission/rpc"):
        self._session = requests.session()
        self._base_url = 'http://%s:%s/%s' % (host, port, path)
        self._token = ''
        self._tag = itertools.count(random.randint(0, 1000))

    def __getattr__(self, name):
        method = (lambda self, **kwargs: self._do_request(name, kwargs)).__get__(self, self.__class__)
        setattr(self, name, method)
        return method

    def _do_request(self, name, args):
        name = name.replace('_', '-')
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

