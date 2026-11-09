"""실험09 RAM — v2 보드. C1 2bit RAM(74HC00 ×2 + 74HC03), C2 16bit RAM(74670).

C1 은 맨바닥에서 짓고 C2 는 전부 뽑고 새로 짓는다(`rebuild: all`). 회로마다 배선표 하나를 쓰고, 그림마다
`g`(배선표의 누적 단계)로 잘라 그린다. 칩 자리와 레일 착지 행은 전 단계 superset 판에서 한 번 정해 준비·단계·
완성본이 같은 홀을 쓴다(실험08 과 같은 틀).

C1 게이트 배정(netlist M13): 교안 p6 그대로면 래치 출력 Q 가 U1·U2 의 f쪽(pin 11)이고 그것을 받는 74HC03
읽기 게이트 입력은 a쪽(pin 2·5)이라 칩 사이 선이 쪽을 바꾼다(R8). 래치 두 게이트 중 Q 를 내는 게이트(교안 pin
12·13→11)와 리셋 쪽 입력 게이트(교안 pin 4·5→6)의 자리를 맞바꿔 Q 를 a쪽 pin 6 에 둔다. 74HC03 은 교안
그대로다 — LED 를 구동하는 출력 게이트가 f쪽(pin 11·8)이다.

74HC03 은 열린 드레인이라 출력 넷에 10kΩ 풀업을 단다(p6). 엔진 `pull_up` 이 핀 스트립 끝 홀(a·j 열)에서
가장 가까운 +5V 레일로 눕혀 꽂는다.
"""
from functools import partial

from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips, place_paths,
    place_wires, place_marker_hints, draw_routed, _dip_pin_row as _pin_row, _dip_side as _side, dip_pins)

BOARD = 'v2'
SLOTS = ('S1', 'S2', 'S3', 'S4')
LAYOUT = {'slots': {'S1': 5, 'S2': 15, 'S3': 25, 'S4': 8},
          'leds': {'ram2': {'OUT0': 3, 'OUT1': 8},
                   'ram16': {'Q1': 16, 'Q2': 21, 'Q3': 26, 'Q4': 31}},
          'bridge': [34, 35], 'bridge_policy': 'lower-clearance-v1'}
SIDE_LEAD_MAX = 11
SIDE_LEAD_MAX_REASON = ('74HC00 래치 칩은 입력 셋(IN·WR1·WR0)과 그 갈래·공유선, 래치 되먹임까지 리드 18, 74HC03 은 '
    '입력 둘·칩 사이선 둘·풀업 넷·12·13 과 9·10 묶음·LED 급전까지 리드 20 이다. 합이 16 을 넘어 어느 게이트 '
    '배정으로도 한쪽 8 에 못 담는다.')
STAGE_WIRE_BUDGET = 8
STAGE_WIRE_BUDGET_REASON = ('74670 의 첫 데이터 비트(D1→Q1)는 WE·RE·WA·WB·RA·RB·D1 입력 일곱이 다 꽂혀야 상류에 뜬 '
    '입력이 없다. 입력 점퍼 일곱 + Q1 급전 하나가 여덟이다(netlist M11). 준비 단계에는 신호선을 넣을 수 없다.')

# 배선표 (첫 g, 끝 g, 색, 출발, 도착, 설명). g 는 회로마다의 누적 단계 — 준비 1·2 가 g1·g2, 단계 s 가 g(2+s).
_RAM2_WIRES = (
    (3, None, 'sig', ('U1', 3), ('U1', 4), "A-S': U1 pin 3 -> U1 pin 4"),
    (4, None, 'sig', ('U1', 1), ('U1', 13), 'IN0: U1 pin 1 -> U1 pin 13'),
    (4, None, 'sig', ('U1', 11), ('U1', 10), "A-R': U1 pin 11 -> U1 pin 10"),
    (5, None, 'sig', ('U1', 6), ('U1', 9), 'A-Q: U1 pin 6 -> U1 pin 9'),
    (5, None, 'sig', ('U1', 8), ('U1', 5), "A-Q': U1 pin 8 -> U1 pin 5"),
    (6, None, 'sig', ('U1', 6), ('U3', 2), 'A-Q: U1 pin 6 -> U3 pin 2'),
    (7, None, 'sig', ('U3', 3), ('U3', 12), "A-RD': U3 pin 3 -> U3 pin 12"),
    (7, None, 'sig', ('U3', 12), ('U3', 13), "A-RD': U3 pin 12 -> U3 pin 13"),
    (7, None, 'sig', ('U3', 11), ('LED', 'OUT0'), 'OUT0 = U3 pin 11 -> LED OUT0'),
    (8, None, 'sig', ('U2', 3), ('U2', 4), "B-S': U2 pin 3 -> U2 pin 4"),
    (8, None, 'sig', ('U1', 2), ('U2', 2), 'WR1: U1 pin 2 -> U2 pin 2'),
    (9, None, 'sig', ('U1', 12), ('U2', 12), 'WR0: U1 pin 12 -> U2 pin 12'),
    (9, None, 'sig', ('U2', 1), ('U2', 13), 'IN1: U2 pin 1 -> U2 pin 13'),
    (9, None, 'sig', ('U2', 11), ('U2', 10), "B-R': U2 pin 11 -> U2 pin 10"),
    (10, None, 'sig', ('U2', 6), ('U2', 9), 'B-Q: U2 pin 6 -> U2 pin 9'),
    (10, None, 'sig', ('U2', 8), ('U2', 5), "B-Q': U2 pin 8 -> U2 pin 5"),
    (11, None, 'sig', ('U2', 6), ('U3', 5), 'B-Q: U2 pin 6 -> U3 pin 5'),
    (12, None, 'sig', ('U3', 6), ('U3', 9), "B-RD': U3 pin 6 -> U3 pin 9"),
    (12, None, 'sig', ('U3', 9), ('U3', 10), "B-RD': U3 pin 9 -> U3 pin 10"),
    (12, None, 'sig', ('U3', 8), ('LED', 'OUT1'), 'OUT1 = U3 pin 8 -> LED OUT1'),
)
_RAM16_WIRES = (
    (3, None, 'sig', ('U1', 10), ('LED', 'Q1'), 'Q1 = U1 pin 10 -> LED Q1'),
    (4, None, 'sig', ('U1', 9), ('LED', 'Q2'), 'Q2 = U1 pin 9 -> LED Q2'),
    (5, None, 'sig', ('U1', 7), ('LED', 'Q3'), 'Q3 = U1 pin 7 -> LED Q3'),
    (6, None, 'sig', ('U1', 6), ('LED', 'Q4'), 'Q4 = U1 pin 6 -> LED Q4'),
)


def _cross(w):
    """칩 사이 선이 먼저다 — 배선기가 표 순서대로 깔아 건너는 선에 반 행을 남긴다."""
    return w[3][0] == w[4][0]


_RAM2_WIRES = tuple(sorted(_RAM2_WIRES, key=_cross))
_RAM2_INPUTS = ((3, None, 'IN0', 'U1', 1), (3, None, 'WR1', 'U1', 2), (4, None, 'WR0', 'U1', 12),
                (6, None, 'OE0', 'U3', 1), (8, None, 'IN1', 'U2', 1), (11, None, 'OE1', 'U3', 4))
# 가운데 레일 입력(f쪽)은 핀 행 순서(위→아래)로 그린다 — 번호 원이 배지 바로 위에 앉으므로, 위 이웃의
# 배지가 먼저 그려져 있어야 원이 그것을 비켜 간다(실험05 C1 Bit0~Bit3 과 같은 순서)
_RAM16_INPUTS = ((3, None, 'D1', 'U1', 15), (3, None, 'WA', 'U1', 14), (3, None, 'WB', 'U1', 13),
                 (3, None, 'WE', 'U1', 12), (3, None, 'RE', 'U1', 11), (3, None, 'RB', 'U1', 4),
                 (3, None, 'RA', 'U1', 5), (4, None, 'D2', 'U1', 1), (5, None, 'D3', 'U1', 2),
                 (6, None, 'D4', 'U1', 3))
# 풀업 (첫 g, 칩, 핀) — 74HC03 열린 드레인 출력마다 10kΩ
_RAM2_PULLUPS = ((6, 'U3', 3), (7, 'U3', 11), (11, 'U3', 6), (12, 'U3', 8))
_RAM2_FINAL_G, _RAM16_FINAL_G = 12, 6


def _chain(b, top, tag):
    b.led_chain(b.cols['right']['a'], top, tag, f'{tag}: 출력 1 이면 켜짐', block='right')


def _pull(b, row, pin, u):
    L = b.cols['left']
    b.pull_up(L['a'] if _side(pin) == 'a' else L['j'], row, f'{u} pin {pin} 열린 드레인 출력')


def _ops_ram2(lay, k):
    ops = [(1, None, lambda b: b.draw_chip('74HC00', k['U1'])), (1, None, lambda b: b.draw_chip('74HC00', k['U2'])),
           (1, None, lambda b: b.draw_chip('74HC03', k['U3'])), (1, None, lambda b: b.connect_jacks()),
           (1, None, lambda b: b.connect_rail_bridges(lay))]
    ops += [(1, None, partial(lambda b, r: b.connect_power(r, gnd_col='a'), r=k[u])) for u in ('U1', 'U2', 'U3')]
    for g, u, pin in _RAM2_PULLUPS:
        ops.append((g, None, partial(_pull, row=_pin_row(k[u], pin), pin=pin, u=u)))
    for tag in ('OUT0', 'OUT1'):
        ops.append((2, None, partial(_chain, top=lay['leds']['ram2'][tag], tag=tag)))
    return ops


def _ops_ram16(lay, k):
    u1 = k['U1']
    ops = [(1, None, lambda b: b.draw_chip('74670', u1)), (1, None, lambda b: b.connect_jacks()),
           (1, None, lambda b: b.connect_rail_bridges(lay)), (1, None, lambda b: b.connect_power(u1, gnd_col='a'))]
    for tag in ('Q1', 'Q2', 'Q3', 'Q4'):
        ops.append((2, None, partial(_chain, top=lay['leds']['ram16'][tag], tag=tag)))
    return ops


def _input_ops(inputs, k, circuit):
    ops = []
    for first, last, name, u, pin in inputs:
        n = dip_pins(circuit.models[u])

        def jump(b, name=name, u=u, pin=pin, n=n):
            side = _side(pin, n)
            _input_jumper(b, b.cols['left'], _pin_row(k[u], pin, n), name, f'{u} pin {pin}', side=side,
                          col='b' if side == 'a' else 'j')
        ops.append((first, last, jump))
    return ops


def _apply(bb, ops, g, superset):
    """전 단계 판(`res`)에 다 그려 레일 착지 행을 정하고, 지금 단계의 것만 같은 행으로 `bb` 에 다시 그린다."""
    res = BreadboardRenderer(board=BOARD)
    res.enable_steps()
    free = res.free_rail_row
    for first, last, op in ops:
        picks = []

        def remember(*a):
            picks.append(free(*a))
            return picks[-1]
        res.free_rail_row = remember
        op(res)
        res.free_rail_row = free
        if superset or (first <= g and (last is None or g <= last)):
            rows = iter(picks)
            real = bb.free_rail_row
            bb.free_rail_row = lambda *a: next(rows)
            try:
                op(bb)
            finally:
                bb.free_rail_row = real


def _fixed(circuit, ops_fn, inputs, final_g, bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    bb.led_order_policy = 'fixed'
    bb.route_side_lanes = True
    bb.route_avoid_bodies = True     # 배선기가 R13 위반 경로를 처음부터 거른다(고정 LED 탐색과 같다)
    k = place_chips(circuit, lay)
    ops = ops_fn(lay, k)
    # 입력을 LED 사슬보다 먼저 그린다 — 사슬 번호 원이 입력 배지를 비켜 간다(SKILL 배선기 문단)
    at = next(i for i, op in enumerate(ops) if getattr(op[2], 'func', None) is _chain)
    ops[at:at] = _input_ops(inputs, k, circuit)
    _apply(bb, ops, final_g if stage is None else stage, superset)


def _fixed_ram2(bb, stage, superset=False, layout=None):
    _fixed(RAM2, _ops_ram2, _RAM2_INPUTS, _RAM2_FINAL_G, bb, stage, superset, layout)


def _fixed_ram16(bb, stage, superset=False, layout=None):
    _fixed(RAM16, _ops_ram16, _RAM16_INPUTS, _RAM16_FINAL_G, bb, stage, superset, layout)


RAM2 = PlaceCircuit('ram2', {'U1': 'S1', 'U2': 'S2', 'U3': 'S3'}, {'U1': '74HC00', 'U2': '74HC00', 'U3': '74HC03'},
                    ('OUT0', 'OUT1'), _RAM2_WIRES, _fixed_ram2, tuple((u, p) for *_x, u, p in _RAM2_INPUTS))
RAM16 = PlaceCircuit('ram16', {'U1': 'S4'}, {'U1': '74670'},
                     ('Q1', 'Q2', 'Q3', 'Q4'), _RAM16_WIRES, _fixed_ram16,
                     tuple((u, p) for *_x, u, p in _RAM16_INPUTS))
PLACE = [RAM2, RAM16]


def _board(template, circuit, g, baseline, title, sub, *, palette=False, partial_=None, submit=False,
           hand=None, hand_guide=False):
    bb = BreadboardRenderer(template, baseline=baseline, board=BOARD, palette=palette, hand=hand, hand_guide=hand_guide)
    bb.side_lead_max = SIDE_LEAD_MAX
    bb.led_order_policy = 'fixed'
    bb.enable_steps()
    bb.partial = partial_
    bb.set_header(title, sub, submit=submit)
    bb.marker_hints = place_marker_hints(circuit, LAYOUT)
    circuit.fixed(bb, g, False, LAYOUT)
    draw_routed(bb, place_wires(circuit, LAYOUT), place_paths(circuit, LAYOUT), g)
    return bb


_POWER_OFF = '전원을 꺼요. 배선만 육안으로 대조해요.'
_E1 = '실험 1) 2bit RAM'
_E2 = '실험 2) 16bit RAM (IC 74670)'


def build_e9_ram2(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    g = _RAM2_FINAL_G if stage is None else 2 + stage
    bb = _board(template_path, RAM2, g, baseline, _E1 + (f' — {stage}단계' if stage else ''),
                '74HC00 ×2 + 74HC03 ×1 · 10kΩ 풀업 ×4 · 입력은 점퍼', palette=stage is not None,
                partial_=g < _RAM2_FINAL_G, submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('74HC03 출력은 열린 드레인이라 10kΩ 풀업이 1 을 만든다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_ram2(output_path, template_path=None, baseline=None, *, order):
    titles = ('보드·칩·전원 준비', 'LED 준비')
    bb = _board(template_path, RAM2, order, baseline, f'{_E1} 준비 {order} · {titles[order - 1]}',
                _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


def build_e9_ram16(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    g = _RAM16_FINAL_G if stage is None else 2 + stage
    bb = _board(template_path, RAM16, g, baseline, _E2 + (f' — {stage}단계' if stage else ''),
                '74670 ×1 · 입력 열 개는 점퍼', palette=stage is not None, partial_=g < _RAM16_FINAL_G,
                submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('74670 전원은 pin 16(+5V), pin 8(GND)다. WE·RE 는 0 일 때 켜진다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_ram16(output_path, template_path=None, baseline=None, *, order):
    titles = ('칩·전원 준비', 'LED 준비')
    # rebuild: all — 앞 회로를 전부 뽑으므로 첫 준비는 기준선을 잇지 않는다
    bb = _board(template_path, RAM16, order, None if order == 1 else baseline,
                f'{_E2} 준비 {order} · {titles[order - 1]}', _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


_N1 = '실험09_1_결선도_2bitRAM'
_N2 = '실험09_2_결선도_16bitRAM'
_RAM2_STAGES = ('A세트', 'A리셋', 'A래치', 'A읽기', 'OUT0', 'B세트', 'B리셋', 'B래치', 'B읽기', 'OUT1')
_RAM16_STAGES = ('Q1', 'Q2', 'Q3', 'Q4')
BOARDS = ([(f'{_N1}_{s}단계_{name}.png', build_e9_ram2, s) for s, name in enumerate(_RAM2_STAGES, 1)]
          + [(f'{_N2}_{s}단계_{name}.png', build_e9_ram16, s) for s, name in enumerate(_RAM16_STAGES, 1)])
RESTART = (f'{_N2}_1단계_Q1.png',)     # rebuild: all — `place_verify` 가 여기서 기준선을 끊는다
ASSEMBLY_BOARDS = {
    f'{_N1}_1단계_A세트.png': [(f'{_N1}_1준비_{i}.png', partial(_prep_ram2, order=i)) for i in (1, 2)],
    f'{_N2}_1단계_Q1.png': [(f'{_N2}_1준비_{i}.png', partial(_prep_ram16, order=i)) for i in (1, 2)],
}
FINALS = [(f'{_N1}.png', build_e9_ram2), (f'{_N2}.png', build_e9_ram16)]
