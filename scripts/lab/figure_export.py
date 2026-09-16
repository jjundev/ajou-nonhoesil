"""예상 결과 그림 HTML → PNG, 그리고 그림 속 숫자 검사.

**캡처는 사본으로 한다.** 그림 HTML 은 아티팩트 게시용이라 doctype·charset 이
없다(게시 때 뼈대가 붙는다). 그대로 file:// 로 열면 한글이 깨진다. 그래서
doctype·charset 을 붙인 사본을 임시 폴더에 쓰고 그것을 연다.

**성공 판정은 `html2pdf` 와 같다** — 파일이 생겼는지로만 본다. Chrome 은 macOS
에서 정상 동작 중에도 stderr 로 경고를 뱉는다. 옛 PNG 가 남아 성공처럼 보이지
않게 찍기 전에 지운다.

**숫자 검사**는 그림 속 소수값이 예비보고서 md 에 같은 글자로 있는지 본다.
보간·환산한 값과 `1.4` 를 `1.40` 으로 찍어 없는 정밀도를 만드는 것을 막는다.
눈금 라벨은 `class="tick"` 으로 빠진다.
"""

import argparse
import html as html_lib
import re
import subprocess
import tempfile
from pathlib import Path

from . import config, figure
from .html2pdf import DEFAULT_CHROME, resolve_chrome
from .spec_parser import parse_spec
from .validate import Finding

WIDTH = 1000
BUDGET_MS = 10000

_HEIGHTS = re.compile(r'data-fig-heights="([\d,]+)"')
_TEXT = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
_TICK = re.compile(r'class="[^"]*\btick\b[^"]*"')
_TAG = re.compile(r"<[^>]+>")
_DECIMAL = re.compile(r"(?<![\d.])\d+\.\d+(?!\d|\.\d)")


class FigureError(RuntimeError):
    pass


def wrap_for_capture(html_text) -> str:
    return ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8"></head><body>\n'
            + html_text + "\n</body></html>\n")


def _write_copy(html_path, tmp) -> Path:
    html_path = Path(html_path)
    if not html_path.exists():
        raise FigureError(f"그림 HTML 이 없다: {html_path}")
    copy = Path(tmp) / "figure.html"
    copy.write_text(wrap_for_capture(html_path.read_text(encoding="utf-8")), encoding="utf-8")
    return copy


def dump_dom(html_path, chrome=DEFAULT_CHROME, timeout=120) -> str:
    """사본을 헤드리스로 열어 스크립트가 그린 뒤의 DOM 을 돌려준다.

    DOM 뜨기는 PNG 추출과 달리 남는 파일이 없다 — 종료 코드가 0 이 아니거나
    표준출력이 비면 실패로 본다(`html2pdf.html_to_pdf` 와 같은 판정 스타일).
    """
    html_path = Path(html_path)
    if not html_path.exists():
        raise FigureError(f"그림 HTML 이 없다: {html_path}")
    chrome = resolve_chrome(chrome)
    with tempfile.TemporaryDirectory() as tmp:
        copy = _write_copy(html_path, tmp)
        proc = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu",
             f"--virtual-time-budget={BUDGET_MS}", "--dump-dom", copy.as_uri()],
            capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise FigureError(
            f"DOM 을 뜨지 못했다 (종료 코드 {proc.returncode}).\n"
            f"stderr:\n{proc.stderr.strip()}"
        )
    return proc.stdout


def parse_heights(dom_text) -> list:
    m = _HEIGHTS.search(dom_text)
    if m is None:
        raise FigureError("data-fig-heights 가 없다 — 템플릿의 높이 기록 줄이 지워졌거나 "
                          "그림이 하나도 없다")
    return [int(h) for h in m.group(1).split(",") if h]


def capture_command(chrome, url, out_png, height, scale=3) -> list:
    return [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--force-device-scale-factor={scale}", f"--window-size={WIDTH},{height}",
            f"--virtual-time-budget={BUDGET_MS}", f"--screenshot={out_png}", url]


def export_pngs(html_path, out_dir, names, heights, chrome=DEFAULT_CHROME,
                scale=3, timeout=120) -> list:
    """`?fig=N` 으로 그림 N 번째를 한 장씩 찍는다. 이름·높이 순서는 그림 순서다."""
    if len(names) != len(heights):
        raise FigureError(f"그림 이름 {len(names)}개와 높이 {len(heights)}개가 다르다")
    out_dir = Path(out_dir).resolve()
    chrome = resolve_chrome(chrome)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        copy = _write_copy(html_path, tmp)
        for i, (name, height) in enumerate(zip(names, heights), start=1):
            png = out_dir / name
            if png.exists():
                png.unlink()
            subprocess.run(capture_command(chrome, f"{copy.as_uri()}?fig={i}", png, height, scale),
                           capture_output=True, text=True, timeout=timeout)
            if not png.exists():
                raise FigureError(f"PNG 가 생성되지 않았다: {png}")
            out.append(png)
    return out


def figure_numbers(dom_text) -> list:
    """눈금이 아닌 SVG 글자의 소수값을 나온 순서대로."""
    out = []
    for attrs, inner in _TEXT.findall(dom_text):
        if _TICK.search(attrs):
            continue
        out.extend(_DECIMAL.findall(html_lib.unescape(_TAG.sub("", inner))))
    return out


def check_figure_numbers(dom_text, md_text) -> list:
    body = set(_DECIMAL.findall(md_text))
    return [Finding("error", "예상 결과 그림",
                    f"그림의 {n} 이 예비보고서 md 에 같은 글자로 없다 — 보간·환산한 값이거나 "
                    "자릿수를 바꿨다. 본문 글자대로 고치거나 그 요소를 뺀다")
            for n in sorted(set(figure_numbers(dom_text)) - body)]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="예상 결과 그림: 판정 → 숫자 검사 → PNG 추출")
    p.add_argument("experiment", type=int)
    p.add_argument("--check-only", action="store_true", help="숫자 검사까지만 한다")
    args = p.parse_args(argv)

    root = config.find_project_root(Path("."))
    exp = root / config.experiment_dir(args.experiment)
    spec = parse_spec(exp / "체크리스트/명세.md")
    pairs = figure.capture_tables(spec)
    if not pairs:
        print(figure.gate_message(spec))
        return 0

    names = [figure.figure_png_name(exp, item) for item, _ in pairs]
    if len(set(names)) != len(names):
        raise FigureError(f"그림 이름이 겹친다 — 한 항목에 capture 표가 둘 이상이다: {names}")
    html_path = exp / "output" / f"{exp.name}_예상결과.html"
    md_path = exp / "output" / f"{exp.name}_예비보고서.md"
    chrome = config.load_course_info(root).get("chrome") or DEFAULT_CHROME

    dom = dump_dom(html_path, chrome)
    heights = parse_heights(dom)
    if len(heights) != len(names):
        raise FigureError(
            f"기록된 그림 높이가 {len(heights)}개인데 그림은 {len(names)}개다 — "
            "그림 스크립트가 도중에 멈췄을 수 있다 (콘솔 에러로 뒤 그림들이 안 그려지면 "
            "그 그림의 <text> 가 DOM 에 없어 숫자 검사가 findings 를 하나도 못 낸다)"
        )
    findings = check_figure_numbers(dom, md_path.read_text(encoding="utf-8"))
    for f in findings:
        print(f)
    if findings:
        return 1
    if args.check_only:
        print("숫자 검사 통과")
        return 0
    for png in export_pngs(html_path, exp / "output", names, heights, chrome):
        print(png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
