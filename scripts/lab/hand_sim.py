"""손그림 모사 키트 — 실험 하나의 완성본 결선도로 팀원 전달용 PDF 두 개를 낸다(`make-hand-sim`).

- `실험NN_손그림모사.pdf` — 배선만 마커로 그은 것처럼 흔들어 그리고 칩·LED·저항·입력 이름은 비운
  그림. 팀원이 이 위에 부품을 그려 넣는다.
- `실험NN_부품그리기.pdf` — 같은 흔들림의 선을 회색으로, 비워 둔 부품만 색으로 그린 안내판 + 부품표.

완성본 하나가 각 PDF 의 한 쪽이다. 주차 결선 파일(`배치.py`)의 `FINALS` 빌더를 `hand=<시드>` 로
부른다. 시드는 손그림모사 PNG 이름에서 나오므로 다시 뽑아도 같은 그림이다. PNG 는 임시 폴더에서만
만든다 — 도장·사이드카 없는 PNG 가 `결선도/` 에 있으면 검사 도구가 정본으로 읽는다.

    .venv/bin/python -m scripts.lab.hand_sim --experiment 5
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

from scripts.lab import config
from scripts.lab.hand_grid import REPO_ROOT, load_renderer
from scripts.lab.html2pdf import html_to_pdf
from scripts.lab.trace_guide import OUT_DIR

LEGEND = ('회색 선은 이미 그려져 있어요 · 색으로 된 칩·LED·저항·입력 이름만 그리세요 '
          '(칩 핀·LED·저항의 회색 다리도 부품과 함께 그려요)')

# 태블릿 판 — 따라그리기(`trace_guide`)와 같다
CSS = """
@page { size: 210mm 420mm; margin: 12mm 10mm; }
body { font-family: 'Apple SD Gothic Neo', sans-serif; margin: 0; }
.page { break-after: page; }
.page:last-child { break-after: auto; }
h1 { font-size: 13pt; margin: 0 0 2mm; }
p.legend { font-size: 9.5pt; margin: 0 0 2mm; }
img { display: block; max-width: 100%; margin: 0 auto 2mm; }
img.sim { max-height: 390mm; }
img.guide { max-height: 230mm; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; }
th, td { border: 1px solid #999; padding: 0.6mm 1.5mm; text-align: left; }
th { background: #eee; }
"""


def hand_seed(filename):
    return int.from_bytes(hashlib.sha256(filename.encode('utf-8')).digest()[:8], 'big')


def output_paths(experiment):
    """(손그림모사 PDF, 부품그리기 PDF) — `결선도/팀원전달용/`."""
    folder = config.experiment_folder_name(experiment)
    base = REPO_ROOT / config.experiment_dir(experiment) / '결선도' / OUT_DIR
    return base / f'{folder}_손그림모사.pdf', base / f'{folder}_부품그리기.pdf'


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


def render_final(fn, final_name, work_dir):
    """완성본 하나 → (안내판 bb, 손그림모사 PNG, 부품그리기 PNG). 둘은 같은 시드다."""
    handout = Path(work_dir) / final_name.replace('결선도', '손그림모사')
    guide = Path(work_dir) / final_name.replace('결선도', '부품그리기')
    seed = hand_seed(handout.name)
    fn(str(handout), hand=seed)
    bb = fn(str(guide), hand=seed, hand_guide=True)
    return bb, handout, guide


def _doc(title, body):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>\n')


def render_handout_html(title, pages):
    """`pages` = [(쪽 제목, 이미지 이름)]."""
    return _doc(title, ''.join(
        f'<section class="page"><h1>{html.escape(t)}</h1>'
        f'<img class="sim" src="{quote(img)}" alt="{html.escape(t)}"></section>'
        for t, img in pages))


def render_guide_html(title, pages):
    """`pages` = [(쪽 제목, 이미지 이름, `guide_rows`)]."""
    def table(rows):
        body = ''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(n)}</td><td>{html.escape(at)}</td></tr>'
                       for k, n, at in rows)
        return ('<table><thead><tr><th>종류</th><th>이름</th><th>자리</th></tr></thead>'
                f'<tbody>{body}</tbody></table>')
    return _doc(title, ''.join(
        f'<section class="page"><h1>{html.escape(t)}</h1><p class="legend">{html.escape(LEGEND)}</p>'
        f'<img class="guide" src="{quote(img)}" alt="{html.escape(t)}">{table(rows)}</section>'
        for t, img, rows in pages))


def check_pdf(path, n):
    """완성본 `n` 장에 한 쪽씩, 쪽마다 그림 하나 — 표나 그림이 넘치면 쪽이 늘어난다."""
    path = Path(path)
    counts = [len(p.images) for p in PdfReader(str(path)).pages]
    if counts != [1] * n:
        raise ValueError(f'{path.name} 가 {len(counts)}쪽(쪽별 그림 {counts})이다 — '
                         f'완성본 {n}장에 한 쪽씩이어야 한다')


def make_pdfs(finals, handout_out, guide_out, title):
    """임시 폴더에서 두 PDF 를 만들고 둘 다 `check_pdf` 를 통과한 뒤에만 `out` 으로 옮긴다."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        sim_pages, guide_pages = [], []
        for name, fn in finals:
            bb, handout, guide = render_final(fn, name, d)
            sim_pages.append((bb.title, handout.name))
            guide_pages.append((f'{bb.title} — 부품 그리기', guide.name, guide_rows(bb)))
        made = []
        for kind, html_text, out in (
                ('sim', render_handout_html(f'{title} 손그림모사', sim_pages), handout_out),
                ('guide', render_guide_html(f'{title} 부품 그리기', guide_pages), guide_out)):
            page = d / f'{kind}.html'
            page.write_text(html_text, encoding='utf-8')
            pdf = d / f'{kind}.pdf'
            html_to_pdf(page, pdf)
            check_pdf(pdf, len(finals))
            made.append((pdf, Path(out)))
        for pdf, out in made:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdf, out)
    return Path(handout_out), Path(guide_out)


def main(argv=None):
    parser = argparse.ArgumentParser(description='완성본 결선도로 손그림모사·부품그리기 PDF 를 낸다')
    parser.add_argument('--experiment', type=int, required=True)
    parser.add_argument('--final', action='append', help='배치.py FINALS 의 완성본 PNG 이름 (생략하면 전부)')
    parser.add_argument('--out-dir', default=None, help='출력 폴더 (기본: 결선도/팀원전달용/)')
    args = parser.parse_args(argv)

    all_finals = dict(load_renderer().load_board(args.experiment).FINALS)
    names = args.final or list(all_finals)
    missing = [n for n in names if n not in all_finals]
    if missing:
        raise SystemExit(f'FINALS 에 없는 완성본: {", ".join(missing)} — 가능한 이름: {", ".join(all_finals)}')
    finals = [(n, all_finals[n]) for n in names]
    # 그리기 전에 전부 본다 — 앞 완성본만 뽑고 터지지 않게
    lacking = [fn.__name__ for _, fn in finals if 'hand_guide' not in inspect.signature(fn).parameters]
    if lacking:
        raise SystemExit(f'{", ".join(lacking)} 가 hand_guide 를 안 받는다 — '
                         'make-hand-sim 스킬 §빌더 단계로 배치.py 에 인자를 단다')
    sim_out, guide_out = output_paths(args.experiment)
    if args.out_dir:
        sim_out, guide_out = Path(args.out_dir) / sim_out.name, Path(args.out_dir) / guide_out.name
    try:
        return make_pdfs(finals, sim_out, guide_out, config.experiment_folder_name(args.experiment))
    except ValueError as e:
        raise SystemExit(str(e)) from None


if __name__ == '__main__':
    main()
