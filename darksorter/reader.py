import logging
import re
from datetime import datetime
from fractions import Fraction
from hashlib import md5
from pathlib import Path

import dateutil.parser
import exifread
import numpy as np
import rawpy
from astropy.io import fits
from astropy.io.fits import PrimaryHDU

DEFAULT_CCD_TEMP = 100
RAW_DARK_MEAN_THRESHOLD = 0.003
RAW_DARK_P95_THRESHOLD = 0.01
RAW_DARK_BRIGHT_PIXEL_THRESHOLD = 0.05
RAW_DARK_BRIGHT_PIXEL_RATIO_THRESHOLD = 0.0001
FITS_FILE_SUFFIXES = frozenset({".fits"})
RAW_FILE_SUFFIXES = frozenset(
    {
        ".arw",
        ".cr2",
        ".cr3",
        ".dng",
        ".nef",
        ".orf",
        ".pef",
        ".raf",
        ".raw",
        ".rw2",
        ".srw",
    }
)
SUPPORTED_FILE_SUFFIXES = FITS_FILE_SUFFIXES | RAW_FILE_SUFFIXES
FRAME_TYPES = ("dark", "bias", "flat", "light")

logger = logging.getLogger(__name__)


def get_hdu(file: Path) -> PrimaryHDU:
    if is_raw_file(file):
        return get_raw_hdu(file)
    return fits.open(file)[0]


def is_raw_file(file: Path) -> bool:
    return file.suffix.casefold() in RAW_FILE_SUFFIXES


def get_raw_hdu(file: Path) -> PrimaryHDU:
    with file.open("rb") as raw_file:
        tags = exifread.process_file(raw_file, details=False)

    hdu = PrimaryHDU()
    hdu.header["INSTRUME"] = get_raw_camera_name(tags)
    hdu.header["FRAME"] = get_raw_frame_type(file)
    hdu.header["EXPTIME"] = get_raw_exposure_time(tags)
    hdu.header["DATE-OBS"] = get_raw_date(tags).isoformat()
    hdu.header["ISOSPEED"] = get_raw_iso(tags)
    hdu.header["ORIGNAME"] = file.name
    return hdu


def get_raw_camera_name(tags: dict[str, object]) -> str:
    make = get_tag_text(tags, "Image Make")
    model = get_tag_text(tags, "Image Model")
    if not make and not model:
        raise ValueError("RAW file does not contain camera make or model")
    if not make:
        return model
    if not model:
        return make

    camera_make = normalize_camera_make(make)
    if model.casefold().startswith(camera_make.casefold()):
        return f"{camera_make}{model[len(camera_make) :]}"
    return f"{camera_make} {model}"


def normalize_camera_make(make: str) -> str:
    words_to_remove = {
        "corporation",
        "corp.",
        "corp",
        "company",
        "co.",
        "co",
        "ltd.",
        "ltd",
    }
    words = [word for word in make.split() if word.casefold() not in words_to_remove]
    return " ".join(words).title()


def infer_frame_type(file: Path) -> str:
    return infer_explicit_frame_type(file) or "light"


def infer_explicit_frame_type(file: Path) -> str | None:
    name_parts = {
        part for part in re.split(r"[^a-z0-9]+", file.stem.casefold()) if part
    }
    for frame_type in FRAME_TYPES:
        if frame_type in name_parts:
            return frame_type

    for part in reversed(file.parts[:-1]):
        frame_type = part.casefold()
        if frame_type in FRAME_TYPES:
            return frame_type

    return None


def get_raw_frame_type(file: Path) -> str:
    explicit_frame_type = infer_explicit_frame_type(file)
    if explicit_frame_type:
        return explicit_frame_type
    if is_raw_dark_frame(file):
        return "dark"
    return "light"


def is_raw_dark_frame(file: Path) -> bool:
    try:
        with rawpy.imread(str(file)) as raw:
            raw_image = raw.raw_image_visible.astype("float64")
            black_level = get_raw_black_level(raw)
            white_level = float(raw.white_level)
    except rawpy.LibRawError as exc:
        raise ValueError("RAW file cannot be decoded") from exc

    return is_dark_signal(raw_image, black_level, white_level)


def is_dark_signal(
    raw_image: np.ndarray, black_level: float, white_level: float
) -> bool:
    signal_range = white_level - black_level
    if signal_range <= 0:
        raise ValueError("RAW file has invalid black or white level")

    normalized = np.clip((raw_image - black_level) / signal_range, 0, 1)
    mean_signal = float(normalized.mean())
    p95_signal = float(np.percentile(normalized, 95))
    bright_pixel_ratio = float((normalized > RAW_DARK_BRIGHT_PIXEL_THRESHOLD).mean())

    return (
        mean_signal <= RAW_DARK_MEAN_THRESHOLD
        and p95_signal <= RAW_DARK_P95_THRESHOLD
        and bright_pixel_ratio <= RAW_DARK_BRIGHT_PIXEL_RATIO_THRESHOLD
    )


def get_raw_black_level(raw: rawpy.RawPy) -> float:
    black_levels = raw.black_level_per_channel
    if not black_levels:
        raise ValueError("RAW file does not contain black level")
    return sum(black_levels) / len(black_levels)


def get_raw_exposure_time(tags: dict[str, object]) -> float:
    tag = get_first_tag(tags, "EXIF ExposureTime", "Image ExposureTime")
    if tag is None:
        raise ValueError("RAW file does not contain exposure time")
    return tag_to_float(tag)


def get_raw_date(tags: dict[str, object]) -> datetime:
    value = get_tag_text(
        tags,
        "EXIF DateTimeOriginal",
        "Image DateTimeOriginal",
        "Image DateTime",
        "EXIF DateTimeDigitized",
    )
    if not value:
        raise ValueError("RAW file does not contain observation date")
    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")


def get_raw_iso(tags: dict[str, object]) -> int:
    tag = get_first_tag(
        tags,
        "EXIF ISOSpeedRatings",
        "EXIF RecommendedExposureIndex",
        "Image ISOSpeedRatings",
    )
    if tag is None:
        raise ValueError("RAW file does not contain ISO speed")
    return int(tag_to_float(tag))


def get_tag_text(tags: dict[str, object], *names: str) -> str:
    tag = get_first_tag(tags, *names)
    if tag is None:
        return ""
    return str(tag).strip()


def get_first_tag(tags: dict[str, object], *names: str) -> object | None:
    for name in names:
        if name in tags:
            return tags[name]
    return None


def tag_to_float(tag: object) -> float:
    value = getattr(tag, "values", [tag])[0]
    if hasattr(value, "num") and hasattr(value, "den"):
        return value.num / value.den
    return float(Fraction(str(value)))


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
    def date(self) -> datetime:
        return get_date(self.hdu)

    def __hash__(self) -> int:
        if not self._hash:
            self._hash = get_header_hash(self.hdu)
        return self._hash
