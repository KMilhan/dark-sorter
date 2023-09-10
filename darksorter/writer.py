from pathlib import Path

from darksorter.reader import FITS


def get_new_path(base: Path, fits_file: FITS) -> Path:
    file_name = (
        "_".join(
            [
                fits_file.frame_type,
                str(fits_file.date.strftime("%Y-%m-%dT%H_%M_%S.%f")),
                str(hash(fits_file)),
            ]
        )
        + ".fits"
    )
    return (
        base
        / fits_file.camera
        / fits_file.gain_or_iso
        / (str(fits_file.exposure_time) + "sec")
        / (str(fits_file.temperature) + "C")
        / file_name
    )


def write_if_not_exist(base: Path, fits_file: FITS, copy: bool = False) -> None:
    new_path = get_new_path(base, fits_file)
    if new_path.exists():
        return
    # exist ok for parallel creation
    new_path.parent.mkdir(parents=True, exist_ok=True)
    if copy:
        new_path.write_bytes(fits_file.path.read_bytes())
    else:
        fits_file.path.rename(new_path)
