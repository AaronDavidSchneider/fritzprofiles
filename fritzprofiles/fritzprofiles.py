# Copyright 2020 Aaron David Schneider. All rights reserved.

import argparse
import hashlib
import logging

import lxml.etree
import lxml.html
import requests


class FritzProfileSwitch:
    def __init__(self, url, user, password, profile):
        self.url = url if "http://" in url or "https://" in url else f"http://{url}"
        self._user = user
        self._password = password
        self.profile_name = profile
        self.sid = self.login()
        self.profile_id = self.get_id()
        self.get_state()

    def get_sid_challenge(self, url):
        r = requests.get(url, allow_redirects=True)
        data = lxml.etree.fromstring(r.content)
        sid = data.xpath('//SessionInfo/SID/text()')[0]
        challenge = data.xpath('//SessionInfo/Challenge/text()')[0]
        return sid, challenge

    def login(self):
        logging.info("LOGGING IN TO FRITZ!BOX AT {}...".format(self.url))
        sid, challenge = self.get_sid_challenge(self.url + '/login_sid.lua')
        if sid == '0000000000000000':
            md5 = hashlib.md5()
            md5.update(challenge.encode('utf-16le'))
            md5.update('-'.encode('utf-16le'))
            md5.update(self._password.encode('utf-16le'))
            response = challenge + '-' + md5.hexdigest()
            url = self.url + '/login_sid.lua?username=' + self._user + '&response=' + response
            sid, challenge = self.get_sid_challenge(url)
        if sid == '0000000000000000':
            self.failed = True
            raise PermissionError(
                'Cannot login to {} using the supplied credentials. Only works if login via user and password is enabled in the FRITZ!Box'.format(
                    self.url))
        self.failed = False

        return sid

    def get_id(self):
        logging.info('FETCHING THE PROFILE ID...')
        data = {'xhr': 1, 'sid': self.sid, 'no_sidrenew': '', 'page': 'kidPro'}
        url = self.url + '/data.lua'
        r = requests.post(url, data=data, allow_redirects=True)
        html = lxml.html.fromstring(r.text)
        self.profiles = []
        for row in html.xpath('//table[@id="uiProfileList"]/tr'):
            profile_name = row.xpath('td[@class="name"]/span/text()')
            if not profile_name:
                continue
            profile_name = profile_name[0]
            profile_id = row.xpath('td[@class="btncolumn"]/button[@name="edit"]/@value')[0]
            if profile_name == self.profile_name:
                return profile_id
        self.failed = True
        raise AttributeError(
            'The specified profile {} does not exist. Please check the spelling.'.format(self.profile_name))

    def get_state(self):
        url = self.url + '/data.lua'
        data = {"sid": self.sid, "edit": self.profile_id, "page": "kids_profileedit"}
        r = requests.post(url, data=data, allow_redirects=True)
        if r.status_code != 200:
            # login again to fetch new sid
            self.sid = self.login(self._user, self._password)
            data = {"sid": self.sid, "edit": self.profile_id, "page": "kids_profileedit"}
            r = requests.post(url, data=data, allow_redirects=True)

        html = lxml.html.fromstring(r.text)
        state = html.xpath('//div[@class="time_ctrl_options"]/input[@checked="checked"]/@value')[0]
        self.last_state = state
        return state

    def set_state(self, state):
        url = self.url + '/data.lua'
        data = {"sid": self.sid, "edit": self.profile_id, "time": state, "budget": "unlimited", "apply": "",
                "page": "kids_profileedit"}
        r = requests.post(url, data=data, allow_redirects=True)

        if r.status_code != 200:
            # login again to fetch new sid
            self.sid = self.login(self._user, self._password)
            data = {"sid": self.sid, "edit": self.profile_id, "time": state, "budget": "unlimited", "apply": "",
                    "page": "kids_profileedit"}
            r = requests.post(url, data=data, allow_redirects=True)

        return r

    def print_state(self):
        state = self.get_state()
        print(state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', metavar='URL', type=str, default='http://fritz.box',
                        help='The URL of your Fritz!Box; default: http://fritz.box')
    parser.add_argument('--user', metavar='USER', type=str, default='',
                        help='Login username; default: empty')
    parser.add_argument('--password', metavar='PASSWORD', type=str, required=True,
                        help='Login password')
    parser.add_argument('--profile', metavar="PROFILE", type=str, required=True,
                        help='The Profile you want to obtain information about or switch')
    parser.add_argument('--get_state', action='store_true',
                        help='get state of profile')
    parser.add_argument('--set_state', metavar='STATE', type=str,
                        help='value to which the profile should be set')
    args = parser.parse_args()

    fps = FritzProfileSwitch(args.url, args.user, args.password, args.profile)
    if args.get_state:
        fps.print_state()
    if bool(args.set_state):
        fps.set_state(args.set_state)


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError as e:
        logging.error('Failed to connect to Fritz!Box')
        logging.error(e)
    except PermissionError as e:
        logging.error(e)
