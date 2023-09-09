from hashlib import sha1
from pathlib import Path

from astropy.io import fits
from astropy.io.fits import PrimaryHDU

DEFAULT_CCD_TEMP = 100


def get_hdu(file: Path) -> PrimaryHDU:
    return fits.open(file)[0]


def get_camera_name(hdu: PrimaryHDU) -> str:
    return hdu.header["INSTRUME"]


def get_frame_type(hdu: PrimaryHDU) -> str:
    return hdu.header["FRAME"]


def get_exposure_time(hdu: PrimaryHDU) -> float:
    return float(hdu.header["EXPTIME"])


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


class FITS:
    def __init__(self, path: Path, hdu: PrimaryHDU):
        self.path = path
        self.hdu = hdu

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
    def __hash__(self):
        return int(sha1(self.hdu.data).hexdigest(), 16)


def read_all_fits_files(root: Path) -> list[FITS]:
    paths = list(root.rglob("*.fits"))
    res: list[FITS] = []
    for idx in range(len(paths)):
        hdu = get_hdu(paths[idx])
        fits_files = FITS(paths[idx], hdu)
        if fits_files.frame_type == "dark":
            res.append(FITS(paths[idx], hdu))
    return res
