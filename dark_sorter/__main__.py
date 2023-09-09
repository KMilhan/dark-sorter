from pathlib import Path

import typer
from rich import print
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from dark_sorter.reader import FITS, get_hdu, logger
from dark_sorter.writer import get_new_path, write_if_not_exist

console = Console()


def read_all_dark_fits_files(root: Path) -> list[FITS]:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Finding all dark FITS files...", total=None)
        paths = list(root.rglob("*.fits"))
    res: list[FITS] = []
    print("Reading dark FITS files")
    with typer.progressbar(length=len(paths)) as progress:
        for idx in range(len(paths)):
            progress.update(1)
            progress.label = str(paths[idx])
            try:
                hdu = get_hdu(paths[idx])
            except OSError:
                logger.debug(f"Found empty or corrupt FITS file: {paths[idx]}")
                continue
            fits_file = FITS(paths[idx], hdu)
            if fits_file.frame_type == "dark":
                res.append(FITS(paths[idx], hdu))
    print("Read all files")
    return res


def main(root: Path, new_path: Path, copy: bool = True):
    print(
        f"Find dark frames from [bold green]{root}[/bold green] and construct dark library at [bold green]{new_path}[/bold green]"
    )
    all_dark_files = read_all_dark_fits_files(root)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(
            description=f"Hashing and sorting {len(all_dark_files)} files", total=None
        )
        all_dark_files.sort(key=lambda x: get_new_path(new_path, x))
        print(f"Found {len(all_dark_files)} dark frames")

    table = Table("Old location", "New location")
    for fits in all_dark_files:
        if not get_new_path(new_path, fits).exists():
            table.add_row(str(fits.path), str(get_new_path(new_path, fits)))

    console.print(table)

    confirm_construct = typer.confirm(
        "Are you certain you wish to create or append to the dark library?"
    )
    if not confirm_construct:
        print("Not creating")
        raise typer.Abort()

    with typer.progressbar(length=len(all_dark_files)) as progress:
        for idx in range(len(all_dark_files)):
            progress.update(1)
            progress.label = str(get_new_path(new_path, all_dark_files[idx]))
            write_if_not_exist(new_path, all_dark_files[idx], copy)


def entrypoint():
    return typer.run(main)


if __name__ == "__main__":
    typer.run(main)
