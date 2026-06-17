"""Markdown rendering for scanner results."""

from __future__ import annotations

from manga_scanner.models import MangaScan


def _escape_markdown(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("*", r"\*")
        .replace("_", r"\_")
        .replace("[", r"\[")
        .replace("]", r"\]")
        .replace("#", r"\#")
        .replace("-", r"\-")
        .replace(".", r"\.")
        .replace("`", r"\`")
    )


def render_markdown(scan: MangaScan) -> str:
    """Render a deterministic Markdown report.

    Expected format:
    - ``# <title>``
    - Source metadata bullets
    - One ``## Page N`` section per page
    - Dimensions, OCR text, and warnings
    - Escape Markdown-sensitive text where needed
    """

    source_path = scan.source_path.as_posix()

    lines = [
        f"# {_escape_markdown(scan.title)}",
        "",
        f"- Source: `{source_path}`",
        f"- Type: {scan.source_type}",
        f"- Pages: {len(scan.pages)}",
        "",
    ]

    for page in scan.pages:
        lines.extend(
            [
                f"## Page {page.page_number}",
                "",
                f"- Source page: `{page.source_name}`",
                f"- Dimensions: {page.width} x {page.height}",
                "",
                "### OCR Text",
                "",
            ]
        )

        if page.text_blocks:
            for index, block in enumerate(page.text_blocks, start=1):
                lines.append(f"{index}. {_escape_markdown(block)}")
        else:
            lines.append("_No text detected._")

        lines.append("")

        if page.warnings:
            lines.extend(["### Warnings", "", *[f"- {_escape_markdown(warning)}" for warning in page.warnings], ""])

    return "\n".join(lines).rstrip() + "\n"
