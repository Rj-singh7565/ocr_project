"""High-level scan orchestration."""

from __future__ import annotations

from pathlib import Path

from manga_scanner.loaders import load_pages
from manga_scanner.models import MangaScan, OcrEngine, PageScan
from manga_scanner.ocr import NullOcrEngine


def scan_source(path: str | Path, ocr_engine: OcrEngine | None = None) -> MangaScan:
    """Scan a source and return OCR-ready Markdown data.

    Expected behavior:
    - Use ``load_pages`` to read the source.
    - Use ``NullOcrEngine`` when ``ocr_engine`` is ``None``.
    - Strip empty OCR blocks.
    - Add a warning when a page has no OCR text.
    - Add a warning for very tall manhwa-style pages.
    """

    source_path = Path(path)
    engine = ocr_engine or NullOcrEngine()
    pages = load_pages(source_path)

    page_scans = []
    for page in pages:
        raw_blocks = engine.recognize(page)
        text_blocks = tuple(
            block.strip()
            for block in raw_blocks
            if isinstance(block, str) and block.strip()
        )

        warnings = list()
        if not text_blocks:
            warnings.append("No OCR text detected.")
        if page.height >= page.width * 2.5:
            warnings.append("Long vertical manhwa-style page.")

        page_scans.append(
            PageScan(
                page_number=page.page_number,
                source_name=page.source_name,
                width=page.width,
                height=page.height,
                text_blocks=text_blocks,
                warnings=tuple(warnings),
            )
        )

    suffix = source_path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        source_type = "image"
        title = source_path.stem
    elif suffix == ".pdf":
        source_type = "pdf"
        title = source_path.stem
    elif suffix in {".cbz", ".zip"}:
        source_type = "archive"
        title = source_path.stem
    else:
        source_type = "folder"
        title = source_path.name

    return MangaScan(
        title=title,
        source_path=source_path,
        source_type=source_type,
        pages=tuple(page_scans),
    )
