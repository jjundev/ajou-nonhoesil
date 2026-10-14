# 번호 원 고정 시험용 합성 보드 — 실험 보드가 아니다. 배치기(`place_search`)로 고른 자리가 아니라
# 함정이 서도록 손으로 정한 자리다(`PlaceEnforced` 대상 아님).
#
# 함정: 단계 1 에만 있는 LED 사슬 셋(우 a 22·28·38행)이 입력 E(U4 pin 13, 좌 30행) 점퍼 번호 원의
# 기본 자리를 막는다. 힌트(`place_marker_hints`) 없이 그리면 그 원이 단계 그림과 완성본에서 다른
# 자리에 앉는다 — 2026-10-05 실험04 v2 시험판 MUX 입력 E·D3 와 같은 꼴(`test_breadboard_place.MarkerTrap`).
from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips,
                               place_marker_hints, place_paths, draw_routed,
                               _dip_pin_row as _pin_row, _dip_side as _side)

BOARD = 'v2'
SLOTS = ('K1',)
LAYOUT = {'slots': {'K1': 29}, 'leds': {'trap': {'L1': 22, 'L2': 28, 'L3': 38}}, 'bridge': [48, 49]}
STAGES = (1, 2, None)

_WIRES = (
    (1, 1, 'sig', ('U4', 12), ('LED', 'L1'), '임시 급전: U4 pin 12 -> LED1'),
    (1, 1, 'sig', ('U4', 8), ('LED', 'L3'), '임시 급전: U4 pin 8 -> LED3'),
    (1, 1, 'sig', ('U4', 6), ('LED', 'L2'), '임시 급전: U4 pin 6 -> LED2'),
    (2, None, 'sig', ('U4', 12), ('LED', 'L1'), 'Y = U4 pin 12 -> LED1'),
)
_INPUTS = ((1, 'E', 'U4', 13), (1, 'S1', 'U4', 9), (1, 'S0', 'U4', 5))


def _frame(bb, layout):
    L = bb.cols['left']
    gnd_row, vcc_row = layout['bridge']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], gnd_row, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], vcc_row, kind='vcc')


def _fixed(bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    R, L, k, leds = bb.cols['right'], bb.cols['left'], place_chips(TRAP, lay), lay['leds']['trap']
    bb.draw_chip('74HC04', k['U4'])
    _frame(bb, lay)
    bb.connect_power(k['U4'], gnd_col='a')
    if superset or (stage is not None and stage < 2):
        for tag in ('L1', 'L2', 'L3'):
            bb.led_chain(R['a'], leds[tag], tag, '임시 관측', block='right')
    else:
        bb.led_chain(R['a'], leds['L1'], 'Y', 'Y', block='right')
    for s, name, chip, pin in _INPUTS:
        if superset or stage is None or s <= stage:
            side = _side(pin)
            _input_jumper(bb, L, _pin_row(k[chip], pin), name, f'{chip} pin {pin}',
                          side=side, col='a' if side == 'a' else 'j')


TRAP = PlaceCircuit('trap', {'U4': 'K1'}, {'U4': '74HC04'}, ('L1', 'L2', 'L3'), _WIRES, _fixed,
                    tuple((c, p) for _s, _n, c, p in _INPUTS))


def _draw(bb, stage, hints=True):
    """실험 빌더의 그리기 함수와 같은 순서. `hints=False` 는 함정이 살아 있는지 재는 시험 전용."""
    bb.partial = stage is not None and stage < 2
    bb.marker_hints = place_marker_hints(TRAP, LAYOUT) if hints else {}
    _fixed(bb, stage)
    draw_routed(bb, TRAP.wires, place_paths(TRAP, LAYOUT), stage)
