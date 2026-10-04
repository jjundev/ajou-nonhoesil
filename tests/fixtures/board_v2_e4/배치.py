# 실험04 v2 시험판 — 승인본(`보고서/실험04/결선도/배치.py`, v1)을 v2 규약으로 다시 놓아 본다.
# 계획: `docs/plans/2026-10-03-실험04-v2-시험판-구현계획.md`. 결과: 같은 폴더의 `…-결과.md`.
#
# 칩 넷 전부 좌 블록(R9), LED 는 우 a 열(R10). R8 은 면제하지 않는다 — 칩 사이 선은 쪽을
# 바꾸지 않고, 쪽을 바꿔야 하는 신호는 **같은 칩 안에서** 이어 가거나 n.c. 핀·미사용 게이트
# 입력을 중계로 거친다. 교안 핀 번호는 그 때문에 바뀐다(승인본 netlist 와 다르다).
#
#   K1 좌 5행  : 74HC04 (U4)
#   K2 좌 17행 : 74HC20 (U1) / 74HC11 (U5)
#   K3 좌 29행 : 74HC20 (U2) / 비움
#   K4 좌 41행 : 74HC20 (U3) / 74HC11 (U6)
#
# **경로는 손으로 찍지 않는다.** 배선표(어느 핀을 어느 핀에)만 적고, 경로는 엔진 `route_plan()` 이
# R3(끝점이 선 아래)·R4(같은 축 포개짐)·R6(자기 스트립 안 구간)과 같은 식으로 골라 낸다.
# 칩 넷이 한 블록에 몰리면 a~d / g~j 열은 끝점으로 차서 세로선이 지나갈 데가 없다 — 그래서
# 가로는 **반 행**(두 행 사이), 세로는 **홀 열 사이**나 여백 차선을 탄다. 경로는 회로마다 한 번,
# 모든 단계의 선을 한 판에 올린 superset 판에서 정하고 단계 그림은 그 경로를 그대로 쓴다 —
# 단계마다 경로가 달라지면 기준선 회색 선과 새 선이 어긋난다.
import functools

from render_breadboard import (BreadboardRenderer, _input_jumper, fresh_board, removal_board,
                               route_plan, draw_routed, _dip_pin_row as _pin_row, _dip_side as _side)

BOARD = 'v2'
K1, K2, K3, K4 = 5, 17, 29, 41
LED_TOP = (19, 23, 27, 43)            # DMUX 우 a 열 LED1~4 사슬 윗행 — Y0·Y3 이 곧게 건넌다
MUX_LED_TOP = (47, 51, 55, 59)        # MUX — LED1 이 Y(U3 pin 8, 47행)와 같은 행

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다.')


def _frame(bb):
    """잭 → 좌 바깥 레일, 좌 바깥 → 가운데 브리지 두 가닥(SKILL §2b). 우 바깥 레일은 안 쓴다."""
    L = bb.cols['left']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], 53, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], 54, kind='vcc')


# ---------------- C1 4x1 MUX ----------------

_MUX_CHIPS = {'U4': K1, 'U1': K2, 'U2': K3, 'U3': K4}
_ML = MUX_LED_TOP
# 인버터: S0 = 게이트 3 (5→6, a), S1 = 게이트 4 (9→8, f), E = 게이트 6 (13→12, f).
# 앞단: U1 A = D0 항, U1 B = D1 항, U2 A = D2 항, U2 B = D3 항. 합류: U3 **게이트 B**(→ pin 8, f쪽).
# 임시 급전선(끝 단계가 있는 줄)은 superset 판에 함께 올려 경로를 정한다 — 완성본에는 안 그린다.
# 인버터 임시선은 E'·S0'·S1' 행 순서(7·10·11)대로 LED1·2·3 이고 4걷기에서 뽑는다(R10).
_MUX_WIRES = [
    (1, 3, 'sig', ('U4', 12), ('LED', _ML[0]), "임시 급전: E' = U4 pin 12 -> LED1 (4걷기에서 뽑는다)"),
    (2, 3, 'sig', ('U4', 8), ('LED', _ML[2]), "임시 급전: S1' = U4 pin 8 -> LED3 (4걷기에서 뽑는다)"),
    (3, 3, 'sig', ('U4', 6), ('LED', _ML[1]), "임시 급전: S0' = U4 pin 6 -> LED2 (4걷기에서 뽑는다)"),
    (4, None, 'sig', ('U4', 6), ('U1', 1), "S0' (U4 pin 6) -> U1 pin 1"),
    (4, None, 'sig', ('U4', 12), ('U1', 12), "E' (U4 pin 12) -> U1 pin 12"),
    (4, None, 'sig', ('U1', 12), ('U1', 4), "E' 이어 감 (U1 pin 12 -> U1 pin 4)"),
    (4, None, 'sig', ('U4', 8), ('U1', 10), "S1' (U4 pin 8) -> U1 pin 10"),
    (4, None, 'sig', ('U1', 10), ('U1', 2), "S1' 이어 감 (U1 pin 10 -> U1 pin 2)"),
    (4, 7, 'sig', ('U1', 6), ('LED', _ML[0]), '임시 급전: U1 pin 6 -> LED1 (8걷기에서 뽑는다)'),
    (5, None, 'sig', ('U4', 5), ('U1', 3), 'S0 (U4 pin 5) -> U1 pin 3 (n.c. 중계)'),
    (5, None, 'sig', ('U1', 3), ('U1', 9), 'S0 이어 감 (U1 pin 3 -> U1 pin 9)'),
    (5, 7, 'sig', ('U1', 8), ('LED', _ML[1]), '임시 급전: U1 pin 8 -> LED2 (8걷기에서 뽑는다)'),
    (6, None, 'sig', ('U4', 6), ('U2', 1), "S0' (U4 pin 6) -> U2 pin 1"),
    (6, None, 'sig', ('U4', 12), ('U2', 12), "E' (U4 pin 12) -> U2 pin 12"),
    (6, None, 'sig', ('U2', 12), ('U2', 4), "E' 이어 감 (U2 pin 12 -> U2 pin 4)"),
    (6, None, 'sig', ('U4', 9), ('U2', 10), 'S1 (U4 pin 9) -> U2 pin 10'),
    (6, None, 'sig', ('U2', 10), ('U2', 2), 'S1 이어 감 (U2 pin 10 -> U2 pin 2)'),
    (6, 7, 'sig', ('U2', 6), ('LED', _ML[2]), '임시 급전: U2 pin 6 -> LED3 (8걷기에서 뽑는다)'),
    (7, None, 'sig', ('U4', 5), ('U2', 3), 'S0 (U4 pin 5) -> U2 pin 3 (n.c. 중계)'),
    (7, None, 'sig', ('U2', 3), ('U2', 9), 'S0 이어 감 (U2 pin 3 -> U2 pin 9)'),
    (7, 7, 'sig', ('U2', 8), ('LED', _ML[3]), '임시 급전: U2 pin 8 -> LED4 (8걷기에서 뽑는다)'),
    (8, None, 'mid', ('U1', 8), ('U3', 12), "(E'·S1'·S0·D1)' (U1 pin 8) -> U3 pin 12"),
    (8, None, 'mid', ('U2', 8), ('U3', 9), "(E'·S1·S0·D3)' (U2 pin 8) -> U3 pin 9"),
    (8, None, 'mid', ('U1', 6), ('U3', 3), "(E'·S1'·S0'·D0)' (U1 pin 6) -> U3 pin 3 (n.c. 중계)"),
    (8, None, 'mid', ('U3', 3), ('U3', 13), '이어 감 (U3 pin 3 -> U3 pin 13)'),
    (8, None, 'mid', ('U2', 6), ('U3', 1), "(E'·S1·S0'·D2)' (U2 pin 6) -> U3 pin 1 (미사용 입력 중계)"),
    (8, None, 'mid', ('U3', 1), ('U3', 10), '이어 감 (U3 pin 1 -> U3 pin 10)'),
    (8, None, 'sig', ('U3', 8), ('LED', _ML[0]), 'Y = U3 pin 8 -> LED1'),
]
_MUX_INPUTS = [(1, 'E', 'U4', 13), (2, 'S1', 'U4', 9), (3, 'S0', 'U4', 5),
               (4, 'D0', 'U1', 5), (5, 'D1', 'U1', 13), (6, 'D2', 'U2', 5), (7, 'D3', 'U2', 13)]


def _mark_nc(bb, k, pins):
    for p in pins:
        bb.unused_inputs.append({'chip': '74HC20', 'pin': p, 'rail': None,
                                 'block': 'left', 'pin1_row': k})


def _mux_fixed(bb, stage, superset=False):
    R = bb.cols['right']
    bb.draw_chip('74HC04', K1)
    for k in (K2, K3, K4):
        bb.draw_chip('74HC20', k)
    _frame(bb)
    for k in (K1, K2, K3, K4):
        bb.connect_power(k, gnd_col='a')
    if superset or (stage is not None and stage < 8):
        for i, tag in enumerate(('L1', 'L2', 'L3', 'L4')):
            bb.led_chain(R['a'], _ML[i], tag, '중간 노드 관측 — 임시 급전선은 걷기 그림이 뽑는다',
                         block='right')
    else:
        bb.led_chain(R['a'], _ML[0], 'Y', 'Y — 진리표 T1 의 Y 열', block='right')
    _inputs(bb, _MUX_CHIPS, _MUX_INPUTS, stage, superset)


@functools.lru_cache(maxsize=None)
def _mux_paths():
    return route_plan(_mux_fixed, _MUX_CHIPS, _MUX_WIRES, board=BOARD)


def _mux_draw(bb, stage):
    bb.partial = stage is not None and stage < 8
    _mux_fixed(bb, stage)
    draw_routed(bb, _MUX_WIRES, _mux_paths(), stage)
    bb.mark_unused_inputs([1, 3, 11], K1, chip='74HC04')
    bb.mark_unused_outputs([2, 4, 10], K1, chip='74HC04')
    for k in (K2, K3, K4):
        _mark_nc(bb, k, (11,))
    bb.mark_unused_inputs([2, 4, 5], K4, chip='74HC20 (U3)')
    bb.mark_unused_outputs([6], K4, chip='74HC20 (U3)')
    bb.note(_INPUT_NOTE)


def build_trial_mux(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """C1 4x1 MUX v2 시험판. `stage` 1..8 또는 None(완성)."""
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    bb.set_header('실험04 v2 시험판: 4x1 MUX', '74HC04 + 74HC20 ×3 · 칩 좌 블록, LED 우 블록')
    _mux_draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


# ---------------- C2 1x4 DMUX ----------------

_DMUX_CHIPS = {'U4': K1, 'U5': K2, 'U6': K4}
# (첫 단계, 끝 단계(임시선만), 색, 출발, 도착, 설명). 순서 = 그리는 순서 = 경로를 정하는 순서.
_DMUX_WIRES = [
    (1, None, 'sig', ('U4', 9), ('U6', 13), 'S1 (U4 pin 9) -> U6 pin 13'),
    (1, None, 'sig', ('U6', 12), ('LED', LED_TOP[3]), 'Y3 = U6 pin 12 -> LED4'),
    (2, None, 'sig', ('U6', 1), ('U5', 3), 'S0 (U6 pin 1) -> U5 pin 3'),
    (2, None, 'sig', ('U4', 8), ('U5', 13), "S1' (U4 pin 8) -> U5 pin 13"),
    (2, None, 'sig', ('U5', 13), ('U5', 4), "S1' 이어 감 (U5 pin 13 -> U5 pin 4)"),
    (2, None, 'sig', ('U6', 2), ('U5', 5), 'D (U6 pin 2) -> U5 pin 5'),
    (2, None, 'sig', ('U5', 6), ('LED', LED_TOP[1]), 'Y1 = U5 pin 6 -> LED2'),
    (3, None, 'sig', ('U6', 1), ('U4', 1), 'S0 (U6 pin 1) -> U4 pin 1'),
    (3, None, 'sig', ('U4', 2), ('U5', 2), "S0' (U4 pin 2) -> U5 pin 2"),
    (3, None, 'sig', ('U5', 2), ('U5', 10), "S0' 이어 감 (U5 pin 2 -> U5 pin 10)"),
    (3, None, 'sig', ('U4', 9), ('U5', 9), 'S1 (U4 pin 9) -> U5 pin 9'),
    (3, None, 'sig', ('U6', 2), ('U6', 11), 'D 이어 감 (U6 pin 2 -> U6 pin 11, 미사용 입력 중계)'),
    (3, None, 'sig', ('U6', 11), ('U5', 11), 'D (U6 pin 11) -> U5 pin 11'),
    (3, None, 'sig', ('U5', 8), ('LED', LED_TOP[2]), 'Y2 = U5 pin 8 -> LED3'),
    (4, None, 'sig', ('U6', 2), ('U5', 1), 'D (U6 pin 2) -> U5 pin 1'),
    (4, None, 'sig', ('U5', 12), ('LED', LED_TOP[0]), 'Y0 = U5 pin 12 -> LED1'),
]
# 입력 점퍼 (단계, 이름, 칩, 핀). 고정물과 함께 경로보다 **먼저** 그린다 — 레일 착지 행이
# 앞 선에 따라 바뀌지 않게.
_DMUX_INPUTS = [(1, 'S0', 'U6', 1), (1, 'D', 'U6', 2), (1, 'S1', 'U4', 9)]


def _inputs(bb, chips, inputs, stage, superset):
    L = bb.cols['left']
    for s, name, chip, pin in inputs:
        if superset or stage is None or s <= stage:
            side = _side(pin)
            _input_jumper(bb, L, _pin_row(chips[chip], pin), name, f'{chip} pin {pin}',
                          side=side, col='a' if side == 'a' else 'j')


def _dmux_fixed(bb, stage, superset=False):
    R = bb.cols['right']
    bb.draw_chip('74HC04', K1)
    bb.draw_chip('74HC11', K2)
    bb.draw_chip('74HC11', K4)
    _frame(bb)
    for k in (K1, K2, K4):
        bb.connect_power(k, gnd_col='a')
    for i, tag in enumerate(('Y0', 'Y1', 'Y2', 'Y3')):
        bb.led_chain(R['a'], LED_TOP[i], tag, f'{tag} — 진리표 T3 의 {tag} 열', block='right')
    _inputs(bb, _DMUX_CHIPS, _DMUX_INPUTS, stage, superset)


@functools.lru_cache(maxsize=None)
def _dmux_paths():
    return route_plan(_dmux_fixed, _DMUX_CHIPS, _DMUX_WIRES, board=BOARD)


def _dmux_draw(bb, stage):
    bb.partial = stage is not None and stage < 4
    _dmux_fixed(bb, stage)
    draw_routed(bb, _DMUX_WIRES, _dmux_paths(), stage)
    bb.mark_unused_inputs([3, 5, 11, 13], K1, chip='74HC04')
    bb.mark_unused_outputs([4, 6, 10, 12], K1, chip='74HC04')
    bb.mark_unused_inputs([3, 4, 5, 9, 10], K4, chip='74HC11 (U6)')
    bb.mark_unused_outputs([6, 8], K4, chip='74HC11 (U6)')
    bb.note(_INPUT_NOTE)


def build_trial_dmux(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """C2 1x4 DMUX v2 시험판. `stage` 1..4 또는 None(완성)."""
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    bb.set_header('실험04 v2 시험판: 1x4 DMUX', '74HC04 + 74HC11 ×2 · 칩 좌 블록, LED 우 블록')
    _dmux_draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


BOARDS = [
    ('trial_e4_mux_1.png', build_trial_mux, 1),
    ('trial_e4_mux_2.png', build_trial_mux, 2),
    ('trial_e4_mux_3.png', build_trial_mux, 3),
    ('trial_e4_mux_4걷기.png',
     removal_board((build_trial_mux, 3), (build_trial_mux, 4),
                   '시험판 MUX — 4단계 걷기', '인버터 임시 급전선 셋을 뽑는다'), None),
    ('trial_e4_mux_4.png', build_trial_mux, 4),
    ('trial_e4_mux_5.png', build_trial_mux, 5),
    ('trial_e4_mux_6.png', build_trial_mux, 6),
    ('trial_e4_mux_7.png', build_trial_mux, 7),
    ('trial_e4_mux_8걷기.png',
     removal_board((build_trial_mux, 7), (build_trial_mux, 8),
                   '시험판 MUX — 8단계 걷기', 'NAND 임시 급전선 넷과 LED2~4 사슬을 뽑는다'), None),
    ('trial_e4_mux_8.png', build_trial_mux, 8),
    ('trial_e4_dmux_1.png', fresh_board(build_trial_dmux), 1),
    ('trial_e4_dmux_2.png', build_trial_dmux, 2),
    ('trial_e4_dmux_3.png', build_trial_dmux, 3),
    ('trial_e4_dmux_4.png', build_trial_dmux, 4),
]

# 기준선을 끊고 새 회로를 시작하는 보드 — 앞 회로가 막혀도 여기서 다시 잰다.
RESTART = {'trial_e4_dmux_1.png'}
# 측정값(2026-10-03, 계획 Task 4 Step 4) — 보드마다 새 신호선 수(입력 점퍼 포함). 승인본
# 예산 5 를 넘는 것은 MUX 4·6·8단계와 DMUX 3단계(각 7)다 — 같은 칩 안 이어 가기와 중계가
# 한 관측 노드에 두세 가닥씩 더 든다. 막힘(R7·R8·R10)은 없다.
MEASURED_NEW_SIGNAL = {
    'trial_e4_mux_1.png': 2, 'trial_e4_mux_2.png': 2, 'trial_e4_mux_3.png': 2,
    'trial_e4_mux_4걷기.png': 0, 'trial_e4_mux_4.png': 7, 'trial_e4_mux_5.png': 4,
    'trial_e4_mux_6.png': 7, 'trial_e4_mux_7.png': 4, 'trial_e4_mux_8걷기.png': 0,
    'trial_e4_mux_8.png': 7,
    'trial_e4_dmux_1.png': 5, 'trial_e4_dmux_2.png': 5, 'trial_e4_dmux_3.png': 7,
    'trial_e4_dmux_4.png': 2,
}
KNOWN_BLOCKERS = {}
FINALS = [('trial_e4_mux.png', build_trial_mux), ('trial_e4_dmux.png', build_trial_dmux)]
