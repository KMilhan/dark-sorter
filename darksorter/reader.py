import logging
from datetime import datetime
from hashlib import md5
from pathlib import Path

import dateutil.parser
from astropy.io import fits
from astropy.io.fits import PrimaryHDU

DEFAULT_CCD_TEMP = 100

logger = logging.getLogger(__name__)


def get_hdu(file: Path) -> PrimaryHDU:
    # Error handling can be added here to handle exceptions like FileNotFound, PermissionError, etc.
    return fits.open(file)[0]


def get_camera_name(hdu: PrimaryHDU) -> str:
    return hdu.header["INSTRUME"].replace("ZWO CCD", "ZWO")


def get_frame_type(hdu: PrimaryHDU) -> str:
    if "FRAME" not in hdu.header:
        return "light"
    return hdu.header["FRAME"]


def get_exposure_time(hdu: PrimaryHDU) -> float:
    return float(hdu.header["EXPTIME"])


def get_date(hdu: PrimaryHDU) -> datetime:
    return dateutil.parser.parse(hdu.header["DATE-OBS"])


def get_ccd_temp(hdu: PrimaryHDU) -> int:
    try:
        return int(float(hdu.header["CCD-TEMP"]))
    except KeyError:
        return DEFAULT_CCD_TEMP


def get_iso_or_gain(hdu: PrimaryHDU) -> str:
    try:
        return f"GAIN_{hdu.header['GAIN']}"
    except KeyError:
        return f"ISO_{hdu.header['ISOSPEED']}"


def get_header_hash(hdu: PrimaryHDU) -> int:
    str_header = ""
    for key in hdu.header:
        str_header += str(hdu.header[key])
    return int(md5(str_header.encode()).hexdigest(), 16)


class FITS:
    def __init__(self, path: Path, hdu: PrimaryHDU):
        self.path = path
        self.hdu = hdu
        self._hash: int | None = None

    @property
    def camera(self) -> str:
        return get_camera_name(self.hdu)

    @property
    def temperature(self) -> int:
        return get_ccd_temp(self.hdu)

    @property
    def exposure_time(self) -> float:
        return get_exposure_time(self.hdu)

    @property
    def frame_type(self) -> str:
        return get_frame_type(self.hdu).lower()

    @property
    def gain_or_iso(self) -> str:
        return get_iso_or_gain(self.hdu)

    @property
    def date(self):
        return get_date(self.hdu)

    def __hash__(self):
        if not self._hash:
            self._hash = get_header_hash(self.hdu)
        return self._hash
