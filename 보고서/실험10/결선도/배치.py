"""실험10 DAC — v2 보드. C1 7490 카운터, C2 DAC 전체 회로(74HC04 + 74HC05 + LM741), C3 핀 개방·Rf 변경.

C1 을 맨바닥에서 짓고 C2 는 그 위에 이어 짓는다. 두 회로는 배선표 하나(`_WIRES`)를 쓰고 그림마다 `g`(누적 단계)로
잘라 그린다. 칩 자리와 레일 착지 행은 전 단계 superset 판에서 한 번 정해 준비·단계·완성본이 같은 홀을 쓴다
(실험08 과 같은 틀). C3 은 C2 완성본에서 잠시 바꾸고 되돌리는 절차라 보드가 C2 완성본과 같다.

전원 둘(사용자 결정 2026-11-16): +5V 는 빨강 잭 → 좌 바깥 → 가운데 레일(표준), +15V 는 노랑 잭 → 우 바깥 VCC
레일이다. 우 바깥 VCC 레일은 +15V 전용이고 LM741 pin 7 과 분배기 R10 만 거기 닿는다 — 엔진이 그 레일 넷에
다른 칩 핀이 닿으면 멈춘다(`DIP_SUPPLY`). 우 바깥 GND 레일은 회색 잭 둘째 선이 먹인다.

저항망(사용자 결정 2026-11-16): 우 블록 LED 아래 36~45행을 저항 구역으로 쓴다(`LED_BLOCK_PARTS_REASON`).
가산 노드는 우 a~e 38행과 우 f~j 38행 두 스트립을 골을 건너는 점퍼로 잇는다. 가중 저항은 두 행씩 세워
36행(OA·OC)과 40행(OB·OD)에서 38행으로 내려온다. Rf(R12)는 U4 pin 6 행(38, 레일 빈 행)에서 가운데 레일을
건너 가산 노드 왼쪽 끝에 눕는다 — 그래서 U4 를 pin 6 이 38행에 오게 36행에 둔다.

7490 출력(f쪽)은 74HC04 입력(a쪽)으로 바로 못 간다(R8). QA·QB·QC 는 LED 사슬 신호 스트립(`TAP`)을 거쳐
U2 로 간다 — 넷은 교안 핀 연결과 같다(실험08 C5 와 같은 중계). QD 는 U1 pin 11 → U2 pin 9 가 둘 다 f쪽이라 바로 간다.
"""
from functools import partial

from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips, place_paths,
    place_wires, place_marker_hints, draw_routed, removal_board, _dip_pin_row as _pin_row,
    _dip_side as _side, dip_pins)

BOARD = 'v2'
SLOTS = ('S1', 'S2', 'S3', 'S4')
LAYOUT = {'slots': {'S1': 4, 'S2': 15, 'S3': 25, 'S4': 36},
          'leds': {'dac': {'QD': 3, 'QC': 8, 'QB': 13, 'QA': 18}},
          'bridge': [48, 49], 'bridge_policy': 'lower-clearance-v1'}
# 저항망 행 — 가산 노드(U4 pin 6 행과 같다), +15V 착지, 분배기 윗행, DAC OUTPUT 계측선이 우 여백으로 가는 반 행
_SUM, _V15, _DIV, _PROBE = 38, 42, 43, 46.5
SIDE_LEAD_MAX = 10
SIDE_LEAD_MAX_REASON = ('74HC05 는 비트마다 입력·출력·1.5k 풀업 셋을 받는다. 교안 핀(게이트 1·2·3 = a쪽, 4 = f쪽)을 '
    '지키면 a쪽이 입력 셋·출력 셋·풀업 셋·GND 로 10 이다. 게이트를 옮기면 C3 절차 4 가 가리키는 U2→U3 선의 '
    '교안 핀 번호가 바뀐다.')
STAGE_WIRE_BUDGET = 5
STAGE_WIRE_BUDGET_REASON = ('가산 노드는 네 비트 가지를 한꺼번에 받는다. U3 출력 넷 → 가중 저항 스트립 넷 + 가산 노드 두 '
    '스트립을 잇는 골 점퍼 하나가 다섯이다(4입력 게이트 입력 4 + 1 과 같은 셈). 저항은 준비 그림에서 꽂는다.')
LED_BLOCK_PARTS_REASON = ('칩 넷(7490·74HC04·74HC05·LM741)이 좌 블록 3~39행을 채워 저항 열셋(풀업 넷 밖 가중 넷·Rf·'
    '분배기 셋)을 둘 자리가 없다. 사용자 결정(2026-11-16)으로 우 블록 LED 아래 36~45행을 저항 구역으로 쓴다.')

# 배선표 (첫 g, 끝 g, 색, 출발, 도착, 설명). g 는 아래 `_G` 표의 누적 단계다.
#   C1: 준비 1·2 = g1·g2, 단계 1·2 = g3·g4      C2: 단계 1~3 = g5~g7, 4단계 준비 1~3 = g8~g10,
#   단계 4·5·6 = g11·g12·g13 (6단계 앞이 VP 걷기)
_WIRES = (
    (3, None, 'sig', ('U1', 12), ('U1', 1), 'QA: U1 pin 12 -> U1 pin 1 (CLKB)'),
    (3, None, 'sig', ('U1', 12), ('LED', 'QA'), 'QA = U1 pin 12 -> LED QA'),
    (4, None, 'sig', ('U1', 9), ('LED', 'QB'), 'QB = U1 pin 9 -> LED QB'),
    (4, None, 'sig', ('U1', 8), ('LED', 'QC'), 'QC = U1 pin 8 -> LED QC'),
    (4, None, 'sig', ('U1', 11), ('LED', 'QD'), 'QD = U1 pin 11 -> LED QD'),
    (5, None, 'sig', ('U2', 1), ('TAP', 'QA'), 'QA: U1 pin 12 (LED QA 스트립) -> U2 pin 1'),
    (5, None, 'sig', ('U2', 3), ('TAP', 'QB'), 'QB: U1 pin 9 (LED QB 스트립) -> U2 pin 3'),
    (5, None, 'sig', ('U2', 5), ('TAP', 'QC'), 'QC: U1 pin 8 (LED QC 스트립) -> U2 pin 5'),
    (6, None, 'sig', ('U1', 11), ('U2', 9), 'QD: U1 pin 11 -> U2 pin 9'),
    (6, None, 'mid', ('U2', 2), ('U3', 1), "QA': U2 pin 2 -> U3 pin 1"),
    (6, None, 'mid', ('U2', 4), ('U3', 3), "QB': U2 pin 4 -> U3 pin 3"),
    (7, None, 'mid', ('U2', 6), ('U3', 5), "QC': U2 pin 6 -> U3 pin 5"),
    (7, None, 'mid', ('U2', 8), ('U3', 9), "QD': U2 pin 8 -> U3 pin 9"),
    (11, None, 'mid', ('NODE', 'SUM_E'), ('NODE', 'SUM_F'), '가산 노드: 우 a~e 38행 -> 우 f~j 38행'),
    (11, None, 'mid', ('U3', 2), ('NODE', 'OA'), 'OA: U3 pin 2 -> R5 윗다리 스트립'),
    (11, None, 'mid', ('U3', 4), ('NODE', 'OB'), 'OB: U3 pin 4 -> R6 아랫다리 스트립'),
    (11, None, 'mid', ('U3', 6), ('NODE', 'OC'), 'OC: U3 pin 6 -> R7 윗다리 스트립'),
    (11, None, 'mid', ('U3', 8), ('NODE', 'OD'), 'OD: U3 pin 8 -> R8 아랫다리 스트립'),
    (12, None, 'sig', ('U4', 2), ('NODE', 'SUM'), '가산 노드 -> U4 pin 2'),
    (12, 12, 'sig', ('U4', 3), ('NODE', 'GND'), 'VP: U4 pin 3 -> GND 레일'),
    (13, None, 'sig', ('U4', 3), ('NODE', 'WIPER'), 'VP: U4 pin 3 -> R9 가운데 단자'),
)
_INPUTS = ((3, None, 'CLK', 'U1', 14),)
_FINAL_G = 13
# 저항 (첫 g, 이름, 값, 한 끝, 다른 끝, 설명, 글자 자리). 끝은 (블록, 열, 행) 또는 ('rail', 블록, 열, 행).
_PULLUPS = ((6, 'R1', '1.5k', 'U3', 2), (6, 'R2', '1.5k', 'U3', 4), (7, 'R3', '1.5k', 'U3', 6),
            (7, 'R4', '1.5k', 'U3', 8))


def _rail_tie(bb, row, side, kind, desc):
    """고정 입력을 레일로 — a쪽은 좌 바깥, f쪽은 가운데 레일."""
    L = bb.cols['left']
    x_hole, x_rail = (L['a'], L[kind]) if side == 'a' else (L['j'], L['mid_' + kind])
    rail = bb.free_rail_row(row, x_rail)
    bb.step_wire([(x_hole, bb.r_y(row)), (x_rail, bb.r_y(rail))], kind, desc)


def _pullup(bb, name, value, top, pin):
    """1.5k 풀업 — 74HC05 출력 핀 스트립 끝 홀(a·j)에서 가까운 +5V 레일로 눕힌다(교안 p9 Pull up)."""
    L = bb.cols['left']
    n = dip_pins('74HC05')
    row = _pin_row(top, pin, n)
    x, x_rail = (L['a'], L['vcc']) if _side(pin, n) == 'a' else (L['j'], L['mid_vcc'])
    rail = bb.free_rail_row(row, x_rail)
    at = None if _side(pin, n) == 'a' else (L['j'] + 2, bb.r_y(row) + 7)
    bb.resistor((x, row), (x_rail, rail), name, value, f'U3 pin {pin} 풀업 -> +5V', text_at=at)


def _network(bb):
    """가중 저항 넷과 Rf — 우 블록 36~40행. 가산 노드는 38행 두 스트립."""
    L, R = bb.cols['left'], bb.cols['right']
    s = _SUM
    bb.resistor((L['j'], s), (R['a'], s), 'R12', '4.5k', 'Rf: U4 pin 6 행 -> 가산 노드',
                text_at=(R['a'] - 54, bb.r_y(s) - 18))
    bb.resistor((R['c'], s - 2), (R['c'], s), 'R5', '22.6k', 'QA 비트(LSB): OA 스트립 -> 가산 노드')
    bb.resistor((R['d'], s + 2), (R['d'], s), 'R6', '10.5k', 'QB 비트: OB 스트립 -> 가산 노드')
    bb.resistor((R['g'], s - 2), (R['g'], s), 'R7', '4.5k', 'QC 비트: OC 스트립 -> 가산 노드')
    bb.resistor((R['h'], s + 2), (R['h'], s), 'R8', '1.5k', 'QD 비트(MSB): OD 스트립 -> 가산 노드')


def _divider(bb, wiper_open):
    """분배기 +15V → R10 → R9(가변) → R11 → GND. R9 는 우 h 열 세 행, 와이퍼가 V+ 후보다."""
    R = bb.cols['right']
    d = _DIV
    bb.resistor((R['j'], d), (R['vcc'], bb.free_rail_row(d, R['vcc'])), 'R10', '1k', '+15V -> R9 윗단자',
                text_at=(R['j'] + 6, bb.r_y(d) - 19))
    bb.potentiometer(R['h'], d, 'R9', '330', '분배기 가변저항 — 가운데 단자가 V+ 후보', wiper_open=wiper_open)
    bb.resistor((R['j'], d + 2), (R['gnd'], bb.free_rail_row(d + 2, R['gnd'])), 'R11', '1k', 'R9 아랫단자 -> GND',
                text_at=(R['j'] + 6, bb.r_y(d + 2) + 7))


def _nodes(bb):
    """배선기 끝 — 저항 스트립의 빈 홀."""
    L, R = bb.cols['left'], bb.cols['right']
    s = _SUM
    bb.node('OA', [(R[c], s - 2) for c in 'ab'])
    bb.node('OB', [(R[c], s + 2) for c in 'ab'])
    bb.node('OC', [(R[c], s - 2) for c in 'f'])
    bb.node('OD', [(R[c], s + 2) for c in 'f'])
    bb.node('SUM_E', [(R['e'], s)])
    bb.node('SUM_F', [(R['f'], s)])
    bb.node('SUM', [(R['b'], s)])
    bb.node('GND', [(L['gnd'], r) for r in (s - 1, s - 2, s + 2)])
    bb.node('WIPER', [(R[c], _DIV + 1) for c in 'fg'])


def _ops(lay, k, g):
    u1, u2, u3, u4 = k['U1'], k['U2'], k['U3'], k['U4']
    ops = [(1, None, lambda b: b.draw_chip('7490', u1)), (1, None, lambda b: b.connect_jacks()),
           (1, None, lambda b: b.connect_rail_bridges(lay)), (1, None, lambda b: b.connect_power(u1, gnd_col='a'))]
    for p, name in ((2, 'R01'), (3, 'R02'), (6, 'R91'), (7, 'R92')):
        ops.append((1, None, partial(_rail_tie, row=_pin_row(u1, p, 14), side='a', kind='gnd',
                                     desc=f'U1 pin {p} {name} -> GND 레일')))
    ops.append((1, None, lambda b: b.mark_unused_inputs((4, 13), u1, chip='7490 (U1) n.c.')))
    for tag in ('QD', 'QC', 'QB', 'QA'):
        ops.append((2, None, partial(_chain, top=lay['leds']['dac'][tag], tag=tag)))
    ops += [(5, None, lambda b: b.draw_chip('74HC04', u2)), (5, None, lambda b: b.connect_power(u2, gnd_col='a')),
            (5, None, lambda b: b.mark_unused_inputs((11, 13), u2, chip='74HC04 (U2)')),
            (5, None, lambda b: b.mark_unused_outputs((10, 12), u2, chip='74HC04 (U2)'))]
    ops += [(6, None, lambda b: b.draw_chip('74HC05', u3)), (6, None, lambda b: b.connect_power(u3, gnd_col='a')),
            (6, None, lambda b: b.mark_unused_inputs((11, 13), u3, chip='74HC05 (U3)')),
            (6, None, lambda b: b.mark_unused_outputs((10, 12), u3, chip='74HC05 (U3)'))]
    for first, name, value, _u, pin in _PULLUPS:
        ops.append((first, None, partial(_pullup, name=name, value=value, top=u3, pin=pin)))
    ops += [(8, None, lambda b: b.draw_chip('LM741', u4)), (8, None, lambda b: b.connect_jacks_15v()),
            (8, None, lambda b: b.connect_power(u4, gnd_col='a', v15_rail_row=_V15)),
            (8, None, lambda b: b.mark_unused_inputs((1, 5, 8), u4, chip='LM741 (U4) OFFSET NULL·NC'))]
    ops.append((9, None, _network))
    ops.append((10, None, partial(_divider, wiper_open=g < 13)))
    ops.append((12, None, partial(_probe, top=u4)))
    return ops


def _chain(b, top, tag):
    b.led_chain(b.cols['right']['a'], top, tag, f'{tag}: 출력 1 이면 켜짐', block='right')


def _probe(b, top):
    L = b.cols['left']
    b.instrument(L['h'], _pin_row(top, 6, 8), 'DAC OUTPUT', '오실로스코프 CH — U4 pin 6 (DC 결합)',
                 lane_row=_PROBE, side='right')


def _input_ops(k):
    ops = []
    for first, last, name, u, pin in _INPUTS:
        n = dip_pins(DAC.models[u])

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
    res.led_block_parts = LED_BLOCK_PARTS_REASON
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


def _fixed(bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    g = _FINAL_G if stage is None else stage
    bb.led_order_policy = 'fixed'
    bb.route_side_lanes = True
    bb.led_block_parts = LED_BLOCK_PARTS_REASON
    k = place_chips(DAC, lay)
    _nodes(bb)
    ops = _ops(lay, k, g)
    # 입력을 LED 사슬보다 먼저 그린다 — 사슬 번호 원이 입력 배지를 비켜 간다(SKILL 배선기 문단)
    at = next(i for i, op in enumerate(ops) if getattr(op[2], 'func', None) is _chain)
    ops[at:at] = _input_ops(k)
    _apply(bb, ops, g, superset)


DAC = PlaceCircuit('dac', {'U1': 'S1', 'U2': 'S2', 'U3': 'S3', 'U4': 'S4'},
                   {'U1': '7490', 'U2': '74HC04', 'U3': '74HC05', 'U4': 'LM741'},
                   ('QD', 'QC', 'QB', 'QA'), _WIRES, _fixed,
                   tuple((u, p) for *_x, u, p in _INPUTS))
PLACE = [DAC]


def _board(path, template, g, baseline, title, sub, *, palette=False, partial_=None, submit=False,
           hand=None, hand_guide=False):
    bb = BreadboardRenderer(template, baseline=baseline, board=BOARD, palette=palette, hand=hand, hand_guide=hand_guide)
    bb.side_lead_max = SIDE_LEAD_MAX
    bb.led_order_policy = 'fixed'
    bb.led_block_parts = LED_BLOCK_PARTS_REASON
    bb.enable_steps()
    bb.partial = partial_
    bb.set_header(title, sub, submit=submit)
    bb.marker_hints = place_marker_hints(DAC, LAYOUT)
    DAC.fixed(bb, g, False, LAYOUT)
    draw_routed(bb, place_wires(DAC, LAYOUT), place_paths(DAC, LAYOUT), g)
    return bb


_POWER_OFF = '전원과 신호발생기 출력을 꺼요. 배선만 육안으로 대조해요.'
_E1 = '실험 1) DAC — 1. 7490 카운터 확인'
_E2 = '실험 1) DAC — 2~3. DAC 전체 회로'
_E3 = '실험 1) DAC — 4~6. 핀 개방·Rf 변경·병렬 저항'
_NOTE_POWER = ('7490 전원은 pin 5(+5V)·pin 10(GND), 74HC04·74HC05 는 pin 14·7, LM741 은 pin 7(+15V)·pin 4(GND)다. '
               '+15V 는 우 바깥 레일 하나에만 있다.')


def _hand_guard(hand, stage):
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')


def build_e10_counter(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    _hand_guard(hand, stage)
    g = 4 if stage is None else 2 + stage
    bb = _board(output_path, template_path, g, baseline, _E1 + (f' {stage}단계' if stage else ''),
                '7490 ×1 · CLK 사각파 주기 1s · LED QD~QA', palette=stage is not None, partial_=g < 4,
                submit=stage is None, hand=hand, hand_guide=hand_guide)
    bb.note('7490 전원은 pin 5(+5V), pin 10(GND)다. R01·R02·R91·R92(pin 2·3·6·7)는 GND 다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_counter(output_path, template_path=None, baseline=None, *, order):
    titles = ('칩·전원·리셋 핀 준비', 'LED 준비')
    bb = _board(output_path, template_path, order, baseline, f'{_E1} 준비 {order} · {titles[order - 1]}',
                _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


_DAC_STAGE_G = {1: 5, 2: 6, 3: 7, 4: 11, 5: 12, 6: 13}


def build_e10_dac(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    _hand_guard(hand, stage)
    g = _FINAL_G if stage is None else _DAC_STAGE_G[stage]
    sub = ('7490 + 74HC04 + 74HC05 + LM741 · ' + ('CLK 주기 1s' if g <= 7 else 'CLK 1.0kHz')
           + (' · V+ = R9 가운데 단자' if g >= 13 else ' · V+ = GND' if g == 12 else ''))
    bb = _board(output_path, template_path, g, baseline, _E2 + (f' {stage}단계' if stage else ''), sub,
                palette=stage is not None, partial_=g < _FINAL_G, submit=stage is None, hand=hand,
                hand_guide=hand_guide)
    bb.note(_NOTE_POWER)
    bb.note('QA·QB·QC 는 LED 사슬 신호 스트립을 거쳐 U2 입력으로 간다. 교안 핀 연결과 같은 넷이다.')
    bb.export(output_path, max_row=63)
    return bb


def _prep_dac(output_path, template_path=None, baseline=None, *, order):
    titles = ('LM741·+15V 전원 준비', '가중 저항·Rf 준비', '분배기 준비')
    bb = _board(output_path, template_path, 7 + order, baseline, f'{_E2} 준비 {order} · {titles[order - 1]}',
                _POWER_OFF, palette=True, partial_=True)
    bb.export(output_path, max_row=63)
    return bb


def build_e10_change(output_path, template_path=None, stage=None, baseline=None, hand=None, hand_guide=False):
    """C3 — 보드는 C2 완성본과 같다. 바꾸는 자리(U2→U3 선 셋·R12·R6)를 체크리스트가 이 그림으로 짚는다."""
    _hand_guard(hand, stage)
    bb = _board(output_path, template_path, _FINAL_G, baseline, _E3 + (f' {stage}단계' if stage else ''),
                '발생기 1.0kHz · 바꾼 것은 그 절차가 끝나면 되돌린다', palette=stage is not None,
                submit=False, hand=hand, hand_guide=hand_guide)
    bb.note(_NOTE_POWER)
    bb.note('절차 4 는 U2→U3 선의 U3 쪽 끝을 잠시 뽑아 들고 본 뒤 다시 꽂는다. 절차 5 는 R12 를 2.7k 로 바꿨다가 '
            '4.5k 로, 절차 6 은 22.6k 세 개 직렬(68k 대신, 조교 지시)을 점퍼로 R6 와 병렬로 이었다가 점퍼를 뽑는다.')
    bb.export(output_path, max_row=63)
    return bb


_OPEN_WIRES = ("QA': U2 pin 2 -> U3 pin 1", "QB': U2 pin 4 -> U3 pin 3", "QC': U2 pin 6 -> U3 pin 5")


def _final_snapshot(template_path=None):
    import os, tempfile
    with tempfile.TemporaryDirectory() as d:
        return build_e10_change(os.path.join(d, 'base.png'), template_path, stage=1).snapshot()


def _open_board(output_path, template_path=None, stage=None, baseline=None):
    """C3 1단계 — 절차 4(T5~T7)에서 하나씩 뽑았다 다시 꽂는 U2→U3 선 셋을 걷기 표시(빨간 점선·번호)로 짚는다.

    보드에는 아무것도 새로 꽂지 않는다. 걷기 보드 꼴을 빌려 세 선만 표시하고 나머지는 회색 C2 완성본이다.
    `build_` 접두어를 두지 않는다 — `removal_board` 와 같은 이유(steps 가 비어 가독성 검사에 걸린다).
    """
    base = _final_snapshot(template_path)
    keys = {k: _OPEN_WIRES.index(desc) + 1 for k, desc in base['wires'].items() if desc in _OPEN_WIRES}
    assert len(keys) == 3, keys
    ghost = dict(base, ghost={'wires': keys, 'title': f'{_E3} 1단계 · 선 개방(T5~T7)',
                              'subtitle': '빨간 선 ①→T5, ②→T6, ③→T7. U3 쪽 끝 하나만 뽑아 보고 다시 꽂아요'})
    return build_e10_change(output_path, template_path, stage=1, baseline=ghost)


def _rf_board(output_path, template_path=None, stage=None, baseline=None):
    """C3 2단계 — 절차 5(T8). 회색 C2 완성본 위에 R12(Rf) 자리만 빨간 점선 ①로 짚는다. 같은 두 홀에
    2.7k 를 꽂았다가 4.5k 로 되돌리므로 새로 그릴 선·부품은 없다."""
    bb = _board(output_path, template_path, _FINAL_G, _final_snapshot(template_path),
                f'{_E3} 2단계 · Rf 교체(T8)', '빨간 점선 ① R12(4.5k)를 뽑고 같은 두 구멍에 2.7k. 끝나면 4.5k 로',
                palette=True, submit=False)
    L, R = bb.cols['left'], bb.cols['right']
    bb.mark_part((L['j'], _SUM), (R['a'], _SUM), 1)
    bb.note('R12 = 좌 j38(U4 pin 6 행) ↔ 우 a38(가산 노드). 바꾸는 동안 전원과 발생기 출력을 꺼요.')
    bb.export(output_path, max_row=63)
    return bb


# T9 병렬 사슬 — 68k 대신 22.6k 세 개 직렬(67.8k, 조교 지시 2026-11-20). R6 둘레(우 38~42행)에는 세 개를 세울
# 자리가 없다: 우 a~e 38행은 다 차 있고, 39행은 R6 몸통·글자가 막고, 40.5·41.5행에는 OD·+15V 가로선이 지나
# 세운 저항이 선을 가린다(R15). 그래서 빈 아래 영역(우 a~e 51~57행)에 사슬을 세우고(3단계 준비) 점퍼 둘로
# OB 스트립(R6 아랫다리 줄, 40행)과 가산 노드(우 f~j 38행 — e38→f38 점퍼로 a~e 38행과 같은 넷)에 잇는다(3단계).
_T9 = (('b', 51, 53), ('c', 53, 55), ('d', 55, 57))      # (열, 윗행, 아랫행)


def _t9_chain(bb):
    R = bb.cols['right']
    for k, (c, r0, r1) in enumerate(_T9, 1):
        bb.resistor((R[c], r0), (R[c], r1), f'R{12 + k}', '22.6k',
                    f'T9 사슬 {k}/3: 우 {r0}행 스트립 -> 우 {r1}행 스트립 (68k 대신)')


def _chain_prep(output_path, template_path=None, baseline=None, *, order=1):
    """C3 3단계 준비 — 사슬만 꽂는다. 회로와는 아직 닿지 않으니 양 끝(우 51행·57행)을 멀티미터로 재 67.8k 를 본다."""
    bb = _board(output_path, template_path, _FINAL_G, _final_snapshot(template_path),
                f'{_E3} 3단계 준비 · 22.6k 사슬', '22.6k 세 개를 우 51→53, 53→55, 55→57행에 세워 직렬로(68k 대신)',
                palette=True, partial_=True)
    _t9_chain(bb)
    bb.note('사슬 양 끝 = 우 a~e 51행과 우 a~e 57행. 전원과 상관없이 두 스트립 사이를 멀티미터로 재 약 67.8kΩ 을 확인한다.')
    bb.export(output_path, max_row=63)
    return bb


def _lane_route(bb, srcs, dsts):
    """끝 홀 후보 둘 사이의 점퍼 경로 — [A, 반 행, 열 사이 통로 X, 반 행, B] 꼴을 모두 대 보고 엔진의 합법 검사
    (`_valid`: 홀 위·다리 위·몸통 건너기 금지)와 번호 원 자리(`_marker_spot`)를 통과한 가장 짧은 것. 엔진
    배선기(`_routes`)의 통로 후보에는 우 블록 아래 빈 영역에서 올라오는 경로가 없어 여기서 고른다."""
    from render_breadboard import _seg_boxes, _clean, _valid, _marker_spot
    R, half = bb.cols['right'], bb.spec.row_pitch / 2
    xs = sorted(R[c] for c in 'abcdefghij')
    lanes = [(a + b) / 2 for a, b in zip(xs, xs[1:])]
    segs = [(k, pts) for k, pts, _ in bb._segments]
    boxes = _seg_boxes(segs)
    others = [p for _k, pts, _d in bb._segments for p in (pts[0], pts[-1])]
    others += [(x, bb.r_y(r)) for (x, r), what in bb._leads.items() if '다리' in what]
    best = None
    for ax, ar in srcs:
        for bx, br in dsts:
            if (ax, ar) in bb._leads or (bx, br) in bb._leads:
                continue
            A, B = (ax, bb.r_y(ar)), (bx, bb.r_y(br))
            for X in lanes:
                for y1 in (A[1] - half, A[1] + half):
                    for y2 in (B[1] - half, B[1] + half):
                        p = _clean([A, (A[0], y1), (X, y1), (X, y2), (B[0], y2), B])
                        if not _valid(bb, p, others, segs, boxes):
                            continue
                        m = _marker_spot(bb, p)
                        if m is None:
                            continue
                        cost = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(p, p[1:]))
                        if best is None or cost < best[0]:
                            best = (cost, p, m)
    assert best is not None, f'점퍼 경로 없음: {srcs} -> {dsts}'
    return best[1], best[2]


def _parallel_board(output_path, template_path=None, stage=None, baseline=None):
    """C3 3단계 — 절차 6(T9). R6 는 그대로 두고 사슬 양 끝을 점퍼 둘로 OB 스트립과 가산 노드에 잇는다.
    끝나면 점퍼 둘만 뽑는다(사슬은 남겨도 회로와 안 닿는다)."""
    import os, tempfile
    with tempfile.TemporaryDirectory() as d:
        base = _chain_prep(os.path.join(d, 'prep.png'), template_path).snapshot()
    bb = _board(output_path, template_path, _FINAL_G, base, f'{_E3} 3단계 · 병렬 저항(T9)',
                'R6 는 그대로. 사슬 두 끝을 점퍼로 R6 아랫다리 줄·가산 노드에. 끝나면 점퍼만 뽑아요',
                palette=True, submit=False)
    _t9_chain(bb)
    R = bb.cols['right']
    top = [(R[c], _T9[0][1]) for c in 'acde']
    bot = [(R[c], _T9[-1][2]) for c in 'abce']
    for srcs, dsts, desc in ((top, [(R[c], _SUM + 2) for c in 'bce'], 'T9 사슬 윗끝 -> OB 스트립(R6 아랫다리 줄)'),
                             (bot, [(R[c], _SUM) for c in 'ij'], 'T9 사슬 아랫끝 -> 가산 노드(우 f~j 38행)')):
        path, marker = _lane_route(bb, srcs, dsts)
        bb.step_wire(path, 'sig', desc, marker_at=marker)
    bb.note('68k 대신 22.6k ×3 직렬(조교 지시). 10.5k ∥ 67.8k ≈ 9.1k. 끝나면 점퍼 둘을 뽑으면 보드가 C2 완성본 회로와 같다.')
    bb.export(output_path, max_row=63)
    return bb


_N1 = '실험10_1_결선도_7490카운터'
_N2 = '실험10_1_결선도_DAC'
BOARDS = [
    (f'{_N1}_1단계_QA.png', build_e10_counter, 1), (f'{_N1}_2단계_QBQCQD.png', build_e10_counter, 2),
    (f'{_N2}_1단계_7404.png', build_e10_dac, 1), (f'{_N2}_2단계_7405AB.png', build_e10_dac, 2),
    (f'{_N2}_3단계_7405CD.png', build_e10_dac, 3), (f'{_N2}_4단계_가중저항.png', build_e10_dac, 4),
    (f'{_N2}_5단계_가산기.png', build_e10_dac, 5),
    (f'{_N2}_6걷기_VP.png', removal_board((build_e10_dac, 5), (build_e10_dac, 6),
        '실험 1) DAC — 2~3. V+ 점퍼 걷기', '전원과 발생기 출력을 꺼요. 빨간 선(VP → GND)만 뽑아요.'), None),
    (f'{_N2}_6단계_분배기.png', build_e10_dac, 6),
    (f'{_N2}_1단계_선개방.png', _open_board, None),
    (f'{_N2}_2단계_Rf.png', _rf_board, None),
    (f'{_N2}_3단계_병렬.png', _parallel_board, 3),
]
ASSEMBLY_BOARDS = {
    f'{_N1}_1단계_QA.png': [(f'{_N1}_1준비_{i}.png', partial(_prep_counter, order=i)) for i in (1, 2)],
    f'{_N2}_4단계_가중저항.png': [(f'{_N2}_4준비_{i}.png', partial(_prep_dac, order=i)) for i in (1, 2, 3)],
    f'{_N2}_3단계_병렬.png': [(f'{_N2}_3준비_사슬.png', _chain_prep)],
}
FINALS = [(f'{_N1}.png', build_e10_counter), (f'{_N2}.png', build_e10_dac)]
