# 실험05 결선 — 엔진 `render_breadboard.py --experiment 5` 가 이 파일의 `BOARDS`(기준선 사슬)·
# `FINALS`(완성본)를 뽑는다. 근거: `보고서/실험05/결선도/netlist.md`(C1 BCD 디코더 · C2 Excess-3
# 인코더), `체크리스트/명세.md`.
#
# v2 판형(SKILL §2b) — 칩은 전부 좌 블록(R9), LED 는 우 a 열(R10). R8 은 면제하지 않는다.
#
#   K1 : 74HC42 (U4) / 비움
#   K2 : 비움 / 74HC04 (U1)
#   K3 : 비움 / 74HC20 (U2)
#   K4 : 비움 / 74HC20 (U3)
#   행은 `LAYOUT` — 배치기(`python -m scripts.lab.place_search 보고서/실험05/결선도/배치.py`)가 고른 값을
#   옮겨 적는다(SKILL §4a). 손으로 고치지 않는다 — PlaceEnforced 가 `배치탐색.md` 와 맞댄다.
#
# **C1** 은 시험판(`tests/fixtures/board_v2_e5/배치.py`)과 같은 결선이다 — LED 는 칩 핀 행 순서(Y0~Y5,
# Y9, Y6, Y8, Y7 — netlist M17), a쪽 출력 → LED 선은 칩 이름 상자에 가까운 핀부터 적는다(SKILL §2b).
#
# **C2 의 팬아웃은 칩 사이 선이 같은 쪽끼리 가도록 짠다**(R8, SKILL §4a 「v2 에서 R8 과 함께 가기」).
# 쪽을 바꾸는 신호는 셋이다 — `D4'`(a→f)는 U3 안에서 pin 1 → 9, `D0'`(f→a)는 U3 안에서 pin 12 → 4,
# `D3'`(a→f)는 **U2 의 n.c. pin 3 을 디딤돌로** U3 pin 2 → U2 pin 3 → U2 pin 10 이다(netlist M18).
# `D2'` 는 U1 pin 8 → U2 pin 12 → U3 pin 10 순서로 잇는다 — U3 f쪽 리드를 8 에 묶는다(R7).
# 칩 한쪽 리드는 U1 f·U2 a·U3 a·U3 f 가 8 이다(superset, 임시 급전 포함).
# LED 는 진리표 열 순서 A3·A2·A1·A0 이다. 2단계 임시 급전이 LED A2 를 빌리므로 R10 은 U1 이 U2 와
# U3 사이에 설 때만 맞는다 — 배치기가 그런 순서만 통과시킨다. 임시 급전은 f쪽 `D0'`(U1 pin 12)다 —
# a쪽 `D4'`(pin 4)는 a쪽 리드 여덟 사이로 칩 몸통을 건널 반 행이 없어 어느 배치에서도 길이 없었다.
from render_breadboard import (BreadboardRenderer, _input_jumper, fresh_board, removal_board,
                               PlaceCircuit, place_chips, place_paths, place_marker_hints, draw_routed,
                               _dip_pin_row as _pin_row, _dip_side as _side)

BOARD = 'v2'
SLOTS = ('K1', 'K2', 'K3', 'K4')
LAYOUT = {'slots': {'K1': 3, 'K2': 17, 'K3': 5, 'K4': 29},
          'leds': {'bcd': {'Y0': 6, 'Y1': 10, 'Y2': 14, 'Y3': 18, 'Y4': 22, 'Y5': 26, 'Y9': 30, 'Y6': 34,
                           'Y8': 38, 'Y7': 42},
                   'xs3': {'A3': 7, 'A2': 13, 'A1': 32, 'A0': 38}},
          'bridge': [41, 42]}

STAGE_WIRE_BUDGET = 5
STAGE_WIRE_BUDGET_REASON = ('74HC42 출력 하나는 입력 넷이 다 있어야 정해지고(C1 1단계 = 입력 넷 + 급전 '
                            '하나), 74HC20 출력 하나도 입력 넷을 받는다 — 입력 일부만 물리면 관측 노드 '
                            '상류가 뜬다. 예산 = 게이트 입력 수 + 1 (netlist M8, 실험04 와 같은 근거)')

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다.')


def _frame(bb, layout):
    """잭 → 좌 바깥 레일, 좌 바깥 → 가운데 브리지 두 가닥(SKILL §2b). 우 바깥 레일은 안 쓴다."""
    L = bb.cols['left']
    gnd_row, vcc_row = layout['bridge']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], gnd_row, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], vcc_row, kind='vcc')


def _inputs(bb, chips, inputs, stage, superset, pins=14):
    L = bb.cols['left']
    for s, name, chip, pin in inputs:
        if superset or stage is None or s <= stage:
            side = _side(pin, pins)
            _input_jumper(bb, L, _pin_row(chips[chip], pin, pins), name, f'{chip} pin {pin}',
                          side=side, col='a' if side == 'a' else 'j')


# ---------------- C1 BCD → 10진 디코더 ----------------

_BCD_LEDS = ('Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y9', 'Y6', 'Y8', 'Y7')
_BCD_OUT = {'Y0': 1, 'Y1': 2, 'Y2': 3, 'Y3': 4, 'Y4': 5, 'Y5': 6, 'Y6': 7, 'Y7': 9, 'Y8': 10, 'Y9': 11}
# (출력, 단계) — 순서 = 그리는 순서 = 경로를 정하는 순서(머리 주석). 단계는 netlist `## 단계` 표.
_BCD_ORDER = (('Y3', 2), ('Y2', 2), ('Y1', 2), ('Y0', 1), ('Y4', 3), ('Y5', 3), ('Y6', 3),
              ('Y9', 4), ('Y8', 4), ('Y7', 4))
_BCD_WIRES = [(s, None, 'sig', ('U4', _BCD_OUT[t]), ('LED', t), f'{t} = U4 pin {_BCD_OUT[t]} -> LED {t}')
              for t, s in _BCD_ORDER]
# 입력 점퍼 (단계, 이름, 칩, 핀). Bit0 이 최하위(교안 p9 SW1 = 74HC42 A).
_BCD_INPUTS = [(1, 'Bit0', 'U4', 15), (1, 'Bit1', 'U4', 14), (1, 'Bit2', 'U4', 13), (1, 'Bit3', 'U4', 12)]
_LOW_NOTE = 'Y0~Y9 LED 는 출력 0 에서 켜진다(Negative Logic).'
_ORDER_NOTE = ('LED 는 74HC42 출력 핀의 행 순서로 붙는다 — 위에서부터 Y0~Y5, Y9, Y6, Y8, Y7'
               '(Y7·Y8·Y9 = pin 9·10·11 이 아래에서 위로 올라간다). 진리표 열 순서(Y0~Y9)와 다르다(netlist M17).')


def _bcd_fixed(bb, stage, superset=False, layout=None):
    """칩·전원·브리지·LED 열 사슬(Negative Logic)·입력 점퍼 — 전부 1단계 기반이다."""
    lay = layout or LAYOUT
    R, k = bb.cols['right'], place_chips(BCD, lay)
    bb.draw_chip('74HC42', k['U4'])
    _frame(bb, lay)
    bb.connect_power(k['U4'], gnd_col='a')
    # 입력 점퍼를 LED 사슬보다 먼저 — 번호 원은 그때까지 그려진 배지만 피한다. 사슬이 먼저면 `Y0` 사슬
    # 번호 원(우 c9)이 뒤에 붙는 `Bit3` 배지에 닿는다
    _inputs(bb, k, _BCD_INPUTS, stage, superset, pins=16)
    for tag in _BCD_LEDS:
        bb.led_chain(R['a'], lay['leds']['bcd'][tag], tag, f'{tag} — 진리표 T1 의 {tag} 열', block='right',
                     active_low=True)


def _bcd_draw(bb, stage):
    bb.partial = stage is not None and stage < 4
    bb.marker_hints = place_marker_hints(BCD, LAYOUT)
    _bcd_fixed(bb, stage)
    draw_routed(bb, BCD.wires, place_paths(BCD, LAYOUT), stage)
    bb.note(_INPUT_NOTE)
    bb.note(_LOW_NOTE)
    bb.note(_ORDER_NOTE)


def build_e5_bcd(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """C1 BCD → 10진 디코더(74HC42). `stage` 1..4 또는 None(완성)."""
    if layer is not None and stage is not None:
        raise ValueError('layer 는 완성본(stage=None)에만 준다 — 단계 그림에는 임시 급전선이 있다')
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    title = '실험 1-2) BCD to Decimal Decoder' + (f' — {stage}단계' if stage else '')
    bb.set_header(title, '74HC42 · Y0~Y9 = 입력 BCD 의 그 수에서만 0 (LED 는 0 에서 켜짐)',
                  submit=baseline is None and stage is None)
    _bcd_draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


# ---------------- C2 10진 → Excess-3 인코더 ----------------

_XS3_LEDS = ('A3', 'A2', 'A1', 'A0')
# (첫 단계, 끝 단계(임시선만), 색, 출발, 도착, 설명). 순서 = 그리는 순서 = 경로를 정하는 순서.
# 임시 급전선은 superset 판에 함께 올려 경로를 정한다 — 완성본에는 안 그린다.
_XS3_WIRES = [
    (1, None, 'sig', ('U1', 2), ('U2', 1), "D5' (U1 pin 2) -> U2 pin 1"),
    (1, None, 'sig', ('U2', 6), ('LED', 'A3'), 'A3 = U2 pin 6 -> LED A3'),
    (2, 2, 'sig', ('U1', 12), ('LED', 'A2'), "임시 급전: D0' = U1 pin 12 -> LED A2 (3걷기에서 뽑는다)"),
    (3, None, 'sig', ('U1', 4), ('U3', 1), "D4' (U1 pin 4) -> U3 pin 1"),
    (3, None, 'sig', ('U1', 6), ('U3', 2), "D3' (U1 pin 6) -> U3 pin 2"),
    (3, None, 'sig', ('U1', 12), ('U3', 12), "D0' (U1 pin 12) -> U3 pin 12"),
    (3, None, 'sig', ('U3', 12), ('U3', 4), "D0' 이어 감 (U3 pin 12 -> U3 pin 4)"),
    (3, None, 'sig', ('U3', 6), ('LED', 'A1'), 'A1 = U3 pin 6 -> LED A1'),
    (4, None, 'sig', ('U3', 1), ('U3', 9), "D4' 이어 감 (U3 pin 1 -> U3 pin 9)"),
    (4, None, 'sig', ('U1', 8), ('U2', 12), "D2' (U1 pin 8) -> U2 pin 12"),
    (4, None, 'sig', ('U2', 12), ('U3', 10), "D2' 이어 감 (U2 pin 12 -> U3 pin 10)"),
    (4, None, 'sig', ('U3', 8), ('LED', 'A0'), 'A0 = U3 pin 8 -> LED A0'),
    (5, None, 'sig', ('U3', 9), ('U2', 9), "D4' 이어 감 (U3 pin 9 -> U2 pin 9)"),
    (5, None, 'sig', ('U3', 2), ('U2', 3), "D3' 이어 감 (U3 pin 2 -> U2 pin 3, n.c. 중계)"),
    (5, None, 'sig', ('U2', 3), ('U2', 10), "D3' 이어 감 (U2 pin 3 -> U2 pin 10)"),
    (5, None, 'sig', ('U1', 10), ('U2', 13), "D1' (U1 pin 10) -> U2 pin 13"),
    (5, None, 'sig', ('U2', 8), ('LED', 'A2'), 'A2 = U2 pin 8 -> LED A2'),
]
# 입력 점퍼 (단계, 이름, 칩, 핀). D1 은 5단계에서 쓰지만 5단계가 예산에 차서 2단계에 꽂아 둔다.
_XS3_INPUTS = [(1, 'D5', 'U1', 1), (2, 'D4', 'U1', 3), (2, 'D3', 'U1', 5), (2, 'D0', 'U1', 13),
               (2, 'D1', 'U1', 11), (4, 'D2', 'U1', 9)]
# 교안 p12 가 VCC 에 묶은 74HC20 입력 — 쓰는 게이트의 입력이다(미사용 아님). 기반이라 1단계에 꽂는다.
_XS3_TIES = {'U2': (2, 4, 5), 'U3': (5, 13)}


def _tie_vcc(bb, k, chip, pins):
    """74HC20 입력을 가까운 +5V 레일로 — a쪽은 a 열에서 좌 바깥 VCC, f쪽은 j 열에서 가운데 VCC."""
    L = bb.cols['left']
    for p in pins:
        row, side = _pin_row(k, p), _side(p)
        x_pin = L['a'] if side == 'a' else L['j']
        x_rail = L['vcc'] if side == 'a' else L['mid_vcc']
        r = bb.free_rail_row(row, x_rail)
        bb.step_wire([(x_pin, bb.r_y(row)), (x_rail, bb.r_y(r))], 'vcc', f'{chip} pin {p} -> +5V (교안 VCC 묶음)',
                     marker_near=((x_pin + x_rail) // 2, bb.r_y(row) - 11))


def _mark_nc(bb, k, chip, pins):
    for p in pins:
        bb.unused_inputs.append({'chip': chip, 'pin': p, 'rail': None, 'block': 'left', 'pin1_row': k})


def _xs3_fixed(bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    R, k, leds = bb.cols['right'], place_chips(XS3, lay), lay['leds']['xs3']
    bb.draw_chip('74HC04', k['U1'])
    bb.draw_chip('74HC20', k['U2'])
    bb.draw_chip('74HC20', k['U3'])
    _frame(bb, lay)
    for u in ('U1', 'U2', 'U3'):
        bb.connect_power(k[u], gnd_col='a')
    for u, pins in _XS3_TIES.items():
        _tie_vcc(bb, k[u], u, pins)
    for tag in _XS3_LEDS:
        bb.led_chain(R['a'], leds[tag], tag, f'{tag} — 진리표 T2 의 {tag} 열', block='right')
    _inputs(bb, k, _XS3_INPUTS, stage, superset)


def _xs3_draw(bb, stage):
    bb.partial = stage is not None and stage < 5
    bb.marker_hints = place_marker_hints(XS3, LAYOUT)
    _xs3_fixed(bb, stage)
    draw_routed(bb, XS3.wires, place_paths(XS3, LAYOUT), stage)
    k = place_chips(XS3, LAYOUT)
    _mark_nc(bb, k['U2'], '74HC20 (U2)', (11,))
    _mark_nc(bb, k['U3'], '74HC20 (U3)', (3, 11))
    bb.note(_INPUT_NOTE)


def build_e5_xs3(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """C2 10진 → Excess-3 인코더(74HC04 + 74HC20 ×2). `stage` 1..5 또는 None(완성). C1 을 전부 뽑고
    새로 짓는다(`rebuild: true`) — 사슬에는 `fresh_board` 로 들어가 기준선 없이 그린다."""
    if layer is not None and stage is not None:
        raise ValueError('layer 는 완성본(stage=None)에만 준다 — 단계 그림에는 임시 급전선이 있다')
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    title = '실험 2-2) Decimal to Excess-3 Code Encoder' + (f' — {stage}단계' if stage else '')
    bb.set_header(title, "74HC04 NOT 6 + 74HC20 4입력 NAND 4 · A3 = D5, A2 = D4+D3+D2+D1, "
                         "A1 = D4+D3+D0, A0 = D4+D2+D0",
                  submit=baseline is None and stage is None)
    _xs3_draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


BCD = PlaceCircuit('bcd', {'U4': 'K1'}, {'U4': '74HC42'}, _BCD_LEDS, tuple(_BCD_WIRES), _bcd_fixed,
                   tuple((c, p) for _s, _n, c, p in _BCD_INPUTS))
XS3 = PlaceCircuit('xs3', {'U1': 'K2', 'U2': 'K3', 'U3': 'K4'},
                   {'U1': '74HC04', 'U2': '74HC20', 'U3': '74HC20'}, _XS3_LEDS, tuple(_XS3_WIRES), _xs3_fixed,
                   tuple((c, p) for _s, _n, c, p in _XS3_INPUTS))
PLACE = [BCD, XS3]

_C1 = '실험05_1-2_결선도_BCD디코더'
_C2 = '실험05_2-2_결선도_Excess3인코더'
BOARDS = [
    (f'{_C1}_1단계_Y0.png', build_e5_bcd, 1),
    (f'{_C1}_2단계_Y1Y3.png', build_e5_bcd, 2),
    (f'{_C1}_3단계_Y4Y6.png', build_e5_bcd, 3),
    (f'{_C1}_4단계_Y7Y9.png', build_e5_bcd, 4),
    (f'{_C2}_1단계_A3.png', fresh_board(build_e5_xs3), 1),
    (f'{_C2}_2단계_D0인버터.png', build_e5_xs3, 2),
    (f'{_C2}_3걷기_인버터프로브.png',
     removal_board((build_e5_xs3, 2), (build_e5_xs3, 3),
                   "실험 2-2: Excess-3 인코더 — 3단계 걷기 (임시 급전선 1가닥)",
                   "D0' → LED A2 임시 급전선을 뽑는다 · 회색은 그대로 둔다"), None),
    (f'{_C2}_3단계_A1.png', build_e5_xs3, 3),
    (f'{_C2}_4단계_A0.png', build_e5_xs3, 4),
    (f'{_C2}_5단계_A2.png', build_e5_xs3, 5),
]
FINALS = [
    ('실험05_1-2_결선도_BCD디코더.png', build_e5_bcd),
    ('실험05_2-2_결선도_Excess3인코더.png', build_e5_xs3),
]

# 따라 그리기 층 — 완성본 번호 1..N 을 이어 자른 구간 (lo, hi, 이름). `make-trace-guide` 가 쓴다.
LAYERS = {
    f'{_C1}.png': [
        (1, 4, '전원 잭·레일 브리지'),
        (5, 6, 'U4 전원'),
        (7, 10, '입력 Bit0~3 → U4'),
        (11, 22, 'LED 사슬 Y0~Y5'),
        (23, 30, 'LED 사슬 Y9·Y6·Y8·Y7'),
        (31, 37, 'a쪽 Y0~Y6 → LED (U4)'),
        (38, 40, 'f쪽 Y9·Y8·Y7 → LED (U4)'),
    ],
    f'{_C2}.png': [
        (1, 4, '전원 잭·레일 브리지'),
        (5, 15, '칩 전원 U1·U2·U3'),
        (16, 23, 'LED 사슬 A3~A0'),
        (24, 29, '입력 D5~D0 → U1'),
        (30, 37, 'A3 (U2) · A1 (U3)'),
        (38, 45, 'A0 (U3) · A2 (U2)'),
    ],
}
