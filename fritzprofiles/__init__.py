import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

name = "fritzprofiles"

from .fritzprofiles import FritzProfileSwitch
