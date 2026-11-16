"""손그림 모사 키트 — 실험 하나의 완성본 결선도로 팀원 전달용 PDF 두 개를 낸다(`make-hand-sim`).

- `실험NN_<실험_제목>_손그림모사.pdf` — 빈 판형 PDF 쪽 그대로에 배선만 벡터 펜 선(한 굵기, 은은한 휨)으로 얹은
  것. 칩·LED·저항·입력 이름은 비운다 — 팀원이 이 위에 부품을 그려 넣는다. 제목은 없다 — 실험 이름은
  작성자가 손으로 적는다. 판형 이미지가 원본 그대로라 `review-hand-diagram` 격자 보정이 그대로 된다.
- `실험NN_<실험_제목>_부품그리기.pdf` — 같은 흔들림의 선을 회색으로, 비워 둔 부품만 색으로 그린 안내판 + 부품표.

완성본 하나가 각 PDF 의 한 쪽이고, 회로를 고르지 않으면 명세 항목마다 최종본 하나만 싣는다.
주차 결선 파일(`배치.py`)의 `FINALS` 빌더를 `hand=<시드>` 로 부른다. 시드는 손그림모사 PNG 이름에서 나오므로 다시 뽑아도 같은 그림이다. PNG 는 임시 폴더에서만
만든다 — 도장·사이드카 없는 PNG 가 `결선도/` 에 있으면 검사 도구가 정본으로 읽는다.

    .venv/bin/python -m scripts.lab.hand_sim --experiment 5
"""
import argparse
from contextlib import ExitStack
import hashlib
import html
import inspect
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

import pymupdf
from pypdf import PdfReader

from scripts.lab import config
from scripts.lab.hand_grid import REPO_ROOT, load_renderer
from scripts.lab.html2pdf import html_to_pdf
from scripts.lab.netlist_parser import final_per_item, parse_netlist

# 팀원 전달용 PDF 폴더 — 결선도/ 아래
OUT_DIR = '팀원전달용'

LEGEND = ('회색 선은 이미 그려져 있어요 · 색으로 된 칩·LED·저항·입력 이름만 그리세요 '
          '(칩 핀·LED·저항의 회색 다리도 부품과 함께 그려요)')
LEGEND_PROBE = ' · 계측 접점(점선·원·꼬리표)도 그려요'
LEGEND_DISPLAY = LEGEND.replace('칩·LED', '칩·표시기·LED').replace('칩 핀·LED', '칩·표시기 핀·LED')

# 부품그리기 안내판 — 태블릿 판. 손그림모사는 `board_page` 판
CSS = """
@page { size: 210mm 420mm; margin: 12mm 10mm; }
body { font-family: 'Apple SD Gothic Neo', sans-serif; margin: 0; }
.page { break-after: page; }
.page:last-child { break-after: auto; }
h1 { font-size: 13pt; margin: 0 0 2mm; }
p.legend { font-size: 9.5pt; margin: 0 0 2mm; }
img { display: block; max-width: 100%; margin: 0 auto 2mm; }
/* Windows 글꼴에서도 BCD 부품표 25행과 범례가 396mm 인쇄 영역에 들어간다. */
img.guide { max-height: 220mm; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; }
th, td { border: 1px solid #999; padding: 0.6mm 1.5mm; text-align: left; }
th { background: #eee; }
"""


def hand_seed(filename):
    return int.from_bytes(hashlib.sha256(filename.encode('utf-8')).digest()[:8], 'big')


def output_paths(experiment):
    """(손그림모사 PDF, 부품그리기 PDF) — `결선도/팀원전달용/`."""
    exp_dir = REPO_ROOT / config.experiment_dir(experiment)
    return (config.artifact_path(exp_dir, '손그림모사'),
            config.artifact_path(exp_dir, '부품그리기'))


def guide_rows(bb):
    """안내판 부품표 — (종류, 이름, 자리). 칩 → 표시기 → LED → 저항 → 입력 → 계측, 각각 엔진 기록 순서."""
    def hole(sym):
        return bb._sym_addr(('hole', sym))
    def dip(kind, part):
        return (kind, part['label'], f'{"좌" if part["block"] == "left" else "우"} 블록 · pin 1 = {part["pin1_row"]}행')
    rows = [dip('칩', c) for c in bb.chips]
    rows += [dip('표시기', d) for d in bb.displays]
    rows += [('LED', ch['tag'], f'애노드 {hole(ch["anode"])} · 캐소드 {hole(ch["cathode"])}')
             for ch in bb.led_chains]
    rows += [('저항', r['label'], f'{hole(r["top"])} → {hole(r["bottom"])}')
             for r in bb.resistors]
    rows += [('저항', p['label'], f'{hole(p["ends"][0])} → {hole(p["ends"][1])} · 와이퍼 {hole(p["wiper"])}')
             for p in bb.pots]
    rows += [('입력', i['name'], f'레일 쪽 끝 {bb.addr(*bb._segments[i["seg"]][1][0])} 옆')
             for i in bb.inputs]
    # 그림에 그린 계측 접점만 — `instrument_note`(그릴 자리 없는 접점)는 `sym` 이 없다
    rows += [('계측', p['label'], f'접점 {p["at"]}') for p in bb.probes if 'sym' in p]
    return rows


def legend_for(rows):
    """표시기·계측 접점이 있는 쪽만 범례가 그것을 말한다 — 없는 실험의 PDF 는 그대로다."""
    kinds = {k for k, _, _ in rows}
    legend = LEGEND_DISPLAY if '표시기' in kinds else LEGEND
    return legend + LEGEND_PROBE if '계측' in kinds else legend


def render_final(fn, final_name, work_dir):
    """완성본 하나 → (안내판 bb, 손그림모사 bb, 부품그리기 PNG). 둘은 같은 시드다."""
    if '결선도' not in final_name:
        # 두 PNG 이름이 같아져 안내판이 손그림모사를 덮는다 — 쪽 검사로는 못 잡는다
        raise ValueError(f'완성본 이름에 "결선도" 가 없다: {final_name} — 손그림모사·부품그리기 이름을 못 가른다')
    handout = Path(work_dir) / final_name.replace('결선도', '손그림모사')
    guide = Path(work_dir) / final_name.replace('결선도', '부품그리기')
    seed = hand_seed(handout.name)
    sim_bb = fn(str(handout), hand=seed)
    bb = fn(str(guide), hand=seed, hand_guide=True)
    return bb, sim_bb, guide


def _doc(title, body):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>\n')


def template_pdf(spec):
    """빈 판형 PDF 경로 — 판형 PNG 옆 같은 이름의 .pdf. 없는 판형(v1)이면 None."""
    png = Path(spec.template[0])
    pdf = (png if png.is_absolute() else REPO_ROOT / png).with_suffix('.pdf')
    return pdf if pdf.exists() else None


def board_page(spec):
    """빈 판형 PDF 의 (쪽 크기 pt, 판형 그림 자리 Rect). 손그림모사 쪽을 이 판에 같은 자리로 놓아야
    팀원이 쓰던 빈 판형과 홀이 겹친다. 판형 PDF 가 없는 판형(v1)은 A4 너비에 판형 그림을 꽉 채운다."""
    pdf = template_pdf(spec)
    if pdf is not None:
        with pymupdf.open(pdf) as doc:
            page = doc[0]
            rects = [r for im in page.get_images() for r in page.get_image_rects(im[0])]
            if len(rects) != 1:
                raise ValueError(f'{pdf.name} 에 판형 그림이 {len(rects)}개다 — 하나여야 자리를 안다')
            return page.rect, rects[0]
    w, h = spec.size
    rect = pymupdf.Rect(0, 0, 595, 595 * h / w)
    return rect, rect


def handout_transform(spec):
    """논리 좌표 -> 손그림모사 쪽 pt 변환과 굵기 배율(pt / 논리 px)."""
    _, slot = board_page(spec)
    w, h = spec.size
    sx, sy = slot.width / w, slot.height / h
    return (lambda x, y: (slot.x0 + x * sx, slot.y0 + y * sy)), sx


def make_handout_pdf(spec, bbs, out):
    """빈 판형 쪽 그대로 + 배선 벡터 획. 제목·실험 이름은 작성자가 손으로 적는다."""
    rb = load_renderer()
    size, slot = board_page(spec)
    to_pt, k = handout_transform(spec)
    tpl = template_pdf(spec)
    with ExitStack() as stack:
        doc = stack.enter_context(pymupdf.open())
        tpl_doc = stack.enter_context(pymupdf.open(tpl)) if tpl is not None else None
        for bb in bbs:
            if bb.overlay.getbbox() is not None:
                raise ValueError(f'{bb.title}: 손그림 모드 overlay 에 배선 밖 그림이 남았다 — 벡터 쪽에 못 옮긴다 '
                                 '(instrument 프로브 등). make-hand-sim §넓힐 때 손볼 곳')
            if tpl_doc is not None:
                doc.insert_pdf(tpl_doc, from_page=0, to_page=0)
                page = doc[-1]
            else:
                page = doc.new_page(width=size.width, height=size.height)
                page.insert_image(slot, filename=str(rb._default_template(spec)))
            rb.draw_strokes(page, bb.hand_strokes, to_pt, k)
        doc.save(str(out))
    return out


def render_guide_html(title, pages):
    """`pages` = [(쪽 제목, 이미지 이름, `guide_rows`)]."""
    def table(rows):
        body = ''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(n)}</td><td>{html.escape(at)}</td></tr>'
                       for k, n, at in rows)
        return ('<table><thead><tr><th>종류</th><th>이름</th><th>자리</th></tr></thead>'
                f'<tbody>{body}</tbody></table>')
    return _doc(title, ''.join(
        f'<section class="page"><h1>{html.escape(t)}</h1><p class="legend">{html.escape(legend_for(rows))}</p>'
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
        sim_bbs, guide_pages = [], []
        for name, fn in finals:
            bb, sim_bb, guide = render_final(fn, name, d)
            sim_bbs.append(sim_bb)
            guide_pages.append((f'{bb.title} — 부품 그리기', guide.name, guide_rows(bb)))
        sim_pdf = make_handout_pdf(bb.spec, sim_bbs, d / 'sim.pdf')
        check_pdf(sim_pdf, len(finals))
        page = d / 'guide.html'
        page.write_text(render_guide_html(f'{title} 부품 그리기', guide_pages), encoding='utf-8')
        guide_pdf = d / 'guide.pdf'
        html_to_pdf(page, guide_pdf)
        check_pdf(guide_pdf, len(finals))
        made = [(sim_pdf, Path(handout_out)), (guide_pdf, Path(guide_out))]
        for pdf, out in made:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdf, out)
    return Path(handout_out), Path(guide_out)


def main(argv=None):
    parser = argparse.ArgumentParser(description='완성본 결선도로 손그림모사·부품그리기 PDF 를 낸다')
    parser.add_argument('--experiment', type=int, required=True)
    parser.add_argument('--final', action='append', help='배치.py FINALS 의 완성본 PNG 이름 (생략하면 항목별 최종본)')
    parser.add_argument('--out-dir', default=None, help='출력 폴더 (기본: 결선도/팀원전달용/)')
    args = parser.parse_args(argv)

    all_finals = dict(load_renderer().load_board(args.experiment).FINALS)
    if args.final:
        missing = [n for n in args.final if n not in all_finals]
        if missing:
            raise SystemExit(f'FINALS 에 없는 완성본: {", ".join(missing)} — 가능한 이름: {", ".join(all_finals)}')
        finals = [(n, all_finals[n]) for n in args.final]
    else:
        netlist = REPO_ROOT / config.experiment_dir(args.experiment) / '결선도/netlist.md'
        try:
            finals = final_per_item(parse_netlist(netlist), list(all_finals.items()))
        except ValueError as e:
            raise SystemExit(str(e)) from None
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
