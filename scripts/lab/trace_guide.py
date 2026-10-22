"""따라 그리기 PDF — 완성본 결선도를 층으로 나눠 팀원이 한 쪽씩 옮겨 그리게 한다.

주차 결선 파일(`배치.py`)의 `FINALS` 와 `LAYERS` 를 읽는다. 완성본 한 장마다 0쪽(완성본
전체 + notes)과 층마다 한 쪽을 낸다. 층 그림은 엔진 `layer=(lo, hi)` 로 그린다 — 앞 층
회색, 이번 층 색·완성본 번호, 뒤 층은 안 보인다. 표는 완성본 사이드카 `steps` 에서 그 층
번호만 고른다. 조립 절차(`BOARDS`)는 쓰지 않는다 — 임시 급전선이 손그림에 섞인다.

층 PNG 는 임시 폴더에만 둔다. 커밋하는 것은 PDF 한 개다.

    .venv/bin/python -m scripts.lab.trace_guide 4
"""
import argparse
import contextlib
import html
import inspect
import io
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from pypdf import PdfReader

from scripts.lab import config
from scripts.lab.hand_grid import load_renderer
from scripts.lab.html2pdf import PdfError, html_to_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = '팀원전달용'
LEGEND = ('회색 선은 앞 쪽에서 이미 그렸어요. 이번 쪽에서는 색 선만 번호 순서대로 그려요. '
          '신호선은 선마다 색이 달라요 — 같은 색 점끼리 이으면 돼요. 이 색은 찾기용이라 손그림은 원래 펜 색으로 그려요.')

CSS = """
@page { size: 210mm 420mm; margin: 12mm 10mm; }
body { font-family: 'Apple SD Gothic Neo', sans-serif; font-size: 11pt; color: #111; margin: 0; }
.page { break-after: page; }
.page:last-child { break-after: auto; }
h1 { font-size: 15pt; margin: 0 0 3mm; }
.legend { margin: 0 0 3mm; color: #555; }
img { width: 100%; display: block; }
table { width: 100%; border-collapse: collapse; margin-top: 3mm; font-size: 10pt; }
th, td { border-bottom: 1px solid #ccc; padding: 1mm 2mm; text-align: left; vertical-align: top; }
td.n { width: 8mm; font-weight: 700; }
td.hole { white-space: nowrap; }
.kind-vcc { color: #c81e1e; } .kind-gnd { color: #1e3cc8; }
.kind-sig { color: #191919; } .kind-mid { color: #14823c; }
ul.notes { margin-top: 4mm; padding-left: 5mm; }
"""


class LayerError(ValueError):
    """`LAYERS` 가 없거나 완성본 번호를 빈틈없이 덮지 않는다."""


@dataclass
class Page:
    image: str        # 작업 폴더 안 PNG 파일 이름
    heading: str
    rows: list        # 사이드카 steps 중 이 쪽 번호
    notes: list       # 완성본 notes — 0쪽에만
    legend: str       # 층 쪽 안내 한 줄 — 완성본 쪽은 ''
    colors: dict = field(default_factory=dict)   # 번호 → RGBA, 엔진 층 렌더가 칠한 신호선 색(`wire_colors`)


def check_layers(name, layers, n_steps):
    """층 경계가 1..n_steps 를 빈틈·겹침 없이 덮는지. 어긋나면 번호를 말하고 멈춘다."""
    expected = 1
    for lo, hi, label in layers:
        if lo != expected:
            raise LayerError(f'{name}: 층 "{label}" 은 {expected}번에서 시작해야 하는데 {lo}번에서 시작한다')
        if hi < lo:
            raise LayerError(f'{name}: 층 "{label}" 의 끝 {hi}번이 시작 {lo}번보다 앞이다')
        expected = hi + 1
    if expected - 1 != n_steps:
        raise LayerError(f'{name}: 층이 {expected - 1}번에서 끝나는데 완성본 배선은 {n_steps}개다')


def build_pages(board, work_dir):
    """완성본마다 0쪽 + 층 쪽. 그림과 사이드카는 `work_dir` 에 쓴다.

    엔진이 보드마다 찍는 `[SUCCESS] Exported: <임시 경로>` 는 삼킨다 — 곧 지워질 경로다.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return _build_pages(board, Path(work_dir))


def _build_pages(board, work_dir):
    layers = getattr(board, 'LAYERS', None)
    if not layers:
        raise LayerError('배치.py 에 LAYERS 가 없다 — 완성본마다 (lo, hi, 이름) 층 목록을 둔다')
    pages = []
    for filename, fn in board.FINALS:
        if filename not in layers:
            raise LayerError(f'{filename}: LAYERS 에 층 목록이 없다')
        if 'layer' not in inspect.signature(fn).parameters:
            raise LayerError(f'{filename}: 빌더 {fn.__name__} 가 layer 를 안 받는다 — 시그니처에 '
                             'layer=None 을 더하고 BreadboardRenderer(..., layer=layer) 로 넘긴다')
        final = fn(str(work_dir / filename), None)
        steps = final.sidecar()['steps']
        check_layers(filename, layers[filename], len(steps))
        pages.append(Page(filename, f'{final.title} — 완성본 (목표 그림)', [],
                          list(final.notes), ''))
        stem, total, legend = Path(filename).stem, len(layers[filename]), legend_for(final)
        palette = len(load_renderer().LAYER_PALETTE)
        for i, (lo, hi, label) in enumerate(layers[filename], 1):
            name = f'{stem}_층{i}.png'
            part = fn(str(work_dir / name), None, layer=(lo, hi))
            colors = dict(part.wire_colors)
            if len(colors) > palette:
                raise LayerError(f'{filename}: 층 "{label}" 의 색 신호선이 {len(colors)}가닥인데 팔레트는 '
                                 f'{palette}색이다 — 같은 색이 두 번 나온다. 그 층을 쪼갠다')
            rows = [s for s in steps if lo <= s['n'] <= hi]
            pages.append(Page(name, f'{final.title} — {i}/{total} · {label} ({lo}~{hi}번)',
                              rows, [], legend, colors))
    return pages


def legend_for(final):
    """층 쪽 안내. 칩·LED·저항은 층과 상관없이 모든 쪽에 색으로 그려지므로, 그 보드에 **있는**
    부품만 처음부터 그려 두라고 덧붙인다(실험02 는 LED·저항이 없다)."""
    parts = (['칩'] if final.chips else []) + (['LED', '저항'] if final.led_chains else [])
    if not parts:
        return LEGEND
    return f'{LEGEND} {"·".join(parts)}은 처음부터 그려 두세요.'


def _row(s, colors=None):
    rgba = (colors or {}).get(s['n'])
    style = f' style="color:rgb({rgba[0]},{rgba[1]},{rgba[2]})"' if rgba else ''
    return (f'<tr><td class="n kind-{s["kind"]}"{style}>{s["n"]}</td>'
            f'<td class="hole">{html.escape(s["from"])} → {html.escape(s["to"])}</td>'
            f'<td>{html.escape(s["desc"])}</td></tr>')


def render_html(pages, title):
    body = []
    for p in pages:
        parts = [f'<section class="page"><h1>{html.escape(p.heading)}</h1>']
        if p.legend:
            parts.append(f'<p class="legend">{html.escape(p.legend)}</p>')
        parts.append(f'<img src="{quote(p.image)}" alt="{html.escape(p.heading)}">')
        if p.rows:
            parts.append('<table><thead><tr><th>번호</th><th>홀</th><th>뜻</th></tr></thead><tbody>'
                         + ''.join(_row(s, p.colors) for s in p.rows) + '</tbody></table>')
        if p.notes:
            parts.append('<ul class="notes">'
                         + ''.join(f'<li>{html.escape(t)}</li>' for t in p.notes) + '</ul>')
        parts.append('</section>')
        body.append(''.join(parts))
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>\n'
            + '\n'.join(body) + '\n</body></html>\n')


def make_pdf(board, out):
    """`board` 의 따라 그리기 PDF 를 `out` 에 쓴다. 쪽 수(섹션 수)를 돌려준다.

    임시 폴더에서 만들고 `check_pdf` 를 통과한 뒤에만 `out` 으로 옮긴다 — 넘쳐서 실패해도
    커밋된 PDF 는 그대로 남는다.
    """
    out = Path(out)
    with tempfile.TemporaryDirectory() as d:
        pages = build_pages(board, d)
        html_path = Path(d) / 'guide.html'
        html_path.write_text(render_html(pages, out.stem), encoding='utf-8')
        made = Path(d) / 'guide.pdf'
        html_to_pdf(html_path, made)
        check_pdf(made, pages)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(made, out)
    return len(pages)


def check_pdf(out, pages):
    """섹션 하나가 정확히 한 쪽, 쪽마다 그림 하나인지. 표가 넘치면 그림 없는 쪽이 끼어든다."""
    counts = [len(p.images) for p in PdfReader(str(out)).pages]
    if counts == [1] * len(pages):
        return
    k = next((i for i, c in enumerate(counts) if c != 1), len(pages))
    culprit = pages[max(k - 1, 0)].heading
    raise LayerError(f'PDF 가 {len(counts)}쪽이다(섹션 {len(pages)}개) — {k + 1}쪽에 그림이 없다. '
                     f'"{culprit}" 쪽이 넘쳤다 — 그 층을 둘로 쪼갠다')


def output_path(experiment):
    exp_dir = REPO_ROOT / config.experiment_dir(experiment)
    return config.artifact_path(exp_dir, '따라그리기')


def make_guide(experiment, out=None):
    board = load_renderer().load_board(experiment)
    out = Path(out) if out else output_path(experiment)
    return out, make_pdf(board, out)


def main(argv=None):
    parser = argparse.ArgumentParser(description='완성본 결선도를 층으로 나눈 따라 그리기 PDF')
    parser.add_argument('experiment', type=int, help='실험 번호 (배치.py 에 LAYERS 가 있어야 한다)')
    parser.add_argument('--out', default=None, help='PDF 경로 (기본: config.artifact_path의 팀원전달용 PDF 경로 (실험07부터 제목 포함))')
    args = parser.parse_args(argv)
    try:
        out, n = make_guide(args.experiment, args.out)
    except (LayerError, PdfError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        return 1
    print(f'[SUCCESS] {out} ({n}쪽)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
