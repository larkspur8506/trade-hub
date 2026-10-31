"""Regenerate the trade-hub icons.

The glyph is Lucide's `chart-candlestick` (ISC license) fetched from Iconify —
NOT hand-drawn (user decision, 2026-10-31). Rendering needs a browser, so this
script only builds the render page; the screenshot step runs in the harness
browser (or headless chrome) at 1024x1024, then pillow downscales.

Pipeline (run from repo root):
1. /opt/data/venvs/img/bin/python scripts/gen_icons.py        # writes /tmp/icon_render.html
2. browser: open file:///tmp/icon_render.html, set viewport 1024x1024, screenshot
3. resize the shot to icon-512/192, apple-touch-icon(180), favicon-32 into app/static/
"""
from __future__ import annotations

import urllib.request

OUT_HTML = "/tmp/icon_render.html"
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0}
.tile{{width:1024px;height:1024px;display:flex;align-items:center;justify-content:center;
background:linear-gradient(145deg,#1b2f4d 0%,#141a26 55%,#0e1118 100%);}}
svg{{width:760px;height:760px;filter:drop-shadow(0 14px 28px rgba(0,0,0,.45))}}
</style></head><body><div class="tile">{svg}</div></body></html>"""


def main() -> None:
    url = "https://api.iconify.design/lucide/chart-candlestick.svg"
    svg = urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
    # white glyph on the dark tile; thicker strokes survive 32-60px sizes
    svg = svg.replace("currentColor", "#ffffff").replace('stroke-width="2"', 'stroke-width="2.4"')
    with open(OUT_HTML, "w") as f:
        f.write(PAGE.format(svg=svg))
    print("render page written:", OUT_HTML)


if __name__ == "__main__":
    main()
