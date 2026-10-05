"""단계·구역 블록마다 제 높이의 쪽을 준다 — 쪽 길이 wrap_content.

체크리스트 PDF 는 태블릿으로 본다(2026-09-28 사용자). 고정 높이 쪽에서는 결선도 그림과
그 아래 확인·단계 진리표가 쪽 경계에서 갈렸다. 가장 긴 블록에 맞춰 모든 쪽을 늘리면 짧은
블록 아래가 비므로, **블록마다 이름 붙은 쪽**(`@page fit-<i>`)을 주고 높이를 실측값으로 한다.

CSS 에는 "내용만큼" 쪽 크기가 없어 두 번 간다: 크롬에 HTML 을 띄워 블록 높이를 재고
(`measure`), 그 값으로 쪽 규칙을 HTML 에 심는다(`fit_pages`). 그다음 `html_to_pdf` 는 평소대로.
크롬은 `page` 값이 바뀌는 곳에서 쪽을 넘기므로 블록마다 이름이 달라야 한다.

블록이 아닌 부분(공통면)은 HTML 의 기본 `@page` 를 그대로 쓴다.
"""

import math
import re
import subprocess
from pathlib import Path

from scripts.lab.html2pdf import DEFAULT_CHROME, PdfError, resolve_chrome

# 렌더러가 찍는 블록 여는 태그 그대로 — 렌더 테스트들이 이 문자열로 블록을 자른다.
# `stage` 는 단계 블록(테두리 있음), `fit` 은 스타일 없는 래퍼(회로 머리글·완성본·핀 점검+기록표·마무리).
FIT_OPEN = '<div class="stage">'
FIT_PLAIN = '<div class="fit">'
_OPEN = re.compile(r'<div class="(stage|fit)">')
_TAGGED = re.compile(r'<div class="(stage|fit)" data-fit="\d+">')
_STYLE = re.compile(r'<style id="fit-pages">.*?</style>\n?', re.S)
_PAGE = re.compile(r"@page\s*\{\s*size:\s*(\d+)mm\s+\d+mm;\s*margin:\s*(\d+)mm\s+(\d+)mm")
_PAD = 4      # mm — 실측(화면)과 인쇄의 반올림 차이를 덮는 여유
_RESULT = "data-fit-mm"


def page_box(html: str) -> tuple[int, int, int]:
    """기본 `@page` 의 (폭, 위아래 여백, 좌우 여백) mm. 블록 쪽도 폭·여백은 같게 둔다."""
    m = _PAGE.search(html)
    if m is None:
        raise ValueError("`@page { size: <폭>mm <높이>mm; margin: <세로>mm <가로>mm }` 규칙이 없다")
    return tuple(int(g) for g in m.groups())


def strip(html: str) -> str:
    """앞서 심은 쪽 규칙과 번호를 걷어 낸다 — 다시 돌려도 같은 결과가 나오게."""
    return _TAGGED.sub(lambda m: f'<div class="{m.group(1)}">', _STYLE.sub("", html))


def tag(html: str) -> str:
    """`stage`·`fit` 블록마다 `data-fit="<i>"` 를 문서 순서대로 단다."""
    parts = _OPEN.split(strip(html))        # [앞, 클래스, 뒤, 클래스, 뒤, ...]
    return parts[0] + "".join(f'<div class="{parts[k]}" data-fit="{(k - 1) // 2}">{parts[k + 1]}'
                              for k in range(1, len(parts), 2))


def fit_style(heights: list[float], box: tuple[int, int, int]) -> str:
    """블록 i 에 `@page fit-i` — 높이는 실측 + 위아래 여백 + 여유, mm 올림."""
    width, mv, mh = box
    rules = []
    for i, h in enumerate(heights):
        size = math.ceil(h + 2 * mv + _PAD)
        rules.append(f"@page fit-{i} {{ size: {width}mm {size}mm; margin: {mv}mm {mh}mm; }}\n"
                     f'[data-fit="{i}"] {{ page: fit-{i}; }}')
    return '<style id="fit-pages">\n' + "\n".join(rules) + "\n</style>\n"


# 인쇄 본문 폭(쪽 폭 - 좌우 여백)으로 레이아웃을 고정하고, 블록마다 위아래 바깥 여백까지 잰다.
# onload 는 그림이 다 들어온 뒤라 그림 높이가 들어간다.
_MEASURE = """<script>window.addEventListener('load',()=>{{
const px=96/25.4;
const r=[...document.querySelectorAll('[data-fit]')].map(e=>{{
 const s=getComputedStyle(e);
 return ((e.getBoundingClientRect().height+parseFloat(s.marginTop)+parseFloat(s.marginBottom))/px).toFixed(2)}});
document.documentElement.setAttribute('{attr}',r.join(','))}});</script>
<style>html{{width:{content}mm}}</style>"""


def measure(html: str, base: Path, chrome=DEFAULT_CHROME, timeout=120) -> list[float]:
    """`data-fit` 블록들의 높이(mm). `base` 는 그림 상대 경로를 풀 폴더다."""
    width, _, mh = page_box(html)
    probe = base / "_fit_pages_measure.html"
    probe.write_text(html + _MEASURE.format(attr=_RESULT, content=width - 2 * mh),
                     encoding="utf-8")
    try:
        out = subprocess.run(
            [resolve_chrome(chrome), "--headless", "--disable-gpu", "--window-size=1200,2000",
             "--virtual-time-budget=10000", "--dump-dom", probe.resolve().as_uri()],
            capture_output=True, text=True, timeout=timeout).stdout
    finally:
        probe.unlink(missing_ok=True)
    m = re.search(rf'{_RESULT}="([^"]*)"', out)
    if m is None:
        raise PdfError("블록 높이를 재지 못했다 — 크롬이 DOM 을 돌려주지 않았다")
    return [float(x) for x in m.group(1).split(",")] if m.group(1) else []


def fit_pages(html_path, chrome=DEFAULT_CHROME) -> list[float]:
    """HTML 파일에 블록별 쪽 규칙을 심어 덮어쓴다. 잰 높이(mm)를 돌려준다."""
    html_path = Path(html_path)
    html = tag(html_path.read_text(encoding="utf-8"))
    heights = measure(html, html_path.parent, chrome)
    style = fit_style(heights, page_box(html))
    # 뒤에 붙인다 — 크롬은 이름 없는 `@page` 가 뒤에 오면 이름 붙은 쪽의 size 까지 덮는다
    # (2026-09-28 실측: 앞에 두었더니 쪽은 갈리는데 높이가 전부 420mm 였다).
    html_path.write_text(html + style, encoding="utf-8")
    return heights
