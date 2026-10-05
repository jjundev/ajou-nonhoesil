# 실험05 v2 시험판 — 1-2 BCD → 10진 디코더(74HC42) 하나. DIP-16 칩과 Negative Logic LED 를 엔진이
# 그리는지 잰다. 설계: `docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md`.
#
#   K1 : 74HC42 (U1) — 입력 A·B·C·D = pin 15·14·13·12(f쪽, 가운데 GND 레일에서), 출력 Y0~Y9 =
#        pin 1~7·9~11. 칩 핀은 전부 쓴다(미사용 없음).
#   LED 는 칩 핀 행 순서다(R10, 사용자 #13): Y0 Y1 Y2 Y3 Y4 Y5 Y9 Y6 Y8 Y7. Y7·Y8·Y9 가 pin 9·10·11
#   (행 k+7·k+6·k+5)이라 진리표 순서로 두면 건너는 선이 엇갈린다.
#   a쪽 출력 → LED 선은 칩 이름 상자에 가까운 핀부터 적는다(pin 4, 3, 2, 1, 5, 6, 7) — 이름 상자가
#   반 행 k+3.5 를 막으면 a쪽 일곱 가닥이 건널 반 행이 핀마다 하나로 정해지고, 배선기 수리는 막힌 선
#   앞 한 가닥만 바꿔 본다. 위에서부터 깔면 pin 4 가 막힌다.
#   행은 `LAYOUT` — 배치기(`python -m scripts.lab.place_search tests/fixtures/board_v2_e5/배치.py`)가
#   고른 값을 옮겨 적는다(SKILL §4). 손으로 고치지 않는다 — PlaceEnforced 가 `배치탐색.md` 와 맞댄다.
from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips, place_paths,
                               place_marker_hints, draw_routed, _dip_pin_row)

BOARD = 'v2'
SLOTS = ('K1',)
LAYOUT = {'slots': {'K1': 3},
          'leds': {'bcd': {'Y0': 6, 'Y1': 10, 'Y2': 14, 'Y3': 18, 'Y4': 22, 'Y5': 26, 'Y9': 30, 'Y6': 34,
                           'Y8': 38, 'Y7': 42}},
          'bridge': [15, 16]}

_LEDS = ('Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y9', 'Y6', 'Y8', 'Y7')
_OUT = {'Y0': 1, 'Y1': 2, 'Y2': 3, 'Y3': 4, 'Y4': 5, 'Y5': 6, 'Y6': 7, 'Y7': 9, 'Y8': 10, 'Y9': 11}
# (단계) — 한 단계 새 신호선 셋 이하. 순서 = 그리는 순서 = 경로를 정하는 순서(머리 주석)
_ORDER = (('Y3', 1), ('Y2', 1), ('Y1', 1), ('Y0', 2), ('Y4', 2), ('Y5', 2),
          ('Y6', 3), ('Y9', 3), ('Y8', 3), ('Y7', 4))
_WIRES = [(s, None, 'sig', ('U1', _OUT[t]), ('LED', t), f'{t} = U1 pin {_OUT[t]} -> LED {t}')
          for t, s in _ORDER]
# 입력 점퍼 (단계, 이름, 칩, 핀). A 가 LSB(교안 p9 Bit0).
_INPUTS = [(1, 'A', 'U1', 15), (1, 'B', 'U1', 14), (1, 'C', 'U1', 13), (1, 'D', 'U1', 12)]

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다.')


def _fixed(bb, stage, superset=False, layout=None):
    """칩·전원·브리지·LED 사슬 열·입력 점퍼 넷 — 전부 1단계 기반이다."""
    lay = layout or LAYOUT
    L, R = bb.cols['left'], bb.cols['right']
    k = place_chips(BCD, lay)['U1']
    bb.draw_chip('74HC42', k)
    gnd_row, vcc_row = lay['bridge']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], gnd_row, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], vcc_row, kind='vcc')
    bb.connect_power(k, gnd_col='a')
    for tag in _LEDS:
        bb.led_chain(R['a'], lay['leds']['bcd'][tag], tag, f'{tag} — 진리표 {tag} 열', block='right')
    for _s, name, chip, pin in _INPUTS:
        _input_jumper(bb, L, _dip_pin_row(k, pin, 16), name, f'{chip} pin {pin}', side='f', col='j')


def _draw(bb, stage):
    bb.partial = stage is not None and stage < 4
    bb.marker_hints = place_marker_hints(BCD, LAYOUT)
    _fixed(bb, stage)
    draw_routed(bb, BCD.wires, place_paths(BCD, LAYOUT), stage)
    bb.note(_INPUT_NOTE)


def build_trial_bcd(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """1-2 BCD → 10진 디코더 v2 시험판. `stage` 1..4 또는 None(완성)."""
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    bb.set_header('실험05 v2 시험판: BCD → 10진 디코더', '74HC42 · 칩 좌 블록, LED 우 블록')
    _draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


BCD = PlaceCircuit('bcd', {'U1': 'K1'}, {'U1': '74HC42'}, _LEDS, tuple(_WIRES), _fixed,
                   tuple((c, p) for _s, _n, c, p in _INPUTS))
PLACE = [BCD]

BOARDS = [(f'trial_e5_bcd_{s}.png', build_trial_bcd, s) for s in (1, 2, 3, 4)]
RESTART = set()
FINALS = [('trial_e5_bcd.png', build_trial_bcd)]
