"""Sorting helpers for manga page filenames."""

from __future__ import annotations

import re


def natural_sort_key(value: str) -> tuple[object, ...]:
    """Return a key that sorts embedded numbers numerically.

    Example:
        ``page2.png`` should sort before ``page10.png``.

    The key splits the string into alternating text and digit chunks:
    lowercase text chunks for case-insensitive comparison and convert digit
    chunks to integers so values like ``page10`` sort after ``page2``.
    """

    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
        if part != ""
    )
