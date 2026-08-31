# -*- coding: utf-8 -*-
"""Convert JSPS (IOWebDOC) PDFs into text-extractable dual-layer PDFs."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pymupdf

# Optional external font override. Built-in "japan" is preferred (reliable Unicode).
_FONT_CANDIDATES = [
    os.environ.get("JAPANESE_FONT_PATH", ""),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
    r"C:\Windows\Fonts\meiryo.ttc",
]


def load_japanese_font() -> tuple[pymupdf.Font, str]:
    """Return (Font, label). Prefer MuPDF built-in Japan font for correct Unicode."""
    try:
        font = pymupdf.Font("japan")
        return font, "builtin:japan"
    except Exception:
        pass

    for path in _FONT_CANDIDATES:
        if path and Path(path).is_file():
            try:
                return pymupdf.Font(fontfile=path), path
            except Exception:
                continue

    # Last resort: any default font (may not cover all CJK)
    return pymupdf.Font(), "fallback-default"


def find_japanese_font() -> str | None:
    """Compatibility helper for UI status."""
    _, label = load_japanese_font()
    return label


def convert_jsps_pdf(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    render_scale: float = 2.0,
) -> tuple[Path, dict]:
    """
    Rebuild PDF as image background + invisible Unicode text layer.

    Returns (output_path, stats).
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"PDF not found: {input_path}")

    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_readable.pdf")
    else:
        output_path = Path(output_path)

    font, font_label = load_japanese_font()
    src = pymupdf.open(input_path)
    dst = pymupdf.open()

    total_chars = 0
    pages_with_text = 0
    matrix = pymupdf.Matrix(render_scale, render_scale)
    page_count = src.page_count

    try:
        for page in src:
            new_page = dst.new_page(width=page.rect.width, height=page.rect.height)

            pix = page.get_pixmap(matrix=matrix, alpha=False)
            new_page.insert_image(new_page.rect, pixmap=pix)
            pix = None

            writer = pymupdf.TextWriter(new_page.rect)
            page_chars = 0
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text") or ""
                        if not text.strip():
                            continue
                        bbox = span["bbox"]
                        size = max(float(span.get("size") or 10), 4.0)
                        # TextWriter uses baseline point
                        point = pymupdf.Point(
                            bbox[0],
                            min(bbox[3] - 0.5, page.rect.height - 0.5),
                        )
                        try:
                            writer.append(point, text, font=font, fontsize=size)
                            page_chars += len(text)
                        except Exception:
                            continue

            if page_chars:
                writer.write_text(new_page, render_mode=3)
                pages_with_text += 1
            total_chars += page_chars

        output_path.parent.mkdir(parents=True, exist_ok=True)
        dst.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        dst.close()
        src.close()

    stats = {
        "pages": page_count,
        "chars": total_chars,
        "pages_with_text": pages_with_text,
        "font": font_label,
        "output": str(output_path),
    }
    return output_path, stats


def convert_to_temp(
    input_path: str | Path, *, suffix: str = "_readable.pdf"
) -> tuple[Path, dict]:
    """Convert into a temp file (for web upload flow). Caller should delete after send."""
    input_path = Path(input_path)
    fd, tmp_name = tempfile.mkstemp(prefix="jsps_readable_", suffix=suffix)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        return convert_jsps_pdf(input_path, tmp_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
