# Copyright 2020 Aaron David Schneider. All rights reserved.
import hashlib
import logging
from typing import Set, Tuple, Union

import lxml.etree
import lxml.html
import requests

_LOGGER = logging.getLogger(__name__)


def get_all_profiles(url: str, user: str, password: str) -> Set[str]:
    _LOGGER.debug("FETCHING AVAILABLE PROFILES...")
    profiles = set()
    none_profile = FritzProfileSwitch(url, user, password, None)
    data = {"xhr": 1, "sid": none_profile.sid, "no_sidrenew": "", "page": "kidPro"}
    url = none_profile.url + "/data.lua"
    r = requests.post(url, data=data, allow_redirects=True)
    html = lxml.html.fromstring(r.text)
    for row in html.xpath('//table[@id="uiProfileList"]/tr'):
        profile_name = row.xpath('td[@class="name"]/span/text()')
        if not profile_name:
            continue
        profiles.add(profile_name[0])

    return profiles


def get_sid_challenge(url: str) -> Tuple[str, str]:
    r = requests.get(url, allow_redirects=True)
    parser = lxml.etree.XMLParser(recover=True)
    data = lxml.etree.fromstring(r.content, parser=parser)
    sid = data.xpath("//SessionInfo/SID/text()")[0]
    challenge = data.xpath("//SessionInfo/Challenge/text()")[0]
    return sid, challenge


class FritzProfileSwitch:
    def __init__(self, url: str, user: str, password: str, profile: Union[str, None]):
        """
        Initialize fritzprofiles object.
        """
        self.url: str = (
            url if "http://" in url or "https://" in url else f"http://{url}"
        )
        self._user: str = user
        self._password: str = password
        self.profile_name: str = profile
        self.sid: str = self.login()

        self._last_state: Union[str, None] = None
        self.filtertype: Union[str, None] = None
        self.parental: Union[str, None] = None
        self.disallow_guest: Union[str, None] = None
        self.failed: bool = False

        if profile:
            self.profile_id: str = self.get_id()
            self.get_state()

    def login(self) -> str:
        _LOGGER.debug("LOGGING IN TO FRITZ!BOX AT {}...".format(self.url))
        sid, challenge = get_sid_challenge(self.url + "/login_sid.lua")
        if sid == "0000000000000000":
            md5 = hashlib.md5()
            md5.update(challenge.encode("utf-16le"))
            md5.update("-".encode("utf-16le"))
            md5.update(self._password.encode("utf-16le"))
            response = challenge + "-" + md5.hexdigest()
            url = (
                self.url
                + "/login_sid.lua?username="
                + self._user
                + "&response="
                + response
            )
            sid, challenge = get_sid_challenge(url)
        if sid == "0000000000000000":
            self.failed = True
            raise PermissionError(
                "Cannot login to {} using the supplied credentials. Only works if login via user and password is "
                "enabled in the FRITZ!Box".format(self.url)
            )

        return sid

    def get_id(self) -> Union[str, None]:
        _LOGGER.debug("FETCHING THE PROFILE ID...")
        data = {"xhr": 1, "sid": self.sid, "no_sidrenew": "", "page": "kidPro"}
        url = self.url + "/data.lua"
        r = requests.post(url, data=data, allow_redirects=True)
        html = lxml.html.fromstring(r.text)
        for row in html.xpath('//table[@id="uiProfileList"]/tr'):
            profile_name = row.xpath('td[@class="name"]/span/text()')
            if not profile_name:
                continue
            profile_name = profile_name[0]
            profile_id: str = row.xpath(
                'td[@class="btncolumn"]/button[@name="edit"]/@value'
            )[0]
            if profile_name == self.profile_name:
                return profile_id

        self.failed = True
        raise AttributeError(
            "The specified profile {} does not exist. Please check the spelling.".format(
                self.profile_name
            )
        )

    def get_state(self) -> str:
        url = self.url + "/data.lua"
        data = {"sid": self.sid, "edit": self.profile_id, "page": "kids_profileedit"}
        r = requests.post(url, data=data, allow_redirects=True)
        if r.status_code != 200:
            # login again to fetch new sid
            self.sid = self.login()
            data["sid"] = self.sid
            r = requests.post(url, data=data, allow_redirects=True)

        html = lxml.html.fromstring(r.text)
        self._last_state: str = html.xpath(
            '//div[@class="time_ctrl_options"]/input[@checked="checked"]/@value'
        )[0]

        parental = html.xpath(
            '//div[@class="formular"]/input[@name="parental"]/@checked'
        )
        self.parental = "on" if parental == ["checked"] else None

        disallow_guest = html.xpath(
            '//div[@class="formular"]/input[@name="disallow_guest"]/@checked'
        )
        self.disallow_guest = "on" if disallow_guest == ["checked"] else None

        black = html.xpath('//div[@class="formular"]/input[@value="black"]/@checked')
        white = html.xpath('//div[@class="formular"]/input[@value="white"]/@checked')
        if white == ["checked"] and self.parental is not None:
            self.filtertype = "white"
        elif black == ["checked"] and self.parental is not None:
            self.filtertype = "black"

        return self._last_state

    def set_state(self, state: str) -> None:
        self.get_state()
        url = self.url + "/data.lua"

        data = {
            "sid": self.sid,
            "edit": self.profile_id,
            "time": state,
            "budget": "unlimited",
            "apply": "nop",
            "page": "kids_profileedit",
        }
        if self.parental is not None:
            data["parental"] = self.parental
        if self.disallow_guest is not None:
            data["disallow_guest"] = self.disallow_guest
        if self.filtertype is not None:
            data["filtertype"] = self.filtertype

        r = requests.post(url, data=data, allow_redirects=True)

        if r.status_code != 200:
            # login again to fetch new sid
            self.sid = self.login()
            data["sid"] = self.sid
            requests.post(url, data=data, allow_redirects=True)

        return None

    def print_state(self) -> None:
        state = self.get_state()
        print(state)
