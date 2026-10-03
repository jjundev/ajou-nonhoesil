# 실험04 v2 시험판 — 승인본(`보고서/실험04/결선도/배치.py`, v1)을 v2 규약으로 다시 놓아 본다.
# 계획: `docs/plans/2026-10-03-실험04-v2-시험판-구현계획.md`. 결과: 같은 폴더의 `…-결과.md`.
#
# 칩 넷 전부 좌 블록(R9), LED 는 우 a 열(R10). R8 은 면제하지 않는다 — 칩 사이 선은 쪽을
# 바꾸지 않고, 쪽을 바꿔야 하는 신호는 **같은 칩 안에서** 이어 가거나 n.c. 핀·미사용 게이트
# 입력을 중계로 거친다. 교안 핀 번호는 그 때문에 바뀐다(승인본 netlist 와 다르다).
#
#   K1 좌 5행  : 74HC04 (U4)
#   K2 좌 17행 : 74HC20 (U1) / 74HC11 (U5)
#   K3 좌 29행 : 74HC20 (U2) / 비움
#   K4 좌 41행 : 74HC20 (U3) / 74HC11 (U6)
#
# **경로는 손으로 찍지 않는다.** 배선표(어느 핀을 어느 핀에)만 적고, 경로는 `_route()` 가
# 엔진의 R3(끝점이 선 아래)·R4(같은 축 포개짐)·R6(자기 스트립 안 구간)과 같은 식으로 골라 낸다.
# 칩 넷이 한 블록에 몰리면 a~d / g~j 열은 끝점으로 차서 세로선이 지나갈 데가 없다 — 그래서
# 가로는 **반 행**(두 행 사이), 세로는 **홀 열 사이**나 여백 차선을 탄다. 경로는 회로마다 한 번,
# 모든 단계의 선을 한 판에 올린 superset 판에서 정하고 단계 그림은 그 경로를 그대로 쓴다 —
# 단계마다 경로가 달라지면 기준선 회색 선과 새 선이 어긋난다.
import functools

from render_breadboard import BreadboardRenderer, _input_jumper, fresh_board, removal_board

BOARD = 'v2'
K1, K2, K3, K4 = 5, 17, 29, 41
LED_TOP = (19, 23, 27, 43)            # DMUX 우 a 열 LED1~4 사슬 윗행 — Y0·Y3 이 곧게 건넌다
MUX_LED_TOP = (47, 51, 55, 59)        # MUX — LED1 이 Y(U3 pin 8, 47행)와 같은 행

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다.')


def _pin_row(k, pin):
    """칩 pin 1 행 `k` 에서 핀 `pin` 이 앉는 행."""
    return k + pin - 1 if pin <= 7 else k + 14 - pin


def _side(pin):
    return 'a' if pin <= 7 else 'f'


def _frame(bb):
    """잭 → 좌 바깥 레일, 좌 바깥 → 가운데 브리지 두 가닥(SKILL §2b). 우 바깥 레일은 안 쓴다."""
    L = bb.cols['left']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], 53, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], 54, kind='vcc')


# ---------------- 배선기 ----------------

_STRIP_COLS = {'a': 'abcd', 'f': 'ghij'}


def _end_holes(bb, chips, end):
    """배선 끝 하나가 꽂힐 수 있는 홀 후보 [(x, y)]. `end` 는 ('U5', 13) 또는 ('LED', top_row)."""
    L, R = bb.cols['left'], bb.cols['right']
    if end[0] == 'LED':
        return [(R['a'], bb.r_y(end[1]))]
    k, pin = chips[end[0]], end[1]
    row = _pin_row(k, pin)
    return [(L[c], bb.r_y(row)) for c in _STRIP_COLS[_side(pin)]
            if (L[c], row) not in bb._leads and (L[c], row) not in bb._passed]


def _lanes(bb, led):
    """세로선이 달릴 x 후보. 홀 열 자체와 홀 열 사이(±12), 좌 여백·가운데 여백 차선.
    칩 몸통(e~f 사이)은 뺀다 — 세로선이 칩 위를 덮는다. LED 로 가는 선은 가운데 여백만 쓴다."""
    L, R = bb.cols['left'], bb.cols['right']
    if led:
        return [548, 560, 572, 600, 624, 636, 648]
    xs = [L[c] for c in 'abcdghij'] + [L[c] + 12 for c in 'abcghi'] + [L['j'] + 12]
    xs += [212, 224, 236, 248, 260, 560, 572]
    return sorted(set(xs))


def _axis(a, b):
    if abs(a[0] - b[0]) < .5:
        return 'v'
    if abs(a[1] - b[1]) < .5:
        return 'h'
    return None


def _on_seg(p, a, b, margin=6):
    """엔진 `_endpoints_under_wires` 와 같은 식 — p 가 구간 ab 의 **중간** 위에 있는가."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = (dx * dx + dy * dy) ** .5
    if length < 1:
        return False
    along = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length
    if along <= margin or length - along <= margin:
        return False
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / length < 1.5


def _clean(path):
    out = []
    for p in path:
        if out and abs(out[-1][0] - p[0]) < .5 and abs(out[-1][1] - p[1]) < .5:
            continue
        if len(out) >= 2 and _axis(out[-2], out[-1]) and _axis(out[-2], out[-1]) == _axis(out[-1], p):
            out[-1] = p
            continue
        out.append(p)
    return out


def _cost(bb, path):
    cost = 40 * (len(path) - 2)
    for a, b in zip(path, path[1:]):
        cost += abs(a[0] - b[0]) + abs(a[1] - b[1])
        # 행 위를 그대로 지나는 가로선은 그 행의 홀 위를 덮는다 — 반 행보다 비싸게
        if _axis(a, b) == 'h' and bb.hole_at(a[0], a[1]) is not None or (
                _axis(a, b) == 'h' and abs((a[1] - bb.spec.row0) / bb.spec.row_pitch % 1) < .1):
            cost += abs(a[0] - b[0]) * .5
    return cost


def _valid(bb, path, others_pts, segs):
    # R6 — 두 점이 다 같은 스트립의 홀이면 그 구간은 전기적으로 없는 것과 같다
    for a, b in zip(path, path[1:]):
        sa = bb._strip(bb.sym(a[0], bb._row_of(a[1]))) if bb.hole_at(*a) else None
        sb = bb._strip(bb.sym(b[0], bb._row_of(b[1]))) if bb.hole_at(*b) else None
        if sa is not None and sa == sb:
            return False
        if _axis(a, b) is None:
            return False
    # 꺾임점이 리드가 있는 홀 위에 앉으면 안 된다
    for c in path[1:-1]:
        h = bb.hole_at(*c)
        if h is not None and h in bb._leads:
            return False
    # 새 선의 끝점이 기존 선 아래
    for q in (path[0], path[-1]):
        for _k, pts in segs:
            for a, b in zip(pts, pts[1:]):
                if _on_seg(q, a, b):
                    return False
    # 기존 끝점·부품 다리가 새 선 아래
    for q in others_pts:
        for a, b in zip(path, path[1:]):
            if _on_seg(q, a, b):
                return False
    # 같은 축 포개짐(R4) — 색과 무관하게 8px 로 본다
    for a, b in zip(path, path[1:]):
        ax = _axis(a, b)
        for _k, pts in segs:
            for c, d in zip(pts, pts[1:]):
                if _axis(c, d) != ax:
                    continue
                if ax == 'v' and abs(a[0] - c[0]) < 1.5:
                    lo = max(min(a[1], b[1]), min(c[1], d[1]))
                    hi = min(max(a[1], b[1]), max(c[1], d[1]))
                    if hi - lo > 2:
                        return False
                if ax == 'h' and abs(a[1] - c[1]) < 1.5:
                    lo = max(min(a[0], b[0]), min(c[0], d[0]))
                    hi = min(max(a[0], b[0]), max(c[0], d[0]))
                    if hi - lo > 2:
                        return False
    return True


def _route(bb, chips, frm, to):
    """`frm`→`to` 의 경로. 후보는 [A, (A.x, y1), (X, y1), (X, y2), (B.x, y2), B] 꼴이다 —
    y1·y2 는 끝 행 또는 반 행 위아래, X 는 `_lanes()`. 싼 순으로 보며 첫 합법 경로를 쓴다."""
    led = to[0] == 'LED'
    half = bb.spec.row_pitch / 2
    srcs, dsts = _end_holes(bb, chips, frm), _end_holes(bb, chips, to)
    cands = []
    for A in srcs:
        for B in dsts:
            for d1 in (0, -half, half):
                for d2 in ((0,) if led else (0, -half, half)):
                    y1, y2 = A[1] + d1, B[1] + d2
                    for X in _lanes(bb, led) + [A[0], B[0]]:
                        p = _clean([A, (A[0], y1), (X, y1), (X, y2), (B[0], y2), B])
                        cands.append(p)
    others = []
    segs = [(k, pts) for k, pts, _d in bb._segments]
    for _k, pts, _d in bb._segments:
        others += [pts[0], pts[-1]]
    for (x, r), what in bb._leads.items():
        if '다리' in what or '애노드' in what or '캐소드' in what:
            others.append((x, bb.r_y(r)))
    seen = set()
    for p in sorted(cands, key=lambda p: (_cost(bb, p), p)):
        t = tuple(p)
        if t in seen:
            continue
        seen.add(t)
        if _valid(bb, p, others, segs):
            return p
    raise AssertionError(f'경로 없음: {frm} -> {to}')


def _plan(build_fixed, chips, wires):
    """superset 판(모든 단계의 고정물 + 앞 선)에서 선마다 경로를 정한다 — `wires` 순서대로."""
    bb = BreadboardRenderer(None, board=BOARD)
    bb.enable_steps()
    build_fixed(bb, None, superset=True)
    paths = []
    for _s, _e, kind, frm, to, desc in wires:
        p = _route(bb, chips, frm, to)
        bb.step_wire(p, kind, desc)
        paths.append(p)
    return paths


def _draw_wires(bb, wires, paths, stage):
    for (s, e, kind, _frm, _to, desc), p in zip(wires, paths):
        if stage is None:
            if e is not None:
                continue
        elif not (s <= stage and (e is None or stage <= e)):
            continue
        bb.step_wire(p, kind, desc)


# ---------------- C2 1x4 DMUX ----------------

_DMUX_CHIPS = {'U4': K1, 'U5': K2, 'U6': K4}
# (첫 단계, 끝 단계(임시선만), 색, 출발, 도착, 설명). 순서 = 그리는 순서 = 경로를 정하는 순서.
_DMUX_WIRES = [
    (1, None, 'sig', ('U4', 9), ('U6', 13), 'S1 (U4 pin 9) -> U6 pin 13'),
    (1, None, 'sig', ('U6', 12), ('LED', LED_TOP[3]), 'Y3 = U6 pin 12 -> LED4'),
    (2, None, 'sig', ('U6', 1), ('U5', 3), 'S0 (U6 pin 1) -> U5 pin 3'),
    (2, None, 'sig', ('U4', 8), ('U5', 13), "S1' (U4 pin 8) -> U5 pin 13"),
    (2, None, 'sig', ('U5', 13), ('U5', 4), "S1' 이어 감 (U5 pin 13 -> U5 pin 4)"),
    (2, None, 'sig', ('U6', 2), ('U5', 5), 'D (U6 pin 2) -> U5 pin 5'),
    (2, None, 'sig', ('U5', 6), ('LED', LED_TOP[1]), 'Y1 = U5 pin 6 -> LED2'),
    (3, None, 'sig', ('U6', 1), ('U4', 1), 'S0 (U6 pin 1) -> U4 pin 1'),
    (3, None, 'sig', ('U4', 2), ('U5', 2), "S0' (U4 pin 2) -> U5 pin 2"),
    (3, None, 'sig', ('U5', 2), ('U5', 10), "S0' 이어 감 (U5 pin 2 -> U5 pin 10)"),
    (3, None, 'sig', ('U4', 9), ('U5', 9), 'S1 (U4 pin 9) -> U5 pin 9'),
    (3, None, 'sig', ('U6', 2), ('U6', 11), 'D 이어 감 (U6 pin 2 -> U6 pin 11, 미사용 입력 중계)'),
    (3, None, 'sig', ('U6', 11), ('U5', 11), 'D (U6 pin 11) -> U5 pin 11'),
    (3, None, 'sig', ('U5', 8), ('LED', LED_TOP[2]), 'Y2 = U5 pin 8 -> LED3'),
    (4, None, 'sig', ('U6', 2), ('U5', 1), 'D (U6 pin 2) -> U5 pin 1'),
    (4, None, 'sig', ('U5', 12), ('LED', LED_TOP[0]), 'Y0 = U5 pin 12 -> LED1'),
]
# 입력 점퍼 (단계, 이름, 칩, 핀). 고정물과 함께 경로보다 **먼저** 그린다 — 레일 착지 행이
# 앞 선에 따라 바뀌지 않게.
_DMUX_INPUTS = [(1, 'S0', 'U6', 1), (1, 'D', 'U6', 2), (1, 'S1', 'U4', 9)]


def _inputs(bb, chips, inputs, stage, superset):
    L = bb.cols['left']
    for s, name, chip, pin in inputs:
        if superset or stage is None or s <= stage:
            side = _side(pin)
            _input_jumper(bb, L, _pin_row(chips[chip], pin), name, f'{chip} pin {pin}',
                          side=side, col='a' if side == 'a' else 'j')


def _dmux_fixed(bb, stage, superset=False):
    R = bb.cols['right']
    bb.draw_chip('74HC04', K1)
    bb.draw_chip('74HC11', K2)
    bb.draw_chip('74HC11', K4)
    _frame(bb)
    for k in (K1, K2, K4):
        bb.connect_power(k, gnd_col='a')
    for i, tag in enumerate(('Y0', 'Y1', 'Y2', 'Y3')):
        bb.led_chain(R['a'], LED_TOP[i], tag, f'{tag} — 진리표 T3 의 {tag} 열', block='right')
    _inputs(bb, _DMUX_CHIPS, _DMUX_INPUTS, stage, superset)


@functools.lru_cache(maxsize=None)
def _dmux_paths():
    return _plan(_dmux_fixed, _DMUX_CHIPS, _DMUX_WIRES)


def _dmux_draw(bb, stage):
    bb.partial = stage is not None and stage < 4
    _dmux_fixed(bb, stage)
    _draw_wires(bb, _DMUX_WIRES, _dmux_paths(), stage)
    bb.mark_unused_inputs([3, 5, 11, 13], K1, chip='74HC04')
    bb.mark_unused_outputs([4, 6, 10, 12], K1, chip='74HC04')
    bb.mark_unused_inputs([3, 4, 5, 9, 10], K4, chip='74HC11 (U6)')
    bb.mark_unused_outputs([6, 8], K4, chip='74HC11 (U6)')
    bb.note(_INPUT_NOTE)


def build_trial_dmux(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """C2 1x4 DMUX v2 시험판. `stage` 1..4 또는 None(완성)."""
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    bb.set_header('실험04 v2 시험판: 1x4 DMUX', '74HC04 + 74HC11 ×2 · 칩 좌 블록, LED 우 블록')
    _dmux_draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


BOARDS = []
FINALS = [('trial_e4_dmux.png', build_trial_dmux)]
