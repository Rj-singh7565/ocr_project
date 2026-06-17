"""Load manga/manhwa pages from folders, CBZ/ZIP archives, and PDFs."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, UnidentifiedImageError

from manga_scanner.errors import (
    CorruptSourceError,
    EmptySourceError,
    SourceNotFoundError,
    UnsupportedSourceError,
)
from manga_scanner.models import PageInput
from manga_scanner.sorting import natural_sort_key

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_ARCHIVE_EXTENSIONS = {".cbz", ".zip"}
SUPPORTED_PDF_EXTENSION = ".pdf"


def _validate_path(path: Path) -> None:
    if not path.exists():
        raise SourceNotFoundError(str(path))


def _load_image_from_bytes(data: bytes, *, source_name: str, page_number: int) -> PageInput:
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            image = image.convert("RGB")
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise CorruptSourceError(f"Cannot read image data for {source_name}") from exc

    return PageInput(
        page_number=page_number,
        source_name=source_name,
        image=image,
        width=image.width,
        height=image.height,
    )


def _load_from_image_file(path: Path) -> list[PageInput]:
    try:
        with Image.open(path) as image:
            image.load()
            image = image.convert("RGB")
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise CorruptSourceError(str(path)) from exc

    return [
        PageInput(
            page_number=1,
            source_name=path.name,
            image=image,
            width=image.width,
            height=image.height,
        )
    ]


def _load_from_folder(path: Path) -> list[PageInput]:
    images = sorted(
        (child for child in path.iterdir() if child.is_file() and child.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS),
        key=lambda child: natural_sort_key(child.name),
    )

    if not images:
        raise EmptySourceError(str(path))

    pages = []
    for page_number, image_path in enumerate(images, start=1):
        pages.append(
            _load_image_from_bytes(
                image_path.read_bytes(),
                source_name=image_path.name,
                page_number=page_number,
            )
        )
    return pages


def _load_from_archive(path: Path) -> list[PageInput]:
    try:
        with zipfile.ZipFile(path) as archive:
            members = sorted(
                (
                    info
                    for info in archive.infolist()
                    if not info.is_dir() and Path(info.filename).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
                ),
                key=lambda info: natural_sort_key(Path(info.filename).name),
            )
            if not members:
                raise EmptySourceError(str(path))

            pages = []
            for page_number, member in enumerate(members, start=1):
                try:
                    data = archive.read(member.filename)
                except (KeyError, OSError, zipfile.BadZipFile) as exc:
                    raise CorruptSourceError(str(path)) from exc

                pages.append(
                    _load_image_from_bytes(
                        data,
                        source_name=member.filename,
                        page_number=page_number,
                    )
                )
            return pages
    except zipfile.BadZipFile as exc:
        raise CorruptSourceError(str(path)) from exc


def _load_from_pdf(path: Path) -> list[PageInput]:
    try:
        document = fitz.open(path)
    except Exception as exc:  # noqa: BLE001
        raise CorruptSourceError(str(path)) from exc

    try:
        pages = []
        for page_number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap()
            image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
            pages.append(
                PageInput(
                    page_number=page_number,
                    source_name=f"page-{page_number}",
                    image=image,
                    width=image.width,
                    height=image.height,
                )
            )
        if not pages:
            raise EmptySourceError(str(path))
        return pages
    except Exception as exc:  # noqa: BLE001
        raise CorruptSourceError(str(path)) from exc
    finally:
        document.close()


def load_pages(path: str | Path) -> list[PageInput]:
    """Load pages from an image folder, CBZ/ZIP archive, or PDF.

    Expected behavior:
    - Raise ``SourceNotFoundError`` when the path does not exist.
    - Raise ``UnsupportedSourceError`` for unsupported paths.
    - Raise ``EmptySourceError`` when no readable pages are found.
    - Return pages sorted by natural page order.
    """

    path = Path(path)
    _validate_path(path)

    suffix = path.suffix.lower()

    if path.is_dir():
        return _load_from_folder(path)

    if path.is_file() and suffix in SUPPORTED_IMAGE_EXTENSIONS:
        return _load_from_image_file(path)

    if path.is_file() and suffix in SUPPORTED_ARCHIVE_EXTENSIONS:
        return _load_from_archive(path)

    if path.is_file() and suffix == SUPPORTED_PDF_EXTENSION:
        return _load_from_pdf(path)

    raise UnsupportedSourceError(str(path))
