# 실험06 결선 — 엔진 `render_breadboard.py --experiment 6` 이 이 파일의 `BOARDS`(기준선 사슬)·
# `FINALS`(완성본)를 뽑는다. 근거: `보고서/실험06/결선도/netlist.md`(C1 SR 래치 · C2 D 래치 · C3 JK
# 플립플롭), `체크리스트/명세.md`.
#
# v2 판형(SKILL §2b) — 칩은 전부 좌 블록(R9), LED 는 우 a 열(R10).
#
#   K1 : 74HC00 (U1) / 74HC00 (U1, 그대로) / 74HC76 (U3)
#   K2 : 비움 / 74HC04 (U2) / 비움
#   행은 `LAYOUT` — 배치기(`python -m scripts.lab.place_search 보고서/실험06/결선도/배치.py`)가 고른 값을
#   옮겨 적는다(SKILL §4a). 손으로 고치지 않는다 — PlaceEnforced 가 `배치탐색.md` 와 맞댄다.
#
# **C1·C2 는 칩 한쪽 리드가 9 다**(`SIDE_LEAD_MAX` 예외). 교안 핀 번호 그대로면 U1 f쪽이 되먹임 두
# 가닥의 네 끝 + Q·Q' LED 급전 둘 + 앞단 출력 도착 둘 + VCC = 9, C2 의 a쪽은 D 이어 감이 더해져 9 다.
# 게이트를 어떻게 바꿔 나눠도 칩 양쪽 합이 17 이라(한도 합 16) R7 을 지킬 배정이 없다.
#
# **C2 는 C1 위에 짓는다**(netlist M9) — 두 회로가 배선표 하나(`LATCH`)를 단계 1·2 로 나눠 쓴다. R 입력
# 점퍼만 빠진다(1걷기). **C3 은 전부 새로 짓는다**(`rebuild: all`, netlist M10) — 단계가 없어 완성본만 있다.
from render_breadboard import (BreadboardRenderer, _input_jumper, removal_board,
                               PlaceCircuit, place_chips, place_paths, place_marker_hints, draw_routed,
                               _dip_pin_row as _pin_row, _dip_side as _side)

BOARD = 'v2'
SLOTS = ('K1', 'K2')
LAYOUT = {'slots': {'K1': 3, 'K2': 13},
          'leds': {'latch': {"Q'": 5, 'Q': 10}, 'jk': {'Q': 3, "Q'": 8}},
          'bridge': [23, 24]}

SIDE_LEAD_MAX = 9
SIDE_LEAD_MAX_REASON = ('74HC00 한 칩으로 짓는 SR·D 래치(교안 p7·p8)는 칩 쪽 리드가 17 이다 — 입력 '
                        '점퍼 셋, E 이어 감 둘, 앞단 → 뒷단 넷, 되먹임 넷, LED 급전 둘, 전원 둘. 한쪽 8 '
                        '이면 합 16 이라 어느 게이트 배정으로도 못 담는다. 교안 핀 번호대로 f쪽 9 (C2 는 '
                        'a쪽도 D 이어 감으로 9)')

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다.')


def _frame(bb, layout):
    """잭 → 좌 바깥 레일, 좌 바깥 → 가운데 브리지 두 가닥(SKILL §2b). 우 바깥 레일은 안 쓴다."""
    L = bb.cols['left']
    gnd_row, vcc_row = layout['bridge']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], gnd_row, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], vcc_row, kind='vcc')


def _inputs(bb, chips, inputs, pins=14):
    L = bb.cols['left']
    for name, chip, pin in inputs:
        side = _side(pin, pins)
        _input_jumper(bb, L, _pin_row(chips[chip], pin, pins), name, f'{chip} pin {pin}',
                      side=side, col='a' if side == 'a' else 'j')


def _renderer(template_path, baseline, layer, stage, hand=None, hand_guide=False):
    if layer is not None and stage is not None:
        raise ValueError('layer 는 완성본(stage=None)에만 준다')
    if hand is not None and stage is not None:
        raise ValueError('hand 는 완성본(stage=None)에만 준다')
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD,
                            palette=stage is not None, hand=hand, hand_guide=hand_guide)   # 단계 그림만 선마다 색(체크리스트)
    bb.side_lead_max = SIDE_LEAD_MAX
    bb.enable_steps()
    return bb


# ---------------- C1 SR 래치 · C2 D 래치 (C1 위에) ----------------
# 두 회로가 배선표 하나(`LATCH`)를 나눠 쓴다 — 단계 1 = C1 의 선, 단계 2 = C2 가 더하는 두 가닥. 경로를
# 한 superset 판(U2·R 점퍼 함께)에서 정해야 C1 선이 C2 에서 같은 경로로 그려져 회색이 된다. C1 을 따로
# 깔면 C1 번호 원이 나중에 U2 가 설 자리에 앉는다(R11).

_LATCH_LEDS = ("Q'", 'Q')      # 위 → 아래 = 칩 핀 행 순서(pin 11 이 pin 8 위, R10)
# (첫 단계, 끝 단계, 색, 출발, 도착, 설명). 순서 = 그리는 순서 = 경로를 정하는 순서
_LATCH_WIRES = [
    (1, None, 'sig', ('U1', 2), ('U1', 4), 'E 이어 감 (U1 pin 2 -> U1 pin 4)'),
    (1, None, 'sig', ('U1', 3), ('U1', 9), "앞단 출력 (U1 pin 3) -> U1 pin 9"),
    (1, None, 'sig', ('U1', 6), ('U1', 13), "앞단 출력 (U1 pin 6) -> U1 pin 13"),
    (1, None, 'sig', ('U1', 8), ('U1', 12), 'Q 되먹임 (U1 pin 8 -> U1 pin 12)'),
    (1, None, 'sig', ('U1', 11), ('U1', 10), "Q' 되먹임 (U1 pin 11 -> U1 pin 10)"),
    (1, None, 'sig', ('U1', 11), ('LED', "Q'"), "Q' = U1 pin 11 -> LED Q'"),
    (1, None, 'sig', ('U1', 8), ('LED', 'Q'), 'Q = U1 pin 8 -> LED Q'),
    (2, None, 'sig', ('U1', 1), ('U2', 1), 'D 이어 감 (U1 pin 1 -> U2 pin 1)'),
    (2, None, 'sig', ('U2', 2), ('U1', 5), "D' (U2 pin 2) -> U1 pin 5"),
]
_SR_INPUTS = [('S', 'U1', 1), ('E', 'U1', 2), ('R', 'U1', 5)]
_D_INPUTS = [('D', 'U1', 1), ('E', 'U1', 2)]     # C1 의 S 점퍼가 그대로 D 다. R 점퍼는 1걷기에서 뽑는다
_LED_DESC = {'Q': 'Q — 진리표의 Q(t) 열', "Q'": "Q' — 기록 칸 없음 (netlist M4)"}


def _latch_fixed(bb, stage, superset=False, layout=None):
    """C1(`stage` 1)·C2(`stage` 2)·superset 의 고정물. 그리는 순서가 같아야 레일 착지 행이 같고 C2 에서
    C1 부분이 회색이 된다(SKILL §4a 기준선) — U1·브리지·입력·LED 사슬, 그다음 U2."""
    lay = layout or LAYOUT
    R, k = bb.cols['right'], place_chips(LATCH, lay)
    bb.draw_chip('74HC00', k['U1'])
    _frame(bb, lay)
    bb.connect_power(k['U1'], gnd_col='a')
    # 입력 점퍼를 LED 사슬보다 먼저 — 번호 원은 그때까지 그려진 배지만 피한다
    _inputs(bb, k, _D_INPUTS if stage == 2 else _SR_INPUTS)
    for tag in _LATCH_LEDS:
        bb.led_chain(R['a'], lay['leds']['latch'][tag], tag, _LED_DESC[tag], block='right')
    if superset or stage == 2:
        bb.draw_chip('74HC04', k['U2'])
        bb.connect_power(k['U2'], gnd_col='a')
        bb.mark_unused_inputs((3, 5, 9, 11, 13), k['U2'], chip='74HC04 (U2)')
        bb.mark_unused_outputs((4, 6, 8, 10, 12), k['U2'], chip='74HC04 (U2)')


def _latch_draw(bb, stage):
    bb.marker_hints = place_marker_hints(LATCH, LAYOUT)
    _latch_fixed(bb, stage)
    draw_routed(bb, LATCH.wires, place_paths(LATCH, LAYOUT), stage)
    bb.note(_INPUT_NOTE)


def build_e6_sr(output_path, template_path=None, stage=None, baseline=None, layer=None,
               hand=None, hand_guide=False):
    """C1 SR 래치(74HC00). 단계가 없다 — 완성본 하나이고 C2 1걷기의 앞 보드다."""
    bb = _renderer(template_path, baseline, layer, stage, hand, hand_guide)
    bb.set_header('실험 1) SR Latch with Enable',
                  '74HC00 NAND 넷 · E=1 에서 S=1 은 Set, R=1 은 Reset · 첫 입력은 Set 또는 Reset',
                  submit=baseline is None)
    _latch_draw(bb, 1)
    bb.export(output_path, max_row=63)
    return bb


def build_e6_d(output_path, template_path=None, stage=None, baseline=None, layer=None,
               hand=None, hand_guide=False):
    """C2 D 래치(74HC00 + 74HC04). `stage` 1 또는 None(완성) — 1단계가 곧 완성이다."""
    bb = _renderer(template_path, baseline, layer, stage, hand, hand_guide)
    title = '실험 2-1) D Latch with Enable' + (f' — {stage}단계' if stage else '')
    bb.set_header(title, '74HC00 NAND 넷 + 74HC04 NOT 하나 · E=1 에서 Q 가 D 를 따른다',
                  submit=baseline is None and stage is None)
    _latch_draw(bb, 2)
    bb.export(output_path, max_row=63)
    return bb


# ---------------- C3 JK 플립플롭 (74HC76) ----------------

_JK_LEDS = ('Q', "Q'")          # 위 → 아래 = 칩 핀 행 순서(pin 15 가 pin 14 위, R10)
_JK_WIRES = [
    (1, None, 'sig', ('U3', 15), ('LED', 'Q'), 'Q = U3 pin 15 -> LED Q'),
    (1, None, 'sig', ('U3', 14), ('LED', "Q'"), "Q' = U3 pin 14 -> LED Q'"),
]
_JK_INPUTS = [('CLK', 'U3', 1), ('Set', 'U3', 2), ('Reset', 'U3', 3), ('J', 'U3', 4), ('K', 'U3', 16)]
_JK_DESC = {'Q': 'Q — 진리표 T3 의 Q(t) 열', "Q'": "Q' — 기록 칸 없음 (netlist M4)"}
_JK_NOTE = ('74HC76 은 pin 5 가 +5V, pin 13 이 GND 다(16·8 이 아니다). Set·Reset 은 0 에서 작동한다 — '
            'J·K 행에서는 둘 다 +5V 에 꽂는다.')


def _jk_fixed(bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    R, k = bb.cols['right'], {'U3': lay['slots']['K1']}
    bb.draw_chip('74HC76', k['U3'])
    _frame(bb, lay)
    bb.connect_power(k['U3'])
    _inputs(bb, k, _JK_INPUTS, pins=16)
    for tag in _JK_LEDS:
        bb.led_chain(R['a'], lay['leds']['jk'][tag], tag, _JK_DESC[tag], block='right')
    bb.mark_unused_inputs((6, 7, 8, 9, 12), k['U3'], chip='74HC76 (U3)')
    bb.mark_unused_outputs((10, 11), k['U3'], chip='74HC76 (U3)')


def build_e6_jk(output_path, template_path=None, stage=None, baseline=None, layer=None,
               hand=None, hand_guide=False):
    """C3 JK 플립플롭(74HC76 1번). 단계가 없다 — C2 를 전부 걷고 새로 짓는다(`rebuild: all`)."""
    bb = _renderer(template_path, baseline, layer, stage, hand, hand_guide)
    bb.set_header('실험 3-2) JK F/F – IC(74HC76) 활용',
                  '74HC76 1번 플립플롭 · CLK 하강 에지에서 J·K 대로 · Set·Reset 은 0 에서 작동',
                  submit=baseline is None)
    bb.marker_hints = place_marker_hints(JK, LAYOUT)
    _jk_fixed(bb, stage)
    draw_routed(bb, JK.wires, place_paths(JK, LAYOUT), None)
    bb.note(_INPUT_NOTE)
    bb.note(_JK_NOTE)
    bb.export(output_path, max_row=63)
    return bb


LATCH = PlaceCircuit('latch', {'U1': 'K1', 'U2': 'K2'}, {'U1': '74HC00', 'U2': '74HC04'}, _LATCH_LEDS,
                     tuple(_LATCH_WIRES), _latch_fixed,
                     tuple((c, p) for _n, c, p in _SR_INPUTS))
JK = PlaceCircuit('jk', {'U3': 'K1'}, {'U3': '74HC76'}, _JK_LEDS, tuple(_JK_WIRES), _jk_fixed,
                  tuple((c, p) for _n, c, p in _JK_INPUTS))
PLACE = [LATCH, JK]

_C1 = '실험06_1_결선도_SR래치'
_C2 = '실험06_2-1_결선도_D래치'
_C3 = '실험06_3-2_결선도_JK플립플롭'
BOARDS = [
    (f'{_C2}_1걷기_R입력.png',
     removal_board((build_e6_sr, None), (build_e6_d, 1),
                   '실험 2-1: D 래치 — 1단계 걷기 (R 입력 점퍼 1가닥)',
                   'C1 의 R 입력 점퍼를 뽑는다 · S 점퍼는 그대로 두고 D 라 부른다 · 회색은 그대로 둔다'), None),
    (f'{_C2}_1단계_D반전.png', build_e6_d, 1),
]
FINALS = [
    (f'{_C1}.png', build_e6_sr),
    (f'{_C2}.png', build_e6_d),
    (f'{_C3}.png', build_e6_jk),
]

# 따라 그리기 층 — 완성본 번호를 이어 자른 구간 (lo, hi, 이름). `scripts.lab.trace_guide 6` 이 읽는다.
LAYERS = {
    f'{_C1}.png': [
        (1, 4, "전원 잭·레일 브리지"),
        (5, 9, "U1 전원·입력 S·E·R"),
        (10, 13, "Q'·Q LED 사슬"),
        (14, 16, "앞단 NAND (U1)"),
        (17, 20, "되먹임 → Q'·Q LED (U1)"),
    ],
    f'{_C2}.png': [
        (1, 4, "전원 잭·레일 브리지"),
        (5, 8, "U1 전원·입력 D·E"),
        (9, 14, "Q'·Q LED 사슬 + U2 전원"),
        (15, 17, "앞단 NAND (U1)"),
        (18, 21, "되먹임 → Q'·Q LED (U1)"),
        (22, 23, "D 반전 (U2)"),
    ],
    f'{_C3}.png': [
        (1, 4, "전원 잭·레일 브리지"),
        (5, 11, "U3 전원·입력 다섯"),
        (12, 17, "Q·Q' LED 사슬 → U3 출력"),
    ],
}
