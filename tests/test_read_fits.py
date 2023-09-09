from pathlib import Path

from astropy.io import fits

from dark_sorter.reader import (
    get_hdu,
    get_camera_name,
    get_ccd_temp,
    read_all_fits_files,
    get_iso_or_gain,
)

here = Path(__file__).parent
resources = here / "resources"


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


def test_read_all_files():
    all_fits = read_all_fits_files(resources)
    assert len(all_fits) == 4
    for file in all_fits:
        assert file.frame_type == "dark"


def test_fits_object():
    target = read_all_fits_files(resources)
    assert hash(target[0]) != hash(target[1])
    assert hash(target[0]) != hash(target[2])
    assert hash(target[1]) != hash(target[2])
    assert hash(target[2]) == hash(target[3])
    assert hash(target[0]) != hash(target[3])
    assert hash(target[1]) != hash(target[3])
