"""손그림 모사 시험판 — 완성본 결선도 한 장을 배선만 마커로 그은 것처럼 흔들어 그린다.

주차 결선 파일(`배치.py`)의 `FINALS` 에서 이름이 같은 빌더를 `hand=<시드>` 로 부른다. 시드는
출력 파일 이름에서 나오므로 다시 뽑아도 같은 그림이다. 사이드카·도장은 없다.

    .venv/bin/python -m scripts.lab.hand_sim --experiment 4 --final 실험04_1-1_결선도_4x1MUX.png

`--guide` 를 주면 팀원 전달용 **부품 그리기 안내판**도 낸다 — 같은 흔들림의 선을 회색으로,
시험판에서 비워 둔 칩·LED·저항·입력 이름을 색으로 그린 PNG 와, 그 그림·부품표를 실은 A4 한 쪽
PDF(2026-10-12).
"""
import argparse
import hashlib
import html
import inspect
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from pypdf import PdfReader

from scripts.lab.hand_grid import REPO_ROOT, load_renderer
from scripts.lab.html2pdf import html_to_pdf

LEGEND = ('회색 선은 이미 그려져 있어요 · 색으로 된 칩·LED·저항·입력 이름만 그리세요 '
          '(칩 핀·LED·저항의 회색 다리도 부품과 함께 그려요)')

CSS = """
@page { size: A4; margin: 10mm; }
body { font-family: 'Apple SD Gothic Neo', sans-serif; margin: 0; }
h1 { font-size: 13pt; margin: 0 0 2mm; }
p.legend { font-size: 9.5pt; margin: 0 0 2mm; }
img { display: block; max-width: 100%; max-height: 185mm; margin: 0 auto 2mm; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; }
th, td { border: 1px solid #999; padding: 0.6mm 1.5mm; text-align: left; }
th { background: #eee; }
"""


def hand_seed(filename):
    return int.from_bytes(hashlib.sha256(filename.encode('utf-8')).digest()[:8], 'big')


def guide_rows(bb):
    """안내판 부품표 — (종류, 이름, 자리). 칩 → LED → 저항 → 입력, 각각 엔진 기록 순서."""
    def hole(sym):
        return bb._sym_addr(('hole', sym))
    rows = [('칩', c['label'], f'{"좌" if c["block"] == "left" else "우"} 블록 · pin 1 = {c["pin1_row"]}행')
            for c in bb.chips]
    rows += [('LED', ch['tag'], f'애노드 {hole(ch["anode"])} · 캐소드 {hole(ch["cathode"])}')
             for ch in bb.led_chains]
    rows += [('저항', r['label'], f'{hole(r["top"])} → {hole(r["bottom"])}')
             for r in bb.resistors]
    rows += [('입력', i['name'], f'레일 쪽 끝 {bb.addr(*bb._segments[i["seg"]][1][0])} 옆')
             for i in bb.inputs]
    return rows


def render_guide_html(title, image_name, rows):
    body = ''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(n)}</td><td>{html.escape(at)}</td></tr>'
                   for k, n, at in rows)
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>'
            f'<h1>{html.escape(title)}</h1><p class="legend">{html.escape(LEGEND)}</p>'
            f'<img src="{quote(image_name)}" alt="{html.escape(title)}">'
            '<table><thead><tr><th>종류</th><th>이름</th><th>자리</th></tr></thead>'
            f'<tbody>{body}</tbody></table></body></html>\n')


def check_guide_pdf(path):
    """정확히 한 쪽, 그림 하나 — 표가 넘치면 쪽이 늘어난다."""
    counts = [len(p.images) for p in PdfReader(str(path)).pages]
    if counts != [1]:
        raise ValueError(f'안내 PDF 가 {len(counts)}쪽(쪽별 그림 {counts})이다 — 한 쪽에 그림 하나여야 한다')


def make_guide_pdf(bb, png, out):
    """임시 폴더에서 만들고 `check_guide_pdf` 를 통과한 뒤에만 `out` 으로 옮긴다."""
    with tempfile.TemporaryDirectory() as d:
        shutil.copyfile(png, Path(d) / png.name)
        page = Path(d) / 'guide.html'
        page.write_text(render_guide_html(f'{bb.title} — 부품 그리기', png.name, guide_rows(bb)),
                        encoding='utf-8')
        made = Path(d) / 'guide.pdf'
        html_to_pdf(page, made)
        check_guide_pdf(made)
        shutil.copyfile(made, out)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description='완성본 결선도 한 장을 손그림 모사로 뽑는다')
    parser.add_argument('--experiment', type=int, required=True)
    parser.add_argument('--final', required=True, help='배치.py FINALS 의 완성본 PNG 이름')
    parser.add_argument('--out', default=str(REPO_ROOT / 'tmp/hand-sim'))
    parser.add_argument('--guide', action='store_true', help='부품 그리기 안내 PNG·PDF 도 낸다')
    args = parser.parse_args(argv)

    finals = dict(load_renderer().load_board(args.experiment).FINALS)
    if args.final not in finals:
        raise SystemExit(f'FINALS 에 없는 완성본: {args.final} — 가능한 이름: {", ".join(finals)}')
    fn = finals[args.final]
    if args.guide and 'hand_guide' not in inspect.signature(fn).parameters:
        raise SystemExit(f'{args.final}: 빌더 {fn.__name__} 가 hand_guide 를 안 받는다 — '
                         '지금은 실험04 MUX 만 된다')
    out = Path(args.out) / args.final.replace('결선도', '손그림모사')
    seed = hand_seed(out.name)
    fn(str(out), hand=seed)
    if not args.guide:
        return out
    guide_png = Path(args.out) / args.final.replace('결선도', '부품그리기')
    bb = fn(str(guide_png), hand=seed, hand_guide=True)
    pdf = make_guide_pdf(bb, guide_png, guide_png.with_suffix('.pdf'))
    return out, guide_png, pdf


if __name__ == '__main__':
    main()
