"""실험07 6-bit shift register — v2 보드, v3 관측 절차.

BIT1/3/5 = 각 HC76 둘째 F/F(J9 K12 Q11 Q'10), BIT2/4/6 = 첫째 F/F.
패키지 경계는 Q15→J9, Q'14→K12로 모두 f쪽이다(R8 유지).
LED 실제 순서는 BIT1~BIT6다. 사용자 승인 순서에 한해 R10 순서 역전만 허용한다.
"""
from functools import partial
from pathlib import Path
import json

from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit,
    place_chips, draw_routed, removal_board,
    _dip_pin_row as _pin_row, _dip_side as _side)

class ShiftRenderer(BreadboardRenderer):
    """실험07 승인 숫자 순서만 R10 순서 검사에서 예외로 둔다.

    칩→LED 사슬 이외의 블록 건너기, 홀·넷·리드·가독성 검사는 원래대로다.
    출력 핀 행이 BIT2/1·4/3·6/5여도 관측 LED는 BIT1~6로 배치한다.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.led_order_policy = 'fixed'
        self.validation_only = globals().get('_SEARCH_VALIDATE_ONLY', False)



BOARD = 'v2'
SLOTS = ('S1', 'S2', 'S3', 'S4')
LAYOUT = {'slots': {'S1': 6, 'S2': 16, 'S3': 27, 'S4': 38}, 'leds': {'shift': {'BIT1': 14, 'BIT2': 18, 'BIT3': 26, 'BIT4': 30, 'BIT5': 36, 'BIT6': 40}}, 'bridge': [48, 49]}
SIDE_LEAD_MAX = 12
SIDE_LEAD_MAX_REASON = ('74HC76 두 F/F를 모두 사용한다. 중간 패키지의 a쪽은 CLK 네 끝+CLR 네 끝+'
    'PR 둘+VCC 하나+J 하나=12, f쪽은 J/K/Q/Q보수 여덟 핀 중 GND 포함 8끝+LED 두 끝=10이다. '
    'DIP-16 여덟 행의 32 자유 홀에 분산하며 R1~R6·R8·R9·R11~R14는 그대로 검사하고 R10 순서만 승인 예외다. '
    '입력 분배를 합쳐도 사용 16핀+LED 2가닥으로 총 18끝 이상이므로 양쪽 8로는 불가능하다.')

# (첫 단계, 끝 단계, 색, 출발, 도착, 설명). 배선당 처음 꽂는 단계만 다르고 경로는 동일하다.
_WIRES = [
    (1, None, 'sig', ('U1', 9), ('U1', 10), 'D 두 입력 묶음: U1 pin 9 -> U1 pin 10'),
    (2, None, 'sig', ('U2', 1), ('U2', 6), 'CLK: U2 pin 1 -> U2 pin 6'),
    (2, None, 'sig', ('U2', 6), ('U3', 1), 'CLK: U2 pin 6 -> U3 pin 1'),
    (3, None, 'sig', ('U3', 1), ('U3', 6), 'CLK: U3 pin 1 -> U3 pin 6'),
    (3, None, 'sig', ('U3', 6), ('U4', 1), 'CLK: U3 pin 6 -> U4 pin 1'),
    (3, None, 'sig', ('U4', 1), ('U4', 6), 'CLK: U4 pin 1 -> U4 pin 6'),
    (4, None, 'sig', ('U2', 3), ('U2', 8), 'CLR: U2 pin 3 -> U2 pin 8'),
    (4, None, 'sig', ('U2', 8), ('U3', 3), 'CLR: U2 pin 8 -> U3 pin 3'),
    (5, None, 'sig', ('U3', 3), ('U3', 8), 'CLR: U3 pin 3 -> U3 pin 8'),
    (5, None, 'sig', ('U3', 8), ('U4', 3), 'CLR: U3 pin 8 -> U4 pin 3'),
    (5, None, 'sig', ('U4', 3), ('U4', 8), 'CLR: U4 pin 3 -> U4 pin 8'),
    (7, None, 'sig', ('U1', 9), ('U2', 9), 'D: U1 pin 9 -> U2 pin 9 (BIT1 J)'),
    (7, None, 'sig', ('U1', 8), ('U2', 12), "D' (U1 pin 8) -> U2 pin 12 (BIT1 K)"),
    (7, None, 'sig', ('U2', 11), ('LED', 'BIT1'), 'BIT1 = U2 pin 11 -> LED BIT1'),
]
# 이후 한 BIT마다 J·K·LED 세 가닥. 홀수 BIT는 둘째 F/F, 짝수는 첫째 F/F다.
_BITS = [('U2', 9, 12, 11, 10), ('U2', 4, 16, 15, 14),
         ('U3', 9, 12, 11, 10), ('U3', 4, 16, 15, 14),
         ('U4', 9, 12, 11, 10), ('U4', 4, 16, 15, 14)]
for _i, (_prev, _cur) in enumerate(zip(_BITS, _BITS[1:]), 2):
    _u, _j, _k, _q, _qb = _cur
    _pu, _pj, _pk, _pq, _pqb = _prev
    _WIRES.extend([
        (_i + 6, None, 'mid', (_pu, _pq), (_u, _j), f'BIT{_i-1}: {_pu} pin {_pq} -> {_u} pin {_j} (BIT{_i} J)'),
        (_i + 6, None, 'mid', (_pu, _pqb), (_u, _k), f"BIT{_i-1} 보수: {_pu} pin {_pqb} -> {_u} pin {_k} (BIT{_i} K)"),
        (_i + 6, None, 'sig', (_u, _q), ('LED', f'BIT{_i}'), f'BIT{_i} = {_u} pin {_q} -> LED BIT{_i}'),
    ])
_INPUTS = [(1, 'D', 'U1', 9), (2, 'CLK', 'U2', 1), (4, 'CLR', 'U2', 3),
           (6, 'PR1', 'U2', 7), (6, 'PR2', 'U2', 2)]
_LED_ORDER = ('BIT1', 'BIT2', 'BIT3', 'BIT4', 'BIT5', 'BIT6')


def _fixed(bb, stage, superset=False, layout=None, _with_temps=True, _apply=None):
    # Normal rendering calls each operation directly. Preparation uses the same
    # full reservation pass, replaying selected operations at its exact rail holes.
    def put(group, method, *args, **kwargs):
        if _apply is not None:
            return _apply(group, method, args, kwargs)
        if method == 'input':
            return _input_jumper(bb, *args, **kwargs)
        return getattr(bb, method)(*args, **kwargs)
    lay = layout or LAYOUT
    L, R, k = bb.cols['left'], bb.cols['right'], place_chips(SHIFT, lay)
    for u in ('U1', 'U2', 'U3', 'U4'):
        put(1, 'draw_chip', SHIFT.models[u], k[u])
    put(1, 'connect_jacks')
    put(1, 'bridge_rails', L['gnd'], L['mid_gnd'], lay['bridge'][0], kind='gnd')
    put(1, 'bridge_rails', L['vcc'], L['mid_vcc'], lay['bridge'][1], kind='vcc')
    for u in ('U1', 'U2', 'U3', 'U4'):
        put(int(u[1:]), 'connect_power', k[u], gnd_col='a')
    # 사용하는 PR을 1로 고정한다. 미사용 입력으로 등록하지 않는다.
    for u in ('U3', 'U4'):
        for p in (2, 7):
            row = _pin_row(k[u], p, 16)
            rail_row = bb.free_rail_row(row, L['vcc'])
            put(int(u[1:]), 'step_wire', [(L['a'], bb.r_y(row)), (L['vcc'], bb.r_y(rail_row))], 'vcc',
                         f'{u} pin {p} PR 비활성 -> +5V 레일')
    for first, name, u, p in _INPUTS:
        if superset or stage is None or first <= stage:
            n = 14 if u == 'U1' else 16
            side = _side(p, n)
            put(7, 'input', L, _pin_row(k[u], p, n), name, f'{u} pin {p}',
                          side=side, col='a' if side == 'a' else 'j')
    for tag in _LED_ORDER:
        put(5 if tag in _LED_ORDER[:3] else 6, 'led_chain', R['a'], lay['leds']['shift'][tag], tag,
                     f'{tag}: 출력 1이면 켜짐 · 명세 기록 순서와 같은 숫자 순서', block='right')
    put(1, 'mark_unused_inputs', tuple(_map_pin('U1', p) for p in (1, 2, 4, 5, 12, 13)), k['U1'], chip='74HC00 (U1)')
    put(1, 'mark_unused_outputs', tuple(_map_pin('U1', p) for p in (3, 6, 11)), k['U1'], chip='74HC00 (U1)')
    put(1, 'mark_unused_outputs', (_map_pin('U4', 14),), k['U4'], chip='74HC76 (U4)')

    # a쪽 임시선은 CLK·CLR 분배선과 함께 남는다. f쪽 J/K 임시선은 해당
    # 데이터선 연결 전에 걷는다. 둘을 동시에 superset에 강제하면 존재하지 않는
    # 배선 조합이 경로를 막는다. 실제 모든 단계·걷기 보드는 별도로 verify한다.
    if _with_temps and (superset or stage is not None):
        for active_from, u, pin, kind, path in _temporary_plan(lay):
            if (superset and _side(pin, 16) == 'a') or (not superset and stage < active_from):
                put(int(u[1:]), 'step_wire', path, kind, f'임시 {u} pin {pin} -> {"+5V" if kind == "vcc" else "GND"} · {active_from}걷기에서 뽑아요',
                             marker_at=(80 if _side(pin, 16) == 'a' else 1160, path[0][1]))


# 아직 연결하지 않은 **사용 입력**이다. 미사용 핀으로 등록하거나 플로팅으로 두지 않는다.
_TEMP = [(2, 'U2', 1, 'gnd'), (2, 'U2', 6, 'gnd'), (2, 'U3', 1, 'gnd'),
         (3, 'U3', 6, 'gnd'), (3, 'U4', 1, 'gnd'), (3, 'U4', 6, 'gnd'),
         (4, 'U2', 3, 'gnd'), (4, 'U2', 8, 'gnd'), (4, 'U3', 3, 'gnd'),
         (5, 'U3', 8, 'gnd'), (5, 'U4', 3, 'gnd'), (5, 'U4', 8, 'gnd'),
         (6, 'U2', 7, 'vcc'), (6, 'U2', 2, 'vcc')]
for _i, (_u, _j, _k, _q, _qb) in enumerate(_BITS, 7):
    _TEMP.extend([(_i, _u, _j, 'gnd'), (_i, _u, _k, 'gnd')])


def _temporary_plan(lay):
    # 완성본 경로와 각 임시선의 제거 시점을 함께 고려해 예약한 실제 홀/경로다.
    if lay != _ROUTE_DATA['layout']:
        raise ValueError('실험07 임시 입력선의 승인 배치가 다르다')
    if [row[:4] for row in _ROUTE_DATA['temporaries']] != [list(row) for row in _TEMP]:
        raise ValueError('실험07 임시 입력선 목록이 승인 경로와 다르다')
    return _ROUTE_DATA['temporaries']


_ROUTE_DATA = json.loads((Path(__file__).parent / '설계' / '승인경로.json').read_text(encoding='utf-8'))
_MARKER_HINTS = None


def _approved_paths():
    # 승인 완성본의 경로를 단계·손그림에서도 재사용한다. 낡은 경로는 조용히 쓰지 않는다.
    if _ROUTE_DATA['layout'] != LAYOUT or _ROUTE_DATA['wires'] != json.loads(json.dumps(SHIFT.wires)):
        raise ValueError('실험07 승인경로.json이 현재 배치/배선표와 다르다')
    return _ROUTE_DATA['plans']


def _marker_hints():
    global _MARKER_HINTS
    if _MARKER_HINTS is None:
        proto = ShiftRenderer(board=BOARD)
        proto.enable_steps()
        _fixed(proto, None, False, LAYOUT, _with_temps=False)
        _MARKER_HINTS = dict(proto.settled_markers)
    return _MARKER_HINTS


_ASSEMBLY_TITLES = ('보드·U1 전원 준비', 'U2 입력 고정', 'U3 입력 고정',
                    'U4 입력 고정', '위쪽 LED 준비', '아래쪽 LED 준비')


def _build_assembly(output_path, template_path=None, baseline=None, *, assembly_order):
    if assembly_order not in range(1, 7):
        raise ValueError('준비 순서는 1~6이다')
    bb = ShiftRenderer(template_path, baseline=baseline, palette=True, board=BOARD)
    bb.side_lead_max = SIDE_LEAD_MAX
    bb.partial = True
    bb.enable_steps()
    bb.set_header(f'실험 1) 단계 1 준비 {assembly_order} · {_ASSEMBLY_TITLES[assembly_order-1]}',
                  '전원과 신호발생기 출력을 꺼요. 배선만 육안으로 대조해요.')
    bb.marker_hints = _marker_hints()
    reservation = ShiftRenderer(board=BOARD)
    reservation.side_lead_max = SIDE_LEAD_MAX
    reservation.enable_steps()

    def apply(group, method, args, kwargs):
        # Execute ALL foundation work on a reservation board. Rail allocation
        # includes not-yet-assembled parts, so no hole moves between pages.
        choices = []
        free = reservation.free_rail_row
        def remember(*a):
            row = free(*a)
            choices.append(row)
            return row
        reservation.free_rail_row = remember
        try:
            if method == 'input':
                _input_jumper(reservation, *args, **kwargs)
            else:
                getattr(reservation, method)(*args, **kwargs)
        finally:
            reservation.free_rail_row = free
        if group > assembly_order:
            return
        rows = iter(choices)
        real_free = bb.free_rail_row
        bb.free_rail_row = lambda *a: next(rows)
        try:
            getattr(bb, method)(*args, **kwargs)
        finally:
            bb.free_rail_row = real_free

    _fixed(reservation, 1, _apply=apply)
    bb.note('전원은 꺼 둬요. 이번 그림은 정상 동작을 확인한 결과가 아니에요.')
    bb.export(output_path, max_row=63)
    return bb


def build_e7_shift(output_path, template_path=None, stage=None, baseline=None, layer=None,
                   hand=None, hand_guide=False):
    if stage is not None and (layer is not None or hand is not None):
        raise ValueError('layer/hand는 완성본에만 준다')
    bb = ShiftRenderer(template_path, baseline=baseline, layer=layer, board=BOARD,
                            palette=stage is not None, hand=hand, hand_guide=hand_guide)
    bb.side_lead_max = SIDE_LEAD_MAX
    bb.partial = stage is not None and stage < 12
    bb.enable_steps()
    bb.set_header('실험 1) 6bit Shift Right Register' + (f' — {stage}단계' if stage else ''),
                  '74HC00 ×1 + 74HC76 ×3 · D = SERIAL DATA · BIT 역할을 패키지 안에서 교환',
                  submit=stage is None)
    bb.marker_hints = _marker_hints()
    _fixed(bb, stage)
    draw_routed(bb, SHIFT.wires, _approved_paths(), stage)
    bb.note('74HC76 전원은 pin 5(+5V), pin 13(GND)다. PR·CLR 동시 0은 사용하지 않는다.')
    bb.note('입력 점퍼는 0 자리다. 1은 레일 쪽 끝을 +5V로 옮긴다. CLK은 검증한 발생기 출력으로 구동한다.')
    bb.note('LED 신호→애노드→캐소드→330Ω→GND. 저항과 LED 직렬 순서는 논리 넷에 영향을 주지 않는다.')
    bb.export(output_path, max_row=63)
    return bb


SHIFT = PlaceCircuit('shift', {'U1': 'S1', 'U2': 'S2', 'U3': 'S3', 'U4': 'S4'},
                     {'U1': '74HC00', 'U2': '74HC76', 'U3': '74HC76', 'U4': '74HC76'},
                     _LED_ORDER, tuple(_WIRES), _fixed,
                     tuple((u, p) for _, _, u, p in _INPUTS))
PLACE = [SHIFT]
_NAME = '실험07_1_결선도_6bit시프트레지스터'
_STAGE_NAMES = ('입력반전', '앞클럭', '전체클럭', '앞초기화', '전체초기화', '프리셋',
                'BIT1', 'BIT2', 'BIT3', 'BIT4', 'BIT5', 'BIT6')
BOARDS = []
for _i, _name in enumerate(_STAGE_NAMES, 1):
    if _i > 1:
        BOARDS.append((f'{_NAME}_{_i}걷기_임시입력.png',
                       removal_board((build_e7_shift, _i-1), (build_e7_shift, _i),
                           f'실험 1) {_i}단계 전 임시 입력 걷기',
                           '전원부터 꺼요. 빨간 임시 고정선만 뽑고 다음 단계의 신호선을 꽂아요.'), None))
    BOARDS.append((f'{_NAME}_{_i}단계_{_name}.png', build_e7_shift, _i))
ASSEMBLY_BOARDS = {BOARDS[0][0]: [
    (f'{_NAME}_1준비_{i}.png', partial(_build_assembly, assembly_order=i))
    for i in range(1, 7)
]}
FINALS = [(f'{_NAME}.png', build_e7_shift)]

# 완성본 번호를 빠짐없이 나눈 손그림 안내용 층.
LAYERS = {f'{_NAME}.png': [
    (1, 4, '전원 잭·레일 브리지'), (5, 12, 'U1~U4 전원'),
    (13, 16, 'BIT3~6 프리셋 비활성'), (17, 21, '입력 D·CLK·CLR·PR1·PR2'),
    (22, 27, 'LED BIT1·BIT2·BIT3 사슬'), (28, 33, 'LED BIT4·BIT5·BIT6 사슬'),
    (34, 39, '입력 반전·공통 CLK'), (40, 44, '공통 CLR'),
    (45, 47, 'BIT1 데이터·LED'), (48, 50, 'BIT2 데이터·LED'),
    (51, 53, 'BIT3 데이터·LED'), (54, 56, 'BIT4 데이터·LED'),
    (57, 59, 'BIT5 데이터·LED'), (60, 62, 'BIT6 데이터·LED'),
]}


# Search adapter: explicit, reversible physical assignments; normal rendering uses
# identity mappings and the approved JSON, never the last explored candidate.
from contextlib import contextmanager
from dataclasses import replace
import copy
import re

_SEARCH_VALIDATE_ONLY = False
_SEARCH_VARIANT = {'nand': 3, 'ff': [False, False, False]}


def _map_pin(u, pin, variant=None):
    v = variant or _SEARCH_VARIANT
    if u == 'U1' and v['nand'] == 4:
        return {8: 11, 9: 12, 10: 13, 11: 8, 12: 9, 13: 10}.get(pin, pin)
    if u in ('U2', 'U3', 'U4') and v['ff'][int(u[1:]) - 2]:
        return {1: 6, 6: 1, 2: 7, 7: 2, 3: 8, 8: 3, 4: 9, 9: 4,
                10: 14, 14: 10, 11: 15, 15: 11, 12: 16, 16: 12}.get(pin, pin)
    return pin


def search_variants():
    # Same NAND operation, or a bijective swap of the two complete FF units.
    # Every control/data/output terminal is mapped, including PR1/PR2 and temps.
    import itertools
    return [dict(nand=n, ff=list(bits)) for n in (3, 4)
            for bits in itertools.product((False, True), repeat=3)]


_ORIGINAL_SHIFT = SHIFT
_ORIGINAL_INPUTS = copy.deepcopy(_INPUTS)
_ORIGINAL_TEMP = copy.deepcopy(_TEMP)


def search_circuit(variant):
    def end(p):
        return p if p[0] == 'LED' else (p[0], _map_pin(*p, variant))
    def description(text):
        return re.sub(r'(U[1-4]) pin (\d+)',
                      lambda m: f'{m[1]} pin {_map_pin(m[1], int(m[2]), variant)}', text)
    wires = tuple((s, e, k, end(f), end(t), description(d))
                  for s, e, k, f, t, d in _ORIGINAL_SHIFT.wires)
    return replace(_ORIGINAL_SHIFT, wires=wires,
                   inputs=tuple((u, _map_pin(u, p, variant)) for _, _, u, p in _ORIGINAL_INPUTS))


def search_temporaries(variant):
    return [(first, u, _map_pin(u, p, variant), kind) for first, u, p, kind in _ORIGINAL_TEMP]


@contextmanager
def search_context(candidate, plans, temporaries, validation_only=False):
    global LAYOUT, SHIFT, _INPUTS, _TEMP, _ROUTE_DATA, _MARKER_HINTS, _SEARCH_VARIANT, _SEARCH_VALIDATE_ONLY
    saved = (LAYOUT, SHIFT, _INPUTS, _TEMP, _ROUTE_DATA, _MARKER_HINTS, _SEARCH_VARIANT, _SEARCH_VALIDATE_ONLY)
    try:
        _SEARCH_VALIDATE_ONLY = validation_only
        LAYOUT = copy.deepcopy(candidate['layout'])
        _SEARCH_VARIANT = candidate['variant']
        SHIFT = search_circuit(_SEARCH_VARIANT)
        _INPUTS = [(s, name, u, _map_pin(u, p)) for s, name, u, p in _ORIGINAL_INPUTS]
        _TEMP = search_temporaries(_SEARCH_VARIANT)
        _ROUTE_DATA = dict(layout=LAYOUT, wires=json.loads(json.dumps(SHIFT.wires)),
                           plans=plans, temporaries=temporaries)
        _MARKER_HINTS = None
        yield
    finally:
        (LAYOUT, SHIFT, _INPUTS, _TEMP, _ROUTE_DATA, _MARKER_HINTS, _SEARCH_VARIANT, _SEARCH_VALIDATE_ONLY) = saved


def search_fixed(bb, layout, variant):
    candidate = dict(layout=layout, variant=variant)
    with search_context(candidate, [], []):
        _fixed(bb, None, False, layout, _with_temps=False)


def search_baseline():
    return dict(candidate=dict(layout=copy.deepcopy(LAYOUT), variant=copy.deepcopy(_SEARCH_VARIANT)),
                weight=4., order='original', plans=copy.deepcopy(_approved_paths()),
                temporaries=copy.deepcopy(_temporary_plan(LAYOUT)))


def search_assert_drivers(bb, stage):
    if stage is None:
        return  # Power is off during removal.
    def label(u, p):
        return f"{SHIFT.models[u]}#{LAYOUT['slots'][SHIFT.chips[u]]} pin {p}"
    nets = bb.nets()
    outputs = {label(u, p) for u in ('U2', 'U3', 'U4') for p in (10, 11, 14, 15)}
    outputs.add(label('U1', _map_pin('U1', 8)))
    for u in ('U2', 'U3', 'U4'):
        for p in (1, 2, 3, 4, 6, 7, 8, 9, 12, 16):
            node = next(n for n in nets if label(u, p) in n['labels'])
            if not (node['rails'] or outputs.intersection(node['labels'])
                    or any(x.startswith('입력 ') for x in node['labels'])):
                raise AssertionError(f'Undriven input at stage {stage}: {u} pin {p}')


_APPROVED_LAYOUT = copy.deepcopy(LAYOUT)
_APPROVED_ROUTES = copy.deepcopy(_ROUTE_DATA)
_LOGICAL_NETS = None


def _logical_nets(bb):
    """Normalize physical package rows/pins to approved logical terminal IDs."""
    locations = {(SHIFT.models[u], LAYOUT['slots'][slot]): u for u, slot in SHIFT.chips.items()}
    nodes = []
    for node in bb.nets():
        labels = []
        for text in node['labels']:
            match = re.fullmatch(r'(74HC\d+)#(\d+) pin (\d+)', text)
            if match:
                u = locations[(match[1], int(match[2]))]
                # Every allowed assignment is an involution of whole devices.
                text = f'{u} pin {_map_pin(u, int(match[3]))}'
            labels.append(text)
        nodes.append((tuple(sorted(labels)), tuple(sorted(node['rails']))))
    return tuple(sorted(nodes))


def search_assert_equivalent(bb, name):
    global _LOGICAL_NETS
    actual = _logical_nets(bb)
    if _LOGICAL_NETS is None:
        expected = {}
        candidate = dict(layout=_APPROVED_LAYOUT, variant=dict(nand=3, ff=[False] * 3))
        with search_context(candidate, _APPROVED_ROUTES['plans'], _APPROVED_ROUTES['temporaries'],
                            validation_only=True):
            base = None
            for filename, fn, stage in BOARDS:
                for prep_name, prep_fn in ASSEMBLY_BOARDS.get(filename, []):
                    expected[prep_name] = _logical_nets(prep_fn('/unused.png'))
                sample = fn('/unused.png', stage=stage, baseline=base)
                base = sample.snapshot()
                expected[filename] = _logical_nets(sample)
            for filename, fn in FINALS:
                expected[filename] = _logical_nets(fn('/unused.png'))
        _LOGICAL_NETS = expected
    if actual != _LOGICAL_NETS[name]:
        raise AssertionError(f'Logical net equivalence failed: {name}')
