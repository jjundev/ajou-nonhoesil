"""복습노트 HTML 을 파일 하나로 합친다 (CSS·JS·글꼴·그림을 모두 인라인).

    python -m scripts.lab.standalone_note 실험05 [--kind all(기본)|실험설명|문제설명] [--out DIR]
    python -m scripts.lab.standalone_note 실험01 실험05 --kind all   # 실험 2개 이상 → zip
    python -m scripts.lab.standalone_note 실험01~05                   # 범위도 된다
    python -m scripts.lab.standalone_note all                        # 실험 폴더 전부 → zip

파일이 하나면 `실험NN_<종류>.html` 을 낸다. 둘 이상이면 `실험NN/` 폴더별로 정리한
`논회실_복습노트_실험01~05.zip` 하나를 낸다(Windows 에서도 풀리도록 이름은 NFC·UTF-8 플래그).
"""
import argparse
import base64
import mimetypes
import re
import sys
import unicodedata
import urllib.parse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "복습노트"
KINDS = ("실험설명", "기출문제", "기출풀이", "문제설명")
ZIP_PREFIX = "논회실_복습노트_"
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


def out_name(exp, kind):
    return f"{exp}_{kind}.html"


def zip_name(exps):
    """연속이면 `논회실_복습노트_실험01~05.zip`, 하나면 `…_실험05.zip`, 아니면 `_` 로 잇는다."""
    exps = sorted(dict.fromkeys(exps))
    nums = [re.fullmatch(r"실험(\d+)", e) for e in exps]
    if len(exps) > 1 and all(nums):
        n = [int(m.group(1)) for m in nums]
        if n == list(range(n[0], n[0] + len(n))):
            return f"{ZIP_PREFIX}{exps[0]}~{nums[-1].group(1)}.zip"
    return ZIP_PREFIX + "_".join(exps) + ".zip"


def build(note_dir, kind, linked=frozenset()):
    """linked: 같은 묶음으로 함께 내보내는 종류. 그쪽으로 가는 형제 링크는 묶음 안의 파일로 잇는다."""
    src = note_dir / f"{note_dir.name}_{kind}.html"
    html = src.read_text(encoding="utf-8")
    late = []  # defer 스크립트는 본문 뒤로 옮겨 순서를 지킨다

    def script(m):
        attrs = m.group(1)
        ref = re.search(r'src="([^"]+)"', attrs)
        if not ref:
            return m.group(0)
        code = _safe_js((note_dir / ref.group(1)).resolve().read_text(encoding="utf-8"))
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
        path = (note_dir / href).resolve()
        return f"<style>{_inline_css(path.read_text(encoding='utf-8'), path.parent)}</style>"

    html = re.sub(r'<link[^>]*rel="stylesheet"[^>]*href="(?!https?:)[^"]+"[^>]*>', link, html)
    html = re.sub(r'(<img[^>]*?)src="(?!data:|https?:)([^"]+)"',
                  lambda m: f'{m.group(1)}src="{_uri(note_dir / m.group(2))}"', html)
    sib = re.compile(re.escape(note_dir.name) + r'_(' + "|".join(KINDS) + r')\.(html|pdf)(#[^"]*)?')

    def sibling(m):
        attrs, content = m.group(1), m.group(2)
        href = re.search(r'\bhref="([^"]*)"', attrs)
        hit = sib.fullmatch(urllib.parse.unquote(href.group(1))) if href else None
        if not hit:
            return m.group(0)
        if hit.group(2) == 'html' and hit.group(1) in linked:
            new = urllib.parse.quote(out_name(note_dir.name, hit.group(1))) + (hit.group(3) or "")
            return f'<a{attrs[:href.start()]}href="{new}"{attrs[href.end():]}>{content}</a>'
        attrs = attrs[:href.start()] + attrs[href.end():]
        attrs = attrs.rstrip()
        return f'<span{attrs}>{content}</span>'

    html = re.sub(r'<a\b([^>]*)>(.*?)</a>', sibling, html, flags=re.S)
    html = html.replace('.pack-nav a {', '.pack-nav a, .pack-nav span {')
    html = html.replace('.pack-nav a[aria-current="page"] {',
                        '.pack-nav a[aria-current="page"], .pack-nav span[aria-current="page"] {')
    return html.replace("</body>", "".join(late) + "</body>", 1)


def leftovers(html, bundle=frozenset()):
    """남은 상대경로 참조. 비어 있어야 standalone 이다.

    bundle: 이번에 함께 내보내는 파일 이름. 이 이름을 가리키는 형제 링크만 면제한다.
    """
    html = re.sub(r"<script(?=[\s>])[^>]*>.*?</script>", "<script></script>", html, flags=re.S)  # JS 문자열 속 src= 는 참조가 아니다
    left = re.findall(r'<(?:img|script|link|source|a)\b[^>]*?(?:src|href)="(?!data:|#|https?:|mailto:)([^"]+)"', html)
    left = [h for h in left if urllib.parse.unquote(h).split("#")[0] not in bundle]  # 같은 묶음의 형제
    left += re.findall(r"url\(\s*['\"]?(?!data:|https?:|#)([^)'\"]+)", html)
    return left


def _expand(names):
    """`실험01~05`·`실험01~실험05` 를 풀어 나열한다. 거꾸로거나 해석 못 하면 그대로 둔다."""
    out = []
    for n in names:
        m = re.fullmatch(r"(실험)(\d+)~(?:실험)?(\d+)", n)
        if m and int(m.group(2)) <= int(m.group(3)):
            width = len(m.group(2))
            out += [f"실험{i:0{width}d}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        else:
            out.append(n)
    return out


def check_zip(path):
    """(파일 수·형제 링크 수, 문제 목록). Windows 에서 풀고 열 수 있는 구조인지 본다."""
    problems, links, count = [], 0, 0
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            problems.append(f"zip 손상: {z.testzip()}")
        names = set(z.namelist())
        for info in z.infolist():
            name, count = info.filename, count + 1
            if not unicodedata.is_normalized("NFC", name):
                problems.append(f"NFC 아님: {name}")
            if not info.flag_bits & 0x800:
                problems.append(f"UTF-8 플래그 없음: {name}")
            if re.search(r'[<>:"|?*\\]', name):
                problems.append(f"Windows 금지 문자: {name}")
            if len(name) > 200:
                problems.append(f"경로가 너무 김: {name}")
            if name.endswith(".html"):
                html = z.read(name).decode("utf-8")
                if "charset" not in html[:2048].lower():
                    problems.append(f"charset 선언 없음: {name}")
                folder = name.rsplit("/", 1)[0] if "/" in name else ""
                for href in re.findall(r'href="(?!https?:)([^"#]+\.html)(?:#[^"]*)?"', html):
                    links += 1
                    target = "/".join(x for x in (folder, urllib.parse.unquote(href)) if x)
                    if target not in names:
                        problems.append(f"끊긴 형제 링크: {name} → {target}")
    return f"파일 {count}개, 형제 링크 {links}개", problems


def _targets(names, kinds, strict):
    """(실험들, [(실험, 종류)], 건너뛴 목록). strict 이면 지정한 파일이 없을 때 종료한다."""
    if names == ["all"]:
        exps = sorted(p.name for p in NOTES.glob("실험*") if p.is_dir())
        strict = False
    else:
        exps = names
    pairs, skipped = [], []
    for exp in exps:
        if not (NOTES / exp).is_dir():
            sys.exit(f"없는 폴더: {NOTES / exp}")
        for kind in kinds:
            if (NOTES / exp / f"{exp}_{kind}.html").is_file():
                pairs.append((exp, kind))
            elif kind in {'기출문제', '기출풀이'} and (pdf := NOTES / exp / f'{exp}_{kind}.pdf').is_file():
                if strict:
                    sys.exit(f"PDF 자료를 이용하세요: {pdf}")
            elif strict:
                sys.exit(f"없는 파일: {NOTES / exp / f'{exp}_{kind}.html'}")
            else:
                skipped.append(f"{exp}_{kind}")
    if not pairs:
        sys.exit("내보낼 HTML 이 없다")
    return exps, pairs, skipped


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("exp", nargs="+", help="실험05 …, 실험01~05(범위), 또는 all(실험 폴더 전부)")
    ap.add_argument("--kind", default="all", choices=KINDS + ("all",), help="기본 all(없는 종류는 건너뜀)")
    ap.add_argument("--out", default=str(Path.home() / "Downloads"))
    ap.add_argument("--zip", default=None, help="파일이 둘 이상일 때의 zip 이름(기본: 논회실_복습노트_실험01~05.zip)")
    a = ap.parse_args(argv)
    names = _expand([unicodedata.normalize("NFC", n) for n in a.exp])  # 맥 입력은 NFD 일 수 있다
    kinds = KINDS if a.kind == "all" else (a.kind,)
    exps, pairs, skipped = _targets(names, kinds, a.kind != "all")
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    use_zip = len(pairs) >= 2
    zip_file = a.zip or zip_name([e for e, _ in pairs])
    zf = zipfile.ZipFile(out_dir / zip_file, "w", zipfile.ZIP_DEFLATED) if use_zip else None
    bad = 0
    try:
        for exp, kind in pairs:
            linked = {k for e, k in pairs if e == exp}
            html = build(NOTES / exp, kind, linked)
            left = leftovers(html, {out_name(exp, k) for k in linked})
            if use_zip:
                label = f"{exp}/{out_name(exp, kind)}"
                zf.writestr(unicodedata.normalize("NFC", label), html.encode("utf-8"))
            else:
                label = out_dir / out_name(exp, kind)
                label.write_text(html, encoding="utf-8")
            print(f"{label} ({len(html) // 1024} KB)" + (f"  남은 참조 {left[:5]}" if left else ""))
            bad += bool(left)
    finally:
        if zf:
            zf.close()
    if use_zip:
        zp = out_dir / zip_file
        print(f"{zp} ({zp.stat().st_size // 1024} KB, {len(pairs)}개)")
        summary, problems = check_zip(zp)
        if problems:
            print("zip 검사 실패:\n  " + "\n  ".join(problems))
            bad += 1
        else:
            print(f"zip 검사 통과 ({summary})")
        stray = [n for n in dict.fromkeys(out_name(e, k) for e, k in pairs) if (out_dir / n).is_file()]
        if stray:
            print(f"출력 폴더에 같은 이름의 낱개 파일이 있다(지우지 않았다): {', '.join(stray)}")
    if skipped:
        print("건너뜀(파일 없음): " + ", ".join(skipped))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
