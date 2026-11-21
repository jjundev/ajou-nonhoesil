"""SVG 그림을 Chrome 헤드리스 스크린샷으로 PNG 로 바꾼다.

노션은 SVG 첨부를 그림으로 보여 주지 않으므로 보고서에는 PNG 를 넣는다.
html2pdf 와 같은 규칙으로 판정한다 — Chrome 의 종료 코드·stderr 가 아니라
PNG 가 새로 생겼는지로만 본다.
"""

import re
import subprocess
import tempfile
from pathlib import Path

from .html2pdf import DEFAULT_CHROME, PdfError, resolve_chrome

_VIEWBOX = re.compile(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"')


def svg_size(svg_text: str) -> tuple[int, int]:
    """viewBox 의 폭·높이(정수 반올림)."""
    m = _VIEWBOX.search(svg_text)
    if not m:
        raise ValueError("SVG 에 viewBox 가 없다")
    return round(float(m.group(1))), round(float(m.group(2)))


def render_svg(svg_path, png_path, chrome=DEFAULT_CHROME, scale=2) -> Path:
    svg_path, png_path = Path(svg_path).resolve(), Path(png_path).resolve()
    w, h = svg_size(svg_path.read_text(encoding="utf-8"))
    chrome = resolve_chrome(chrome)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    before = png_path.stat().st_mtime if png_path.exists() else None
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "wrap.html"
        html.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;padding:0;background:#fff;overflow:hidden}"
            f"img{{display:block;width:{w}px;height:{h}px}}</style></head>"
            f"<body><img src='{svg_path.as_uri()}'></body></html>",
            encoding="utf-8")
        proc = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files", f"--screenshot={png_path}",
             f"--window-size={w},{h}", f"--force-device-scale-factor={scale}",
             "--virtual-time-budget=2000", html.as_uri()],
            capture_output=True, text=True, timeout=120)
    if not png_path.exists() or (before is not None and png_path.stat().st_mtime == before):
        raise PdfError(f"PNG 가 생기지 않았습니다: {png_path}\n{proc.stderr[-2000:]}")
    return png_path
