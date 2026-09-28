# 실험04 결선 — 엔진 `render_breadboard.py --experiment 4` 가
# 이 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를 뽑는다.
# 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.
import os
import tempfile

from render_breadboard import BreadboardRenderer, _input_jumper, fresh_board, removal_board


# 실험 4 · Multiplexer & Demultiplexer — 2026-2 배포본 기준, 2026-09-28 저작
#
# 근거: `보고서/실험04/결선도/netlist.md` (C1 4x1 MUX · C2 1x4 DMUX), `체크리스트/명세.md`.
#
# **칩 자리를 좌우 블록으로 가른 이유 (R8).** 4x1 MUX 의 앞단 NAND 넷(U1·U2 의 게이트
# A·B)은 선택 입력 둘 중 하나를 **쪽**으로 가른다 — 게이트 A(핀 1~5, a쪽)는 `S0'`,
# 게이트 B(핀 9~13, f쪽)는 `S0` 를 받는다. 인버터 입력과 출력은 한쪽에 붙으므로 U4 가
# U1·U2 와 같은 블록이면 `S0` 나 `S0'` 둘 중 하나는 반드시 칩 사이에서 쪽을 바꾼다(R8).
# 합류 NAND U3 도 같다 — 입력 1·2·4·5 가 a쪽인데 U1·U2 출력 pin 8 은 f쪽이다. 그래서
# U4·U3 을 우 블록, U1·U2 를 좌 블록에 두었다 — 블록을 건너는 선은 R8 이 보지 않는다
# (중앙 여백을 차선으로 건넌다). 1x4 DMUX 도 같은 이유로 U6 을 우 블록(K4)에 둔다 —
# U6 게이트 1 은 입력 pin 13 과 출력 pin 12 가 f쪽이고 U5 는 그 D 를 a쪽 pin 5 로 받는다.
#
#   K1 우 7행  : 74HC04 (U4)            — C1·C2
#   K2 좌 18행 : 74HC20 (U1) / 74HC11 (U5)
#   K3 좌 30행 : 74HC20 (U2) / 비움
#   K4 우 30행 : 74HC20 (U3) / 74HC11 (U6)
#
# **E 인버터는 게이트 6(pin 13 → 12)이다** — 교안 p8 은 게이트 1(pin 1 → 2)이다. 교안
# 그대로면 U4 a쪽에 입력 셋·출력 셋·갈래 둘·GND 가 몰려 9리드다(R7, netlist M9). 나머지
# 핀 번호는 교안 그대로다.
#
# 팬아웃은 **칩 한쪽 리드가 8 을 넘지 않게** 고른다: `E'` 는 U4 pin 12 에서 U1 pin 4·U2
# pin 4 로 따로 가고 각 칩 안에서 pin 12 로 이어 간다, `S0'` 는 U4 pin 6 에서 U1 pin 1·
# U2 pin 1 로 따로 간다. 같은 칩 안의 a↔f 사슬은 칩 바로 위 행(U1 16·17행, U2 28·29행)을
# 돌아 건넌다 — 칩 몸통 위는 지나지 않는다.
#
# 여백 차선 (홀이 없는 x):
#   212·226 : 좌 VCC 레일~a열 사이 — U4 에서 U1·U2 의 pin 4 로 내려오는 E' 두 가닥
#   490·496·499·505·513·530·536 : 중앙 여백(좌 중앙 VCC~우 중앙 GND) — 좌우를 건너는 선.
#       U2 의 S1·S0' 는 490·499 로 내려와 U1·U2 사이 26·27행으로 좌 블록을 건넌다.
#       513 근처는 중앙 레일 입력 배지(S1·S0·D1·D3·S0·S1) 자리라 그 행을 지나는 선은
#       490·496·530·536 만 쓴다
#   583·590·597 : 우 중앙 VCC 레일~a열 사이 — U4 쪽에서 LED 로 내려가는 선
#
# LED 는 네 개다(교안 준비물). 네 사슬이 우 c42·c46·c51·c57 에 고정이고 C1 은 LED1 = Y,
# C2 는 LED1~4 = Y0~Y3 이다. C1 중간 노드는 그 시점에 빈 LED 의 급전선을 잠시 옮겨 본다.

E4_SLOTS = {'K1': ('right', 7), 'K2': ('left', 18), 'K3': ('left', 30), 'K4': ('right', 30)}
_K1, _K2, _K3, _K4 = (E4_SLOTS[k][1] for k in ('K1', 'K2', 'K3', 'K4'))
_LED = (42, 46, 51, 57)   # 우 c 열 급전 홀 — LED1~LED4

# 4입력 NAND 출력 하나를 보려면 입력 넷과 관측선 하나가 한꺼번에 있어야 한다.
STAGE_WIRE_BUDGET = 5
STAGE_WIRE_BUDGET_REASON = ('4입력 NAND(74HC20) 출력 하나를 관측하려면 입력 넷과 관측 급전선 하나가 '
                            '한꺼번에 있어야 한다 — 입력 일부만 물리면 나머지가 떠서 관측 노드 상류 '
                            '플로팅 금지에 걸린다. 예산 = 게이트 입력 수 + 1 (2026-09-27 결정, netlist M8)')

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')
_NC_NOTE = '74HC20 pin 3·11 은 n.c.(내부 연결 없음)다 — 아무것도 꽂지 않는다.'

_MUX_STAGES = 8
_DMUX_STAGES = 4

_MUX_TITLE = {
    1: "실험 1-1: 4x1 MUX — 1단계 (E 인버터, 노드 E')",
    2: "실험 1-1: 4x1 MUX — 2단계 (S1 인버터, 노드 S1')",
    3: "실험 1-1: 4x1 MUX — 3단계 (S0 인버터, 노드 S0')",
    4: "실험 1-1: 4x1 MUX — 4단계 (U1 NAND A, 노드 (E'·S1'·S0'·D0)')",
    5: "실험 1-1: 4x1 MUX — 5단계 (U1 NAND B, 노드 (E'·S1'·S0·D1)')",
    6: "실험 1-1: 4x1 MUX — 6단계 (U2 NAND A, 노드 (E'·S1·S0'·D2)')",
    7: "실험 1-1: 4x1 MUX — 7단계 (U2 NAND B, 노드 (E'·S1·S0·D3)')",
    8: "실험 1-1: 4x1 MUX — 8단계 (U3 합류 NAND, 노드 Y · 완성)",
}
_DMUX_TITLE = {
    1: "실험 2-1: 1x4 DMUX — 1단계 (U6 AND, 노드 Y3)",
    2: "실험 2-1: 1x4 DMUX — 2단계 (U5 AND 2, 노드 Y1)",
    3: "실험 2-1: 1x4 DMUX — 3단계 (U5 AND 3, 노드 Y2)",
    4: "실험 2-1: 1x4 DMUX — 4단계 (U5 AND 1, 노드 Y0 · 완성)",
}

_MUX_STAGE_NOTE = {
    1: "1단계: 네 칩 전원·레일 브리지·LED 네 사슬을 꽂는다. E 인버터(U4 pin 13→12)만 검사한다 — "
       "LED4 급전선을 **임시로** U4 pin 12 에 꽂아 E' 를 E 두 값으로 본다 (E=0 일 때만 켜짐).",
    2: "2단계: LED3 급전선을 **임시로** U4 pin 4 에 꽂아 S1' 를 본다 (S1=0 일 때만 켜짐). "
       "LED4 는 내내 E' 를 보인다.",
    3: "3단계: LED2 급전선을 **임시로** U4 pin 6 에 꽂아 S0' 를 본다 (S0=0 일 때만 켜짐).",
    4: "4단계: U1 NAND A 에 S0'·S1'·E'·D0 를 물리고 LED1 급전선을 **임시로** U1 pin 6 에 꽂는다. "
       "T1 아홉 행 — 3행(E=0·S1S0=00·D0=1)에서만 꺼진다. 인버터 임시 급전선 셋은 다음 장(5걷기)이 뽑는다.",
    5: "5단계: 앞 장(5걷기)에서 인버터 임시 급전선 셋을 뽑은 상태로 시작한다. U1 NAND B 를 잇고 "
       "LED2 를 **임시로** U1 pin 8 에 꽂는다 — 5행(E=0·S1S0=01·D1=1)에서만 꺼진다.",
    6: "6단계: U2 NAND A 를 잇고 LED3 을 **임시로** U2 pin 6 에 꽂는다 — 7행(E=0·S1S0=10·D2=1)에서만 꺼진다.",
    7: "7단계: U2 NAND B 를 잇고 LED4 를 **임시로** U2 pin 8 에 꽂는다 — 9행(E=0·S1S0=11·D3=1)에서만 꺼진다. "
       "NAND 임시 급전선 넷은 다음 장(8걷기)이 뽑는다.",
    8: "8단계: 앞 장(8걷기)에서 NAND 임시 급전선 넷을 뽑은 상태로 시작한다. U3 에 앞단 출력 넷을 "
       "물리고 LED1 = Y 를 T1 아홉 행 전부로 본다 — 완성이다.",
}
_DMUX_STAGE_NOTE = {
    1: "1단계: MUX 신호선을 전부 뽑고 74HC20 셋을 빼 74HC11 을 K2·K4 에 꽂은 상태다 — 전원선·"
       "브리지·LED 사슬만 남는다. U6 AND 1 에 S0·S1·D 를 물리고 LED4 = Y3 을 본다 (D=1·S1S0=11 에서만 켜짐).",
    2: "2단계: U5 AND 2 에 S0·S1'·D 를 물린다 — LED2 = Y1 (D=1·S1S0=01 에서만 켜짐). U4 는 이 회로에서 처음 쓴다.",
    3: "3단계: U5 AND 3 에 S1·S0'·D 를 물린다 — LED3 = Y2 (D=1·S1S0=10 에서만 켜짐).",
    4: "4단계: U5 AND 1 에 S1'·S0'·D 를 물린다 — LED1 = Y0. 완성이다: D=1 인 행에서 LED 하나만, "
       "D=0 인 행에서는 하나도 안 켜져야 한다.",
}


def _stage_check(circuit, stage):
    if stage is None:
        return
    last = {'mux': _MUX_STAGES, 'dmux': _DMUX_STAGES}[circuit]
    if not 1 <= stage <= last:
        raise ValueError(f'{circuit} 에 {stage}단계는 없다 — 1..{last}')


def _mark_nc(bb, start_row, block):
    """74HC20 pin 3·11 — 내부 연결이 없는 다리. 뜬 핀 검사(R5ⓒ)가 보지 않게 개방으로 적는다."""
    for p in (3, 11):
        bb.unused_inputs.append({'chip': '74HC20', 'pin': p, 'rail': None,
                                 'block': block, 'pin1_row': start_row})
    bb.note(_NC_NOTE)


def _frame(bb):
    """잭 + 레일 브리지. 두 회로가 같은 홀을 쓴다 — DMUX 는 MUX 의 전원선·브리지를 그대로 둔다.

    GND 사슬: 좌 바깥(잭·U1/U2/U5 pin 7·D0/D2) → 좌 중앙(D1/D3) → 우 중앙(U4/U3/U6 pin 7·
    LED·S1/S0) → 우 바깥(E/D). VCC 사슬: 좌 바깥(잭) → 좌 중앙(U1/U2/U5 pin 14) → 우
    바깥(U4/U3/U6 pin 14). 브리지 행은 두 회로 모두 신호선이 없는 39~41·55·61행이다.
    """
    c, r = bb.cols['left'], bb.cols['right']
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 39, kind='gnd')
    bb.bridge_rails(c['mid_gnd'], r['mid_gnd'], 40, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 41, kind='vcc')
    bb.bridge_rails(r['mid_gnd'], r['gnd'], 55, kind='gnd')
    bb.bridge_rails(c['mid_vcc'], r['vcc'], 61, kind='vcc')


def _chains(bb, tags, descs):
    r = bb.cols['right']
    for i, row in enumerate(_LED):
        bb.led_chain(r['c'], row, tags[i], descs[i], block='right')


_IDLE_LEDS = ('L2', 'L3', 'L4')


def _verify_idle_leds(bb):
    """MUX 완성 상태의 R5ⓒ — 뜬 것이 급전하지 않는 LED2~4 애노드뿐인가.

    `partial` 은 R5ⓒ 를 통째로 끈다. 완성본에서 칩 핀이 뜨면 그것은 진짜 결함이라
    `partial` 을 잠시 내리고 검사를 돌려, 걸린 줄이 그 세 애노드뿐인지 본다.
    """
    bb.partial = False
    try:
        bb.verify()
    except AssertionError as e:
        lines = [ln.strip() for ln in str(e).splitlines()[1:]]
        idle = {f'LED {t} 애노드 가 아무 데도 안 물렸다 — 뜬 다리' for t in _IDLE_LEDS}
        if not str(e).startswith('넷이 틀렸다') or set(lines) != idle:
            raise
    finally:
        bb.partial = True


def _mux_draw(bb, stage):
    """C1 4x1 MUX. `stage` 는 1..8 또는 None(완성).

    **단계는 그리기 순서의 앞부분 자르기다.** 배선은 처음 꽂히는 단계 순서로 한 번만
    적고 `on(s, e)` 로 자른다 — 레일 착지 행이 점유 순서로 정해지므로 순서를 바꾸면
    완성본 도장이 바뀐다. `e` 가 있는 것은 그 단계까지만 있는 임시 급전선이다.
    """
    _stage_check('mux', stage)
    c, r = bb.cols['left'], bb.cols['right']
    L = bb.r_y

    def on(s, e=None):
        if stage is None:
            return e is None
        return s <= stage and (e is None or stage <= e)

    def w(pts, desc, kind='sig', s=1, e=None, marker=None):
        if on(s, e):
            bb.step_wire(pts, kind, desc, marker_at=marker)

    # 완성 상태(8단계·완성본)에서도 LED2~4 는 급전하지 않는다 — 중간 노드를 보던 자리라
    # 사슬만 남는다. R5ⓒ 가 그 애노드를 뜬 다리로 잡으므로 완성 상태도 `partial` 로 끄고,
    # 그 셋 말고 뜬 것이 없는지는 `_verify_idle_leds()` 가 export 전에 따로 본다.
    bb.partial = True

    # --- 칩 · 전원 · LED 사슬 (1단계에 한꺼번에) ---
    bb.draw_chip('74HC04', _K1, block='right')
    bb.draw_chip('74HC20', _K2)
    bb.draw_chip('74HC20', _K3)
    bb.draw_chip('74HC20', _K4, block='right')
    _frame(bb)
    bb.connect_power(_K1, block='right', gnd_col='a')
    bb.connect_power(_K2, gnd_col='a')
    bb.connect_power(_K3, gnd_col='a')
    bb.connect_power(_K4, block='right', gnd_col='a')
    probe = {1: None, 2: None, 3: None, 4: None}
    if stage is not None and stage < _MUX_STAGES:
        probe = {1: "(E'·S1'·S0'·D0)'" if stage >= 4 else None,
                 2: "S0'" if stage in (3, 4) else ("(E'·S1'·S0·D1)'" if stage >= 5 else None),
                 3: "S1'" if 2 <= stage <= 4 else ("(E'·S1·S0'·D2)'" if stage >= 6 else None),
                 4: "E'" if stage <= 4 else ("(E'·S1·S0·D3)'" if stage >= 7 else None)}
    descs = []
    for i in (1, 2, 3, 4):
        if i == 1 and not probe[1] and (stage is None or stage == _MUX_STAGES):
            descs.append('Y — 진리표 T1 의 Y 열')
        elif probe[i]:
            descs.append(f'이 단계에는 {probe[i]} 를 본다 — 임시 급전선은 걷기 그림이 뽑는다')
        else:
            descs.append('지금은 급전하지 않는다')
    _chains(bb, ('Y', 'L2', 'L3', 'L4'), descs)

    # --- 1단계: E 인버터 (U4 게이트 6, pin 13 → 12) ---
    if on(1):
        _input_jumper(bb, r, _K1 + 1, 'E', 'U4 pin 13', side='f')
    w([(r['j'], L(9)), (r['j'], L(16)), (583, L(16)), (583, L(57)), (r['c'], L(57))],
      "임시 급전: E' = U4 pin 12 -> LED4 (5걷기에서 뽑는다)", s=1, e=4)

    # --- 2단계: S1 인버터 (pin 3 → 4) ---
    if on(2):
        _input_jumper(bb, r, _K1 + 2, 'S1', 'U4 pin 3')
    w([(r['d'], L(10)), (r['d'], L(15)), (590, L(15)), (590, L(51)), (r['c'], L(51))],
      "임시 급전: S1' = U4 pin 4 -> LED3 (5걷기에서 뽑는다)", s=2, e=4)

    # --- 3단계: S0 인버터 (pin 5 → 6) ---
    if on(3):
        # 번호 원 기본 자리(배지 위 18px)는 S1 배지(9행)에 걸린다 — 배지 아래로 둔다
        _input_jumper(bb, r, _K1 + 4, 'S0', 'U4 pin 5', marker=(513, 18))
    w([(r['c'], L(12)), (r['c'], L(14)), (597, L(14)), (597, L(46)), (r['c'], L(46))],
      "임시 급전: S0' = U4 pin 6 -> LED2 (5걷기에서 뽑는다)", s=3, e=4)

    # --- 4단계: U1 NAND A (pin 1 S0' · 2 S1' · 4 E' · 5 D0 → 6) ---
    w([(r['a'], L(12)), (c['a'], L(12)), (c['a'], L(18))],
      "S0' (U4 pin 6) -> U1 pin 1", s=4)
    w([(r['a'], L(10)), (c['c'], L(10)), (c['c'], L(19))],
      "S1' (U4 pin 4) -> U1 pin 2", s=4)
    w([(r['h'], L(9)), (r['h'], L(6)), (226, L(6)), (226, L(21)), (c['a'], L(21))],
      "E' (U4 pin 12) -> U1 pin 4", s=4)
    if on(4):
        _input_jumper(bb, c, 22, 'D0', 'U1 pin 5')
    w([(c['d'], L(23)), (c['d'], L(25)), (536, L(25)), (536, L(42)), (r['c'], L(42))],
      "임시 급전: U1 pin 6 -> LED1 (8걷기에서 뽑는다)", s=4, e=7)

    # --- 5단계: U1 NAND B (pin 9 S0 · 10 S1' · 12 E' · 13 D1 → 8) ---
    w([(r['d'], L(11)), (r['d'], L(15)), (536, L(15)), (536, L(23)), (c['j'], L(23))],
      'S0 갈래 (U4 pin 5) -> U1 pin 9', s=5)
    w([(c['b'], L(19)), (c['b'], L(17)), (c['j'], L(17)), (c['j'], L(22))],
      "S1' 이어 감 (U1 pin 2 -> U1 pin 10)", s=5)
    w([(c['d'], L(21)), (c['d'], L(16)), (c['h'], L(16)), (c['h'], L(20))],
      "E' 이어 감 (U1 pin 4 -> U1 pin 12)", s=5)
    if on(5):
        _input_jumper(bb, c, 19, 'D1', 'U1 pin 13', side='f')
    w([(c['j'], L(24)), (530, L(24)), (530, L(46)), (r['c'], L(46))],
      '임시 급전: U1 pin 8 -> LED2 (8걷기에서 뽑는다)', s=5, e=7)

    # --- 6단계: U2 NAND A (pin 1 S0' · 2 S1 · 4 E' · 5 D2 → 6) ---
    # U2 의 S0'·S1 은 중앙 여백으로 내려와 U1·U2 사이 빈 행(27·26행)으로 좌 블록을 건넌 뒤
    # 위에서 꽂는다 — 좌 여백 차선을 두 가닥으로 줄여 손으로 따라 그릴 간격을 벌린다
    w([(r['c'], L(12)), (r['c'], L(5)), (499, L(5)), (499, L(27)), (c['a'], L(27)), (c['a'], L(30))],
      "S0' (U4 pin 6) -> U2 pin 1", s=6)
    w([(r['d'], L(9)), (r['d'], L(4)), (490, L(4)), (490, L(26)), (c['c'], L(26)), (c['c'], L(31))],
      'S1 갈래 (U4 pin 3) -> U2 pin 2', s=6)
    w([(r['j'], L(9)), (r['j'], L(3)), (212, L(3)), (212, L(33)), (c['a'], L(33))],
      "E' (U4 pin 12) -> U2 pin 4", s=6, marker=(r['j'], L(4)))
    if on(6):
        _input_jumper(bb, c, 34, 'D2', 'U2 pin 5')
    w([(c['d'], L(35)), (c['d'], L(37)), (513, L(37)), (513, L(51)), (r['c'], L(51))],
      '임시 급전: U2 pin 6 -> LED3 (8걷기에서 뽑는다)', s=6, e=7)

    # --- 7단계: U2 NAND B (pin 9 S0 · 10 S1 · 12 E' · 13 D3 → 8) ---
    w([(c['h'], L(23)), (c['h'], L(35))],
      'S0 이어 감 (U1 pin 9 -> U2 pin 9)', s=7)
    w([(c['b'], L(31)), (c['b'], L(29)), (c['i'], L(29)), (c['i'], L(34))],
      'S1 이어 감 (U2 pin 2 -> U2 pin 10)', s=7)
    w([(c['d'], L(33)), (c['d'], L(28)), (490, L(28)), (490, L(32)), (c['j'], L(32))],
      "E' 이어 감 (U2 pin 4 -> U2 pin 12)", s=7)
    if on(7):
        _input_jumper(bb, c, 31, 'D3', 'U2 pin 13', side='f', col='j')
    w([(c['j'], L(36)), (505, L(36)), (505, L(57)), (r['c'], L(57))],
      '임시 급전: U2 pin 8 -> LED4 (8걷기에서 뽑는다)', s=7, e=7)

    # --- 8단계: U3 합류 NAND (pin 1·2·4·5 → 6) + LED1 = Y ---
    w([(c['d'], L(23)), (c['d'], L(25)), (513, L(25)), (513, L(30)), (r['a'], L(30))],
      '(E\'·S1\'·S0\'·D0)\' (U1 pin 6) -> U3 pin 1', 'mid', s=8)
    w([(c['j'], L(24)), (530, L(24)), (530, L(31)), (r['a'], L(31))],
      '(E\'·S1\'·S0·D1)\' (U1 pin 8) -> U3 pin 2', 'mid', s=8)
    w([(c['d'], L(35)), (c['d'], L(37)), (513, L(37)), (513, L(33)), (r['a'], L(33))],
      '(E\'·S1·S0\'·D2)\' (U2 pin 6) -> U3 pin 4', 'mid', s=8)
    w([(c['j'], L(36)), (505, L(36)), (505, L(34)), (r['a'], L(34))],
      '(E\'·S1·S0·D3)\' (U2 pin 8) -> U3 pin 5', 'mid', s=8)
    w([(r['c'], L(35)), (r['c'], L(42))], 'Y = U3 pin 6 -> LED1', s=8)

    # --- 미사용 · n.c. ---
    bb.mark_unused_inputs([1, 9, 11], _K1, block='right', chip='74HC04')
    bb.mark_unused_outputs([2, 8, 10], _K1, block='right', chip='74HC04')
    _mark_nc(bb, _K2, 'left')
    _mark_nc(bb, _K3, 'left')
    _mark_nc(bb, _K4, 'right')
    bb.mark_unused_inputs([9, 10, 12, 13], _K4, block='right', chip='74HC20 (U3)')
    bb.mark_unused_outputs([8], _K4, block='right', chip='74HC20 (U3)')
    note = None if bb.ghost is not None else _MUX_STAGE_NOTE.get(stage)
    if note:
        bb.note(note)
    bb.note('E 인버터는 U4 게이트 6(pin 13 → 12)이다 — 교안 p8 의 게이트 1(pin 1 → 2) 대신 '
            '쓴다. U4 a쪽 리드가 8 을 넘지 않게 옮겼다(netlist M9). 논리는 같다.')
    bb.note('LED 는 네 개다. 완성본은 LED1 = Y 만 급전한다 — LED2~4 는 중간 노드를 보던 자리다.')
    bb.note(_INPUT_NOTE)


def _dmux_draw(bb, stage):
    """C2 1x4 DMUX. `stage` 는 1..4 또는 None(완성). MUX 를 전부 걷고 새로 짓는다(rebuild)."""
    _stage_check('dmux', stage)
    c, r = bb.cols['left'], bb.cols['right']
    L = bb.r_y

    def on(s):
        return stage is None or s <= stage

    def w(pts, desc, kind='sig', s=1, marker=None):
        if on(s):
            bb.step_wire(pts, kind, desc, marker_at=marker)

    bb.partial = stage is not None and stage < _DMUX_STAGES

    bb.draw_chip('74HC04', _K1, block='right')
    bb.draw_chip('74HC11', _K2)
    bb.draw_chip('74HC11', _K4, block='right')
    _frame(bb)
    bb.connect_power(_K1, block='right', gnd_col='a')
    bb.connect_power(_K2, gnd_col='a')
    bb.connect_power(_K4, block='right', gnd_col='a')
    lit = {1: 4, 2: 2, 3: 3, 4: 1}
    shown = {lit[k] for k in range(1, (stage or _DMUX_STAGES) + 1)}
    descs = [f'Y{i} — 진리표 T3 의 Y{i} 열' if i + 1 in shown else '아직 급전하지 않는다 — 뒤 단계에서 잇는다'
             for i in range(4)]
    _chains(bb, ('Y0', 'Y1', 'Y2', 'Y3'), descs)

    # --- 1단계: U6 AND 1 (pin 1 S0 · 2 S1 · 13 D → 12 = Y3) ---
    if on(1):
        _input_jumper(bb, r, _K4, 'S0', 'U6 pin 1', col='a')
        # 번호 원 기본 자리(배지 위 18px)는 S0 배지(30행)에 걸린다 — 배지 아래로 둔다
        _input_jumper(bb, r, _K4 + 1, 'S1', 'U6 pin 2', col='a', marker=(513, 18))
        _input_jumper(bb, r, _K4 + 1, 'D', 'U6 pin 13', side='f', col='j')
    w([(r['g'], L(32)), (r['g'], L(37)), (583, L(37)), (583, L(57)), (r['c'], L(57))],
      'Y3 = U6 pin 12 -> LED4', s=1)

    # --- 2단계: U5 AND 2 (pin 3 S0 · 4 S1' · 5 D → 6 = Y1) ---
    w([(r['b'], L(30)), (r['b'], L(29)), (215, L(29)), (215, L(20)), (c['a'], L(20))],
      'S0 이어 감 (U6 pin 1 -> U5 pin 3)', s=2)
    w([(r['d'], L(31)), (r['d'], L(25)), (597, L(25)), (597, L(9)), (r['a'], L(9))],
      'S1 이어 감 (U6 pin 2 -> U4 pin 3)', s=2)
    w([(r['a'], L(10)), (c['b'], L(10)), (c['b'], L(21))],
      "S1' (U4 pin 4) -> U5 pin 4", s=2)
    w([(r['i'], L(31)), (r['i'], L(28)), (222, L(28)), (222, L(22)), (c['a'], L(22))],
      'D 이어 감 (U6 pin 13 -> U5 pin 5)', s=2)
    w([(c['d'], L(23)), (c['d'], L(25)), (530, L(25)), (530, L(46)), (r['c'], L(46))],
      'Y1 = U5 pin 6 -> LED2', s=2)

    # --- 3단계: U5 AND 3 (pin 9 S1 · 10 S0' · 11 D → 8 = Y2) ---
    w([(r['c'], L(30)), (r['c'], L(27)), (590, L(27)), (590, L(7)), (r['a'], L(7))],
      'S0 이어 감 (U6 pin 1 -> U4 pin 1)', s=3)
    w([(r['b'], L(8)), (r['b'], L(5)), (505, L(5)), (505, L(22)), (c['j'], L(22))],
      "S0' (U4 pin 2) -> U5 pin 10", s=3)
    w([(r['c'], L(9)), (r['c'], L(4)), (512, L(4)), (512, L(23)), (c['j'], L(23))],
      'S1 이어 감 (U4 pin 3 -> U5 pin 9)', s=3)
    w([(c['c'], L(22)), (c['c'], L(26)), (c['h'], L(26)), (c['h'], L(21))],
      'D 이어 감 (U5 pin 5 -> U5 pin 11)', s=3)
    w([(c['j'], L(24)), (496, L(24)), (496, L(51)), (r['c'], L(51))],
      'Y2 = U5 pin 8 -> LED3', s=3)

    # --- 4단계: U5 AND 1 (pin 1 S1' · 2 S0' · 13 D → 12 = Y0) ---
    w([(r['d'], L(10)), (r['d'], L(6)), (c['d'], L(6)), (c['d'], L(18))],
      "S1' 이어 감 (U4 pin 4 -> U5 pin 1)", s=4)
    w([(r['a'], L(8)), (c['c'], L(8)), (c['c'], L(19))],
      "S0' 이어 감 (U4 pin 2 -> U5 pin 2)", s=4)
    w([(c['i'], L(21)), (c['i'], L(19))],
      'D 이어 감 (U5 pin 11 -> U5 pin 13)', s=4)
    w([(c['j'], L(20)), (536, L(20)), (536, L(42)), (r['c'], L(42))],
      'Y0 = U5 pin 12 -> LED1', s=4)

    bb.mark_unused_inputs([5, 9, 11, 13], _K1, block='right', chip='74HC04')
    bb.mark_unused_outputs([6, 8, 10, 12], _K1, block='right', chip='74HC04')
    bb.mark_unused_inputs([3, 4, 5, 9, 10, 11], _K4, block='right', chip='74HC11 (U6)')
    bb.mark_unused_outputs([6, 8], _K4, block='right', chip='74HC11 (U6)')
    note = _DMUX_STAGE_NOTE.get(stage)
    if note:
        bb.note(note)
    bb.note('K3(좌 30행)는 비운다. MUX 의 K3 전원선은 그대로 두어도 된다 — 칩이 없는 '
            '행에 꽂힌 전원선은 아무 데도 물리지 않는다. 좌 중앙 GND 레일 브리지도 MUX 에서 '
            '남긴 것이다.')
    bb.note(_INPUT_NOTE)


def build_e4_mux(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-1 · Enable 을 갖는 4x1 MUX (74HC04 + 74HC20 ×3). netlist C1. 8단계.

      stage 1~3  U4 인버터 셋 — LED4·3·2 임시 급전으로 E'·S1'·S0'
      stage 4~7  앞단 NAND 넷 — LED1~4 임시 급전 (5걷기·8걷기가 뽑는다)
      stage 8    U3 합류 NAND + LED1 = Y · 완성
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    _stage_check('mux', stage)
    title = _MUX_TITLE[stage] if stage is not None else "실험 1-1: 4x1 MUX 결선도"
    bb.set_header(title, "74HC04 NOT 3 + 74HC20 4입력 NAND 5 · Y = E'·(S1'S0'D0 + S1'S0D1 + S1S0'D2 + S1S0D3)",
                  submit=baseline is None and stage is None)
    _mux_draw(bb, stage)
    if (stage is None or stage == _MUX_STAGES) and bb.ghost is None:
        _verify_idle_leds(bb)
    bb.export(output_path, max_row=61)
    return bb


def build_e4_dmux(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-1 · Enable 을 갖는 1x4 DMUX (74HC04 + 74HC11 ×2). netlist C2. 4단계.

    MUX 신호선을 전부 뽑고 새로 짓는다(`rebuild: true`) — 사슬에는 `fresh_board` 로 들어가
    기준선 없이 그린다. 출력 넷이 곧 LED 넷이라 임시 급전선도 걷기 그림도 없다.
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    _stage_check('dmux', stage)
    title = _DMUX_TITLE[stage] if stage is not None else "실험 2-1: 1x4 DMUX 결선도"
    bb.set_header(title, "74HC04 NOT 2 + 74HC11 3입력 AND 4 · Y0~Y3 = D·(S1'S0' · S1'S0 · S1S0' · S1S0)",
                  submit=baseline is None and stage is None)
    _dmux_draw(bb, stage)
    bb.export(output_path, max_row=61)
    return bb


# 절차 그림 사슬. 보드 n 의 기준선은 보드 n-1 의 배선이다. 임시 급전선을 뽑는 자리마다
# 걷기 보드가 한 장이다(5걷기·8걷기). DMUX 는 MUX 를 전부 걷고 새로 짓는 경계라
# (`rebuild: true`) 걷기 보드 없이 `fresh_board` 로 기준선을 끊는다.
BOARDS = [
    ("실험04_1-1_결선도_4x1MUX_1단계_E인버터.png", build_e4_mux, 1),
    ("실험04_1-1_결선도_4x1MUX_2단계_S1인버터.png", build_e4_mux, 2),
    ("실험04_1-1_결선도_4x1MUX_3단계_S0인버터.png", build_e4_mux, 3),
    ("실험04_1-1_결선도_4x1MUX_4단계_NAND0.png", build_e4_mux, 4),
    ("실험04_1-1_결선도_4x1MUX_5걷기_인버터프로브.png",
     removal_board((build_e4_mux, 4), (build_e4_mux, 5),
                   "실험 1-1: 4x1 MUX — 5단계 걷기 (임시 급전선 3가닥)",
                   "E'·S1'·S0' → LED4·LED3·LED2 임시 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험04_1-1_결선도_4x1MUX_5단계_NAND1.png", build_e4_mux, 5),
    ("실험04_1-1_결선도_4x1MUX_6단계_NAND2.png", build_e4_mux, 6),
    ("실험04_1-1_결선도_4x1MUX_7단계_NAND3.png", build_e4_mux, 7),
    ("실험04_1-1_결선도_4x1MUX_8걷기_NAND프로브.png",
     removal_board((build_e4_mux, 7), (build_e4_mux, 8),
                   "실험 1-1: 4x1 MUX — 8단계 걷기 (임시 급전선 4가닥)",
                   "앞단 NAND 넷 → LED1~LED4 임시 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험04_1-1_결선도_4x1MUX_8단계_Y.png", build_e4_mux, 8),
    ("실험04_2-1_결선도_1x4DMUX_1단계_Y3.png", fresh_board(build_e4_dmux), 1),
    ("실험04_2-1_결선도_1x4DMUX_2단계_Y1.png", build_e4_dmux, 2),
    ("실험04_2-1_결선도_1x4DMUX_3단계_Y2.png", build_e4_dmux, 3),
    ("실험04_2-1_결선도_1x4DMUX_4단계_Y0.png", build_e4_dmux, 4),
]

# 완성본 — 기준선 없이 전부 색. 예비보고서에 싣고 손으로 따라 그리는 원도다.
FINALS = [
    ("실험04_1-1_결선도_4x1MUX.png", build_e4_mux),
    ("실험04_2-1_결선도_1x4DMUX.png", build_e4_dmux),
]


def _e4_baseline(index, template_path=None):
    """`BOARDS[index]` 의 기준선 = 바로 앞 보드의 `snapshot()`. 첫 보드는 None."""
    if index == 0:
        return None
    _name, fn, stage = BOARDS[index - 1]
    with tempfile.TemporaryDirectory() as d:
        return fn(os.path.join(d, 'prev.png'), template_path, stage=stage).snapshot()


def _e4_board(index, output_path, template_path=None):
    _name, fn, stage = BOARDS[index]
    return fn(output_path, template_path, stage=stage,
              baseline=_e4_baseline(index, template_path))


def build_e4_mux_s1(output_path, template_path=None):
    """C1 1단계 — 네 칩·전원·LED 사슬 + E 인버터. 노드 E'."""
    return _e4_board(0, output_path, template_path)


def build_e4_mux_s2(output_path, template_path=None):
    """C1 2단계 — S1 인버터. 노드 S1'."""
    return _e4_board(1, output_path, template_path)


def build_e4_mux_s3(output_path, template_path=None):
    """C1 3단계 — S0 인버터. 노드 S0'."""
    return _e4_board(2, output_path, template_path)


def build_e4_mux_s4(output_path, template_path=None):
    """C1 4단계 — U1 NAND A. 노드 (E'·S1'·S0'·D0)'."""
    return _e4_board(3, output_path, template_path)


def build_e4_mux_s5(output_path, template_path=None):
    """C1 5단계 — 5걷기 뒤에 U1 NAND B. 노드 (E'·S1'·S0·D1)'."""
    return _e4_board(5, output_path, template_path)


def build_e4_mux_s6(output_path, template_path=None):
    """C1 6단계 — U2 NAND A. 노드 (E'·S1·S0'·D2)'."""
    return _e4_board(6, output_path, template_path)


def build_e4_mux_s7(output_path, template_path=None):
    """C1 7단계 — U2 NAND B. 노드 (E'·S1·S0·D3)'."""
    return _e4_board(7, output_path, template_path)


def build_e4_mux_s8(output_path, template_path=None):
    """C1 8단계 — 8걷기 뒤에 U3 합류 NAND. 노드 Y, 완성."""
    return _e4_board(9, output_path, template_path)


def build_e4_dmux_s1(output_path, template_path=None):
    """C2 1단계 — MUX 를 전부 걷은 뒤 U6 AND 1. 노드 Y3."""
    return _e4_board(10, output_path, template_path)


def build_e4_dmux_s2(output_path, template_path=None):
    """C2 2단계 — U5 AND 2. 노드 Y1."""
    return _e4_board(11, output_path, template_path)


def build_e4_dmux_s3(output_path, template_path=None):
    """C2 3단계 — U5 AND 3. 노드 Y2."""
    return _e4_board(12, output_path, template_path)


def build_e4_dmux_s4(output_path, template_path=None):
    """C2 4단계 — U5 AND 1. 노드 Y0, 완성."""
    return _e4_board(13, output_path, template_path)
