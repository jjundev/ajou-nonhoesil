"""따라 그리기 PDF — 완성본 결선도를 층으로 나눠 팀원이 한 쪽씩 옮겨 그리게 한다.

주차 결선 파일(`배치.py`)의 `FINALS` 와 `LAYERS` 를 읽는다. 완성본 한 장마다 0쪽(완성본
전체 + notes)과 층마다 한 쪽을 낸다. 층 그림은 엔진 `layer=(lo, hi)` 로 그린다 — 앞 층
회색, 이번 층 색·완성본 번호, 뒤 층은 안 보인다. 표는 완성본 사이드카 `steps` 에서 그 층
번호만 고른다. 조립 절차(`BOARDS`)는 쓰지 않는다 — 임시 급전선이 손그림에 섞인다.

층 PNG 는 임시 폴더에만 둔다. 커밋하는 것은 PDF 한 개다.

    .venv/bin/python -m scripts.lab.trace_guide 4
"""
import argparse
import html
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from scripts.lab import config
from scripts.lab.hand_grid import load_renderer
from scripts.lab.html2pdf import PdfError, html_to_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = '팀원전달용'
LEGEND = ('회색 선은 앞 쪽에서 이미 그렸어요. 이번 쪽에서는 색 선만 번호 순서대로 그려요. '
          '칩·LED·저항은 처음부터 그려 두세요.')

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
    legend: bool      # 층 쪽 안내 한 줄


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
    """완성본마다 0쪽 + 층 쪽. 그림과 사이드카는 `work_dir` 에 쓴다."""
    work_dir = Path(work_dir)
    layers = getattr(board, 'LAYERS', None)
    if not layers:
        raise LayerError('배치.py 에 LAYERS 가 없다 — 완성본마다 (lo, hi, 이름) 층 목록을 둔다')
    pages = []
    for filename, fn in board.FINALS:
        if filename not in layers:
            raise LayerError(f'{filename}: LAYERS 에 층 목록이 없다')
        final = fn(str(work_dir / filename), None)
        steps = final.sidecar()['steps']
        check_layers(filename, layers[filename], len(steps))
        pages.append(Page(filename, f'{final.title} — 완성본 (목표 그림)', [],
                          list(final.notes), False))
        stem, total = Path(filename).stem, len(layers[filename])
        for i, (lo, hi, label) in enumerate(layers[filename], 1):
            name = f'{stem}_층{i}.png'
            fn(str(work_dir / name), None, layer=(lo, hi))
            rows = [s for s in steps if lo <= s['n'] <= hi]
            pages.append(Page(name, f'{final.title} — {i}/{total} · {label} ({lo}~{hi}번)',
                              rows, [], True))
    return pages


def _row(s):
    return (f'<tr><td class="n kind-{s["kind"]}">{s["n"]}</td>'
            f'<td class="hole">{html.escape(s["from"])} → {html.escape(s["to"])}</td>'
            f'<td>{html.escape(s["desc"])}</td></tr>')


def render_html(pages, title):
    body = []
    for p in pages:
        parts = [f'<section class="page"><h1>{html.escape(p.heading)}</h1>']
        if p.legend:
            parts.append(f'<p class="legend">{html.escape(LEGEND)}</p>')
        parts.append(f'<img src="{quote(p.image)}" alt="{html.escape(p.heading)}">')
        if p.rows:
            parts.append('<table><thead><tr><th>번호</th><th>홀</th><th>뜻</th></tr></thead><tbody>'
                         + ''.join(_row(s) for s in p.rows) + '</tbody></table>')
        if p.notes:
            parts.append('<ul class="notes">'
                         + ''.join(f'<li>{html.escape(t)}</li>' for t in p.notes) + '</ul>')
        parts.append('</section>')
        body.append(''.join(parts))
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>\n'
            + '\n'.join(body) + '\n</body></html>\n')


def make_pdf(board, out):
    """`board` 의 따라 그리기 PDF 를 `out` 에 쓴다. 쪽 수(섹션 수)를 돌려준다."""
    out = Path(out)
    with tempfile.TemporaryDirectory() as d:
        pages = build_pages(board, d)
        html_path = Path(d) / 'guide.html'
        html_path.write_text(render_html(pages, out.stem), encoding='utf-8')
        html_to_pdf(html_path, out)
    return len(pages)


def output_path(experiment):
    folder = config.experiment_folder_name(experiment)
    return (REPO_ROOT / config.experiment_dir(experiment) / '결선도' / OUT_DIR
            / f'{folder}_따라그리기.pdf')


def make_guide(experiment, out=None):
    board = load_renderer().load_board(experiment)
    out = Path(out) if out else output_path(experiment)
    return out, make_pdf(board, out)


def main(argv=None):
    parser = argparse.ArgumentParser(description='완성본 결선도를 층으로 나눈 따라 그리기 PDF')
    parser.add_argument('experiment', type=int, help='실험 번호 (배치.py 에 LAYERS 가 있어야 한다)')
    parser.add_argument('--out', default=None, help='PDF 경로 (기본: 결선도/팀원전달용/실험NN_따라그리기.pdf)')
    args = parser.parse_args(argv)
    try:
        out, n = make_guide(args.experiment, args.out)
    except (LayerError, PdfError, FileNotFoundError) as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        return 1
    print(f'[SUCCESS] {out} ({n}쪽)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
