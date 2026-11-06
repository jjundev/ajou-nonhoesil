"""실물 브레드보드 사진을 체크리스트 단계의 참조 결선과 대조한다.

손그림 검토(`hand_compare`)의 실물판이다. 판정 코드는 그대로 쓰고, 사진에서 홀 주소를 읽는
앞단만 새로 만든다.

**왜 격자를 덮는가.** 2026-11-07 실험08 영상 프레임 판독 시험에서 LED–저항 연결점 4곳 중
0곳을 확정했다. 행 번호가 5칸마다만 찍혀 있어 구멍을 **세다가** 한 행씩 어긋났고, 판독 어긋남과
결선 어긋남을 가를 수 없었다. 그래서 세지 않게 한다 — 사람(vision)은 인쇄된 행 번호 옆 홀
네 곳 이상의 픽셀 좌표만 짚고, 코드가 호모그래피로 모든 홀에 주소를 찍는다. 전사자는 리드가
들어간 점의 라벨을 **읽기만** 한다.

**왜 참조를 늦게 여는가.** 참조를 보며 읽으면 애매한 자리를 정답 쪽으로 읽는다(같은 시험).
`judge` 만 참조를 열고, 격자·전사 단계는 참조 없이 돈다.

좌표계: 단자대 한 블록 안에서 a~e 는 0~4, f~j 는 7~11(가운데 홈이 0.3인치 = 3피치), 행은
행 번호 그대로다. 레일은 판마다 블록과의 간격이 달라 격자에 넣지 않는다 — 레일은 극성만
판정에 쓰이고(`hand_compare.signatures`) 행은 H1 빈 행 검사에만 쓰인다.
"""

import contextlib
import io
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import hand_compare as hc
from .hand_grid import expected_board, load_renderer
from .hand_transcript import TranscriptError, parse_address, parse_transcript

COL_X = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 7, 'g': 8, 'h': 9, 'i': 10, 'j': 11}
BLOCK_NAMES = {'left': '좌', 'right': '우'}
MAX_RESIDUAL = 0.35      # 앵커 재투영 오차 상한(피치 단위). 넘으면 앵커를 다시 짚는다
TARGET_PITCH = 60        # 격자 그림에서 홀 간격(px) — 라벨 'f12' 가 겹치지 않는 크기

# 사진 판정에서 빼는 규칙. 손그림 종이의 표기 검사라 실물에는 뜻이 없다.
# H11 제목, H15 신호 이름 표기(실물 보드에는 글자가 없다).
PHOTO_SKIP = frozenset({'H11', 'H15'})


class PhotoGridError(ValueError):
    """앵커로 격자를 세울 수 없다."""


# ---------------------------------------------------------------- 사진·좌표

def load_photo(path):
    """휴대폰 사진은 EXIF 회전을 달고 온다 — 펴서 연다. 픽셀 좌표는 늘 이 펴진 그림 기준이다."""
    im = Image.open(path)
    return ImageOps.exif_transpose(im).convert('RGB')


def _font(size):
    # 한글 머리말이 네모로 깨지지 않게 한글 글꼴을 먼저 찾는다. LAB_VIDEO_FONT 는 영상 스킬과 같은 변수다
    names = [os.environ.get('LAB_VIDEO_FONT', ''), 'malgun.ttf', 'C:/Windows/Fonts/malgun.ttf',
             'NanumGothic.ttf', 'AppleSDGothicNeo.ttc', 'NotoSansCJK-Regular.ttc', 'arial.ttf', 'DejaVuSans.ttf']
    for name in filter(None, names):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def ruler(photo_path, out_path, crop=None, step=None, max_side=1600):
    """픽셀 눈금을 덮은 그림. 앵커 좌표를 **원본 픽셀**로 읽게 한다.

    Read 도구는 큰 사진을 줄여 보여 준다 — 화면 좌표를 원본으로 옮기다 틀리지 않게
    눈금 숫자가 원본 좌표다. `crop=(x0, y0, x1, y1)` 로 한 구역만 키운다.
    """
    im = load_photo(photo_path)
    x0, y0, x1, y1 = crop or (0, 0, im.width, im.height)
    region = im.crop((x0, y0, x1, y1))
    scale = min(max_side / max(region.size), 6.0)
    region = region.resize((round(region.width * scale), round(region.height * scale)), Image.LANCZOS)
    if step is None:
        span = max(x1 - x0, y1 - y0)
        step = next(s for s in (10, 20, 25, 50, 100, 200, 250, 500, 1000) if span / s <= 16)
    d = ImageDraw.Draw(region)
    f = _font(max(12, round(region.width / 70)))
    for x in range((x0 // step + 1) * step, x1, step):
        px = (x - x0) * scale
        d.line([(px, 0), (px, region.height)], fill=(0, 200, 255), width=1)
        d.text((px + 2, 2), str(x), fill=(0, 120, 255), font=f)
    for y in range((y0 // step + 1) * step, y1, step):
        py = (y - y0) * scale
        d.line([(0, py), (region.width, py)], fill=(255, 0, 200), width=1)
        d.text((2, py + 2), str(y), fill=(200, 0, 160), font=f)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    region.save(out_path)
    return out_path


def logical(addr, board='v2'):
    """'우 f12' -> ('right', 7, 12). 단자대 홀만 받는다."""
    kind, hole = parse_address(addr, board)
    if kind != 'hole' or hole[1] not in COL_X:
        raise PhotoGridError(f'앵커는 단자대 홀이어야 한다(레일·잭 불가): {addr!r}')
    block, col, row = hole
    return block, COL_X[col], row


def _normalize(pts):
    pts = np.asarray(pts, dtype=float)
    c = pts.mean(axis=0)
    s = np.sqrt(2) / max(np.mean(np.linalg.norm(pts - c, axis=1)), 1e-9)
    T = np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1]])
    return T, (np.c_[pts, np.ones(len(pts))] @ T.T)


def _dlt(src, dst):
    """src(논리) -> dst(픽셀) 호모그래피. 정규화 DLT."""
    Ts, s = _normalize(src)
    Td, d = _normalize(dst)
    rows = []
    for (x, y, _), (u, v, _) in zip(s, d):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    A = np.array(rows)
    _, sv, vt = np.linalg.svd(A)
    if sv[-2] < 1e-6 * sv[0]:
        raise PhotoGridError('앵커가 한 줄에 몰려 있다 — 행과 열이 모두 다른 홀을 고른다')
    H = np.linalg.inv(Td) @ vt[-1].reshape(3, 3) @ Ts
    return H / H[2, 2]


def project(H, pts):
    pts = np.asarray(pts, dtype=float)
    p = np.c_[pts, np.ones(len(pts))] @ H.T
    return p[:, :2] / p[:, 2:3]


@dataclass
class Grid:
    """사진 한 장·블록 하나의 격자."""
    photo: str
    block: str
    H: np.ndarray
    pitch: float          # 앵커 근처 홀 간격(px)
    residual: float       # 앵커 재투영 최대 오차(피치)

    def pixel(self, col, row):
        return tuple(project(self.H, [(COL_X[col], row)])[0])


def fit_grid(photo, anchors, board='v2'):
    """앵커 [{'px': [x, y], 'hole': '우 f5'}, ...] (네 개 이상, 한 블록) -> `Grid`.

    재투영 오차가 `MAX_RESIDUAL` 피치를 넘으면 거절한다 — 짚은 좌표나 라벨 중 하나가
    틀린 것이다. 추측으로 넘어가지 않는다.
    """
    if len(anchors) < 4:
        raise PhotoGridError(f'앵커가 {len(anchors)}개다 — 네 개 이상 짚는다(다섯 개 이상 권장)')
    logi = [logical(a['hole'], board) for a in anchors]
    blocks = {b for b, _x, _y in logi}
    if len(blocks) != 1:
        raise PhotoGridError(f'앵커가 여러 블록에 걸친다: {sorted(blocks)} — 블록마다 따로 세운다')
    src = [(x, y) for _b, x, y in logi]
    dst = [a['px'] for a in anchors]
    if len({x for x, _ in src}) < 2 or len({y for _, y in src}) < 2:
        raise PhotoGridError('앵커의 열이나 행이 하나뿐이다 — 네 모서리처럼 퍼뜨린다')
    H = _dlt(src, dst)
    back = project(H, src)
    step = project(H, [(x + 1, y) for x, y in src]) - back
    pitch = float(np.mean(np.linalg.norm(step, axis=1)))
    err = np.linalg.norm(back - np.asarray(dst, float), axis=1) / pitch
    worst = int(np.argmax(err))
    if err[worst] > MAX_RESIDUAL:
        raise PhotoGridError(
            f"앵커가 서로 안 맞는다 — {anchors[worst]['hole']} 가 {err[worst]:.2f} 피치 벗어난다 "
            f'(상한 {MAX_RESIDUAL}). 그 앵커의 좌표나 주소를 다시 짚는다')
    return Grid(str(photo), blocks.pop(), H, pitch, float(err.max()))


def overlay(grid, out_dir, name, rows=None, margin=2.0):
    """격자 그림과 같은 자리의 맨 그림 한 쌍을 쓴다. 돌려주는 값은 두 경로.

    맨 그림을 같이 내는 이유: 점과 라벨이 리드가 들어간 자리를 가린다. 두 장을 번갈아
    본다. `rows=(시작, 끝)` 으로 행 구간을 자른다.
    """
    im = load_photo(grid.photo)
    r0, r1 = rows or (1, 63)
    pts = {(c, r): grid.pixel(c, r) for c in COL_X for r in range(r0, r1 + 1)}
    inside = {k: p for k, p in pts.items()
              if -grid.pitch <= p[0] <= im.width + grid.pitch and -grid.pitch <= p[1] <= im.height + grid.pitch}
    if not inside:
        raise PhotoGridError(f'{r0}~{r1}행이 사진 밖이다')
    xs = [p[0] for p in inside.values()]
    ys = [p[1] for p in inside.values()]
    m = margin * grid.pitch
    box = (max(0, int(min(xs) - m)), max(0, int(min(ys) - m)),
           min(im.width, int(max(xs) + m)), min(im.height, int(max(ys) + m)))
    scale = max(1.0, min(TARGET_PITCH / grid.pitch, 8.0))
    plain = im.crop(box)
    plain = plain.resize((round(plain.width * scale), round(plain.height * scale)), Image.LANCZOS)
    marked = plain.copy()
    layer = Image.new('RGBA', marked.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    p = grid.pitch * scale
    small, big = _font(max(9, round(p * 0.26))), _font(max(12, round(p * 0.45)))
    rad = p * 0.16

    def at(c, r):
        x, y = inside[(c, r)]
        return (x - box[0]) * scale, (y - box[1]) * scale

    for (c, r) in inside:
        x, y = at(c, r)
        five = r % 5 == 0
        color = (255, 40, 40, 230) if five else (0, 220, 255, 200)
        d.ellipse([x - rad, y - rad, x + rad, y + rad], outline=color, width=2)
        d.text((x + rad + 1, y - rad - p * 0.30), f'{c}{r}', fill=(255, 255, 0, 235), font=small,
               stroke_width=2, stroke_fill=(0, 0, 0, 235))
    block = BLOCK_NAMES[grid.block]
    for r in range(r0, r1 + 1):
        if r % 5 == 0 and ('a', r) in inside and ('j', r) in inside:
            for c, dx in (('a', -p * 1.2), ('j', p * 0.5)):
                x, y = at(c, r)
                d.text((x + dx, y - p * 0.25), str(r), fill=(255, 60, 60, 255), font=big,
                       stroke_width=2, stroke_fill=(0, 0, 0, 255))
    d.text((6, 6), f'{block} 블록 · 앵커 오차 최대 {grid.residual:.2f} 피치', fill=(255, 255, 255, 255),
           font=big, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    marked = Image.alpha_composite(marked.convert('RGBA'), layer).convert('RGB')
    os.makedirs(out_dir, exist_ok=True)
    a, b = os.path.join(out_dir, f'{name}_격자.png'), os.path.join(out_dir, f'{name}_맨.png')
    marked.save(a)
    plain.save(b)
    return a, b


def grids_from_file(anchor_path, board='v2'):
    """앵커 파일 -> [(이름, Grid, rows)]. 모양은 SKILL.md 의 `앵커.json`."""
    obj = json.loads(Path(anchor_path).read_text(encoding='utf-8'))
    out = []
    for g in obj['grids']:
        grid = fit_grid(g['photo'], g['anchors'], board)
        out.append((g['name'], grid, tuple(g['rows']) if g.get('rows') else None))
    return out


# ---------------------------------------------------------------- 단계 참조

def _quiet(fn, *a, **k):
    """빌더는 [SUCCESS]·[WARN] 을 찍는다 — 판정 출력에 섞이지 않게 삼킨다."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def stage_names(experiment):
    """체크리스트 순서대로 사진 판정이 되는 단계 이름(.png 뺀 파일명). 걷기 보드는 빠진다 —
    선을 뽑은 뒤의 상태는 다음 단계 사진으로 본다."""
    return [n for n, _f in _stage_builders(experiment)]


def _stage_builders(experiment):
    mod = load_renderer()
    board = mod.load_board(experiment)
    out = []
    for filename, fn, stage, is_assembly in mod.iter_procedure_boards(board):
        name = filename[:-4] if filename.endswith('.png') else filename
        if is_assembly:
            out.append((name, lambda p, f=fn: f(p)))
        elif stage is not None:
            out.append((name, lambda p, f=fn, s=stage: f(p, stage=s)))
    for filename, fn in getattr(board, 'FINALS', []):
        name = filename[:-4] if filename.endswith('.png') else filename
        out.append((name, lambda p, f=fn: f(p)))
    return out


def resolve_stage(experiment, query):
    """'2단계_Y0' · '1준비_2' · 전체 파일명 -> 단계 이름 하나. 여럿이면 후보를 들고 거절한다."""
    names = stage_names(experiment)
    q = query[:-4] if query.endswith('.png') else query
    if q in names:
        return q
    hits = [n for n in names if n.endswith('_' + q)] or [n for n in names if q in n]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise hc.CompareError(f'단계 {query!r} 가 없다. 후보:\n  ' + '\n  '.join(names))
    raise hc.CompareError(f'단계 {query!r} 가 여럿과 맞는다:\n  ' + '\n  '.join(hits))


def stage_reference(experiment, name):
    """그 단계를 마친 보드 상태의 참조 `Diagram`(누적)."""
    builders = dict(_stage_builders(experiment))
    if name not in builders:
        raise hc.CompareError(f'단계 {name!r} 가 없다')
    with tempfile.TemporaryDirectory() as tmp:
        bb = _quiet(builders[name], os.path.join(tmp, 'ref.png'))
    w = bb.wiring()
    ref = hc._from_wiring(w, name, bb.board)
    # 입력(CLK·R0 …)은 참조에서 레일 -> 스트립 점퍼다. 실물에서는 함수발생기 집게일 수 있어
    # 전사의 `external` 을 이 레일 끝으로 바꿔 넣는다(`normalize_transcript`)
    ref.photo_inputs = {}
    for inp in w.get('inputs', []):
        for x in ref.wires:
            ends = [x['frm'], x['to']]
            if ('hole', inp['at']) in ends:
                other = ends[1] if ends[0] == ('hole', inp['at']) else ends[0]
                if other[0] == 'hole' and other[1][1] in hc.RAIL_COLS:
                    ref.photo_inputs[inp['name']] = other[1]
    return ref


# ---------------------------------------------------------------- 전사 정규화

def normalize_transcript(obj, ref, board='v2'):
    """사진 전사 -> `parse_transcript` 가 받는 모양. (정규화한 dict, 알림 목록)

    사진 전사가 손그림 전사와 다른 두 가지를 여기서 메운다.

    1. **LED 극성.** 꽂힌 LED 는 긴 다리가 안 보인다. 극성을 못 읽은 LED 는
       `"legs": [주소, 주소]` 로 적는다. 저항 다리와 한 줄인 다리를 캐소드로 놓고
       '극성 미확인' 알림을 남긴다 — 사람이 평평한 테두리를 눈으로 본다.
    2. **LED 꼬리표.** 전사자는 참조를 안 보므로 Y0·Y1 같은 이름을 모른다. 위에서부터
       `P1`·`P2`… 로 적으면, 애노드가 닿는 칩 핀이 같은 참조 LED 이름으로 바꾸고,
       핀으로 못 가린 것은 행 순서로 맞춘다. 바꾼 대응을 알림에 남긴다.
    """
    obj = json.loads(json.dumps(obj))
    notes = []
    for key in ('page', 'circuit'):
        obj.setdefault(key, 1 if key == 'page' else ref.circuit)
    leds = obj.get('leds', [])
    res = obj.get('resistors', [])

    # 0. 보드 밖 신호원 — 참조처럼 레일 입력으로 놓는다. 입력 핀 서명이 레일 극성으로 접히므로
    # 집게든 레일 점퍼든 같은 뜻이다. 참조에 없는 이름은 그 홀을 보류로 둔다
    inputs = getattr(ref, 'photo_inputs', {})
    for ext in obj.pop('external', []):
        name, at = ext['name'], ext['at']
        rail = inputs.get(name)
        if rail is None:
            obj.setdefault('uncertain', []).append(at)
            notes.append(f'보드 밖 신호 {name!r}({at}) 는 이 단계 참조 입력({", ".join(inputs) or "없음"})에 없다 — 보류')
            continue
        obj.setdefault('wires', []).append({'from': hc._addr(rail, board), 'to': at, 'desc': f'보드 밖 {name}'})
        notes.append(f'{name}: 보드 밖 신호원({at})을 참조처럼 레일 입력으로 놓고 대조했다')

    def strip(addr):
        kind, hole = parse_address(addr, board)
        return hc.node_of(hole) if kind == 'hole' else ('J', hole)

    # 1. 극성 — 저항 다리가 앉은 스트립(점퍼로 이어진 것까지)과 같은 넷인 다리가 캐소드
    probe = dict(obj, leds=[], resistors=[])
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'probe.json'
        p.write_text(json.dumps(probe, ensure_ascii=False), encoding='utf-8')
        nets = hc.build_nets(parse_transcript(p, board=board))
    res_nets = {nets.get(strip(r[k]), strip(r[k])) for r in res for k in ('top', 'bottom')}
    for led in leds:
        if 'legs' not in led:
            continue
        a, b = led.pop('legs')
        na, nb = nets.get(strip(a), strip(a)), nets.get(strip(b), strip(b))
        if (na in res_nets) == (nb in res_nets):
            led['anode'], led['cathode'] = a, b
            obj.setdefault('uncertain', []).extend([a, b])
            notes.append(f"{led['tag']}: 극성 미확인이고 어느 다리가 저항 쪽인지도 갈리지 않는다 — {a}·{b} 를 보류로 둔다")
        else:
            led['anode'], led['cathode'] = (b, a) if na in res_nets else (a, b)
            notes.append(f"{led['tag']}: 극성 미확인 — 저항 쪽 다리 {led['cathode']} 를 캐소드로 놓았다. "
                         'LED 테두리의 평평한 쪽이 그 다리인지 눈으로 확인한다')

    # 2. 꼬리표 — 애노드(Negative 는 저항 윗다리)가 닿는 칩 핀으로 맞춘다
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'tagged.json'
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
        hand = parse_transcript(p, board=board)
    hatt, ratt = hc.attachments(hand), hc.attachments(ref)
    hnets, rnets = hc.build_nets(hand), hc.build_nets(ref)

    def pins(diagram, nets, att, hole):
        return {a for a in att.get(nets.get(hc.node_of(hole)), set()) if a[0] == 'PIN'}

    ref_pins = {c['tag']: pins(ref, rnets, ratt, c['anode']) | pins(ref, rnets, ratt, c['res_top'])
                for c in ref.chains}
    mapping, free_ref = {}, [c['tag'] for c in sorted(ref.chains, key=lambda c: c['anode'][2])]
    for c in sorted(hand.chains, key=lambda c: c['anode'][2]):
        got = pins(hand, hnets, hatt, c['anode']) | pins(hand, hnets, hatt, c['res_top'])
        same = [t for t in free_ref if got and ref_pins[t] & got]
        if len(same) == 1:
            mapping[c['tag']] = same[0]
            free_ref.remove(same[0])
    rest = [c['tag'] for c in sorted(hand.chains, key=lambda c: c['anode'][2]) if c['tag'] not in mapping]
    for h, r in zip(rest, list(free_ref)):
        mapping[h] = r
        notes.append(f'{h} → {r}: 칩 핀으로 못 가려 위에서부터의 순서로 맞췄다')
    for h, r in mapping.items():
        if h != r and not any(n.startswith(f'{h} → ') for n in notes):
            notes.append(f'{h} → {r}: 애노드가 닿는 칩 핀이 같다')
    for led in leds:
        led['tag'] = mapping.get(led['tag'], led['tag'])
    for r in res:
        r['tag'] = mapping.get(r.get('tag', ''), r.get('tag', ''))
    return obj, notes


# ---------------------------------------------------------------- 판정

def photo_verdict(findings):
    if any(f.grade in hc.BLOCKING for f in findings):
        return '수정 필요'
    if any(f.rule == 'H13' for f in findings):
        return '재촬영 필요'
    return '통과'


def judge(experiment, stage, transcript_path, out_dir=None):
    """(단계 이름, 결함들, 알림들). `out_dir` 를 주면 정규화 전사와 판정.md 를 거기 쓴다."""
    name = resolve_stage(experiment, stage)
    board = expected_board(experiment)
    ref = stage_reference(experiment, name)
    raw = json.loads(Path(transcript_path).read_text(encoding='utf-8'))
    obj, notes = normalize_transcript(raw, ref, board)
    target = Path(out_dir) if out_dir else Path(tempfile.mkdtemp())
    target.mkdir(parents=True, exist_ok=True)
    norm = target / '전사_판정용.json'
    norm.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    hand = parse_transcript(norm, board=board)
    findings = [f for f in hc.compare(ref, hand) if f.rule not in PHOTO_SKIP]
    if out_dir:
        (target / '판정.md').write_text(judgment_markdown(name, findings, notes, raw), encoding='utf-8')
    return name, findings, notes


def judgment_markdown(stage, findings, notes, raw):
    v = photo_verdict(findings)
    lines = [f'# 결선 사진 검토 · {stage}', '', f'**판정: {v}**', '']
    photos = raw.get('photos', [])
    if photos:
        lines += ['사진: ' + ', '.join(f"`{p}`" for p in photos), '']
    counts = {g: sum(1 for f in findings if f.grade == g) for g in hc.GRADES}
    lines += ['| 등급 | 건수 |', '|---|---|'] + [f'| {g} | {counts[g]} |' for g in hc.GRADES] + ['']
    if findings:
        lines += ['| 등급 | 규칙 | 자리 | 내용 |', '|---|---|---|---|']
        for f in findings:
            lines.append(f"| {f.grade} | {f.rule} | {f.where} | {f.message.replace('|', chr(92) + '|')} |")
        lines.append('')
    else:
        lines += ['참조와 다른 곳이 없다.', '']
    if notes:
        lines += ['## 전사 정규화 알림', ''] + [f'- {n}' for n in notes] + ['']
    lines += ['## 읽는 법', '',
              '- **수정 필요**: 치명·기능 결함이 있다. 자리는 사진 기준 주소다.',
              '- **재촬영 필요**: 결함은 없지만 사진으로 확정 못 한 끝점(H13)이 있다. 그 자리를 다시 찍는다.',
              '- **통과**: 읽은 끝점이 모두 참조 넷과 같다. 극성 미확인 알림이 있으면 그 LED 만 눈으로 본다.',
              '- 칩·LED 가 참조와 다른 행에 있어도 넷이 같으면 통과다(H10 은 표기로만 알린다).', '']
    return '\n'.join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='photo_wiring')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('stages'); s.add_argument('experiment', type=int)
    r = sub.add_parser('ruler'); r.add_argument('photo'); r.add_argument('out')
    r.add_argument('--crop', type=int, nargs=4); r.add_argument('--step', type=int)
    g = sub.add_parser('grid'); g.add_argument('experiment', type=int); g.add_argument('anchors'); g.add_argument('out_dir')
    j = sub.add_parser('judge'); j.add_argument('experiment', type=int); j.add_argument('stage')
    j.add_argument('transcript'); j.add_argument('out_dir')
    a = ap.parse_args(argv)
    if a.cmd == 'stages':
        for n in stage_names(a.experiment):
            print(n)
    elif a.cmd == 'ruler':
        print(ruler(a.photo, a.out, crop=a.crop, step=a.step))
    elif a.cmd == 'grid':
        for name, grid, rows in grids_from_file(a.anchors, expected_board(a.experiment)):
            for path in overlay(grid, a.out_dir, name, rows):
                print(path)
            print(f'  {name}: {BLOCK_NAMES[grid.block]} 블록, 피치 {grid.pitch:.1f}px, 앵커 오차 최대 {grid.residual:.2f} 피치')
    elif a.cmd == 'judge':
        name, findings, notes = judge(a.experiment, a.stage, a.transcript, a.out_dir)
        print(f'{name}: {photo_verdict(findings)}')
        for f in findings:
            print(' ', f)
        for n in notes:
            print('  알림:', n)
        print(os.path.join(a.out_dir, '판정.md'))


if __name__ == '__main__':
    main()
