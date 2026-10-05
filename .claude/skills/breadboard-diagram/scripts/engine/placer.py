# 결선도 엔진 조각 — 배치기.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

# ---------------------------------------------------------------------------
# 배치기 (v2) — 칩 슬롯 행·LED 윗행·브리지 행을 고른다. 근사 비용으로 후보 전부를 줄 세우고 앞
# `PLACE_TOP` 개만 route_plan 으로 실측한다. 저작 때 `python -m scripts.lab.place_search <배치.py>` 로
# 돌려 주차 `LAYOUT` 에 옮긴다. 설계: `docs/plans/2026-10-05-v2-배치기-설계.md`.
# layout = {'slots': {슬롯: pin 1 행}, 'leds': {회로: {태그: 윗행}}, 'bridge': [GND 행, VCC 행]} — JSON 그대로.

PLACE_GMIN = 3      # 칩 사이 최소 빈 행 — 실물에서 손이 들어갈 여유(2026-10-05 사용자 N2)
PLACE_GMAX = 6
PLACE_STARTS = tuple(range(3, 9))   # 맨 위 칩 pin 1 행 후보
PLACE_TOP = 8       # 근사 순위 앞 몇 개를 route_plan 으로 실측하나 (한 판에 약 1분)
PLACE_ROUNDS = 3
PLACE_LENGTH_SLACK = 1.02   # 순위 띠 — verify 통과 최단의 ×1.02 안에서 밀도 최소(2026-10-05 사용자 N6)
LED_SPAN = 4        # LED 사슬 한 벌 = 윗행 ~ 윗행+3 (LED 두 행 + 저항 아랫다리)
PLACE_ROW_LAST = 61  # 칩·LED·브리지가 쓸 마지막 행 — 62·63 은 레일 빈 행
PLACE_REPORT = '배치탐색.md'


@dataclass(frozen=True)
class PlaceCircuit:
    """배치기가 보는 회로 하나. `chips` 칩 → 슬롯, `models` 칩 → 모델, `leds` LED 태그 위→아래(진리표 열
    순서, 2026-10-05 사용자 N3), `wires` 는 `route_plan` 꼴이되 LED 끝은 `('LED', 'L1')`. `fixed(bb, stage,
    superset, layout)` 는 고정물을 `layout` 자리에 그린다. `inputs` 는 입력 점퍼가 꽂히는 (칩, 핀)."""
    name: str
    chips: dict
    models: dict
    leds: tuple
    wires: tuple
    fixed: object
    inputs: tuple = ()


def layout_key(layout):
    """layout → 캐시 열쇠(키 정렬 JSON)."""
    return json.dumps(layout, sort_keys=True, ensure_ascii=False)


def place_check(circuit):
    """배치기가 다룰 수 있는 회로인가. 아니면 ValueError."""
    bad = sorted({m for m in circuit.models.values() if m not in DIP_PINS})
    if bad:
        raise ValueError(f'{circuit.name}: 배치기는 칩 모델 표(`DIP_PINS`)에 있는 칩만 놓는다 — {bad}')
    tags = {end[1] for w in circuit.wires for end in (w[3], w[4]) if end[0] == 'LED'}
    unknown = sorted(tags - set(circuit.leds))
    if unknown:
        raise ValueError(f'{circuit.name}: leds 에 없는 LED 태그 {unknown}')


def place_chips(circuit, layout):
    """칩 → pin 1 행."""
    return {chip: layout['slots'][slot] for chip, slot in circuit.chips.items()}


def place_wires(circuit, layout):
    """LED 태그 끝을 그 회로의 LED 윗행으로 바꾼 `route_plan` 배선표."""
    rows = layout['leds'].get(circuit.name, {})

    def end(e):
        return ('LED', rows[e[1]]) if e[0] == 'LED' else e
    return [(s, e, kind, end(f), end(t), desc) for s, e, kind, f, t, desc in circuit.wires]


def place_hash(circuits, slots, gmin=PLACE_GMIN, slack=PLACE_LENGTH_SLACK):
    """배선표 지문(16자리) — 바뀌면 배치를 다시 찾는다. `fixed` 는 안 보고 `slack` 은 든다 —
    `PLACE_LENGTH_SLACK` 을 바꾸면 모든 v2 주차가 다시 돌린다."""
    body = {'slots': list(slots), 'gmin': gmin, 'slack': slack, 'circuits': [
        {'name': c.name, 'chips': c.chips, 'models': c.models, 'leds': list(c.leds),
         'wires': [list(w) for w in c.wires], 'inputs': [list(i) for i in c.inputs]}
        for c in circuits]}
    text = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


@lru_cache(maxsize=None)
def _place_geom():
    s = board_spec('v2')
    return s.cols['left'], s.cols['right'], s.row_pitch


def circuit_pins(circuit):
    """칩 → 핀 수. `place_check` 를 지난 회로만 — 모르는 칩은 ValueError."""
    return {chip: dip_pins(m, strict=True) for chip, m in circuit.models.items()}


def slot_rows(circuits, slots):
    """슬롯 → 그 슬롯에 앉는 칩들의 행 수 집합(14핀 7, 16핀 8) — 회로마다 다를 수 있다. 빈 슬롯은 {7}."""
    out = {s: set() for s in slots}
    for c in circuits:
        for chip, s in c.chips.items():
            out[s].add(dip_pins(c.models[chip], strict=True) // 2)
    return {s: (v or {7}) for s, v in out.items()}


def place_wire_cost(chips, wire, pins=None):
    """선 하나의 근사 비용(px) — 최소 맨해튼 + 40·꺾임 + 400·몸통(`_coster` 와 같은 상수). 경로·점유는
    안 본다 — 순위만 매긴다. `pins` 는 칩 → 핀 수(없으면 14)."""
    L, R, pitch = _place_geom()
    _s, _e, _k, frm, to, _d = wire
    pins = pins or {}

    def holes(end):
        if end[0] == 'LED':
            return [(R['a'], end[1])], None
        n = pins.get(end[0], 14)
        row = _dip_pin_row(chips[end[0]], end[1], n)
        side = _dip_side(end[1], n)
        return [(L[c], row) for c in _STRIP_COLS[side]], side

    ha, sa = holes(frm)
    hb, sb = holes(to)
    dist = min(abs(xa - xb) + abs(ra - rb) * pitch for xa, ra in ha for xb, rb in hb)
    led = 'LED' in (frm[0], to[0])
    bends = 2 if led or ha[0][1] != hb[0][1] else 0
    if led:
        body = 1 if 'a' in (sa, sb) else 0
    else:
        body = 1 if frm[0] == to[0] and sa != sb else 0
    return dist + 40 * bends + 400 * body


def mid_rail_rows(circuit, slots, bridge):
    """가운데 레일에서 이미 쓰는 행 — 칩 전원선·브리지·f쪽 입력 점퍼. LED 레일 점퍼가 여기 착지하면
    옆 행으로 비켜 사선이 된다."""
    used = {slots[s] for s in circuit.chips.values()}
    rows = used | set(bridge)
    pins = circuit_pins(circuit)
    for chip, pin in circuit.inputs:
        if _dip_side(pin, pins[chip]) == 'f':
            rows.add(_dip_pin_row(slots[circuit.chips[chip]], pin, pins[chip]))
    return rows


def bridge_rows(slots, rows=None):
    """브리지 두 가닥 [GND 행, VCC 행] — 맨 아래 칩 아래로 2행 이상 띄운 첫 연속 비간극 두 행(칩 행이면
    핀 위를 지난다). 자리가 없으면 None. `rows` 는 `slot_rows`."""
    rows = rows or {}
    r = max(k + max(rows.get(s, {7})) - 1 for s, k in slots.items()) + 3
    while r + 1 <= PLACE_ROW_LAST:
        if r not in RAIL_GAP_ROWS and r + 1 not in RAIL_GAP_ROWS:
            return [r, r + 1]
        r += 1
    return None


def led_rows(circuit, slots, bridge):
    """회로의 LED 윗행 {태그: 행} — DP. 태그 순서대로 위→아래(R10, N3), 사슬끼리 `LED_SPAN` 행 이상,
    윗행+3(레일 점퍼 행)이 레일 빈 행·가운데 레일 사용 행이 아니다. 그 LED 로 가는 모든 단계 선의 근사
    비용 합이 가장 작은 조합(동률은 위쪽). LED 가 없으면 {}, 못 놓으면 None."""
    if not circuit.leds:
        return {}
    chips = {c: slots[s] for c, s in circuit.chips.items()}
    pins = circuit_pins(circuit)
    busy = RAIL_GAP_ROWS | mid_rail_rows(circuit, slots, bridge)
    tops = [t for t in range(3, PLACE_ROW_LAST - LED_SPAN + 2) if t + LED_SPAN - 1 not in busy]
    # 태그마다 그 LED 로 가는 선만 미리 — 후보마다 배선표 전체를 훑지 않게
    mine = {tag: [w for w in circuit.wires if ('LED', tag) in (w[3], w[4])] for tag in circuit.leds}

    def cost(tag, top):
        def sub(e):
            return ('LED', top) if e == ('LED', tag) else e
        return sum(place_wire_cost(chips, (s, e, k, sub(f), sub(t), d), pins)
                   for s, e, k, f, t, d in mine[tag])

    prev = None
    for tag in circuit.leds:
        here = [cost(tag, t) for t in tops]
        if prev is None:
            cur = [(c, (t,)) for c, t in zip(here, tops)]
        else:
            cur, best, j = [], None, 0
            for t, c in zip(tops, here):
                while j < len(tops) and tops[j] + LED_SPAN <= t:
                    if prev[j] is not None and (best is None or prev[j] < best):
                        best = prev[j]
                    j += 1
                cur.append(None if best is None else (best[0] + c, best[1] + (t,)))
        prev = cur
    done = [x for x in prev if x is not None]
    if not done:
        return None
    return dict(zip(circuit.leds, min(done)[1]))


def place_r10_ok(circuit, chips, leds):
    """단계마다 LED 로 건너는 선의 칩 쪽 행 순서가 LED 위아래 순서와 같은가 — `verify()` R10 을 미리
    본다. 단계 k 에 살아 있는 선 = `s <= k` 이고 끝 단계가 없거나 `k <= e` (`draw_routed` 와 같다)."""
    pins = circuit_pins(circuit)
    stages = {w[0] for w in circuit.wires} | {w[1] for w in circuit.wires if w[1] is not None}
    for st in sorted(stages):
        live = []
        for s, e, _k, f, t, _d in circuit.wires:
            if not (s <= st and (e is None or st <= e)):
                continue
            for led, chip in ((t, f), (f, t)):
                if led[0] == 'LED' and chip[0] != 'LED':
                    live.append((leds[led[1]], _dip_pin_row(chips[chip[0]], chip[1], pins[chip[0]])))
        live.sort()
        if any(c1 > c2 for (_a, c1), (_b, c2) in zip(live, live[1:])):
            return False
    return True


def slot_candidates(slots, gmin=PLACE_GMIN, gmax=PLACE_GMAX, starts=PLACE_STARTS, rows=None):
    """슬롯 → pin 1 행 후보 [dict]. 순서(순열, N4) × 맨 위 행 × 칩 사이 빈 행 gmin~gmax. 칩 VCC·GND 행이
    레일 빈 행이거나(전원선이 사선이 된다) 브리지 자리가 없으면 버린다. `rows` 는 `slot_rows`."""
    rows = rows or {}
    out = []
    for order in itertools.permutations(slots):
        for k0 in starts:
            for gaps in itertools.product(range(gmin, gmax + 1), repeat=len(slots) - 1):
                ks = [k0]
                for s, g in zip(order, gaps):
                    ks.append(ks[-1] + max(rows.get(s, {7})) + g)
                if any(k in RAIL_GAP_ROWS or any(k + r - 1 in RAIL_GAP_ROWS for r in rows.get(s, {7}))
                       for s, k in zip(order, ks)):
                    continue
                cand = dict(zip(order, ks))
                if bridge_rows(cand, rows) is not None:
                    out.append(cand)
    return out


def place_proxy(circuits, slots):
    """슬롯 후보 하나 → (근사 비용 합, layout). LED 를 못 놓거나 R10 이 어긋나거나 입력 핀 행이 레일
    빈 행이면 None."""
    for c in circuits:
        pins = circuit_pins(c)
        if any(_dip_pin_row(slots[c.chips[chip]], pin, pins[chip]) in RAIL_GAP_ROWS for chip, pin in c.inputs):
            return None
    bridge = bridge_rows(slots, slot_rows(circuits, slots))
    layout = {'slots': dict(slots), 'leds': {}, 'bridge': bridge}
    total = 0.0
    for c in circuits:
        leds = led_rows(c, slots, bridge)
        if leds is None:
            return None
        chips = place_chips(c, layout)
        if not place_r10_ok(c, chips, leds):
            return None
        layout['leds'][c.name] = leds
        total += sum(place_wire_cost(chips, w, circuit_pins(c)) for w in place_wires(c, layout))
    return total, layout


_PLACE_PATHS = {}


def place_paths(circuit, layout, density_weight=None):
    """`layout` 자리에서 `route_plan` 경로 — 회로·배선표·자리·λ 마다 한 번(사본별 캐시 `_PLACE_PATHS`)."""
    w = DENSITY_WEIGHT if density_weight is None else density_weight
    key = (circuit.name, place_hash([circuit], ()), layout_key(layout), w)
    if key not in _PLACE_PATHS:
        def fixed(bb, stage, superset=False):
            circuit.fixed(bb, stage, superset, layout)
        _PLACE_PATHS[key] = route_plan(fixed, place_chips(circuit, layout), place_wires(circuit, layout),
                                       board='v2', density_weight=w)
    return _PLACE_PATHS[key]


_PLACE_HINTS = {}


def place_marker_hints(circuit, layout):
    """superset 판에서 엔진 고정 부품 번호 원이 비킨 자리 {열쇠: (x, y)}. 빌더가 `bb.marker_hints` 로 주면
    단계 그림·완성본이 같은 자리를 쓴다(2026-10-05)."""
    key = (circuit.name, place_hash([circuit], ()), layout_key(layout))
    if key not in _PLACE_HINTS:
        bb = BreadboardRenderer(None, board='v2')
        bb.enable_steps()
        circuit.fixed(bb, None, True, layout)
        _PLACE_HINTS[key] = dict(bb.settled_markers)
    return _PLACE_HINTS[key]


def place_metrics(circuit, layout, density_weight=None):
    """superset 판(모든 단계의 선 — 학생이 그 회로를 꽂는 동안 꽂는 선 전부)의 `wire_metrics`."""
    plans = place_paths(circuit, layout, density_weight)
    bb = BreadboardRenderer(None, board='v2')
    bb.enable_steps()
    circuit.fixed(bb, None, True, layout)
    for (_s, _e, kind, _f, _t, desc), (p, m) in zip(place_wires(circuit, layout), plans):
        bb.step_wire(p, kind, desc, marker_at=m)
    return wire_metrics(bb)


def _place_measure(circuits, layout):
    """회로마다 superset 지표를 더한다. 막히면 {'blocked': 첫 줄}."""
    tot = {'length': 0.0, 'bends': 0, 'density': 0.0}
    try:
        for c in circuits:
            m = place_metrics(c, layout)
            for k in tot:
                tot[k] += m[k]
    except AssertionError as e:
        return {'blocked': str(e).splitlines()[0]}
    return tot


def place_verify(module, layout, out_dir):
    """주차 모듈의 `BOARDS` 사슬(`RESTART` 에서 끊고)과 `FINALS` 를 `layout` 으로 다 그려 본다 — 막히면
    '보드: 사유' 한 줄, 통과하면 None. 모듈 `LAYOUT` 은 그리는 동안만 바꾼다."""
    saved, name = module.LAYOUT, None
    module.LAYOUT = layout
    try:
        base = None
        for name, fn, stage in module.BOARDS:
            if name in getattr(module, 'RESTART', ()):
                base = None
            bb = fn(os.path.join(out_dir, name), None, stage=stage, baseline=base)
            base = bb.snapshot()
        for name, fn in module.FINALS:
            fn(os.path.join(out_dir, name))
    except AssertionError as e:
        lines = [x.strip() for x in str(e).splitlines() if x.strip()]
        return f'{name}: ' + ' '.join(lines[:2])
    finally:
        module.LAYOUT = saved
    return None


def place_module_hash(module):
    return place_hash(module.PLACE, module.SLOTS, getattr(module, 'GMIN', PLACE_GMIN))


def _serial_map(fn, items):
    return [fn(x) for x in items]


def place_pick(rows, slack=PLACE_LENGTH_SLACK):
    """verify 를 통과한 후보 → (고를 행, 띠 상한). 최단 길이 × `slack` 띠 안에서 (밀도, 꺾임, 길이) 최소
    (2026-10-05 사용자 N6). `route_sweep.py` `pick` 과 같은 꼴."""
    band = min(x['length'] for x in rows) * slack
    inside = [x for x in rows if x['length'] <= band + 1e-9]
    return min(inside, key=lambda x: (x['density'], x['bends'], x['length'], layout_key(x['layout']))), band


def place_plan(module, top=PLACE_TOP, rounds=PLACE_ROUNDS, gmin=None, out_dir=None,
               measure=None, verify=None, mapper=None, chunk=1, slack=PLACE_LENGTH_SLACK):
    """주차 모듈의 칩 행·LED 행·브리지 행을 고른다.

    1. 슬롯 후보 전부를 `place_proxy` 로 줄 세운다.
    2. 기준(지금 `LAYOUT`)과 앞 `top` 개를 실측한다(`measure`).
    3. 기준보다 짧고 밀도가 기준 이하인 것을 전부 `verify` 하고, 통과한 것 중 `place_pick`(N6). 없으면
       다음 `top` 개, `rounds` 번까지. 그래도 없을 때만 기준을 verify 한다(N5). 기준보다 긴 배치는 안 고른다.
    `mapper(fn, items)` 로 라운드마다 실측을 한 묶음에, verify 는 길이 순 `chunk` 개씩 돌린다 —
    `place_search --jobs` 가 프로세스 풀을 넘긴다. 돌려주는 값 {'hash', 'layout', 'rows', 'slack'} —
    rows 는 실측한 후보마다 {'rank', 'proxy', 'layout', 'length', 'bends', 'density' | 'blocked', 'status'}."""
    circuits, slots = list(module.PLACE), tuple(module.SLOTS)
    for c in circuits:
        place_check(c)
    gmin = getattr(module, 'GMIN', PLACE_GMIN) if gmin is None else gmin
    measure = measure or (lambda lay: _place_measure(circuits, lay))
    if verify is None:
        def verify(lay):
            if out_dir:
                return place_verify(module, lay, out_dir)
            # 판마다 지운다 — 안 지우면 탐색마다 수백 MB
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                return place_verify(module, lay, tmp)
    rows_ = slot_rows(circuits, slots)
    ranked = sorted((r for r in (place_proxy(circuits, s) for s in slot_candidates(slots, gmin, rows=rows_))
                     if r is not None), key=lambda r: (r[0], layout_key(r[1])))
    mapper = mapper or _serial_map
    base, rows, chosen, seen = None, [], None, {layout_key(module.LAYOUT)}
    for r in range(rounds):
        todo = [] if base else [dict(rank='기준', proxy=None, layout=module.LAYOUT)]
        for i in range(r * top, min((r + 1) * top, len(ranked))):
            proxy, lay = ranked[i]
            if layout_key(lay) in seen:
                continue
            seen.add(layout_key(lay))
            todo.append(dict(rank=i + 1, proxy=round(proxy), layout=lay))
        for x, m in zip(todo, mapper(measure, [x['layout'] for x in todo])):
            x.update(m)
        rows += todo
        if base is None:
            base = rows[0]
            if 'blocked' in base:
                raise AssertionError(f"기준 LAYOUT 이 막힌다 — {base['blocked']}")
            limit = base['density'] + 1e-9
        ok = sorted((x for x in rows[1:] if 'blocked' not in x and 'status' not in x
                     and x['density'] <= limit and x['length'] < base['length']),
                    key=lambda x: (x['length'], x['density'], layout_key(x['layout'])))
        for j in range(0, len(ok), chunk):
            part = ok[j:j + chunk]
            for x, why in zip(part, mapper(verify, [x['layout'] for x in part])):
                x['status'] = '통과' if why is None else f'verify: {why}'
        passed = [x for x in ok if x['status'] == '통과']
        if passed:
            chosen, band = place_pick(passed, slack)
            for x in passed:
                x['status'] = ('✔ 고름' if x is chosen
                               else '통과 — 띠 안' if x['length'] <= band + 1e-9 else '통과 — 띠 밖')
            break
    if chosen is None:
        why = mapper(verify, [base['layout']])[0]
        base['status'] = '✔ 고름' if why is None else f'verify: {why}'
        if why is None:
            chosen = base
    for x in rows:
        x.setdefault('status', f"막힘: {x['blocked']}" if 'blocked' in x
                     else '밀도 초과' if x['density'] > limit
                     else '기준보다 김' if x is not base and x['length'] >= base['length'] else '')
    if chosen is None:
        raise AssertionError('고를 배치가 없다 — 기준 ' + base['status'])
    return {'hash': place_hash(circuits, slots, gmin, slack), 'layout': chosen['layout'], 'rows': rows,
            'slack': slack}


def place_report(result, title):
    """`배치탐색.md` 본문. 첫 JSON 블록(지문·고른 layout)을 테스트가 읽는다 — 손으로 고치지 않는다."""
    head = json.dumps({'hash': result['hash'], 'layout': result['layout']},
                      ensure_ascii=False, indent=1, sort_keys=True)
    lines = [f'# 배치 탐색 — {title}', '',
             '`python -m scripts.lab.place_search <배치.py>` 가 쓴다. 배선표가 바뀌면 다시 돌린다 — '
             '고른 layout 은 `배치.py` 의 `LAYOUT` 과 netlist `kind: layout` 표에 옮겨 적는다.', '',
             '```json', head, '```', '',
             '길이·밀도는 superset 판(모든 단계의 선) 칸 단위, 회로 합이다. 기준 = 탐색 시점 `LAYOUT`.', '',
             f"순위: 기준보다 짧고 밀도가 기준 이하인 후보를 모두 verify 하고, 통과한 것 중 최단 길이의 "
             f"×{result.get('slack', PLACE_LENGTH_SLACK):g} 안에서 밀도가 가장 낮은 것(동률은 꺾임·길이).", '',
             '| 순위 | 근사(px) | 길이 | 꺾임 | 밀도 | 슬롯 | LED | 결과 |',
             '|---|---|---|---|---|---|---|---|']
    for x in result['rows']:
        slots = ' '.join(f'{k}:{v}' for k, v in sorted(x['layout']['slots'].items()))
        leds = ' '.join(f'{t}:{r}' for c in sorted(x['layout']['leds'])
                        for t, r in x['layout']['leds'][c].items())
        proxy = '' if x['proxy'] is None else x['proxy']
        if 'blocked' in x:
            lines.append(f"| {x['rank']} | {proxy} | — | — | — | {slots} | {leds} | {x['status']} |")
        else:
            lines.append(f"| {x['rank']} | {proxy} | {x['length']:.1f} | {x['bends']} | "
                         f"{x['density']:.1f} | {slots} | {leds} | {x['status']} |")
    return '\n'.join(lines) + '\n'


def read_place_report(path):
    """`배치탐색.md` 의 첫 JSON 블록 → {'hash', 'layout'}."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'```json\n(.*?)\n```', text, re.S)
    if not m:
        raise ValueError(f'{path}: JSON 블록이 없다')
    return json.loads(m.group(1))
