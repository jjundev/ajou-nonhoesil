# 실험03 결선 — 엔진 `render_breadboard.py --experiment 3` 이
# 이 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를 뽑는다.
# 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.
import os
import tempfile

from render_breadboard import BreadboardRenderer, _input_jumper, removal_board


# 실험 3 · 가산기 & 감산기 — 2026-2 배포본(9쪽) 기준, 2026-09-14 저작
#
# 네 회로가 칩 네 종류(74HC86·74HC08·74HC32·74HC04)를 한 패키지씩 나눠 쓴다.
#
# 2026-09-14 조교 공지(`_350547_1`)로 실험실에서 하는 회로는 전가산기(C2)·전감산기(C4)
# 뿐이다. 사슬은 C2(맨바닥에서 2단계) → C4(74HC04 를 끼우는 1단계)다. 반가산기·반감산기
# 빌더(`build_e3_ha`·`build_e3_hs`)는 완성본만 남는다 — 사슬에는 없고, 같은 글자 `B`
# 배지와 손그림 검토의 회귀 사례로 테스트가 쓴다.
# 슬롯은 **역할**에 붙고 칩 종류는 회로가 바뀌어도 그 자리에서 바뀌지 않는다 —
# 정본은 netlist 의 `kind: layout` 표이고 이 상수는 사본이다
# (`tests/test_breadboard_wiring.py` 가 둘을 맞댄다).
#
#   S1 좌 7행  : 74HC86 (U1, XOR) — 네 회로 전부. 입력 A·B·Ci/Bi 가 여기 꽂힌다
#   S2 좌 18행 : 74HC04 (U4, NOT) — C4
#   S3 우 10행 : 74HC08 (U2, AND) — 네 회로 전부
#   S4 우 21행 : 74HC32 (U3, OR)  — C2·C4
#
# 자리를 이렇게 잡은 이유: 교차 배선이 전부 **입력 갈래**(A·B·Ci 가 좌 7·8·11행
# 스트립에서 우측 AND 로 건너는 것)와 인버터 출력 둘(A'·(A⊕B)')뿐이라, 왼쪽
# 블록에는 XOR·NOT·LED1 만 남고 AND→OR 은 우측 안에서 짧게 끝난다. netlist 초안은
# 74HC08 을 좌 18행에 두었는데 그러면 감산기에서 좌우를 오가는 선이 여섯 가닥이다.
#
# 세로 차선(홀이 없는 여백):
#   212 : 좌 레일~a열 사이 — LED1 급전 (XOR 출력 → 좌 a25 사슬)
#   440 : 좌 j열~중앙 레일 사이 — A' (좌 74HC04 pin 2 → 우 74HC08 pin 1)
#   452 : 같은 여백 — (A⊕B)' (좌 74HC04 pin 4 → 우 74HC08 pin 4)
# 입력 갈래는 칩 위(4·5·6행)를 가로질러 우측 a·b·c 열로 내려간다 — 실험01
# 복합회로의 A·B 갈래와 같은 꼴이다.
#
# LED 는 두 개뿐이다(교안 p8). LED1(합/차)은 좌 a25 사슬, LED2(올림/내림)는
# 우 c29 사슬로 고정하고, 회로가 바뀌면 **급전선만** 옮긴다.
#
# 근거: `보고서/실험03/결선도/netlist.md` (C2·C4), `체크리스트/명세.md`.

E3_SLOTS = {'S1': ('left', 7), 'S2': ('left', 18), 'S3': ('right', 10), 'S4': ('right', 21)}
_E3_S1, _E3_S2, _E3_S3, _E3_S4 = (E3_SLOTS[k][1] for k in ('S1', 'S2', 'S3', 'S4'))
_E3_LED1 = 25      # 좌 a25 사슬 — S / D
_E3_LED2 = 29      # 우 c29 사슬 — C / Co / B / Bo
_E3_LANE = 212     # 좌 여백 세로 차선 — LED1 급전
_E3_LANE_A = 440   # 좌 j~중앙 레일 여백 — A' 건너감
_E3_LANE_X = 452   # 같은 여백 — (A⊕B)' 건너감
_E3_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
                  '빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')
_E3_LED_NOTE_REGRESSION = ('LED 는 두 개뿐이다(교안 p8). LED1 = 합/차(S·D), LED2 = 올림/내림(C·Co·B·Bo). '
                           '회로가 바뀌어도 LED·저항은 그대로 두고 급전선만 옮긴다.')
_E3_LED_NOTE_CHAIN = ('LED 는 두 개뿐이다(교안 p8). LED1 = 합/차(S·D), LED2 = 올림/내림(Co·Bo). '
                      '두 회로(전가산기·전감산기)에서 LED·저항·급전선 자리가 같다.')
_E3_XOR_UNUSED = ([4, 5, 9, 10, 12, 13], [6, 8, 11])      # 게이트 1 만 쓸 때
_E3_XOR2_UNUSED = ([9, 10, 12, 13], [8, 11])              # 게이트 1·2 를 쓸 때
_E3_NOT_UNUSED = ([3, 5, 9, 11, 13], [4, 6, 8, 10, 12])   # 인버터 1 만
_E3_NOT2_UNUSED = ([5, 9, 11, 13], [6, 8, 10, 12])        # 인버터 1·2


def _e3_frame(bb):
    """잭 + 레일 브리지 셋. 네 회로가 같은 홀을 쓴다 — 기준선 비교로 회색이 된다.

    끝점이 있는 레일만 잇는다: 좌 바깥(잭·입력·좌 칩 pin 7·LED1) → 우 중앙(우 칩
    pin 7·LED2) 이 GND 사슬이고, 좌 바깥(잭) → 좌 중앙(좌 칩 pin 14) → 우 바깥(우 칩
    pin 14) 이 VCC 사슬이다. 좌 중앙 GND 레일은 끝점이 없어 거치지 않는다 — 거치면
    따라 그릴 가닥만 는다(2026-09-15 조원 지적). 브리지는 레일을 건너뛸 수 있다 —
    VCC 34행도 우 중앙 레일을 건너 우 바깥으로 간다.
    """
    c, r = bb.cols['left'], bb.cols['right']
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], r['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')
    bb.bridge_rails(c['mid_vcc'], r['vcc'], 34, kind='vcc')


def _e3_draw(bb, circuit, stage):
    """네 회로의 공통 그리기. `circuit` 은 ha·fa·hs·fs, `stage` 는 1 또는 None(완성).

    실험실 사슬은 fa 1단계 → fa 완성 → fs 완성이다(2026-09-14 공지 `_350547_1`).
    1단계가 있는 회로는 맨바닥에서 시작하는 ha·fa 뿐이다. hs·fs 에 1단계를 주면
    거절한다 — 그 둘의 1단계는 반감산기를 거치던 옛 사슬의 차분이었다.

    같은 배선은 네 회로에서 같은 헬퍼를 같은 순서로 부른다 — 레일 착지 행이 점유
    순서로 정해지므로 순서가 다르면 같은 선이 다른 행에 앉아 기준선 비교가 깨진다.
    순서: S1 칩 → 프레임 → S1·S3 전원 → 입력 A·B(·Ci/Bi) → LED1 → 우측 AND 쪽
    → LED2 → S4 전원 → S2 전원.
    """
    if stage == 1 and circuit not in ('ha', 'fa'):
        raise ValueError(f'{circuit} 에는 1단계가 없다 — 사슬은 fa 1단계 → fa → fs 다')
    c, r = bb.cols['left'], bb.cols['right']
    L = bb.r_y
    full = circuit in ('fa', 'fs')
    sub = circuit in ('hs', 'fs')
    cin = 'Bi' if sub else 'Ci'
    sum_tag = 'D' if sub else 'S'
    # 반감산기 내림 수는 교안 p6 표기 그대로 입력과 같은 글자 B 다 — 회귀 그림 e3_hs 만 쓴다.
    carry_tag = {'ha': 'C', 'fa': 'Co', 'hs': 'B', 'fs': 'Bo'}[circuit]
    # 사슬(fa·fs)은 급전선이 옮겨지지 않는다 — 회귀 전용 완성본(ha·hs)만 옛 문구를 쓴다.
    led_note = _E3_LED_NOTE_CHAIN if full else _E3_LED_NOTE_REGRESSION
    done = stage != 1
    # 걷기 보드(ghost)는 앞 회로를 완성 상태로 그리지만 뽑을 두 가닥을 점유표에서 빼므로
    # 74HC08 pin 1·4 가 뜬다 — 그게 정상이라 생성자가 켜 둔 `partial` 을 도로 내리지 않는다
    bb.partial = not done or bb.ghost is not None

    # --- 좌 S1: XOR + 입력 + LED1 ---
    bb.draw_chip('74HC86', _E3_S1)
    _e3_frame(bb)
    bb.connect_power(_E3_S1, gnd_col='b')
    bb.connect_power(_E3_S3, block='right', gnd_col='a')
    _input_jumper(bb, c, 7, 'A', '74HC86 pin 1')
    _input_jumper(bb, c, 8, 'B', '74HC86 pin 2')
    if full:
        _input_jumper(bb, c, 11, cin, '74HC86 pin 5 (XOR2)')
        bb.step_wire([(c['c'], L(9)), (c['c'], L(10))], 'mid',
                     'XOR1 출력 A⊕B -> XOR2 입력 (pin 3 -> pin 4)', width=4,
                     marker_at=(c['c'] - 18, L(10) + 9))
    src_row, src_pin = (12, 6) if full else (9, 3)
    bb.step_wire([(c['b'], L(src_row)), (_E3_LANE, L(src_row)),
                  (_E3_LANE, L(_E3_LED1)), (c['a'], L(_E3_LED1))], 'sig',
                 f'{sum_tag} = 74HC86 pin {src_pin} -> LED1',
                 marker_at=(_E3_LANE + 13, L(19)))
    sum_desc = {'ha': 'S = A⊕B — 반가산기 진리표의 S 열', 'fa': 'S = A⊕B⊕Ci — 진리표 T3 의 S 열',
                'hs': 'D = A⊕B — 반감산기 진리표의 D 열', 'fs': 'D = A⊕B⊕Bi — 진리표 T7 의 D 열'}[circuit]
    bb.led_chain(c['a'], _E3_LED1, sum_tag, sum_desc, color_rgb=(210, 140, 0))

    if not done:
        # 1단계: XOR 쪽만. AND 자리(S3) 전원은 미리 꽂았고, LED2 사슬은 급전 없이 둔다
        bb.led_chain(r['c'], _E3_LED2, carry_tag, '아직 급전하지 않는다 — 2단계에서 잇는다',
                     block='right')
        xor_u = _E3_XOR2_UNUSED if full else _E3_XOR_UNUSED
        bb.mark_unused_inputs(xor_u[0], _E3_S1, chip='74HC86')
        bb.mark_unused_outputs(xor_u[1], _E3_S1, chip='74HC86')
        if full:
            bb.note('1단계: 74HC86 게이트 1·2 만 검사한다. LED1 = S = A⊕B⊕Ci 를 여덟 조합 전부 '
                    '본다 (입력에 1 이 홀수 개일 때만 켜짐). 우 10행 전원 두 가닥은 2단계의 '
                    '74HC08 자리다.')
        else:
            bb.note('1단계: 74HC86 게이트 1 만 검사한다. LED1 = S = A⊕B 를 네 조합 전부 본다 '
                    '(01·10 만 켜짐). 우 10행 전원 두 가닥은 2단계의 74HC08 자리다.')
        bb.note(led_note)
        bb.note(_E3_INPUT_NOTE)
        return

    # --- 우 S3: AND + 입력 갈래 ---
    bb.draw_chip('74HC08', _E3_S3, block='right')
    if not sub:
        # A 갈래: 좌 d7 에서 칩 위 4행으로 올려 우 a4 → a10. 감산기는 인버터가
        # 대신 pin 1 을 먹인다 — 전감산기 1단계가 걷는 두 가닥 중 하나다
        bb.step_wire([(c['d'], L(7)), (c['d'], L(4)), (r['a'], L(4)), (r['a'], L(10))], 'sig',
                     '입력 A 갈래 -> 74HC08 pin 1', width=2,
                     marker_at=(r['a'] - 14, L(7)))
    bb.step_wire([(c['c'], L(8)), (c['c'], L(5)), (r['b'], L(5)), (r['b'], L(11))], 'sig',
                 '입력 B 갈래 -> 74HC08 pin 2', width=2,
                 marker_at=(r['b'] + 14, L(8)))

    if sub:
        # --- 좌 S2: NOT. A → pin 1, A' → 우 AND pin 1 (440 차선으로 건넌다) ---
        bb.draw_chip('74HC04', _E3_S2)
        bb.step_wire([(c['d'], L(7)), (c['d'], L(_E3_S2))], 'sig',
                     '입력 A 갈래 -> 74HC04 pin 1', width=2,
                     marker_at=(c['d'] + 16, L(15)))
        bb.step_wire([(c['c'], L(_E3_S2 + 1)), (c['c'], L(17)), (_E3_LANE_A, L(17)),
                      (_E3_LANE_A, L(10)), (r['a'], L(10))], 'mid',
                     "A' (74HC04 pin 2) -> 74HC08 pin 1",
                     marker_at=(_E3_LANE_A - 14, L(13)))
        if circuit == 'fs':
            bb.step_wire([(c['a'], L(9)), (c['a'], L(_E3_S2 + 2))], 'mid',
                         'A⊕B (74HC86 pin 3) -> 74HC04 pin 3 (NOT2)',
                         marker_at=(c['a'] - 20, L(15)))
            bb.step_wire([(c['d'], L(_E3_S2 + 3)), (c['d'], L(25)), (_E3_LANE_X, L(25)),
                          (_E3_LANE_X, L(13)), (r['a'], L(13))], 'mid',
                         "(A⊕B)' (74HC04 pin 4) -> 74HC08 pin 4 (AND2)",
                         marker_at=(_E3_LANE_X + 14, L(20)))

    if full:
        if circuit == 'fa':
            bb.step_wire([(c['a'], L(9)), (c['a'], L(6)), (r['c'], L(6)), (r['c'], L(13))], 'mid',
                         'A⊕B (74HC86 pin 3) -> 74HC08 pin 4 (AND2)',
                         marker_at=(r['c'] + 14, L(8)))
        bb.step_wire([(c['c'], L(11)), (c['c'], L(14)), (r['a'], L(14))], 'sig',
                     f'입력 {cin} 갈래 -> 74HC08 pin 5 (AND2)', width=2,
                     marker_at=(c['j'] + 12, L(14) - 12))

    # --- 우 S4: OR (전가산기·전감산기) ---
    if full:
        bb.draw_chip('74HC32', _E3_S4, block='right')
        bb.step_wire([(r['d'], L(12)), (r['d'], L(_E3_S4 + 1))], 'mid',
                     'AND1 출력 (74HC08 pin 3) -> 74HC32 pin 2',
                     marker_at=(r['d'] + 16, L(18)))
        bb.step_wire([(r['b'], L(15)), (r['b'], L(_E3_S4))], 'mid',
                     'AND2 출력 (74HC08 pin 6) -> 74HC32 pin 1',
                     marker_at=(r['b'] - 16, L(18)))
        bb.step_wire([(r['c'], L(_E3_S4 + 2)), (r['c'], L(_E3_LED2))], 'sig',
                     f'{carry_tag} = 74HC32 pin 3 -> LED2',
                     marker_at=(r['c'] - 16, L(26)))
    else:
        bb.step_wire([(r['c'], L(12)), (r['c'], L(_E3_LED2))], 'sig',
                     f'{carry_tag} = 74HC08 pin 3 -> LED2',
                     marker_at=(r['c'] - 16, L(20)))
    carry_desc = {'ha': 'C = A·B — 반가산기 진리표의 C 열',
                  'fa': 'Co = A·B + (A⊕B)·Ci — 진리표 T3 의 Co 열',
                  'hs': "B = A'·B — 반감산기 진리표의 넷째 열 B (입력 B 와 같은 글자)",
                  'fs': "Bo = A'·B + (A⊕B)'·Bi — 진리표 T7 의 Bo 열"}[circuit]
    bb.led_chain(r['c'], _E3_LED2, carry_tag, carry_desc, block='right')

    # S4 전원: OR 을 쓰는 회로(전가산기·전감산기)만
    if full:
        bb.connect_power(_E3_S4, block='right')
    # S2 전원: 인버터를 쓰는 회로(반감산기·전감산기)만
    if sub:
        bb.connect_power(_E3_S2, gnd_col='a')

    # --- 미사용 핀 등록 ---
    xor_u = _E3_XOR2_UNUSED if full else _E3_XOR_UNUSED
    bb.mark_unused_inputs(xor_u[0], _E3_S1, chip='74HC86')
    bb.mark_unused_outputs(xor_u[1], _E3_S1, chip='74HC86')
    and_u = _E3_XOR2_UNUSED if full else _E3_XOR_UNUSED
    bb.mark_unused_inputs(and_u[0], _E3_S3, block='right', chip='74HC08')
    bb.mark_unused_outputs(and_u[1], _E3_S3, block='right', chip='74HC08')
    if full:
        bb.mark_unused_inputs(_E3_XOR_UNUSED[0], _E3_S4, block='right', chip='74HC32')
        bb.mark_unused_outputs(_E3_XOR_UNUSED[1], _E3_S4, block='right', chip='74HC32')
    if sub:
        not_u = _E3_NOT2_UNUSED if circuit == 'fs' else _E3_NOT_UNUSED
        bb.mark_unused_inputs(not_u[0], _E3_S2, chip='74HC04')
        bb.mark_unused_outputs(not_u[1], _E3_S2, chip='74HC04')
    bb.note(led_note)
    bb.note(_E3_INPUT_NOTE)


def build_e3_ha(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-1 · 반가산기 (74HC86 XOR + 74HC08 AND). 범위 밖 — 사슬에 없다. 2단계.

      stage 1  74HC86(S1) + LED1. S = A⊕B
      stage 2  + 74HC08(S3, 우측) + A·B 갈래 + LED2 = 완성. C = A·B
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    if stage == 1:
        title = "실험 1-1: 반가산기 — 1단계 (XOR, S = A⊕B)"
    elif baseline is None:
        title = "실험 1-1: 반가산기 결선도"
    else:
        title = "실험 1-1: 반가산기 — 2단계 (AND 추가, 완성)"
    bb.set_header(title, "74HC86 (XOR) 게이트 1 → S · 74HC08 (AND) 게이트 1 → C · LED 2개, 330Ω 2개",
                  submit=baseline is None)
    _e3_draw(bb, 'ha', stage)
    bb.export(output_path, max_row=36)
    return bb


def build_e3_fa(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-2 · 전가산기 (74HC86 ×2게이트 + 74HC08 ×2게이트 + 74HC32). netlist C2. 2단계.

    실험실 사슬의 첫 회로라 맨바닥에서 시작한다(반가산기는 조교 공지 `_350547_1` 로
    하지 않는다).

      stage 1  74HC86(S1) XOR1·XOR2 + A·B·Ci 입력 + LED1. S = A⊕B⊕Ci
      stage 2  + 74HC08(S3) AND1·AND2 + 74HC32(S4) OR · LED2 = Co = 완성
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    if stage == 1:
        title = "실험 1-2: 전가산기 — 1단계 (XOR 두 개, S = A⊕B⊕Ci)"
    elif baseline is None:
        title = "실험 1-2: 전가산기 결선도"
    else:
        title = "실험 1-2: 전가산기 — 2단계 (AND 두 개 + OR, 완성)"
    bb.set_header(title, "74HC86 XOR 2개 + 74HC08 AND 2개 + 74HC32 OR · Co = A·B + (A⊕B)·Ci",
                  submit=baseline is None)
    _e3_draw(bb, 'fa', stage)
    bb.export(output_path, max_row=36)
    return bb


def build_e3_hs(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-1 · 반감산기 (74HC86 XOR + 74HC04 NOT + 74HC08 AND). 범위 밖 — 사슬에 없다.

    조교 공지 `_350547_1` 로 실험실에서 하지 않는다. 완성본만 남는다 — 입력과 출력이
    같은 글자 `B` 인 유일한 회로라 가독성·손그림 테스트가 쓴다. 1단계는 없다
    (`_e3_draw` 가 거절한다).
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    title = "실험 2-1: 반감산기 결선도"
    bb.set_header(title, "74HC86 (XOR) → D · 74HC04 (NOT) + 74HC08 (AND) → 내림 수 B = A'·B (입력 B 와 같은 글자)",
                  submit=baseline is None)
    _e3_draw(bb, 'hs', stage)
    bb.export(output_path, max_row=36)
    return bb


def build_e3_fs(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-2 · 전감산기 (네 칩 전부). netlist C4. 걷기 보드(0단계) + 1단계.

    전가산기(C2) 완성 상태에서 바꾼다 — 0단계(걷기 보드)에서 AND1 pin 1 로 가던 A 갈래와
    AND2 pin 4 로 가던 A⊕B 선을 걷고, 1단계에서 74HC04 를 S2 에 꽂아 인버터를 거치게
    다시 꽂는다. Ci 점퍼는 그 자리 그대로 Bi 가 되고, LED 급전선 둘도 그대로다. 1단계가
    곧 완성이다 (`stage=1` 은 `_e3_draw` 가 거절한다). 걷기 보드는 `BOARDS` 의
    `removal_board(...)` 가 만든다 — 이 빌더에 `build_*` 래퍼는 없다.
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    if baseline is None:
        title = "실험 2-2: 전감산기 결선도"
    else:
        title = "실험 2-2: 전감산기 — 1단계 (74HC04 추가, 완성)"
    bb.set_header(title, "74HC86 XOR 2 + 74HC04 NOT 2 + 74HC08 AND 2 + 74HC32 OR · Bo = A'·B + (A⊕B)'·Bi",
                  submit=baseline is None)
    _e3_draw(bb, 'fs', stage)
    bb.export(output_path, max_row=36)
    return bb


# 절차 그림 사슬. 보드 n 의 기준선은 보드 n-1 의 배선이다 — 실험실에서 보드 위에
# 실제로 남아 있는 것. 첫 보드(C2 1단계)는 맨바닥에서 시작하므로 기준선이 없다.
# C2 → C4 경계에 걷기 보드(0단계)가 있다 — 2026-09-18 실험실에서 걷을 두 가닥이
# footer 표에만 있어 놓쳤다. 걷기 보드는 앞 회로가 전부 회색이고 뽑을 선만 빨간 점선이다.
BOARDS = [
    ("실험03_1-2_결선도_전가산기_1단계_XOR.png", build_e3_fa, 1),
    ("실험03_1-2_결선도_전가산기_2단계_Co경로.png", build_e3_fa, None),
    ("실험03_2-2_결선도_전감산기_0단계_걷기.png",
     removal_board((build_e3_fa, None), (build_e3_fs, None),
                   "실험 2-2: 전감산기 — 0단계 (전가산기에서 걷는 선 2가닥)",
                   "A→74HC08 pin 1 갈래와 A⊕B→74HC08 pin 4 를 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험03_2-2_결선도_전감산기_1단계_NOT.png", build_e3_fs, None),
]

# 완성본 — 기준선 없이 전부 색. 예비보고서에 싣고 손으로 따라 그리는 원도다.
FINALS = [
    ("실험03_1-2_결선도_전가산기.png", build_e3_fa),
    ("실험03_2-2_결선도_전감산기.png", build_e3_fs),
]


def _e3_baseline(index, template_path=None):
    """`BOARDS[index]` 의 기준선 = 바로 앞 보드의 `snapshot()`. 첫 보드는 None."""
    if index == 0:
        return None
    _name, fn, stage = BOARDS[index - 1]
    with tempfile.TemporaryDirectory() as d:
        return fn(os.path.join(d, 'prev.png'), template_path, stage=stage).snapshot()


def _e3_board(index, output_path, template_path=None):
    _name, fn, stage = BOARDS[index]
    return fn(output_path, template_path, stage=stage,
              baseline=_e3_baseline(index, template_path))


def build_e3_fa_s1(output_path, template_path=None):
    """C2 1단계 — 74HC86 XOR 두 개 + LED1. S = A⊕B⊕Ci 여덟 조합."""
    return _e3_board(0, output_path, template_path)


def build_e3_fa_s2(output_path, template_path=None):
    """C2 2단계 — 74HC08 AND 두 개와 74HC32 OR 을 더해 완성."""
    return _e3_board(1, output_path, template_path)


def build_e3_fs_s1(output_path, template_path=None):
    """C4 1단계 — 걷기 보드(0단계) 뒤에 74HC04 를 끼워 전감산기로 바꾼다. 완성."""
    return _e3_board(3, output_path, template_path)
