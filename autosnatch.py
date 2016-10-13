#!/usr/bin/env python3

import requests
import json
import time
from re import compile
from requests.auth import HTTPBasicAuth
from time import sleep
import pydle

#edit this
_what_username = ''
_what_password = ''
_what_irc_token = ''
_manager_url = '' # also accepts the transcode add url http://seedbox/transcode/request
_manager_username = ''
_manager_password = ''
_max_release_year = 2016
_bitrate = ['lossless', 'v0 (vbr)', 'v0', '320', '24bit lossless']

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3)'\
        'AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.79'\
        'Safari/535.11',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'\
        ',*/*;q=0.8',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'}


regex = compile('(.+?) - (.+) \[(\d+)\] \[([^\]]+)\] - (MP3|FLAC|Ogg|AAC|AC3|DTS|Ogg Vorbis) / ((?:24bit)?(?: ?Lossless)?(?:[\d|~|\.xVq|\s]*(?:AAC|APX|APS|Mixed|Auto|VBR)?(?: LC)?)?(?: ?(?:\(VBR\)|\(?ABR\)?|[K|k][b|p]{1,2}s)?)?)(?: / (?:Log))?(?: / (?:[-0-9\.]+)\%)?(?: / (?:Cue))?(?: / (CD|DVD|Vinyl|Soundboard|SACD|Cassette|DAT|WEB|Blu-ray))(?: / (Scene))?(?: / (?:Freeleech!))? - https://what\.cd/torrents\.php\?id=(\d+) / https://what\.cd/torrents\.php\?action=download&id=(\d+) - ?(.*)')
_bitrate.append('whatever')

class MyOwnBot(pydle.Client):
    def on_connect(self):
        print("Authing with what.cd")
        self.session = requests.Session()
        self.session.headers.update(headers)
        data = { 'username': _what_username, 'password': _what_password, 'keeplogged': 1, 'login': 'Login' }
        r = self.session.post('https://what.cd/login.php', data=data)
        if r.status_code != 200:
            raise Exception("Can't log in")
        self.last_request = time.time()
        self.rate_limit = 2.1
        self.authkey = None
        self.passkey = None
        accountinfo = self.request('index')
        
        self.authkey = accountinfo['authkey']
        self.passkey = accountinfo['passkey']
        self.userid = accountinfo['id']
        print('Authed as user id {}'.format(self.userid))
        print("Poking drone")
        self.message('Drone', 'ENTER #what.cd-announce {} {}'.format(_what_username, _what_irc_token))

    def on_message(self, source, target, message):
         print("{}: {}".format(source, message))
         self.parse_line(message)

    def parse_line(self, line):
        match = regex.match(line)
        if not match:
            return False

        artist, release, year, release_type, \
            release_format, bitrate, media, _, id, \
            torrent_id, tags = match.groups()

        year = int(year)
        tags = tags.split(', ')

        if 'Freeleech!' in line:
            return False # Removing this is not allowed by the golden rules
            year += 3
            bitrate = 'whatever'

        if year < _max_release_year:
            print("Too old: {}".format(year))
            return False

        if bitrate.lower() not in _bitrate:
            print("Wrong bitrate: {}".format(bitrate))
            return False

        if self.request('torrent', id=torrent_id)['torrent']['userId'] == self.userid:
            print("Skipping because it's a torrent I made it...")
            return False

        print("Fetching: {}".format(line))
        sleep(2)
        fetch_torrent(torrent_id)
    
    def request(self, target, **params):
        while time.time() - self.last_request < self.rate_limit:
            sleep(0.1)
        url = 'https://what.cd/ajax.php'
        params['action'] = target
        if self.authkey:
            params['auth'] = target
        r = self.session.get(url, params=params, allow_redirects=False)
        self.last_request = time.time()
        return r.json()['response']


def fetch_torrent(torrent_id):
        return requests.post(_manager_url,
                             auth=HTTPBasicAuth(_manager_username, _manager_password),
                             data={'id':torrent_id}).json()['success']

if __name__ == '__main__':
    client = MyOwnBot('{}-autosnatch'.format(_what_username), realname='bot')
    client.connect('irc.what-network.net', 6697, tls=True, tls_verify=False)
    client.handle_forever()
