"""
Zero-dependency .docx text extractor.
A .docx file is a zip archive containing word/document.xml.
We parse that XML directly — no python-docx required.
"""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def read_docx(path: Path) -> str:
    """
    Extract all text from a .docx file, preserving paragraph line breaks.
    Returns a plain-text string.
    Raises FileNotFoundError if the file doesn't exist.
    Raises ValueError if the file is not a valid .docx.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"docx not found: {path}")

    try:
        with zipfile.ZipFile(path) as z:
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError(f"Not a valid .docx file: {path}") from exc

    lines = []
    for para in tree.findall(f".//{{{_W}}}p"):
        # Collect all text runs in this paragraph
        texts = [
            elem.text
            for elem in para.findall(f".//{{{_W}}}t")
            if elem.text
        ]
        line = "".join(texts).strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


def read_docx_safe(path: Path, fallback: str = "") -> str:
    """Like read_docx but returns fallback string on any error."""
    try:
        return read_docx(path)
    except Exception:
        return fallback
