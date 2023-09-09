from pathlib import Path

from dark_sorter.reader import get_hdu, FITS
from dark_sorter.writer import get_new_path, write_if_not_exist

here = Path(__file__).parent
resources = here / "resources"


def test_get_new_path():
    # Test read HDU
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    fits1 = FITS(dark1, dark1_hdu)
    new_path1 = get_new_path(Path("."), fits1)
    assert new_path1 == Path(
        "ZWO ASI2600MC Duo/GAIN_0.0/30.0sec/0C/dark_2023-09-06T23_49_21.502000_864869012867954163.fits"
    )
    # Test read HDU
    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_hdu = get_hdu(dark2)
    fits2 = FITS(dark2, dark2_hdu)
    new_path2 = get_new_path(Path("."), fits2)
    assert new_path2 == Path(
        "Nikon DSLR Zfc/ISO_25600/120.0sec/100C/dark_2023-08-19T18_46_18.463000_226796045581031641.fits"
    )


def test_write_if_not_exist():
    # Test read HDU
    dark1 = resources / "Dark_001.fits"
    dark1_hdu = get_hdu(dark1)
    fits1 = FITS(dark1, dark1_hdu)
    write_if_not_exist(Path("."), fits1, copy=True)
    assert Path(
        "ZWO ASI2600MC Duo/GAIN_0.0/30.0sec/0C/dark_2023-09-06T23_49_21.502000_864869012867954163.fits"
    ).exists()
    Path(
        "ZWO ASI2600MC Duo/GAIN_0.0/30.0sec/0C/dark_2023-09-06T23_49_21.502000_864869012867954163.fits"
    ).unlink()

    # Test read HDU
    dark2 = resources / "another_camera_Dark_001.fits"
    dark2_hdu = get_hdu(dark2)
    fits2 = FITS(dark2, dark2_hdu)
    write_if_not_exist(Path("."), fits2, copy=True)
    assert Path(
        "Nikon DSLR Zfc/ISO_25600/120.0sec/100C/dark_2023-08-19T18_46_18.463000_226796045581031641.fits"
    ).exists()
    Path(
        "Nikon DSLR Zfc/ISO_25600/120.0sec/100C/dark_2023-08-19T18_46_18.463000_226796045581031641.fits"
    ).unlink()
