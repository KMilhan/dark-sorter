from pathlib import Path

from darksorter.reader import FITS, get_hdu
from darksorter.writer import get_new_path, write_if_not_exist

here = Path(__file__).parent
resources = here / "resources"
raw_dark = resources / "raw" / "dark" / "RER_4727.NEF"


def test_get_new_path():
    # Test read HDU
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    fits1 = FITS(dark1, dark1_hdu)
    new_path1 = get_new_path(Path(), fits1)
    assert new_path1 == (
        Path("ZWO ASI2600MC Duo")
        / "GAIN_0.0"
        / "30.0sec"
        / "0C"
        / "dark_2023-09-06T23_49_21.502000_864869012867954163.fits"
    )
    # Test read HDU
    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_hdu = get_hdu(dark2)
    fits2 = FITS(dark2, dark2_hdu)
    new_path2 = get_new_path(Path(), fits2)
    assert new_path2 == (
        Path("Nikon DSLR Zfc")
        / "ISO_25600"
        / "120.0sec"
        / "100C"
        / "dark_2023-08-19T18_46_18.463000_226796045581031641.fits"
    )

    raw_hdu = get_hdu(raw_dark)
    raw_file = FITS(raw_dark, raw_hdu)
    raw_new_path = get_new_path(Path(), raw_file)
    assert raw_new_path.parts[:4] == ("Nikon Z fc", "ISO_800", "0.008sec", "100C")
    assert raw_new_path.name.startswith("dark_2022-11-08T19_18_18.000000_")
    assert raw_new_path.suffix == ".NEF"


def test_write_if_not_exist(tmp_path):
    # Test read HDU
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    fits1 = FITS(dark1, dark1_hdu)
    write_if_not_exist(tmp_path, fits1, copy=True)
    assert get_new_path(tmp_path, fits1).exists()

    # Test read HDU
    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_hdu = get_hdu(dark2)
    fits2 = FITS(dark2, dark2_hdu)
    write_if_not_exist(tmp_path, fits2, copy=True)
    assert get_new_path(tmp_path, fits2).exists()

    raw_hdu = get_hdu(raw_dark)
    raw_file = FITS(raw_dark, raw_hdu)
    write_if_not_exist(tmp_path, raw_file, copy=True)
    raw_new_path = get_new_path(tmp_path, raw_file)
    assert raw_new_path.exists()
    assert raw_new_path.suffix == ".NEF"
