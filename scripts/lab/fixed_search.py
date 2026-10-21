"""Deterministic, bounded placement/routing search with immutable LED anchors.

Opt-in beside the historical placer; search never overwrites approved diagrams.
Board adapters supply declared equivalent variants and candidate contexts.
"""
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import copy
import hashlib
import itertools
import json
import math
import tempfile

VERSION = 'fixed-led-search/v1'
ORDERS = ('original', 'long', 'led', 'fanout')
WEIGHTS = (0., .5, 2., 4.)


@dataclass(frozen=True)
class SearchSpec:
    fixed_leds: dict
    budget: int = 256
    slack: float = 1.10
    lower_bridges: bool = False

    def __post_init__(self):
        if type(self.budget) is not int or self.budget < 1 or not math.isfinite(self.slack) or self.slack < 1:
            raise ValueError('budget >= 1 and finite slack >= 1 required')
        object.__setattr__(self, 'fixed_leds', copy.deepcopy(self.fixed_leds))


def key(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def crossings(paths):
    """Unique geometric intersections interior to both wires, including bend vertices.

    Collinear overlap is a physical violation, not a crossing. Endpoints are
    excluded (R2/R3 validate them). Segment endpoints inside a wire are included.
    """
    hits = set()
    for i, left in enumerate(paths):
        for right in paths[i + 1:]:
            for a, b in zip(left, left[1:]):
                ux, uy = b[0] - a[0], b[1] - a[1]
                for c, d in zip(right, right[1:]):
                    vx, vy = d[0] - c[0], d[1] - c[1]
                    den = ux * vy - uy * vx
                    if abs(den) < 1e-9:
                        continue
                    wx, wy = c[0] - a[0], c[1] - a[1]
                    t = (wx * vy - wy * vx) / den
                    u = (wx * uy - wy * ux) / den
                    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
                        p = (a[0] + t * ux, a[1] + t * uy)
                        ends = (left[0], left[-1], right[0], right[-1])
                        if not any(math.dist(p, end) < 1e-7 for end in ends):
                            hits.add(tuple(round(x, 7) for x in p))
    return len(hits)


def metrics(e, bb):
    out = e.wire_metrics(bb)
    out['crossings'] = crossings([pts for k, pts, _ in bb._segments if k in ('sig', 'mid')])
    out['total_length'] = sum(math.dist(a, b) for _, pts, _ in bb._segments
                              for a, b in zip(pts, pts[1:])) / bb.spec.row_pitch
    return out


def select(rows, slack=1.10):
    valid = [r for r in rows if r.get('valid')]
    if not valid:
        raise ValueError('No fully validated candidate; approved diagrams unchanged')
    # Once a placement has a safe lower pair, do not push that same placement
    # further down just to win a secondary signal-routing score.
    def bridge_family(r):
        candidate = r.get('candidate', {})
        lay = candidate.get('layout', {})
        if lay.get('bridge_policy') == 'lower-clearance-v1':
            return key(dict(slots=lay['slots'], leds=lay['leds'], variant=candidate['variant']))
        return None
    nearest = {}
    for r in valid:
        identity = bridge_family(r)
        if identity is not None:
            lay = r['candidate']['layout']
            nearest[identity] = min(nearest.get(identity, math.inf), lay['bridge'][0])
    valid = [r for r in valid if bridge_family(r) is None or
             r['candidate']['layout']['bridge'][0] == nearest[bridge_family(r)]]
    shortest = min(valid, key=lambda r: (r['metrics']['length'], r['key']))
    band = shortest['metrics']['length'] * slack
    inside = [r for r in valid if r['metrics']['length'] <= band + 1e-9]
    chosen = min(inside, key=lambda r: (r['metrics']['density'], r['metrics']['crossings'],
                 r['stage_density'], r['metrics']['bends'], r['metrics']['length'], r['key']))
    return chosen, shortest, band


def pareto(rows):
    """Keep all nondominated measured tradeoffs; no arbitrary scalar proxy cutoff."""
    rows = [r for r in rows if r.get('valid')]
    def vec(r):
        return tuple(r['metrics'][k] for k in ('length', 'density', 'crossings', 'bends'))
    return [r for r in rows if not any(all(a <= b for a, b in zip(vec(q), vec(r)))
            and any(a < b for a, b in zip(vec(q), vec(r))) for q in rows if q is not r)]


def canonical_paths(paths, order):
    result = [None] * len(order)
    for i, path in zip(order, paths):
        result[i] = path
    return result


def wire_order(e, circuit, layout, policy):
    wires = e.place_wires(circuit, layout)
    ids = list(range(len(wires)))
    if policy == 'original':
        return ids
    if policy == 'long':
        chips, pins = e.place_chips(circuit, layout), e.circuit_pins(circuit)
        return sorted(ids, key=lambda i: (-e.place_wire_cost(chips, wires[i], pins), i))
    if policy == 'led':
        return sorted(ids, key=lambda i: ('LED' not in (wires[i][3][0], wires[i][4][0]), i))
    if policy == 'fanout':
        degree = {}
        for w in wires:
            for endpoint in w[3:5]:
                degree[endpoint] = degree.get(endpoint, 0) + 1
        return sorted(ids, key=lambda i: (-sum(degree[p] for p in wires[i][3:5]), i))
    raise ValueError(f'Unknown route order: {policy}')


def validate_anchors(circuits, anchors, e):
    if set(anchors) != {c.name for c in circuits}:
        raise ValueError('Fixed LED circuit names differ')
    for c in circuits:
        rows = anchors[c.name]
        if set(rows) != set(c.leds):
            raise ValueError('Fixed LED tags differ')
        tops = [rows[tag] for tag in c.leds]
        if any(type(t) is not int or t < 3 or t + 3 > e.PLACE_ROW_LAST for t in tops):
            raise ValueError('Fixed LED rows outside board')
        if any(b - a < e.LED_SPAN for a, b in zip(tops, tops[1:])):
            raise ValueError('Fixed LED order/spacing conflict')
        if any(t + 3 in e.RAIL_GAP_ROWS for t in tops):
            raise ValueError('Fixed LED rail hole conflict')


def slot_candidates(e, board):
    """Geometric search domain; actual power/input landings are checked per plan.

    Do not inherit legacy pin1/n assumptions: HC76 has noncorner power pins,
    and rail jumpers can select nearby free holes without moving the chip.
    """
    heights = {s: max(v) for s, v in e.slot_rows(board.PLACE, board.SLOTS).items()}
    for order in itertools.permutations(board.SLOTS):
        for start in getattr(board, 'START_ROWS', e.PLACE_STARTS):
            for gaps in itertools.product(range(getattr(board, 'GMIN', e.PLACE_GMIN), e.PLACE_GMAX + 1),
                                          repeat=len(order) - 1):
                rows = [start]
                for name, gap in zip(order, gaps):
                    rows.append(rows[-1] + heights[name] + gap)
                if rows[-1] + heights[order[-1]] - 1 <= e.PLACE_ROW_LAST:
                    yield dict(zip(order, rows))


def candidates(e, board, spec):
    validate_anchors(board.PLACE, spec.fixed_leds, e)
    rows = e.slot_rows(board.PLACE, board.SLOTS)
    variants = board.search_variants()
    layouts = [copy.deepcopy(board.LAYOUT)]
    layouts += [dict(slots=sl, leds=copy.deepcopy(spec.fixed_leds), bridge=e.bridge_rows(sl, rows))
                for sl in slot_candidates(e, board)]
    ranked = []
    seen = set()
    for lay in layouts:
        lay['leds'] = copy.deepcopy(spec.fixed_leds)
        if lay['bridge'] is None or key(lay) in seen:
            continue
        seen.add(key(lay))
        # A foundation can move only its rail landing without moving an LED.
        # Pin reservations also vary by equivalent assignment, so they cannot
        # safely reject a whole layout here. Validate each actual candidate.
        chips = e.place_chips(board.PLACE[0], lay)
        cost = sum(e.place_wire_cost(chips, w, e.circuit_pins(board.PLACE[0]))
                   for w in e.place_wires(board.PLACE[0], lay))
        ranked.append((cost, lay))
    ranked.sort(key=lambda r: (r[0], key(r[1])))
    # Round-robin chip-order/starting-row families, not merely top proxy scores.
    families = {}
    for cost, lay in ranked:
        family = (tuple(sorted(lay['slots'], key=lay['slots'].get)), min(lay['slots'].values()))
        families.setdefault(family, []).append((cost, lay))
    diverse = []
    for depth in range(max(map(len, families.values()), default=0)):
        for family in sorted(families):
            if depth < len(families[family]):
                diverse.append(families[family][depth][1])
    # Keep proxy leaders as well as families; approved placement always leads.
    ordered = [copy.deepcopy(board.LAYOUT)]
    ordered[0]['leds'] = copy.deepcopy(spec.fixed_leds)
    for a, b in itertools.zip_longest([lay for _, lay in ranked], diverse):
        ordered.extend(x for x in (a, b) if x is not None)
    unique, seen = [], set()
    for lay in ordered:
        if key(lay) not in seen:
            seen.add(key(lay))
            unique.append(lay)
    result = []
    # Visit many placements before exhausting every assignment of any one.
    # First wave pairs the original assignment with rotating alternatives.
    seen = set()
    for wave in range(len(variants)):
        for i, lay in enumerate(unique):
            choices = [variants[0], variants[1 + i % (len(variants) - 1)]] if wave == 0 and len(variants) > 1 else [variants[wave]]
            for variant in choices:
                candidate = dict(layout=lay, variant=variant)
                candidate['key'] = key(candidate)
                if candidate['key'] not in seen:
                    seen.add(candidate['key'])
                    result.append(candidate)
    if spec.lower_bridges:
        # New diagrams only: visit the nearest lower pairs of each placement.
        # Keep generation bounded by the route budget, rather than multiplying
        # the complete placement/assignment domain by every rail row pair.
        lower = []
        for candidate in result:
            for lay in e.lower_bridge_candidates(board.PLACE, candidate['layout']):
                c = dict(layout=lay, variant=copy.deepcopy(candidate['variant']))
                c['key'] = key(c)
                lower.append(c)
                if len(lower) >= spec.budget:
                    return lower
        return lower
    return result


def evaluate_batch(tasks, budget, evaluate, mapper=None):
    mapper = mapper or (lambda fn, xs: list(map(fn, xs)))
    return list(mapper(evaluate, tasks[:budget]))


def _new_board(e, board):
    bb = e.BreadboardRenderer(board='v2')
    bb.led_order_policy = 'fixed'
    bb.route_avoid_bodies = True
    bb.side_lead_max = getattr(board, 'SIDE_LEAD_MAX', e.SIDE_LEAD_MAX)
    return bb


def _signal_plan(e, board, candidate, weight, policy):
    circuit = board.search_circuit(candidate['variant'])
    lay = candidate['layout']
    def fixed(bb, stage, superset=False):
        bb.bridge_policy = lay.get('bridge_policy')
        bb.led_order_policy = 'fixed'
        bb.route_avoid_bodies = True
        bb.side_lead_max = getattr(board, 'SIDE_LEAD_MAX', e.SIDE_LEAD_MAX)
        board.search_fixed(bb, lay, candidate['variant'])
    order = wire_order(e, circuit, lay, policy)
    wires = e.place_wires(circuit, lay)
    # Route only permanent signal wires. Temporary rail ties are reserved below
    # against the exact live signal prefixes, never a fictitious all-stage union.
    plans = e.route_plan(fixed, e.place_chips(circuit, lay), [wires[i] for i in order],
                         density_weight=weight)
    plans = canonical_paths(plans, order)
    bb = _new_board(e, board)
    bb.enable_steps()
    fixed(bb, None)
    for w, (path, marker) in zip(wires, plans):
        bb.step_wire(path, w[2], w[5], marker_at=marker)
    plans = e._resettle_markers(bb, plans)
    return circuit, plans


def temporary_plan(e, board, candidate, circuit, plans):
    """Reserve input-to-rail ties against every signal prefix they coexist with.

    All ties coexist initially; allowing earlier reservations is conservative.
    Ground/power diagonals are legal here, while signal routing stays orthogonal.
    Final validation uses the unmodified physical checks on actual stage boards.
    """
    temps = []
    lay = candidate['layout']
    chips = e.place_chips(circuit, lay)
    for first, u, pin, kind in board.search_temporaries(candidate['variant']):
        bb = _new_board(e, board)
        bb.enable_steps()
        board.search_fixed(bb, lay, candidate['variant'])
        e.draw_routed(bb, circuit.wires, plans, first - 1)
        for _f, pu, pp, pk, pts in temps:
            side = e._dip_side(pp, 16)
            rr = e._dip_pin_row(chips[pu], pp, 16)
            bb.step_wire(pts, pk, 'temporary', marker_at=(80 if side == 'a' else 1160, bb.r_y(rr)))
        L = bb.cols['left']
        row, side = e._dip_pin_row(chips[u], pin, 16), e._dip_side(pin, 16)
        rail = L[kind] if side == 'a' else L['mid_' + kind]
        others = [pt for _, pts, _ in bb._segments for pt in (pts[0], pts[-1])]
        others += [(x, bb.r_y(r)) for (x, r), what in bb._leads.items()
                   if any(tag in what for tag in ('다리', '애노드', '캐소드'))]
        segs = [(k, pts) for k, pts, _ in bb._segments]
        boxes = e._seg_boxes(segs)
        rail_rows = sorted((r for r in range(3, 62) if bb.is_rail_row(r)
                            and (rail, r) not in bb._leads and (rail, r) not in bb._passed),
                           key=lambda r: (abs(r - row), r))
        found = None
        for rr in rail_rows:
            if abs(rr - row) > 20:
                continue
            for col in ('abcd' if side == 'a' else 'jihg'):
                x = L[col]
                if (x, row) in bb._leads or (x, row) in bb._passed:
                    continue
                routes = [[(x, bb.r_y(row)), (rail, bb.r_y(rr))]]
                for dy, rx in itertools.product((.5, -.5, 1.5, -1.5), (rail - 12, rail + 12)):
                    lane = bb.r_y(row + dy)
                    routes.append(e._clean([(x, bb.r_y(row)), (x, lane), (rx, lane),
                                             (rx, bb.r_y(rr)), (rail, bb.r_y(rr))]))
                for path in routes:
                    if e._valid(bb, path, others, segs, boxes, allow_diagonal=True):
                        found = path
                        break
                if found:
                    break
            if found:
                break
        if found is None:
            raise AssertionError(f'Temporary route not found: {first} {u} pin {pin}')
        temps.append([first, u, pin, kind, found])
    return temps


def evaluate(e, board, task, output=None):
    candidate = task['candidate']
    row = dict(key=key(task), candidate=candidate, weight=task['weight'], order=task['order'], valid=False)
    try:
        circuit, plans = _signal_plan(e, board, candidate, task['weight'], task['order'])
        temps = temporary_plan(e, board, candidate, circuit, plans)
        row.update(validate_plan(e, board, candidate, plans, temps, output))
        row.update(plans=plans, temporaries=temps, valid=True)
    except (AssertionError, ValueError) as exc:
        row['failure'] = str(exc)[:1800]
    return row


def validate_plan(e, board, candidate, plans, temps, output=None):
    """All real preparation/removal/stage/final boards use this very plan."""
    with board.search_context(candidate, plans, temps, validation_only=output is None):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(output or tmp)
            dest.mkdir(parents=True, exist_ok=True)
            stages, base = [], None
            for name, fn, st in board.BOARDS:
                for prep_name, prep_fn in getattr(board, 'ASSEMBLY_BOARDS', {}).get(name, []):
                    prep = prep_fn(dest / prep_name)
                    prep.verify()
                    e.check_lower_bridges(prep, candidate['layout'])
                    board.search_assert_equivalent(prep, prep_name)
                bb = fn(dest / name, stage=st, baseline=base)
                bb.verify()
                e.check_lower_bridges(bb, candidate['layout'])
                base = bb.snapshot()
                stages.append(metrics(e, bb))
                board.search_assert_drivers(bb, st)
                board.search_assert_equivalent(bb, name)
            for name, fn in board.FINALS:
                final = fn(dest / name)
                final.verify()
                e.check_lower_bridges(final, candidate['layout'])
                board.search_assert_equivalent(final, name)
            if bb._segments != final._segments or bb.nets() != final.nets():
                raise AssertionError('Procedure final differs from final diagram')
            if [l['tag'] for l in sorted(final.leds, key=lambda l: l['anode'][2])] != list(circuit_tags(board)):
                raise AssertionError('Final LED order changed')
            return dict(metrics=metrics(e, final), stage_density=max(m['density'] for m in stages),
                        stage_crossings=max(m['crossings'] for m in stages), stages=stages,
                        board_count=len(stages) + len(board.FINALS) +
                        sum(map(len, getattr(board, 'ASSEMBLY_BOARDS', {}).values())))


def circuit_tags(board):
    return board.PLACE[0].leds


_WORKER = {}


def _init(path):
    from scripts.lab.place_search import load
    _WORKER['engine'], _WORKER['board'] = load(path)


def _worker(task):
    e, b = _WORKER['engine'], _WORKER['board']
    e._ORDERED.clear()
    return evaluate(e, b, task)


def task(candidate, weight=.5, order='original'):
    return dict(candidate=candidate, weight=weight, order=order)


def neighbors(e, board, seeds, spec):
    sizes = e.slot_rows(board.PLACE, board.SLOTS)
    out = []
    for seed in seeds:
        base = seed['candidate']
        slots = base['layout']['slots']
        changes = []
        for s in sorted(slots):
            for delta in (-2, -1, 1, 2):
                new = dict(slots)
                new[s] += delta
                changes.append(new)
        physical = sorted(slots, key=slots.get)
        for a, b in zip(physical, physical[1:]):
            new = dict(slots)
            new[a], new[b] = new[b], new[a]
            changes.append(new)
        for sl in changes:
            order = sorted(sl, key=sl.get)
            if min(sl.values()) < 3 or any(sl[b] - sl[a] - max(sizes[a]) < 3
                                         for a, b in zip(order, order[1:])):
                continue
            bridge = e.bridge_rows(sl, sizes)
            if bridge is None:
                continue
            lay = dict(slots=sl, leds=copy.deepcopy(spec.fixed_leds), bridge=bridge)
            c = dict(layout=lay, variant=base['variant'])
            c['key'] = key(c)
            out.append(task(c, seed['weight'], seed['order']))
        for variant in board.search_variants():
            c = dict(layout=copy.deepcopy(base['layout']), variant=variant)
            c['key'] = key(c)
            out.append(task(c, seed['weight'], seed['order']))
    return out


def policy_tasks(seeds, budget):
    """Allocate complete 4-order × 4-weight profiles within this phase's budget.

    Truncating an 8-seed Cartesian product systematically skips high weights.
    Bound seed count instead, retaining all settings for each selected seed.
    """
    count = max(1, min(4, budget // (len(WEIGHTS) * len(ORDERS))))
    picked, seen = [], set()
    for seed in seeds:
        c = seed['candidate']
        identity = key((c['layout'], c['variant']))
        if identity not in seen:
            picked.append(seed)
            seen.add(identity)
        if len(picked) == count:
            break
    return [task(r['candidate'], w, policy) for w, policy in itertools.product(WEIGHTS, ORDERS)
            for r in picked]


def run(e, board, path, spec, jobs=1, progress=None):
    if len(board.PLACE) != 1:
        raise ValueError('Fixed search currently requires one circuit per adapter')
    if spec.fixed_leds != board.LAYOUT['leds']:
        raise ValueError('Fixed anchors differ from approved LED coordinates')
    pool = None
    if jobs > 1:
        pool = ProcessPoolExecutor(jobs, initializer=_init, initargs=(str(path),))
    mapper = (lambda fn, xs: list(pool.map(_worker, xs))) if pool else None
    rows, seen = [], set()
    def batch(todo, count):
        if count <= 0:
            return
        unique = []
        for t in todo:
            k = key(t)
            if k not in seen:
                seen.add(k)
                unique.append(t)
                if len(unique) == count:
                    break
        # Fixed-size batches, independent of jobs count and worker completion order.
        for start in range(0, len(unique), 8):
            rows.extend(evaluate_batch(unique[start:start + 8], min(8, spec.budget - len(rows)),
                                       lambda t: evaluate(e, board, t), mapper))
            if progress:
                progress(len(rows), sum(r.get('valid', False) for r in rows))
    try:
        cs = candidates(e, board, spec)
        # Approved frozen plan is independently validated and remains a fallback;
        # it does not consume a new route-generation attempt.
        baseline = board.search_baseline()
        base_eval = validate_plan(e, board, baseline['candidate'], baseline['plans'], baseline['temporaries'])
        baseline.update(base_eval, valid=not spec.lower_bridges, key='approved-baseline', baseline=True)
        half = max(1, spec.budget // 2)
        batch([task(c) for c in cs], half)
        archive = pareto(rows + [baseline])
        seeds = sorted(archive, key=lambda r: (r['metrics']['density'], r['metrics']['length'], r['key']))
        variants = policy_tasks(seeds, max(1, spec.budget // 4))
        batch(variants, max(1, spec.budget // 4))
        archive = pareto(rows + [baseline])
        seeds = sorted(archive, key=lambda r: (r['metrics']['density'], r['metrics']['length'], r['key']))
        nearby = neighbors(e, board, seeds[:8], spec)
        if spec.lower_bridges:
            # Neighbors must pass the same lower-corridor contract; never fall
            # back to a legacy bridge when all lower candidates are blocked.
            for task_ in nearby:
                task_['candidate']['layout']['bridge_policy'] = 'lower-clearance-v1'
                task_['candidate'].pop('key', None)
                task_['candidate']['key'] = key(task_['candidate'])
        batch(nearby, spec.budget - len(rows))
        # If refinement ran out of unseen neighbors, spend remaining attempts on
        # diverse global candidates instead of silently ending early.
        batch((task(c, w, policy) for w, policy in itertools.product(WEIGHTS, ORDERS) for c in cs),
              spec.budget - len(rows))
        chosen, shortest, band = select(rows + [baseline], spec.slack)
        return dict(schema=VERSION, spec=asdict(spec), fingerprint=fingerprint(e, board, spec),
                    attempts=len(rows), candidate_count=len(cs), baseline=baseline,
                    selected=chosen, shortest=shortest, band=band, rows=rows,
                    pareto_keys=[r['key'] for r in pareto(rows + [baseline])])
    finally:
        if pool:
            pool.shutdown()


def fingerprint(e, board, spec):
    paths = [Path(e.__file__), Path(board.__file__), Path(__file__)]
    paths += sorted((Path(e.__file__).parent / 'engine').glob('*.py'))
    paths += sorted((Path(e.REPO_ROOT) / '.claude/assets/breadboard_v2').glob('*'))
    paths = [p for p in paths if p.is_file()]
    data = dict(version=VERSION, spec=asdict(spec), variants=board.search_variants(),
                baseline=board.search_baseline(),
                files={str(p.relative_to(Path(e.REPO_ROOT))): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in paths})
    return hashlib.sha256(key(data).encode()).hexdigest()


def report(result):
    lines = ['# LED 고정 배치 탐색 검증', '',
             f"경로 계산 {result['attempts']}회 / 예산 {result['spec']['budget']}회. "
             '지정한 탐색 범위에서 검증된 최선이며 전역 최적성은 보장하지 않는다.', '',
             f"최단 검증 길이 × {result['spec']['slack']} = {result['band']:.4f}칸 이내에서 "
             '밀도 → 교차 → 단계 최대 밀도 → 꺾임 → 길이 순으로 선택.', '',
             '| 후보 | 길이 | 밀도 | 교차 | 꺾임 | 단계 최대 밀도 | 전체 배선 길이 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for name, row in [('기존 승인본', result['baseline']), ('최단 후보', result['shortest']),
                      ('선택 후보', result['selected'])]:
        m = row['metrics']
        lines.append(f"| {name} | {m['length']:.4f} | {m['density']:.4f} | {m['crossings']} | "
                     f"{m['bends']} | {row['stage_density']:.4f} | {m['total_length']:.4f} |")
    lines += ['', f"고정 LED: `{key(result['spec']['fixed_leds'])}`", '',
              f"지문: `{result['fingerprint']}`", '',
              '실패는 해당 경로 탐색/검증의 실패이며 배치의 불가능성 증명이 아니다.',
              '승인 배치·결선도·측정 기록은 자동으로 교체하지 않는다.', '']
    if result['spec'].get('lower_bridges'):
        pair = result['selected']['candidate']['layout']['bridge']
        lines += [f'긴 전원 브리지: GND {pair[0]}행 · +5V {pair[1]}행 (`lower-clearance-v1`).',
                  '같은 칩·LED·등가 할당에서는 여유를 만족하는 가장 가까운 아래쪽 행 쌍을 먼저 고른다.',
                  '기존 기준은 비교용이며 새 브리지 검증 없이 fallback으로 채택하지 않는다.', '']
    return '\n'.join(lines)
