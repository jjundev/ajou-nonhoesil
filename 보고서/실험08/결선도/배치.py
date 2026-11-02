"""실험08 Counter — v2 보드. C1 2단 2진 카운터, C2~C5 BCD 카운터 + 7447 + FND 507.

C1 은 맨바닥에서 짓고 C2 는 전부 뽑고 새로 짓는다(`rebuild: all`). C3·C4·C5 는 C2 위에 잇는다.
이어 짓는 회로는 배선표 하나(`BCD`)를 쓰고, 그림마다 `g`(배선표의 누적 단계)로 잘라 그린다.
칩을 꽂는 자리와 레일 착지 행은 전 단계 superset 판에서 한 번 정해 준비·단계·완성본이 같은 홀을 쓴다.

C1: 74HC76 출력이 전부 f쪽이라 네 AND 중 Y0·Y3 을 f쪽 게이트에, Y1·Y2 를 a쪽 게이트에 둔다 — 그래야 네
신호가 모두 f쪽 핀에 먼저 내리고 칩 안에서 a쪽으로 건넌다(R8, netlist M13).
C5: 7490 출력(f쪽)을 7447 입력(a쪽)에 바로 이으면 R8 에 걸리고 두 칩의 n.c. 핀은 네 신호를 못 받는다. LED
사슬 신호 스트립은 7490 출력과 같은 넷이므로 거기서 7447 입력으로 간다(`TAP`, R10 은 칩 핀→LED 스트립, M14).
"""
from functools import partial

from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips, place_paths,
    place_wires, place_marker_hints, draw_routed, removal_board, _dip_pin_row as _pin_row,
    _dip_side as _side, dip_pins)

BOARD = 'v2'
SLOTS = ('S1', 'S2')
LAYOUT = {'slots': {'S1': 5, 'S2': 16},
          'leds': {'counter': {'Y0': 3, 'Y1': 8, 'Y2': 13, 'Y3': 18},
                   'bcd': {'A': 3, 'B': 8, 'C': 13, 'D': 18}},
          'fnd': 29, 'bridge': [39, 40], 'bridge_policy': 'lower-clearance-v1'}
SIDE_LEAD_MAX = 11
SIDE_LEAD_MAX_REASON = ('74HC76 은 전원 둘, 고정 입력 여덟, 출력 분기까지 리드 17, 74HC08 은 네 게이트 입력마다 칩 사이선과 '
    '칩 안 이어 가기가 겹쳐 리드 18 이다. 합이 16 을 넘어 어느 게이트 배정으로도 한쪽 8 에 못 담는다.')
STAGE_WIRE_BUDGET = 4
STAGE_WIRE_BUDGET_REASON = ('74HC08 a쪽 게이트의 입력 둘은 74HC76 f쪽 출력에서 칩 사이선 + 칩 안 이어 가기로 와서 '
    '입력 둘 + 출력 급전이 넷이다. 2입력 게이트 관측 노드 하나의 값이다.')

# 배선표 (첫 g, 끝 g, 색, 출발, 도착, 설명). g 는 아래 `_G_*` 표의 누적 단계다.
_COUNTER_WIRES = (
    (4, None, 'sig', ('U1', 15), ('U1', 6), 'A: U1 pin 15 -> U1 pin 6'),
    (5, None, 'sig', ('U1', 14), ('U2', 13), "A': U1 pin 14 -> U2 pin 13"),
    (5, None, 'sig', ('U1', 10), ('U2', 12), "B': U1 pin 10 -> U2 pin 12"),
    (5, None, 'sig', ('U2', 11), ('LED', 'Y0'), 'Y0 = U2 pin 11 -> LED Y0'),
    (6, None, 'sig', ('U1', 15), ('U2', 9), 'A: U1 pin 15 -> U2 pin 9'),
    (6, None, 'sig', ('U2', 9), ('U2', 1), 'A: U2 pin 9 -> U2 pin 1'),
    (6, None, 'sig', ('U2', 12), ('U2', 2), "B': U2 pin 12 -> U2 pin 2"),
    (6, None, 'sig', ('U2', 3), ('LED', 'Y1'), 'Y1 = U2 pin 3 -> LED Y1'),
    (7, None, 'sig', ('U2', 13), ('U2', 4), "A': U2 pin 13 -> U2 pin 4"),
    (7, None, 'sig', ('U1', 11), ('U2', 10), 'B: U1 pin 11 -> U2 pin 10'),
    (7, None, 'sig', ('U2', 10), ('U2', 5), 'B: U2 pin 10 -> U2 pin 5'),
    (7, None, 'sig', ('U2', 6), ('LED', 'Y2'), 'Y2 = U2 pin 6 -> LED Y2'),
    (8, None, 'sig', ('U2', 8), ('LED', 'Y3'), 'Y3 = U2 pin 8 -> LED Y3'),
)
_SEGMENTS = (('a', 13, 7), ('b', 12, 6), ('c', 11, 4), ('d', 10, 2), ('e', 9, 1), ('f', 15, 9), ('g', 14, 10))
_BCD_WIRES = (
    (3, None, 'sig', ('U1', 2), ('U1', 3), 'R0: U1 pin 2 -> U1 pin 3'),
    (4, None, 'sig', ('U1', 12), ('U1', 1), 'QA: U1 pin 12 -> U1 pin 1'),
    (4, None, 'sig', ('U1', 12), ('LED', 'A'), 'A = U1 pin 12 -> LED A'),
    (4, None, 'sig', ('U1', 9), ('LED', 'B'), 'B = U1 pin 9 -> LED B'),
    (5, None, 'sig', ('U1', 8), ('LED', 'C'), 'C = U1 pin 8 -> LED C'),
    (5, None, 'sig', ('U1', 11), ('LED', 'D'), 'D = U1 pin 11 -> LED D'),
    *((9 + i // 3, None, 'sig', ('U2', out), ('SEG', seg), f'{seg}: U2 pin {out} -> 330Ω (U3 pin {fnd})')
      for i, (seg, out, fnd) in enumerate(_SEGMENTS)),
    (12, None, 'sig', ('U2', 7), ('TAP', 'A'), 'A: U1 pin 12 (LED A 스트립) -> U2 pin 7'),
    (12, None, 'sig', ('U2', 1), ('TAP', 'B'), 'B: U1 pin 9 (LED B 스트립) -> U2 pin 1'),
    (12, None, 'sig', ('U2', 2), ('TAP', 'C'), 'C: U1 pin 8 (LED C 스트립) -> U2 pin 2'),
    (13, None, 'sig', ('U2', 6), ('TAP', 'D'), 'D: U1 pin 11 (LED D 스트립) -> U2 pin 6'),
)
# 배선기는 표 순서대로 깐다 — 칩을 건너는 선이 먼저다(그래야 반 행이 남는다). 번호는 단계 안에서만 순서다.
_COUNTER_WIRES = tuple(sorted(_COUNTER_WIRES, key=lambda w: w[3][0] != 'U2' or w[4][0] != 'U2'))
_BCD_WIRES = tuple(sorted(_BCD_WIRES, key=lambda w: w[4][0] != 'TAP'))
_COUNTER_INPUTS = ((4, None, 'CLK', 'U1', 1),)
_BCD_INPUTS = ((3, None, 'R0', 'U1', 2), (3, None, 'CLK', 'U1', 14),
               (8, 11, 'A', 'U2', 7), (8, 11, 'B', 'U2', 1), (8, 11, 'C', 'U2', 2), (8, 12, 'D', 'U2', 6))
_FINAL_G = 13


def _rail_tie(bb, row, side, kind, desc):
    """고정 입력·미사용 입력을 레일로 — a쪽은 좌 바깥, f쪽은 가운데 레일."""
    L = bb.cols['left']
    x_hole, x_rail = (L['a'], L[kind]) if side == 'a' else (L['j'], L['mid_' + kind])
    rail = bb.free_rail_row(row, x_rail)
    bb.step_wire([(x_hole, bb.r_y(row)), (x_rail, bb.r_y(rail))], kind, desc)


def _strip_tie(bb, top, frm, to, n, desc):
    """레일 빈 행의 a쪽 핀은 옆 핀 스트립에서 받는다 — 비켜 내린 레일 착지가 이웃 전원선·입력 점퍼와 엇갈린다."""
    x, y_to = bb.cols['left']['d'], bb.r_y(_pin_row(top, to, n))
    bb.step_wire([(x, bb.r_y(_pin_row(top, frm, n))), (x, y_to)], 'vcc', desc, marker_at=(x - 26, y_to))


def _ops_counter(lay, k):
    u1, u2 = k['U1'], k['U2']
    ops = [(1, None, lambda b: b.draw_chip('74HC76', u1)), (1, None, lambda b: b.draw_chip('74HC08', u2)),
           (1, None, lambda b: b.connect_jacks()), (1, None, lambda b: b.connect_rail_bridges(lay)),
           (1, None, lambda b: b.connect_power(u1, gnd_col='a')), (1, None, lambda b: b.connect_power(u2, gnd_col='a'))]
    for p in (2, 3, 16, 7, 8, 9, 12):
        ops.append((2, None, partial(_rail_tie, row=_pin_row(u1, p, 16), side=_side(p, 16), kind='vcc',
                                     desc=f'U1 pin {p} J·K·PR·CL 고정 -> +5V 레일')))
    ops.append((2, None, partial(_strip_tie, top=u1, frm=3, to=4, n=16, desc='U1 pin 4 J 고정 -> pin 3 스트립(+5V)')))
    for tag in ('Y0', 'Y1', 'Y2', 'Y3'):
        ops.append((3, None, partial(_chain, top=lay['leds']['counter'][tag], tag=tag)))
    return ops


def _ops_bcd(lay, k):
    u1, u2 = k['U1'], k['U2']
    ops = [(1, None, lambda b: b.draw_chip('7490', u1)), (1, None, lambda b: b.connect_jacks()),
           (1, None, lambda b: b.connect_rail_bridges(lay)), (1, None, lambda b: b.connect_power(u1, gnd_col='a'))]
    for p in (6, 7):
        ops.append((1, None, partial(_rail_tie, row=_pin_row(u1, p, 14), side='a', kind='gnd',
                                     desc=f'U1 pin {p} R9 -> GND 레일')))
    ops.append((1, None, lambda b: b.mark_unused_inputs((4, 13), u1, chip='7490 (U1) n.c.')))
    for tag in ('A', 'B', 'C', 'D'):
        ops.append((2, None, partial(_chain, top=lay['leds']['bcd'][tag], tag=tag)))
    ops.append((6, None, lambda b: b.display_chain('FND 507', lay['fnd'])))
    ops += [(7, None, lambda b: b.draw_chip('7447', u2)), (7, None, lambda b: b.connect_power(u2, gnd_col='a'))]
    for p, name in ((3, '/LT'), (4, '/BI·/RBO')):
        ops.append((7, None, partial(_rail_tie, row=_pin_row(u2, p, 16), side='a', kind='vcc',
                                     desc=f'U2 pin {p} {name} -> +5V 레일')))

    ops.append((7, None, partial(_strip_tie, top=u2, frm=4, to=5, n=16, desc='U2 pin 5 /RBI -> pin 4 스트립(+5V)')))
    return ops


def _chain(b, top, tag):
    b.led_chain(b.cols['right']['a'], top, tag, f'{tag}: 출력 1 이면 켜짐', block='right')


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


def _apply(bb, circuit, ops, g, superset):
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


def _fixed(circuit, ops_fn, inputs, bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    bb.led_order_policy = 'fixed'
    bb.route_side_lanes = True
    k = place_chips(circuit, lay)
    ops = ops_fn(lay, k)
    # 입력을 LED 사슬보다 먼저 그린다 — 사슬 번호 원이 입력 배지를 비켜 간다(SKILL 배선기 문단)
    at = next(i for i, op in enumerate(ops) if getattr(op[2], 'func', None) is _chain)
    ops[at:at] = _input_ops(inputs, k, circuit)
    _apply(bb, circuit, ops, _FINAL_G if stage is None else stage, superset)


def _fixed_counter(bb, stage, superset=False, layout=None):
    _fixed(COUNTER, _ops_counter, _COUNTER_INPUTS, bb, stage, superset, layout)


def _fixed_bcd(bb, stage, superset=False, layout=None):
    _fixed(BCD, _ops_bcd, _BCD_INPUTS, bb, stage, superset, layout)


COUNTER = PlaceCircuit('counter', {'U1': 'S1', 'U2': 'S2'}, {'U1': '74HC76', 'U2': '74HC08'},
                       ('Y0', 'Y1', 'Y2', 'Y3'), _COUNTER_WIRES, _fixed_counter,
                       tuple((u, p) for *_x, u, p in _COUNTER_INPUTS))
BCD = PlaceCircuit('bcd', {'U1': 'S1', 'U2': 'S2'}, {'U1': '7490', 'U2': '7447'},
                   ('A', 'B', 'C', 'D'), _BCD_WIRES, _fixed_bcd,
                   tuple((u, p) for *_x, u, p in _BCD_INPUTS))
PLACE = [COUNTER, BCD]


def _board(path, template, circuit, g, baseline, title, sub, *, palette=False, partial_=None, submit=False,
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


_POWER_OFF = '전원과 신호발생기 출력을 꺼요. 배선만 육안으로 대조해요.'
_E1 = '실험 1) 2단 2진 카운터 (비동기)'
_E3 = '실험 3) BCD 카운터'


def build_e8_counter(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    g = 8 if stage is None else 3 + stage
    bb = _board(output_path, template_path, COUNTER, g, baseline,
                _E1 + (f' — {stage}단계' if stage else ''), '74HC76 ×1 + 74HC08 ×1 · CLK 1Hz',
                palette=stage is not None, partial_=g < 8, submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('74HC76 전원은 pin 5(+5V), pin 13(GND)다. J·K·PR·CL 은 전부 +5V 다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_counter(output_path, template_path=None, baseline=None, *, order):
    titles = ('보드·칩·전원 준비', 'U1 입력 고정', 'LED 준비')
    bb = _board(output_path, template_path, COUNTER, order, baseline, f'{_E1} 준비 {order} · {titles[order - 1]}',
                _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


def build_e8_bcd(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    g = 5 if stage is None else 2 + stage
    bb = _board(output_path, template_path, BCD, g, baseline,
                f'{_E3} — 1. BCD Counter' + (f' {stage}단계' if stage else ''), '7490 ×1 · CLK 1Hz · R0 점퍼',
                palette=stage is not None, partial_=g < 5, submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('7490 전원은 pin 5(+5V), pin 10(GND)다. pin 6·7(R9)은 GND 다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_bcd(output_path, template_path=None, baseline=None, *, order):
    titles = ('칩·전원·R9 준비', 'LED 준비')
    # rebuild: all — 앞 회로를 전부 뽑으므로 첫 준비는 기준선을 잇지 않는다
    bb = _board(output_path, template_path, BCD, order, None if order == 1 else baseline,
                f'{_E3} 준비 {order} · {titles[order - 1]}', _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


def build_e8_fnd(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    bb = _board(output_path, template_path, BCD, 6, baseline,
                f'{_E3} — FND Common Anode 테스트' + (f' {stage}단계' if stage else ''),
                'C2 위에 FND 507 + 330Ω ×7 · 7447 은 아직 꽂지 않는다', palette=stage is not None, partial_=True,
                submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('저항 빈 끝은 비어 있다. 시험선은 손에 들고 대며 그림에 없다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_driver(output_path, template_path=None, baseline=None, *, order):
    titles = ('7447·전원·제어핀 준비', '입력 고정')
    bb = _board(output_path, template_path, BCD, 6 + order, baseline, f'{_E3} 준비 {order} · {titles[order - 1]}',
                _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


def build_e8_driver(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    g = 11 if stage is None else 8 + stage
    bb = _board(output_path, template_path, BCD, g, baseline,
                f'{_E3} — 2. BCD to 7-Segment' + (f' {stage}단계' if stage else ''),
                '7447 ×1 + FND 507 · 입력 A~D 는 점퍼', palette=stage is not None, partial_=g < 11,
                submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('7447 전원은 pin 16(+5V), pin 8(GND)다. /LT·/BI·/RBI 는 +5V 다.')
    bb.export(output_path, max_row=63)
    return bb


def build_e8_final(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    g = 13 if stage is None else 11 + stage
    bb = _board(output_path, template_path, BCD, g, baseline,
                f'{_E3} — 3. 최종' + (f' {stage}단계' if stage else ''), '7490 + 7447 + FND 507',
                palette=stage is not None, partial_=g < 13, submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('7490 출력은 LED 사슬 신호 스트립을 거쳐 7447 입력으로 간다.')
    bb.export(output_path, max_row=63)
    return bb


_N1 = '실험08_1_결선도_2단2진카운터'
_N2 = '실험08_3_결선도_BCD카운터'
_N3 = '실험08_3_결선도_FND테스트'
_N4 = '실험08_3_결선도_7447표시기'
_N5 = '실험08_3_결선도_BCD표시기'
BOARDS = [
    (f'{_N1}_1단계_플립플롭.png', build_e8_counter, 1), (f'{_N1}_2단계_Y0.png', build_e8_counter, 2),
    (f'{_N1}_3단계_Y1.png', build_e8_counter, 3), (f'{_N1}_4단계_Y2.png', build_e8_counter, 4),
    (f'{_N1}_5단계_Y3.png', build_e8_counter, 5),
    (f'{_N2}_1단계_입력.png', build_e8_bcd, 1), (f'{_N2}_2단계_AB.png', build_e8_bcd, 2),
    (f'{_N2}_3단계_CD.png', build_e8_bcd, 3),
    (f'{_N3}_1단계_FND.png', build_e8_fnd, 1),
    (f'{_N4}_1단계_abc.png', build_e8_driver, 1), (f'{_N4}_2단계_def.png', build_e8_driver, 2),
    (f'{_N4}_3단계_g.png', build_e8_driver, 3),
    (f'{_N5}_1걷기_입력고정.png', removal_board((build_e8_driver, 3), (build_e8_final, 1),
        '실험 3) 3. 최종 — 입력 고정선 A·B·C 걷기', '전원을 꺼요. 빨간 선만 뽑아요. D 고정선은 남겨요.'), None),
    (f'{_N5}_1단계_ABC.png', build_e8_final, 1),
    (f'{_N5}_2걷기_입력고정.png', removal_board((build_e8_final, 1), (build_e8_final, 2),
        '실험 3) 3. 최종 — 입력 고정선 D 걷기', '전원을 꺼요. 빨간 선만 뽑아요.'), None),
    (f'{_N5}_2단계_D.png', build_e8_final, 2),
]
RESTART = (f'{_N2}_1단계_입력.png',)     # rebuild: all — `place_verify` 가 여기서 기준선을 끊는다
ASSEMBLY_BOARDS = {
    f'{_N1}_1단계_플립플롭.png': [(f'{_N1}_1준비_{i}.png', partial(_prep_counter, order=i)) for i in (1, 2, 3)],
    f'{_N2}_1단계_입력.png': [(f'{_N2}_1준비_{i}.png', partial(_prep_bcd, order=i)) for i in (1, 2)],
    f'{_N4}_1단계_abc.png': [(f'{_N4}_1준비_{i}.png', partial(_prep_driver, order=i)) for i in (1, 2)],
}
FINALS = [(f'{_N1}.png', build_e8_counter), (f'{_N2}.png', build_e8_bcd), (f'{_N3}.png', build_e8_fnd),
          (f'{_N4}.png', build_e8_driver), (f'{_N5}.png', build_e8_final)]
