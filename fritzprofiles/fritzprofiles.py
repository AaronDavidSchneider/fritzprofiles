"""
Utilities to switch and get the state of a fritzbox device profile.

# Copyright 2020 Aaron David Schneider. All rights reserved.
"""


import hashlib
import logging
from typing import Set, Tuple, Union

import lxml.etree  # pylint: disable=no-member
import lxml.html  # pylint: disable=no-member
import requests

_LOGGER = logging.getLogger(__name__)


def get_all_profiles(url: str, user: str, password: str) -> Set[str]:
    """
    Get all profile names.
    """
    _LOGGER.debug("FETCHING AVAILABLE PROFILES...")
    profiles: set = set()
    sid = login(url, user, password)
    data = {"xhr": 1, "sid": sid, "no_sidrenew": "", "page": "kidPro"}
    url = url if "http://" in url or "https://" in url else f"http://{url}"
    response = requests.post(url + "/data.lua", data=data, allow_redirects=True)
    html = lxml.html.fromstring(response.text)
    for row in html.xpath('//table[@id="uiProfileList"]/tr'):
        profile_name = row.xpath('td[@class="name"]/span/text()')
        if not profile_name:
            continue
        profiles.add(profile_name[0])

    return profiles


def get_sid_challenge(url: str) -> Tuple[str, str]:
    """
    Create the sid challenge.
    """
    response = requests.get(url, allow_redirects=True)
    parser = lxml.etree.XMLParser(recover=True)
    data = lxml.etree.fromstring(response.content, parser=parser)
    sid = data.xpath("//SessionInfo/SID/text()")[0]
    challenge = data.xpath("//SessionInfo/Challenge/text()")[0]
    return sid, challenge


def login(url: str, user: str, password: str) -> str:
    """
    Login to fritzbox.
    """
    url = url if "http://" in url or "https://" in url else f"http://{url}"
    _LOGGER.debug("LOGGING IN TO FRITZ!BOX AT %s", url)

    sid, challenge = get_sid_challenge(url + "/login_sid.lua")
    if sid == "0000000000000000":
        md5 = hashlib.md5()
        md5.update(challenge.encode("utf-16le"))
        md5.update("-".encode("utf-16le"))
        md5.update(password.encode("utf-16le"))
        response = challenge + "-" + md5.hexdigest()
        url = url + "/login_sid.lua?username=" + user + "&response=" + response
        sid, challenge = get_sid_challenge(url)
    if sid == "0000000000000000":
        raise PermissionError(
            "Cannot login to {} using the supplied credentials. "
            "Only works if login via user and password is "
            "enabled in the FRITZ!Box".format(url)
        )

    return sid


class FritzProfileSwitch:  # pylint: disable=too-many-instance-attributes
    """
    Class representing the state of a device profile in a fritzbox.
    """

    def __init__(self, url: str, user: str, password: str, profile: str):
        """
        Initialize fritzprofiles object.
        """
        url = url if "http://" in url or "https://" in url else f"http://{url}"

        self._url: str = url
        self._user: str = user
        self._password: str = password
        self._sid = login(self._url, self._user, self._password)

        self.profile_name: str = profile
        self._filtertype: Union[str, None] = None
        self._parental: Union[str, None] = None
        self._disallow_guest: Union[str, None] = None

        self.profile_id: Union[str, None] = self.get_id()
        self.get_state()

    def get_id(self) -> Union[str, None]:
        """
        Get the id of a profile
        """
        _LOGGER.debug("FETCHING THE PROFILE ID...")
        data = {"xhr": 1, "sid": self._sid, "no_sidrenew": "", "page": "kidPro"}
        url = self._url + "/data.lua"
        response = requests.post(url, data=data, allow_redirects=True)
        html = lxml.html.fromstring(response.text)
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

        raise AttributeError(
            "The specified profile {} does not exist. Please check the spelling.".format(
                self.profile_name
            )
        )

    def get_state(self) -> str:
        """
        Get the state of the profile.
        """
        url = self._url + "/data.lua"
        data = {"sid": self._sid, "edit": self.profile_id, "page": "kids_profileedit"}
        response = requests.post(url, data=data, allow_redirects=True)
        if response.status_code != 200:
            # login again to fetch new sid
            self._sid = login(self._url, self._user, self._password)
            data["sid"] = self._sid
            response = requests.post(url, data=data, allow_redirects=True)

        html = lxml.html.fromstring(response.text)
        state: str = html.xpath(
            '//div[@class="time_ctrl_options"]/input[@checked="checked"]/@value'
        )[0]

        parental = html.xpath(
            '//div[@class="formular"]/input[@name="parental"]/@checked'
        )
        self._parental = "on" if parental == ["checked"] else None

        disallow_guest = html.xpath(
            '//div[@class="formular"]/input[@name="disallow_guest"]/@checked'
        )
        self._disallow_guest = "on" if disallow_guest == ["checked"] else None

        black = html.xpath('//div[@class="formular"]/input[@value="black"]/@checked')
        white = html.xpath('//div[@class="formular"]/input[@value="white"]/@checked')
        if white == ["checked"] and self._parental is not None:
            self._filtertype = "white"
        elif black == ["checked"] and self._parental is not None:
            self._filtertype = "black"

        return state

    def set_state(self, state: str) -> None:
        """
        Set the state of the profile.
        """
        self.get_state()
        url = self._url + "/data.lua"

        data = {
            "sid": self._sid,
            "edit": self.profile_id,
            "time": state,
            "budget": "unlimited",
            "apply": "nop",
            "page": "kids_profileedit",
        }
        if self._parental is not None:
            data["parental"] = self._parental
        if self._disallow_guest is not None:
            data["disallow_guest"] = self._disallow_guest
        if self._filtertype is not None:
            data["filtertype"] = self._filtertype

        response = requests.post(url, data=data, allow_redirects=True)

        if response.status_code != 200:
            # login again to fetch new sid
            self._sid = login(self._url, self._user, self._password)
            data["sid"] = self._sid
            requests.post(url, data=data, allow_redirects=True)

    def print_state(self) -> None:
        """
        Print the state of the profile.
        """
        state = self.get_state()
        print(state)
