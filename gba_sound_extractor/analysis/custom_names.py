"""Load and save user-provided song name files.

Supports two formats:

1. **JSON** — ``{"0": "Title Screen", "1": "Route 101", ...}``
2. **Tab-separated text** — one ``index<TAB>name`` per line::

       0	Title Screen
       1	Route 101
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def load_custom_names(path: str) -> Dict[int, str]:
    """Load a song name mapping from *path*.

    Returns a dict mapping integer song index to name string.
    Raises ``ValueError`` on parse failure.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")

    if p.suffix.lower() == ".json":
        return _parse_json(text)
    return _parse_text(text)


def save_custom_names(path: str, names: Dict[int, str]) -> None:
    """Save a song name mapping to *path* (always JSON)."""
    serialisable = {str(k): v for k, v in sorted(names.items())}
    Path(path).write_text(
        json.dumps(serialisable, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Saved %d song names to %s", len(names), path)


def _parse_json(text: str) -> Dict[int, str]:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Expected a JSON object with index→name entries")
    result: Dict[int, str] = {}
    for key, value in raw.items():
        try:
            idx = int(key)
        except (ValueError, TypeError):
            continue
        result[idx] = str(value)
    return result


def _parse_text(text: str) -> Dict[int, str]:
    result: Dict[int, str] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", maxsplit=1)
        if len(parts) != 2:
            # Try space/comma as fallback separator
            parts = line.split(None, maxsplit=1)
        if len(parts) != 2:
            logger.warning("Line %d: cannot parse %r", line_no, line)
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            logger.warning("Line %d: non-integer index %r", line_no, parts[0])
            continue
        result[idx] = parts[1].strip()
    return result
