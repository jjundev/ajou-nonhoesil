"""SVG 그림을 Chrome 헤드리스 스크린샷으로 PNG 로 바꾼다.

노션은 SVG 첨부를 그림으로 보여 주지 않으므로 보고서에는 PNG 를 넣는다.
html2pdf 와 같은 규칙으로 판정한다 — Chrome 의 종료 코드·stderr 가 아니라
PNG 가 새로 생겼는지로만 본다. 찍은 PNG 에는 원본 SVG 의 해시를 tEXt 로 남겨,
SVG 만 고치고 다시 변환하지 않은 것을 테스트가 잡을 수 있게 한다.
"""

import hashlib
import re
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

from .html2pdf import DEFAULT_CHROME, PdfError, resolve_chrome

# 루트 <svg> 태그 안에서만 찾는다 — 아니면 marker 의 viewBox 를 집어 10×10 으로 찍는다.
_SVG_TAG = re.compile(r"<svg\b[^>]*>")
_VIEWBOX = re.compile(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"')
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_NUL = b"\x00"


def svg_size(svg_text: str) -> tuple[int, int]:
    """루트 viewBox 의 폭·높이(정수 반올림)."""
    tag = _SVG_TAG.search(svg_text)
    m = _VIEWBOX.search(tag.group(0)) if tag else None
    if not m:
        raise ValueError("SVG 루트에 viewBox 가 없다")
    return round(float(m.group(1))), round(float(m.group(2)))


def _chunks(data: bytes):
    if not data.startswith(_PNG_SIG):
        raise ValueError("PNG 가 아니다")
    i = len(_PNG_SIG)
    while i < len(data):
        n, kind = struct.unpack(">I4s", data[i:i + 8])
        yield kind, data[i + 8:i + 8 + n], data[i:i + 12 + n]
        i += 12 + n


def png_text(png_path) -> dict:
    """PNG 의 tEXt 청크(키 → 값)."""
    out = {}
    for kind, body, _ in _chunks(Path(png_path).read_bytes()):
        if kind == b"tEXt" and _NUL in body:
            k, v = body.split(_NUL, 1)
            out[k.decode("latin-1")] = v.decode("latin-1")
    return out


def stamp_png_text(png_path, key: str, value: str) -> None:
    """같은 키의 tEXt 를 지우고 IHDR 바로 뒤에 새로 넣는다."""
    path = Path(png_path)
    k = key.encode("latin-1")
    body = k + _NUL + value.encode("latin-1")
    new = struct.pack(">I", len(body)) + b"tEXt" + body + struct.pack(">I", zlib.crc32(b"tEXt" + body))
    parts = [_PNG_SIG]
    for kind, data, raw in _chunks(path.read_bytes()):
        if kind == b"tEXt" and data.split(_NUL, 1)[0] == k:
            continue
        parts.append(raw)
        if kind == b"IHDR":
            parts.append(new)
    path.write_bytes(b"".join(parts))


def render_svg(svg_path, png_path, chrome=DEFAULT_CHROME, scale=2) -> Path:
    svg_path, png_path = Path(svg_path).resolve(), Path(png_path).resolve()
    w, h = svg_size(svg_path.read_text(encoding="utf-8"))
    chrome = resolve_chrome(chrome)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    before = png_path.stat().st_mtime if png_path.exists() else None
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        html = Path(tmp) / "wrap.html"
        html.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;padding:0;background:#fff;overflow:hidden}"
            f"img{{display:block;width:{w}px;height:{h}px}}</style></head>"
            f"<body><img src='{svg_path.as_uri()}'></body></html>",
            encoding="utf-8")
        try:
            proc = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--allow-file-access-from-files", f"--screenshot={png_path}",
                 f"--window-size={w},{h}", f"--force-device-scale-factor={scale}",
                 "--virtual-time-budget=2000", html.as_uri()],
                capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired as e:
            raise PdfError(f"Chrome 이 120초 안에 끝나지 않았습니다: {svg_path}") from e
    if not png_path.exists() or (before is not None and png_path.stat().st_mtime == before):
        raise PdfError(f"PNG 가 생기지 않았습니다: {png_path}\n{proc.stderr[-2000:]}")
    stamp_png_text(png_path, "svg-sha256", hashlib.sha256(svg_path.read_bytes()).hexdigest())
    return png_path
