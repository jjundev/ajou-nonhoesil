"""복습노트 HTML 을 파일 하나로 합친다 (CSS·JS·글꼴·그림을 모두 인라인).

    python -m scripts.lab.standalone_note 실험05 [--kind 실험설명] [--out DIR]
"""
import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "복습노트"
KINDS = ("실험설명", "기출문제", "기출풀이")
KEEP_WEIGHTS = {"400", "500", "600", "700", "800"}
MIME = {".svg": "image/svg+xml", ".woff2": "font/woff2", ".png": "image/png",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _b64(path):
    return base64.b64encode(path.read_bytes()).decode()


def _uri(path):
    mime = MIME.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]
    return f"data:{mime};base64,{_b64(path)}"


def _safe_js(text):
    return text.replace("</script", "<\\/script")


def _inline_css(css, base):
    """url(...) 을 data URI 로. woff2 가 있으면 woff·ttf 대체 항목은 버린다."""
    def font_src(m):
        urls = re.findall(r"url\(\s*['\"]?([^)'\"]+?)['\"]?\s*\)", m.group(0))
        woff2 = [u for u in urls if u.endswith(".woff2")]
        if not woff2:
            return m.group(0)
        return f"src:url({_uri(base / woff2[0])}) format('woff2');"

    def weight_ok(block):
        w = re.search(r"font-weight:\s*(\d+)", block)
        fam = re.search(r"font-family:\s*['\"]?Pretendard", block)
        return not (fam and w and w.group(1) not in KEEP_WEIGHTS)

    def block(m):
        b = m.group(0)
        if not weight_ok(b):
            return ""
        return re.sub(r"src:[^;}]*(?:;|(?=}))", font_src, b)

    css = re.sub(r"@font-face\s*\{[^}]*\}", block, css)
    return re.sub(r"url\(\s*['\"]?(?!data:|https?:)([^)'\"]+?)['\"]?\s*\)",
                  lambda m: f"url({_uri(base / m.group(1))})", css)


def build(note_dir, kind):
    src = note_dir / f"{note_dir.name}_{kind}.html"
    html = src.read_text(encoding="utf-8")
    late = []  # defer 스크립트는 본문 뒤로 옮겨 순서를 지킨다

    def script(m):
        attrs = m.group(1)
        ref = re.search(r'src="([^"]+)"', attrs)
        if not ref:
            return m.group(0)
        code = _safe_js((note_dir / ref.group(1)).read_text(encoding="utf-8"))
        onload = re.search(r'onload="([^"]*)"', attrs)
        parts = f"<script>{code}</script>"
        if onload:
            parts += f"<script>{onload.group(1).replace('&quot;', chr(34))}</script>"
        if "defer" in attrs:
            late.append(parts)
            return ""
        return parts

    html = re.sub(r"<script([^>]*\bsrc=[^>]*)></script>", script, html)

    def link(m):
        href = re.search(r'href="([^"]+)"', m.group(0)).group(1)
        path = note_dir / href
        return f"<style>{_inline_css(path.read_text(encoding='utf-8'), path.parent)}</style>"

    html = re.sub(r'<link[^>]*rel="stylesheet"[^>]*href="(?!https?:)[^"]+"[^>]*>', link, html)
    html = re.sub(r'(<img[^>]*?)src="(?!data:|https?:)([^"]+)"',
                  lambda m: f'{m.group(1)}src="{_uri(note_dir / m.group(2))}"', html)
    def sibling(m):
        attrs, content = m.group(1), m.group(2)
        href = re.search(r'\bhref="([^"]*)"', attrs)
        if not href or not re.fullmatch(re.escape(note_dir.name) + r'_(?:실험설명|기출문제|기출풀이)\.html', href.group(1)):
            return m.group(0)
        attrs = attrs[:href.start()] + attrs[href.end():]
        attrs = attrs.rstrip()
        return f'<span{attrs}>{content}</span>'

    html = re.sub(r'<a\b([^>]*)>(.*?)</a>', sibling, html, flags=re.S)
    html = html.replace('.pack-nav a {', '.pack-nav a, .pack-nav span {')
    html = html.replace('.pack-nav a[aria-current="page"] {',
                        '.pack-nav a[aria-current="page"], .pack-nav span[aria-current="page"] {')
    return html.replace("</body>", "".join(late) + "</body>", 1)


def leftovers(html):
    """남은 상대경로 참조. 비어 있어야 standalone 이다."""
    html = re.sub(r"<script(?=[\s>])[^>]*>.*?</script>", "<script></script>", html, flags=re.S)  # JS 문자열 속 src= 는 참조가 아니다
    left = re.findall(r'<(?:img|script|link|source|a)\b[^>]*?(?:src|href)="(?!data:|#|https?:|mailto:)([^"]+)"', html)
    left += re.findall(r"url\(\s*['\"]?(?!data:|https?:|#)([^)'\"]+)", html)
    return left


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", help="실험05 처럼")
    ap.add_argument("--kind", default="실험설명", choices=KINDS + ("all",))
    ap.add_argument("--out", default=str(Path.home() / "Downloads"))
    a = ap.parse_args(argv)
    note_dir = NOTES / a.exp
    if not note_dir.is_dir():
        sys.exit(f"없는 폴더: {note_dir}")
    bad = 0
    for kind in (KINDS if a.kind == "all" else (a.kind,)):
        html = build(note_dir, kind)
        left = leftovers(html)
        out = Path(a.out) / f"{a.exp}_{kind}_standalone.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"{out} ({len(html) // 1024} KB)" + (f"  남은 참조 {left[:5]}" if left else ""))
        bad += bool(left)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
