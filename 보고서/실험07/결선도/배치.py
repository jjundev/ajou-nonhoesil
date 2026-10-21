"""실험07 6-bit shift register — v2 보드, v3 관측 절차.

BIT1/3/5 = 각 HC76 둘째 F/F(J9 K12 Q11 Q'10), BIT2/4/6 = 첫째 F/F.
패키지 경계는 Q15→J9, Q'14→K12로 모두 f쪽이다(R8 유지).
LED 실제 순서는 BIT2, BIT1, BIT4, BIT3, BIT6, BIT5다(R10).
"""
from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit,
    place_chips, place_paths, place_marker_hints, draw_routed, removal_board,
    _dip_pin_row as _pin_row, _dip_side as _side)

BOARD = 'v2'
SLOTS = ('S1', 'S2', 'S3', 'S4')
LAYOUT = {'bridge': [51, 52], 'leds': {'shift': {'BIT1': 22, 'BIT2': 18, 'BIT3': 33, 'BIT4': 28, 'BIT5': 44, 'BIT6': 40}}, 'slots': {'S1': 7, 'S2': 17, 'S3': 28, 'S4': 39}}
SIDE_LEAD_MAX = 12
SIDE_LEAD_MAX_REASON = ('74HC76 두 F/F를 모두 사용한다. 중간 패키지의 a쪽은 CLK 네 끝+CLR 네 끝+'
    'PR 둘+VCC 하나+J 하나=12, f쪽은 J/K/Q/Q보수 여덟 핀 중 GND 포함 8끝+LED 두 끝=10이다. '
    'DIP-16 여덟 행의 32 자유 홀에 분산하며 R1~R6·R8~R14는 그대로 검사한다. '
    '입력 분배를 합쳐도 사용 16핀+LED 2가닥으로 총 18끝 이상이므로 양쪽 8로는 불가능하다.')

# (첫 단계, 끝 단계, 색, 출발, 도착, 설명). 배선당 처음 꽂는 단계만 다르고 경로는 동일하다.
_WIRES = [
    (1, None, 'sig', ('U1', 12), ('U1', 13), 'D 두 입력 묶음: U1 pin 12 -> U1 pin 13'),
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
    (7, None, 'sig', ('U1', 12), ('U2', 9), 'D: U1 pin 12 -> U2 pin 9 (BIT1 J)'),
    (7, None, 'sig', ('U1', 11), ('U2', 12), "D' (U1 pin 11) -> U2 pin 12 (BIT1 K)"),
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
_INPUTS = [(1, 'D', 'U1', 12), (2, 'CLK', 'U2', 1), (4, 'CLR', 'U2', 3),
           (6, 'PR1', 'U2', 7), (6, 'PR2', 'U2', 2)]
_LED_ORDER = ('BIT2', 'BIT1', 'BIT4', 'BIT3', 'BIT6', 'BIT5')


def _fixed(bb, stage, superset=False, layout=None, _with_temps=True):
    lay = layout or LAYOUT
    L, R, k = bb.cols['left'], bb.cols['right'], place_chips(SHIFT, lay)
    for u in ('U1', 'U2', 'U3', 'U4'):
        bb.draw_chip(SHIFT.models[u], k[u])
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], lay['bridge'][0], kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], lay['bridge'][1], kind='vcc')
    for u in ('U1', 'U2', 'U3', 'U4'):
        bb.connect_power(k[u], gnd_col='a')
    # 사용하는 PR을 1로 고정한다. 미사용 입력으로 등록하지 않는다.
    for u in ('U3', 'U4'):
        for p in (2, 7):
            row = _pin_row(k[u], p, 16)
            rail_row = bb.free_rail_row(row, L['vcc'])
            bb.step_wire([(L['a'], bb.r_y(row)), (L['vcc'], bb.r_y(rail_row))], 'vcc',
                         f'{u} pin {p} PR 비활성 -> +5V 레일')
    for first, name, u, p in _INPUTS:
        if superset or stage is None or first <= stage:
            n = 14 if u == 'U1' else 16
            side = _side(p, n)
            _input_jumper(bb, L, _pin_row(k[u], p, n), name, f'{u} pin {p}',
                          side=side, col='a' if side == 'a' else 'j')
    for tag in _LED_ORDER:
        bb.led_chain(R['a'], lay['leds']['shift'][tag], tag,
                     f'{tag}: 출력 1이면 켜짐 · 명세 기록 순서와 보드 번호가 다름', block='right')
    bb.mark_unused_inputs((1, 2, 4, 5, 9, 10), k['U1'], chip='74HC00 (U1)')
    bb.mark_unused_outputs((3, 6, 8), k['U1'], chip='74HC00 (U1)')
    bb.mark_unused_outputs((14,), k['U4'], chip='74HC76 (U4)')

    # a쪽 임시선은 CLK·CLR 분배선과 함께 남는다. f쪽 J/K 임시선은 해당
    # 데이터선 연결 전에 걷는다. 둘을 동시에 superset에 강제하면 존재하지 않는
    # 배선 조합이 경로를 막는다. 실제 모든 단계·걷기 보드는 별도로 verify한다.
    if _with_temps and (superset or stage is not None):
        for active_from, u, pin, kind, path in _temporary_plan(lay):
            if (superset and _side(pin, 16) == 'a') or (not superset and stage < active_from):
                bb.step_wire(path, kind, f'임시 {u} pin {pin} -> {"+5V" if kind == "vcc" else "GND"} · {active_from}걷기에서 뽑아요',
                             marker_at=(80 if _side(pin, 16) == 'a' else 1160, path[0][1]))


# 아직 연결하지 않은 **사용 입력**이다. 미사용 핀으로 등록하거나 플로팅으로 두지 않는다.
_TEMP = [(2, 'U2', 1, 'gnd'), (2, 'U2', 6, 'gnd'), (2, 'U3', 1, 'gnd'),
         (3, 'U3', 6, 'gnd'), (3, 'U4', 1, 'gnd'), (3, 'U4', 6, 'gnd'),
         (4, 'U2', 3, 'gnd'), (4, 'U2', 8, 'gnd'), (4, 'U3', 3, 'gnd'),
         (5, 'U3', 8, 'gnd'), (5, 'U4', 3, 'gnd'), (5, 'U4', 8, 'gnd'),
         (6, 'U2', 7, 'vcc'), (6, 'U2', 2, 'vcc')]
for _i, (_u, _j, _k, _q, _qb) in enumerate(_BITS, 7):
    _TEMP.extend([(_i, _u, _j, 'gnd'), (_i, _u, _k, 'gnd')])
_TEMP_PLANS = {}


def _temporary_plan(lay):
    # 모든 단계의 고정 입력·LED 레일을 먼저 예약해, 남은 임시선이 단계 사이에서 움직이지 않게 한다.
    key = repr(lay)
    if key not in _TEMP_PLANS:
        proto = BreadboardRenderer(board=BOARD)
        proto.enable_steps()
        _fixed(proto, None, True, lay, _with_temps=False)
        L, k, plan = proto.cols['left'], place_chips(SHIFT, lay), []
        for active_from, u, pin, kind in _TEMP:
            row = _pin_row(k[u], pin, 16)
            side = _side(pin, 16)
            col = 'a' if side == 'a' else 'j'
            rail = L[kind] if side == 'a' else L['mid_'+kind]
            rail_row = proto.free_rail_row(row, rail)
            x0, y0 = L[col], proto.r_y(row)
            direction = 1 if rail > x0 else -1
            lane_y = y0 + proto.spec.row_pitch / 2
            path = [(x0, y0), (x0 + direction*12, lane_y),
                    (rail - direction*12, lane_y), (rail, proto.r_y(rail_row))]
            proto.step_wire(path, kind, f'임시 {u} pin {pin}', marker_at=(40, proto.r_y(row)))
            plan.append((active_from, u, pin, kind, path))
        _TEMP_PLANS[key] = plan
    return _TEMP_PLANS[key]


def build_e7_shift(output_path, template_path=None, stage=None, baseline=None, layer=None,
                   hand=None, hand_guide=False):
    if stage is not None and (layer is not None or hand is not None):
        raise ValueError('layer/hand는 완성본에만 준다')
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD,
                            palette=stage is not None, hand=hand, hand_guide=hand_guide)
    bb.side_lead_max = SIDE_LEAD_MAX
    bb.partial = stage is not None and stage < 12
    bb.enable_steps()
    bb.set_header('실험 1) 6bit Shift Right Register' + (f' — {stage}단계' if stage else ''),
                  '74HC00 ×1 + 74HC76 ×3 · D = SERIAL DATA · BIT 역할을 패키지 안에서 교환',
                  submit=stage is None)
    bb.marker_hints = place_marker_hints(SHIFT, LAYOUT)
    _fixed(bb, stage)
    draw_routed(bb, SHIFT.wires, place_paths(SHIFT, LAYOUT), stage)
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
FINALS = [(f'{_NAME}.png', build_e7_shift)]

# 완성본 번호를 빠짐없이 나눈 손그림 안내용 층.
LAYERS = {f'{_NAME}.png': [
    (1, 4, '전원 잭·레일 브리지'), (5, 12, 'U1~U4 전원'),
    (13, 16, 'BIT3~6 프리셋 비활성'), (17, 21, '입력 D·CLK·CLR·PR1·PR2'),
    (22, 27, 'LED BIT2·BIT1·BIT4 사슬'), (28, 33, 'LED BIT3·BIT6·BIT5 사슬'),
    (34, 39, '입력 반전·공통 CLK'), (40, 44, '공통 CLR'),
    (45, 47, 'BIT1 데이터·LED'), (48, 50, 'BIT2 데이터·LED'),
    (51, 53, 'BIT3 데이터·LED'), (54, 56, 'BIT4 데이터·LED'),
    (57, 59, 'BIT5 데이터·LED'), (60, 62, 'BIT6 데이터·LED'),
]}
