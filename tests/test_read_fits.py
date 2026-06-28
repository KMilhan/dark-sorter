from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from astropy.io import fits

from darksorter.__main__ import read_all_dark_fits_files
from darksorter.reader import (
    get_camera_name,
    get_ccd_temp,
    get_date,
    get_exposure_time,
    get_frame_type,
    get_hdu,
    get_header_hash,
    get_iso_or_gain,
    get_raw_frame_type,
    infer_frame_type,
    is_dark_signal,
    is_raw_dark_frame,
)

here = Path(__file__).parent
resources = here / "resources"
raw_dark = resources / "raw" / "dark" / "RER_4727.NEF"


def test_read_header():
    # Test read HDU
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    assert get_camera_name(dark1_hdu) == "ZWO ASI2600MC Duo"
    assert get_ccd_temp(dark1_hdu) == 0

    # Test read raw
    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_fit = fits.open(dark2)
    assert dark2_fit[0].header["INSTRUME"] == "Nikon DSLR Zfc"
    assert "CCD-TEMP" not in dark2_fit[0].header


def test_read_raw_header():
    raw_hdu = get_hdu(raw_dark)
    assert get_camera_name(raw_hdu) == "Nikon Z fc"
    assert get_frame_type(raw_hdu) == "dark"
    assert get_exposure_time(raw_hdu) == 0.008
    assert get_iso_or_gain(raw_hdu) == "ISO_800"
    assert get_date(raw_hdu) == datetime(2022, 11, 8, 19, 18, 18)
    assert get_ccd_temp(raw_hdu) == 100
    assert raw_hdu.header["ORIGNAME"] == "RER_4727.NEF"


def test_read_raw_header_detects_dark_from_pixels(tmp_path):
    raw_file = tmp_path / "RER_4727.NEF"
    raw_file.write_bytes(raw_dark.read_bytes())

    raw_hdu = get_hdu(raw_file)
    assert get_frame_type(raw_hdu) == "dark"


def test_infer_raw_frame_type():
    assert infer_frame_type(Path("/session/light/Dark_001.NEF")) == "dark"
    assert infer_frame_type(Path("/session/dark/light/DSC_001.NEF")) == "light"
    assert infer_frame_type(Path("/session/dark-sorter/DSC_001.NEF")) == "light"


def test_detect_raw_frame_type():
    assert is_raw_dark_frame(raw_dark)


def test_detect_dark_signal_rejects_dim_light_frame():
    raw_image = np.full((100, 100), 1200.0)
    assert not is_dark_signal(raw_image, black_level=1000, white_level=17000)


def test_detect_dark_signal_allows_hot_pixels():
    raw_image = np.full((100, 100), 1001.0)
    raw_image[0, 0] = 17000.0
    assert is_dark_signal(raw_image, black_level=1000, white_level=17000)


def test_detect_dark_signal_rejects_bright_frame():
    raw_image = np.full((100, 100), 9000.0)
    assert not is_dark_signal(raw_image, black_level=1000, white_level=17000)


def test_detect_dark_signal_rejects_invalid_levels():
    raw_image = np.full((10, 10), 1000.0)
    with pytest.raises(ValueError, match="invalid black or white level"):
        is_dark_signal(raw_image, black_level=1000, white_level=1000)


def test_explicit_frame_type_wins_over_raw_pixel_detection(monkeypatch):
    def fail_if_called(_: Path) -> bool:
        raise AssertionError("explicit frame type should not read RAW pixels")

    monkeypatch.setattr("darksorter.reader.is_raw_dark_frame", fail_if_called)
    assert get_raw_frame_type(Path("/session/dark/DSC_001.NEF")) == "dark"
    assert get_raw_frame_type(Path("/session/light/DSC_001.NEF")) == "light"


def test_raw_pixel_detection_can_reject_dark(monkeypatch):
    monkeypatch.setattr("darksorter.reader.is_raw_dark_frame", lambda _: False)
    assert get_raw_frame_type(Path("/session/DSC_001.NEF")) == "light"


def test_default_temp():
    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_fit = fits.open(dark2)
    assert get_ccd_temp(dark2_fit[0]) == 100


def test_get_iso_or_gain():
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    assert get_iso_or_gain(dark1_hdu) == "GAIN_0.0"

    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_hdu = get_hdu(dark2)
    assert get_iso_or_gain(dark2_hdu) == "ISO_25600"


def test_get_date():
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    assert get_date(dark1_hdu) == datetime(2023, 9, 6, 23, 49, 21, 502000)

    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_hdu = get_hdu(dark2)
    assert get_date(dark2_hdu) == datetime(2023, 8, 19, 18, 46, 18, 463000)


def test_hash():
    all_fits = read_all_dark_fits_files(resources)
    assert len(all_fits) == 5
    for file in all_fits:
        assert get_header_hash(file.hdu)


def test_read_all_files():
    all_fits = read_all_dark_fits_files(resources)
    assert len(all_fits) == 5
    assert any(file.path == raw_dark for file in all_fits)
    for file in all_fits:
        assert file.frame_type == "dark"


def test_fits_object():
    target = read_all_dark_fits_files(resources)
    by_name = {file.path.name: file for file in target}
    assert hash(by_name["Dark_001.fits"]) != hash(
        by_name["another_camera_Dark_001.fits"]
    )
    assert hash(by_name["Dark_001.fits"]) != hash(by_name["Dark_005.fits"])
    assert hash(by_name["another_camera_Dark_001.fits"]) != hash(
        by_name["Dark_005.fits"]
    )
    assert hash(by_name["Dark_005.fits"]) == hash(by_name["same_dark_005.fits"])
    assert hash(by_name["RER_4727.NEF"]) != hash(by_name["Dark_001.fits"])
