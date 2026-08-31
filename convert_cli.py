# -*- coding: utf-8 -*-
"""CLI: convert one or more JSPS PDFs to readable PDFs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from converter import convert_jsps_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description="学振PDFを読み取り可能なPDFに変換")
    parser.add_argument("pdfs", nargs="+", help="入力PDFパス")
    parser.add_argument(
        "-o",
        "--outdir",
        default=None,
        help="出力フォルダ（省略時は入力と同じ場所）",
    )
    args = parser.parse_args()
    outdir = Path(args.outdir) if args.outdir else None
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)

    for pdf in args.pdfs:
        src = Path(pdf)
        if not src.is_file():
            print(f"SKIP missing: {src}", file=sys.stderr)
            continue
        dest = (outdir / f"{src.stem}_readable.pdf") if outdir else None
        path, stats = convert_jsps_pdf(src, dest)
        print(f"OK {src.name} -> {path.name} pages={stats['pages']} chars={stats['chars']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
