#!/usr/bin/env python3
"""Rebuild the WebP case-study images from the source PDFs.

The case-study PDFs are single very tall pages containing nothing but
stacked JPEG strips. Serving them as PDFs meant every phone downloaded a
multi-MB desktop-resolution file plus a PDF engine to draw it. This
extracts the strips and writes WebP variants at several widths so each
device downloads only what its screen can resolve.

Slices are contiguous and sum to the full page height, so stacking them in
page order reproduces the original exactly.

Usage:
    python3 -m venv .venv && .venv/bin/pip install pymupdf pillow
    .venv/bin/python tools/build-case-images.py

Then paste the printed CASES block into index.html.
"""
import io, json, os
import fitz                      # pymupdf
from PIL import Image

SRC = {'bench': 'bench.pdf', 'habble': 'habble.pdf', 'group5': 'group5.pdf'}
STEPS = [900, 1200, 1600, 2000]  # candidate widths; capped at native, never upscaled
QUALITY = 92                     # measured at 45-48 dB PSNR vs source: visually identical
OUT = 'case'


def build():
    os.makedirs(OUT, exist_ok=True)
    cases, total = {}, 0
    for key, src in SRC.items():
        doc = fitz.open(src)
        page = doc[0]
        # order strips by their position on the page, not by xref
        placed = sorted((r.y0, im[0]) for im in page.get_images(full=True)
                        for r in page.get_image_rects(im[0]))
        heights, widths, native = [], None, None
        for idx, (_, xref) in enumerate(placed, 1):
            im = Image.open(io.BytesIO(doc.extract_image(xref)['image'])).convert('RGB')
            native = im.width
            widths = sorted({w for w in STEPS if w < native} | {native})
            for w in widths:
                out = im if w == native else im.resize(
                    (w, round(im.height * w / im.width)), Image.LANCZOS)
                path = f'{OUT}/{key}-{idx:02d}-{w}.webp'
                out.save(path, 'WEBP', quality=QUALITY, method=6)
                total += os.path.getsize(path)
            heights.append(im.height)
        cases[key] = {'w': native, 'widths': widths, 'h': heights}
        print(f'{key}: {len(heights)} slice(s), native {native}px, widths {widths}')
    print(f'\ntotal written: {total / 1048576:.2f} MB\n')
    print('const CASES=' + json.dumps(cases, separators=(',', ':')) + ';')


if __name__ == '__main__':
    build()
