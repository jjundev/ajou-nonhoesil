# 결선도 엔진 조각 — 칩 모델 표·배선기.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

# ---------------------------------------------------------------------------
# 배선기 (v2) — 배선표(어느 핀을 어느 핀에)만 받아 경로와 번호 원 자리를 고른다. 가로는 반 행, 세로는
# 홀 열 사이나 여백 차선을 탄다. 차선 x 값은 v2 기하라 v1 에서는 안 부른다.
# 설계: `docs/plans/2026-10-04-v2-배선기-밀도-설계.md`.


# 칩 모델 표 — 이름 → DIP 핀 수(VCC 는 마지막 핀, GND 는 n/2). 배치기는 없는 칩을 거절하고
# 그리기는 14핀으로 본다(v1 빌더 호환).
DIP_PINS = {
    '74HC00': 14, '74HC02': 14, '74HC04': 14, '74HC08': 14, '74HC10': 14, '74HC11': 14,
    '74HC20': 14, '74HC21': 14, '74HC27': 14, '74HC32': 14, '74HC74': 14, '74HC86': 14,
    '74HC42': 16, '74HC138': 16, '74HC148': 16,
}


def dip_pins(model, strict=False):
    """칩 이름 → 핀 수. 모르면 `strict` 에서 ValueError, 아니면 14."""
    n = DIP_PINS.get(model)
    if n is None:
        if strict:
            raise ValueError(f'모르는 칩 {model!r} — 칩 모델 표 `DIP_PINS` 에 핀 수를 올린다')
        return 14
    return n


def _dip_pin_row(k, pin, n=14):
    """칩 pin 1 행 `k` 에서 DIP-`n` 핀 `pin` 이 앉는 행."""
    return k + pin - 1 if pin <= n // 2 else k + n - pin


def _dip_side(pin, n=14):
    return 'a' if pin <= n // 2 else 'f'


# 밀도 가중치 λ — 비용 = 길이 + 40·꺾임 + 400·몸통횡단 + λ·밀도증분(px). 0 이면 밀도를 안 본다.
# `python -m scripts.lab.route_sweep` 로 정한다(고르는 규칙 `docs/plans/2026-10-04-v2-배선기-밀도-설계.md` #11,
# 스윕 표 `docs/plans/2026-10-03-실험04-v2-시험판-결과.md` §배선기 밀도 스윕).
DENSITY_WEIGHT = 0.5
_RERANK_TOP = 400   # 정적 순위 앞 몇 개만 밀도로 다시 매기나 — 나머지는 정적 순서 그대로


_STRIP_COLS = {'a': 'abcd', 'f': 'ghij'}


def _chip_pins(bb):
    """좌 블록 칩 pin 1 행 → 핀 수 — `pins` 개수로 읽는다(레코드에 키를 더하면 도장이 바뀐다)."""
    return {ch['pin1_row']: len(ch['pins']) for ch in bb.chips if ch['block'] == 'left'}


def _end_holes(bb, chips, end):
    """배선 끝 하나가 꽂힐 수 있는 홀 후보 [(x, y)]. `end` 는 ('U5', 13) 또는 ('LED', top_row)."""
    L, R = bb.cols['left'], bb.cols['right']
    if end[0] == 'LED':
        return [(R['a'], bb.r_y(end[1]))]
    k, pin = chips[end[0]], end[1]
    n = _chip_pins(bb).get(k, 14)
    row = _dip_pin_row(k, pin, n)
    return [(L[c], bb.r_y(row)) for c in _STRIP_COLS[_dip_side(pin, n)]
            if (L[c], row) not in bb._leads and (L[c], row) not in bb._passed]


def _lanes(bb, led):
    """세로선이 달릴 x 후보 — 홀 열과 그 사이, 좌·가운데 여백 차선. 칩 몸통은 뺀다. LED 로 가는 선은
    가운데 여백 쪽만."""
    L = bb.cols['left']
    mid = [x for x in range(542, 660, 6) if min(abs(x - L['mid_gnd']), abs(x - L['mid_vcc'])) > 4]
    xs = [L[c] for c in 'abcdghij'] + [L[c] + 12 for c in 'abcghi'] + [L['j'] + 12]
    xs += [212, 224, 236, 248, 260]
    if led:
        return sorted(set(mid + [L[c] for c in 'ghij'] + [L[c] + 12 for c in 'ghi']))
    return sorted(set(xs + [x for x in mid if x < L['mid_gnd']]))


def _axis(a, b):
    if abs(a[0] - b[0]) < .5:
        return 'v'
    if abs(a[1] - b[1]) < .5:
        return 'h'
    return None


def _on_seg(p, a, b, margin=6):
    """엔진 `_endpoints_under_wires` 와 같은 식 — p 가 구간 ab 의 **중간** 위에 있는가."""
    # 범위 선검사 — 참이면 p 는 구간 범위 ±1.5 안이다. 여유 2 는 아래 나눗셈의 반올림 몫(2026-10-05 속도)
    if not (min(a[0], b[0]) - 2 < p[0] < max(a[0], b[0]) + 2 and min(a[1], b[1]) - 2 < p[1] < max(a[1], b[1]) + 2):
        return False
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


def _holes_passed(a, b, xs, xset, pitch, row0):
    """축 구간 ab 가 덮는 홀 수(양 끝 제외) — 홀 열 위 세로선, 행 위 가로선."""
    if abs(a[0] - b[0]) < .5:
        if round(a[0]) not in xset:
            return 0
        lo, hi = sorted((a[1], b[1]))
        return max(0, math.ceil((hi - 1 - row0) / pitch) - math.floor((lo + 1 - row0) / pitch) - 1)
    f = (a[1] - row0) / pitch % 1
    if .05 < f < .95:
        return 0
    lo, hi = sorted((a[0], b[0]))
    return bisect.bisect_left(xs, hi - 1) - bisect.bisect_right(xs, lo + 1)


def _coster(bb):
    xs = sorted(round(x) for x in bb._addr_map)
    xset, pitch, row0 = set(xs), bb.spec.row_pitch, bb.spec.row0
    L = bb.cols['left']
    bodies = [(bb.r_y(ch['pin1_row']) - 10, bb.r_y(ch['pin1_row'] + len(ch['pins']) // 2 - 1) + 10)
              for ch in bb.chips]

    def body_crossings(path):
        """칩 몸통을 가로지르는 가로 구간 수 — 칩 이름·핀 번호를 덮는다."""
        n = 0
        for a, b in zip(path, path[1:]):
            if abs(a[1] - b[1]) < .5 and min(a[0], b[0]) < L['e'] and max(a[0], b[0]) > L['f']:
                n += sum(1 for y0, y1 in bodies if y0 <= a[1] <= y1)
        return n

    def cost(path):
        """(덮는 홀 수, 길이 + 꺾임 벌점). 덮는 홀이 있는 경로는 버린다(R12)."""
        over = sum(_holes_passed(a, b, xs, xset, pitch, row0) for a, b in zip(path, path[1:]))
        c = 40 * (len(path) - 2) + 400 * body_crossings(path)
        for a, b in zip(path, path[1:]):
            c += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return over, c
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
    # 칩 이름 글자 위를 지나지 않는다(엔진 R14) — 이어 가기는 이름 위아래 반 행으로 건넌다
    for box, _ch in bb.chip_label_boxes:
        if any(bb._seg_in_box(a, b, box) for a, b in zip(path, path[1:])):
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
    # 이미 찍힌 번호 원 아래로 지나가거나 그 아래 홀에 꽂지 않는다 — 원이 선·끝점을 가린다
    for m in bb.marker_boxes:
        x0, y0, x1, y1 = m[0] - 1, m[1] - 1, m[2] + 1, m[3] + 1
        for a, b in zip(path, path[1:]):
            if (min(a[0], b[0]) < x1 and max(a[0], b[0]) > x0
                    and min(a[1], b[1]) < y1 and max(a[1], b[1]) > y0):
                return False
    # 꺾임점이 남의 선에 닿지 않는다 — 맞닿은 두 선은 한 가닥으로 읽힌다(R4 가 못 보는 2px 이하)
    for c in path[1:-1]:           # 끝점(홀)끼리는 R2·단계 겹침을 위에서 따로 본다
        for _k, pts in segs:
            if any(abs(c[0] - q[0]) < 1.5 and abs(c[1] - q[1]) < 1.5 for q in pts) or                     any(_on_seg(c, a, b, margin=0) for a, b in zip(pts, pts[1:])):
                return False
    for _k, pts in segs:
        for q in pts[1:-1]:
            if any(_on_seg(q, a, b, margin=0) for a, b in zip(path, path[1:])):
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
    """`frm`→`to` 의 가장 싼 합법 경로와 번호 원 자리."""
    for found in _routes(bb, chips, frm, to):
        return found
    raise AssertionError(f'경로 없음: {frm} -> {to}')


def _routes(bb, chips, frm, to, density_weight=0.0):
    """`frm`→`to` 의 합법 경로를 싼 순으로 낸다. 후보는 [A, (A.x, y1), (X, y1), (X, y2), (B.x, y2), B]
    꼴이다 — y1·y2 는 끝 행 또는 반 행 위아래, X 는 `_lanes()`."""
    led = to[0] == 'LED'
    srcs, dsts = _end_holes(bb, chips, frm), _end_holes(bb, chips, to)
    others = []
    segs = [(k, pts) for k, pts, _d in bb._segments]
    for _k, pts, _d in bb._segments:
        others += [pts[0], pts[-1]]
    for (x, r), what in bb._leads.items():
        if '다리' in what or '애노드' in what or '캐소드' in what:
            others.append((x, bb.r_y(r)))
    chip_rows = tuple((ch['pin1_row'], len(ch['pins'])) for ch in bb.chips)
    placed = _placed_signal_segs(bb) if density_weight else []
    order = _rerank(_ordered(bb, chip_rows, tuple(srcs), tuple(dsts), led), placed,
                    bb.spec.row_pitch, density_weight)
    for p in order:
        if _valid(bb, p, others, segs):
            p = list(p)
            m = _marker_spot(bb, p)
            if m is not None:          # 번호 원을 찍을 데가 없는 경로는 따라 그릴 수 없다
                yield p, m


_ORDERED = {}


def _ordered(bb, chip_rows, srcs, dsts, led):
    """후보 경로를 싼 순으로 — 덮는 홀이 있는 것은 뺀다. 칩 자리와 끝 홀에만 달려 사본마다 캐시한다
    (`_ORDERED`) — 수리가 같은 선을 다시 깔 때 그대로 쓴다."""
    key = (bb.spec.name, chip_rows, srcs, dsts, led)
    if key in _ORDERED:
        return _ORDERED[key]
    half = bb.spec.row_pitch / 2
    # 가로 통로: 끝 행, 또는 ±0.5·1.5·…·4.5 행
    ds = (0,) + tuple(s * half * n for n in (1, 3, 5, 7, 9) for s in (-1, 1))
    lo_y, hi_y = bb.r_y(1), bb.r_y(63)
    cands = []
    for A in srcs:
        for B in dsts:
            for d1 in ds:
                for d2 in ds:
                    if not (lo_y <= A[1] + d1 <= hi_y and lo_y <= B[1] + d2 <= hi_y):
                        continue
                    y1, y2 = A[1] + d1, B[1] + d2
                    for X in _lanes(bb, led) + [A[0], B[0]]:
                        p = _clean([A, (A[0], y1), (X, y1), (X, y2), (B[0], y2), B])
                        cands.append(p)
    cost = _coster(bb)
    scored = [(cost(p), p) for p in set(map(tuple, cands))]
    out = [(c, p) for (_over, c), p in sorted((s for s in scored if s[0][0] == 0),
                                              key=lambda s: (s[0][1], s[1]))]
    _ORDERED[key] = out
    return out


def _rerank(scored, placed, pitch, weight, top=_RERANK_TOP):
    """정적 순위 [(비용, 경로)] 의 앞 `top` 개를 `비용 + weight·밀도증분` 으로 다시 매긴다. 뒤는
    정적 순서 그대로. weight 0 이면 순서가 안 바뀐다 — 정적 정렬 열쇠도 (비용, 경로) 다."""
    if not weight:
        return [p for _c, p in scored]
    head = sorted(scored[:top], key=lambda s: (s[0] + weight * _density_cost(s[1], placed, pitch), s[1]))
    return [p for _c, p in head] + [p for _c, p in scored[top:]]


_R = 8   # 번호 원 반지름 (엔진 `_marker` 상자 ±8)


def _box_clear(bb, x, y, path_pts):
    """(x, y) 번호 원이 아무것도 안 가리는가 — `_marker_clear` 에 아직 안 그린 제 끝점 두 홀을 더 본다."""
    if any(abs(hx - x) <= _R + 2 and abs(hy - y) <= _R + 2 for hx, hy in (path_pts[0], path_pts[-1])):
        return False
    return bb._marker_clear(x, y)


def _marker_spot(bb, path):
    """경로 위 번호 원 자리 — 가로 구간 먼저(세로 차선의 원은 이웃 차선을 막는다), 긴 구간 순으로
    가운데부터 4px 씩 훑어 `_box_clear` 인 첫 점. 엔진 기본(첫 구간 가운데)은 첫 토막이 반 행이라
    원이 끝점을 덮는다."""
    segs = sorted(zip(path, path[1:]), key=lambda s: (_axis(*s) != 'h',
                                                      -(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))))
    for a, b in segs:
        length = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if length < 2 * _R + 8:
            continue
        mid = length / 2
        for off in range(0, int(mid - _R - 4), 4):
            for t in {mid - off, mid + off}:
                f = t / length
                x, y = round(a[0] + (b[0] - a[0]) * f), round(a[1] + (b[1] - a[1]) * f)
                if _box_clear(bb, x, y, path):
                    return (x, y)
    return None


_REPAIR_BACK, _REPAIR_ALTS = 4, 8   # 막히면 직전 몇 가닥을, 가닥마다 몇 후보까지 바꿔 보는가


def route_plan(build_fixed, chips, wires, board='v2', density_weight=None):
    """superset 판(모든 단계의 고정물 + 앞 선)에서 `wires` 순서대로 선마다 경로와 번호 원 자리를 정한다 —
    단계 그림마다 같은 자리다. v2 판형만.

    뒤 선이 막히면 직전 `_REPAIR_BACK` 가닥 중 **한 가닥만** 다음 후보로 바꾸고 그 뒤를 다시 깐다
    (2026-10-04 MUX U1). 아무 데로나 되돌아가는 탐색은 가짓수가 터졌다."""
    if not board_spec(board).readability:
        raise ValueError(f'route_plan 은 v2 판형만 고른다(차선이 v2 기하다): {board!r}')
    w = DENSITY_WEIGHT if density_weight is None else density_weight

    def board_(upto):
        bb = BreadboardRenderer(None, board=board)
        bb.enable_steps()
        build_fixed(bb, None, superset=True)
        for (_s, _e, kind, _f, _t, desc), (p, m) in zip(wires, upto):
            bb.step_wire(p, kind, desc, marker_at=m)
        return bb

    def greedy(start, upto, stop):
        """`upto` 뒤로 `stop` 가닥째까지 가장 싼 경로를 깐다. 막히면 None."""
        bb, plans = board_(upto), list(upto)
        for _s, _e, kind, frm, to, desc in wires[start:stop + 1]:
            found = next(_routes(bb, chips, frm, to, w), None)
            if found is None:
                return None
            bb.step_wire(found[0], kind, desc, marker_at=found[1])
            plans.append(found)
        return plans

    plans, bb = [], board_([])
    while len(plans) < len(wires):
        i = len(plans)
        _s, _e, kind, frm, to, desc = wires[i]
        found = next(_routes(bb, chips, frm, to, w), None)
        if found is not None:
            bb.step_wire(found[0], kind, desc, marker_at=found[1])
            plans.append(found)
            continue
        for j in range(i - 1, max(-1, i - 1 - _REPAIR_BACK), -1):
            _s, _e, _k, frm_j, to_j, _d = wires[j]     # 수리할 앞 선 — 막힌 선의 frm·to 는 메시지에 남긴다
            alts = itertools.islice(_routes(board_(plans[:j]), chips, frm_j, to_j, w), 1, 1 + _REPAIR_ALTS)
            for alt in alts:
                more = greedy(j + 1, plans[:j] + [alt], i)
                if more is not None:
                    plans = more
                    break
            else:
                continue
            break
        else:
            raise AssertionError(f'경로 없음: {frm} -> {to} ({desc})')
        bb = board_(plans)
    return _resettle_markers(bb, plans)


def _resettle_markers(bb, plans):
    """다 깐 superset 판에서 경로 번호 원을 다시 본다 — 원은 뒤에 깐 선의 끝점을 모른다(2026-10-05).
    R11 에 걸리는 원만 `_auto_marker` 로 다시 고른다."""
    first = len(bb._segments) - len(plans)
    out = list(plans)
    for i, (p, m) in enumerate(plans):
        if m is None:
            continue
        box = (m[0] - 8, m[1] - 8, m[0] + 8, m[1] + 8)
        mine = [lst for lst in (bb._marker_slots, bb.marker_boxes) if box in lst]
        for lst in mine:
            lst.remove(box)                      # 제 원은 빼고 잰다
        if not bb._marker_fits(*m, own=first + i):
            m = bb._auto_marker(first + i) or m
            out[i] = (p, m)
            box = (m[0] - 8, m[1] - 8, m[0] + 8, m[1] + 8)
        for lst in mine:
            lst.append(box)
    return out


def draw_routed(bb, wires, plans, stage):
    for (s, e, kind, _frm, _to, desc), (p, m) in zip(wires, plans):
        if stage is None:
            if e is not None:
                continue
        elif not (s <= stage and (e is None or stage <= e)):
            continue
        bb.step_wire(p, kind, desc, marker_at=m)

def _axis_segs(pts):
    """축 정렬 구간만 [(축, 고정 좌표, lo, hi)] 로. 사선 구간은 밀도에서 뺀다."""
    out = []
    for a, b in zip(pts, pts[1:]):
        if abs(a[0] - b[0]) < .5:
            out.append(('v', a[0], min(a[1], b[1]), max(a[1], b[1])))
        elif abs(a[1] - b[1]) < .5:
            out.append(('h', a[1], min(a[0], b[0]), max(a[0], b[0])))
    return out


def _crowding(sa, sb, pitch):
    """두 축 구간이 1칸보다 가깝게 나란히 달린 정도(px) — 겹친 길이 × (1 − 간격/칸). 간격 0 은 R4 몫.
    (2026-10-04 사용자: 빽빽함 = 가까운 평행선)"""
    if sa[0] != sb[0]:
        return 0.0
    gap = abs(sa[1] - sb[1])
    if gap <= .5 or gap >= pitch:
        return 0.0
    over = min(sa[3], sb[3]) - max(sa[2], sb[2])
    return over * (1 - gap / pitch) if over > 0 else 0.0


def _density_cost(path, placed, pitch):
    """새 경로가 이미 깔린 신호선 구간(`_axis_segs` 꼴) 옆을 얼마나 붙어 달리는가(px)."""
    return sum(_crowding(s, t, pitch) for s in _axis_segs(path) for t in placed)


def _placed_signal_segs(bb):
    return [s for kind, pts, _d in bb._segments if kind in ('sig', 'mid') for s in _axis_segs(pts)]


def wire_metrics(bb):
    """신호선(sig·mid)의 길이(칸)·꺾임·밀도(칸). 밀도는 서로 다른 두 선의 구간 쌍마다 `_crowding`
    을 더한다 — 한 선 안의 구간끼리는 안 센다. 전원·GND·브리지는 안 본다."""
    p = bb.spec.row_pitch
    wires = [pts for kind, pts, _d in bb._segments if kind in ('sig', 'mid')]
    segs = [_axis_segs(pts) for pts in wires]
    length = sum(math.dist(a, b) for pts in wires for a, b in zip(pts, pts[1:]))
    bends = sum(max(len(pts) - 2, 0) for pts in wires)
    dens = sum(_crowding(s, t, p)
               for i in range(len(segs)) for j in range(i + 1, len(segs))
               for s in segs[i] for t in segs[j])
    return {'length': length / p, 'bends': bends, 'density': dens / p}
