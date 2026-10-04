# 실험03 결선 — 엔진 `render_breadboard.py --experiment 3` 이
# 이 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를 뽑는다.
# 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.
import os
import tempfile

from render_breadboard import BreadboardRenderer, _input_jumper, removal_board

# 실험01~04 는 v1 판형으로 승인·도장이 끝났다 — 렌더러 기본값(v2)을 따르지 않게 못 박는다
BOARD = 'v1'


# 실험 3 · 가산기 & 감산기 — 2026-2 배포본(9쪽) 기준, 2026-09-14 저작
#
# 네 회로가 칩 네 종류(74HC86·74HC08·74HC32·74HC04)를 한 패키지씩 나눠 쓴다.
#
# 2026-09-14 조교 공지(`_350547_1`)로 실험실에서 하는 회로는 전가산기(C2)·전감산기(C4)
# 뿐이다. 사슬은 C2(맨바닥에서 5단계) → C4(2단계)이고, **선을 뽑는 자리마다 걷기 보드가
# 한 장씩** 끼어 보드가 열둘이다 — 단계마다 관측 노드 하나이고
# 새 신호선이 셋 이하다(2026-09-20 단계 세분화). 반가산기·반감산기
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

# 회로별 단계 수. `stage == _E3_STAGES[circuit]` 이면 완성 상태다(partial 이 아니다).
# fa 5단계·fs 2단계는 2026-09-20 단계 세분화 규약의 결과다 — 단계 하나가 관측 노드
# 하나를 세우고 새 신호선이 셋 이하다. hs 는 사슬 밖 회귀 그림이라 단계가 없다.
_E3_STAGES = {'ha': 2, 'fa': 5, 'fs': 2}

# 단계마다 보드 아래에 붙는 한 줄. 관측 노드와 급전선을 어디로 옮기는지 말한다.
# 걷는 것은 여기 적지 않는다 — 2026-09-20 걷기 보드 뒤로 뽑는 자리마다 전용 그림이
# 한 장 있고(`<k>걷기`), 이 노트가 같은 말을 또 하면 두 자리가 표류한다.
_E3_STAGE_NOTE = {
    ('fa', 1): '1단계: 74HC86 게이트 1 만 검사한다. LED1 급전선을 **임시로** pin 3 에 꽂아 '
               'A⊕B 를 A·B 네 조합으로 본다 (01·10 만 켜짐). 그 선은 다음 장(2걷기)이 '
               '뽑는다. 우 10행 전원 두 가닥은 3단계의 74HC08 자리다.',
    ('fa', 2): '2단계: 앞 장(2걷기)에서 임시 급전선을 뽑은 상태로 시작한다. XOR2 를 잇는다. '
               'LED1 = S = A⊕B⊕Ci 를 여덟 조합 전부 본다 (입력에 1 이 홀수 개일 때만 켜짐).',
    ('fa', 3): '3단계: 74HC08 의 AND1 만 검사한다. LED2 급전선을 **임시로** U2 pin 3 에 '
               '꽂아 A·B 를 네 조합으로 본다 (11 만 켜짐). 그 선은 다음 장(4걷기)이 뽑는다.',
    ('fa', 4): '4단계: 앞 장(4걷기)에서 뽑은 자리에 임시 급전선을 U2 pin 6 으로 옮겨 '
               '(A⊕B)·Ci 를 여덟 조합 전부 본다. 그 선은 다음 장(5걷기)이 뽑는다.',
    ('fa', 5): '5단계: 앞 장(5걷기)에서 임시 급전선을 뽑은 상태로 시작한다. 74HC32 를 꽂아 '
               '완성한다. LED1 = S 와 LED2 = Co 가 T3 8행에서 동시에 맞아야 한다.',
    ('fs', 1): "1단계: 74HC04 의 NOT1 만 꽂는다. LED2 급전선(1걷기에서 뽑은 것)을 **임시로** "
               "U2 pin 3 에 꽂아 A'·B 를 T7 8행으로 본다 (A=0·B=1 인 행만 켜짐). "
               "그 선은 다음 장(2걷기)이 뽑는다. LED1 은 내내 D 를 보인다.",
    ('fs', 2): "2단계: 앞 장(2걷기)에서 임시 급전선을 뽑은 상태로 시작한다. NOT2 와 LED2 "
               "최종 급전선을 잇는다 — 완성이다. LED1 = D 와 LED2 = Bo 가 T7 8행에서 "
               "동시에 맞아야 한다.",
    ('ha', 1): '1단계: 74HC86 게이트 1 만 검사한다. LED1 = S = A⊕B 를 네 조합 전부 본다 '
               '(01·10 만 켜짐). 우 10행 전원 두 가닥은 2단계의 74HC08 자리다.',
}

_E3_FA_TITLE = {
    1: "실험 1-2: 전가산기 — 1단계 (XOR1, 노드 A⊕B)",
    2: "실험 1-2: 전가산기 — 2단계 (XOR2, 노드 S)",
    3: "실험 1-2: 전가산기 — 3단계 (AND1, 노드 A·B)",
    4: "실험 1-2: 전가산기 — 4단계 (AND2, 노드 (A⊕B)·Ci)",
    5: "실험 1-2: 전가산기 — 5단계 (OR 추가, 노드 Co · 완성)",
}
_E3_FS_TITLE = {
    1: "실험 2-2: 전감산기 — 1단계 (74HC04 NOT1, 노드 A'·B)",
    2: "실험 2-2: 전감산기 — 2단계 (NOT2 추가, 노드 Bo · 완성)",
}


def _e3_stage_check(circuit, stage):
    """이 회로에 그 단계가 있는가. 빌더가 **제목 표를 찾기 전에** 먼저 부른다 —
    `_E3_FA_TITLE[6]` 의 KeyError 가 아니라 ValueError 로 나가야 한다."""
    if stage is None:
        return
    last = _E3_STAGES.get(circuit)
    if last is None or not 1 <= stage <= last:
        raise ValueError(f'{circuit} 에 {stage}단계는 없다 — 회로별 단계 수: {_E3_STAGES}')


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
    """네 회로의 공통 그리기. `circuit` 은 ha·fa·hs·fs, `stage` 는 1..N 또는 None(완성).

    **단계는 그리기 순서의 앞부분 자르기다.** 완성 경로(`stage is None`)의 호출 순서는
    한 줄도 바꾸지 않는다 — 레일 착지 행이 점유 순서로 정해지므로 순서가 바뀌면 완성본
    도장이 바뀌고 손그림 원도·예비보고서 그림이 어긋난다. `at()` 가 "이 배선이 이 보드에
    이미 꽂혀 있는가" 를, `only()`·`probe2` 가 "이 단계에만 있는 임시 급전선인가" 를 묻는다.

    LED 는 둘뿐이라(교안 p8) 중간 노드는 **그 시점에 비어 있는 LED 의 급전선을 그 핀으로
    잠시 옮겨** 본다. 여분 LED 를 더하지 않는다 — 완성본 결선도가 바뀌지 않는다.
    """
    _e3_stage_check(circuit, stage)
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

    def at(fa=1, fs=1, ha=1, hs=1):
        """이 배선이 이 보드에 이미 꽂혀 있는가 — 회로별 '처음 꽂히는 단계' 와 비교한다."""
        return stage is None or stage >= {'fa': fa, 'fs': fs, 'ha': ha, 'hs': hs}[circuit]

    def only(fa=None, fs=None, ha=None, hs=None):
        """**이 단계에서만** 꽂는 임시 급전선인가. 완성본(stage None)에는 없다."""
        return stage is not None and stage == {'fa': fa, 'fs': fs, 'ha': ha, 'hs': hs}[circuit]

    bb.partial = stage is not None and stage < _E3_STAGES[circuit]
    right_on = at(fa=3, fs=1, ha=2)       # 74HC08 이 꽂힌 뒤
    or_on = full and at(fa=5, fs=1)       # 74HC32 와 AND→OR 두 가닥 (C4 는 C2 에서 물려받는다)

    # --- 좌 S1: XOR + 입력 + LED1 ---
    bb.draw_chip('74HC86', _E3_S1)
    _e3_frame(bb)
    bb.connect_power(_E3_S1, gnd_col='b')
    bb.connect_power(_E3_S3, block='right', gnd_col='a')
    _input_jumper(bb, c, 7, 'A', '74HC86 pin 1')
    _input_jumper(bb, c, 8, 'B', '74HC86 pin 2')
    if full and at(fa=2):
        _input_jumper(bb, c, 11, cin, '74HC86 pin 5 (XOR2)')
        bb.step_wire([(c['c'], L(9)), (c['c'], L(10))], 'mid',
                     'XOR1 출력 A⊕B -> XOR2 입력 (pin 3 -> pin 4)', width=4,
                     marker_at=(c['c'] - 18, L(10) + 9))
    if only(fa=1):
        # 임시 프로브 — LED1 을 XOR1 출력에 물려 A⊕B 를 본다. 그 선은 다음 장(`2걷기`)이 뽑는다
        bb.step_wire([(c['b'], L(9)), (_E3_LANE, L(9)),
                      (_E3_LANE, L(_E3_LED1)), (c['a'], L(_E3_LED1))], 'sig',
                     '임시 급전: A⊕B = 74HC86 pin 3 -> LED1 (다음 장 2걷기에서 뽑는다)',
                     marker_at=(_E3_LANE + 13, L(17)))
    elif at(fa=2):
        src_row, src_pin = (12, 6) if full else (9, 3)
        bb.step_wire([(c['b'], L(src_row)), (_E3_LANE, L(src_row)),
                      (_E3_LANE, L(_E3_LED1)), (c['a'], L(_E3_LED1))], 'sig',
                     f'{sum_tag} = 74HC86 pin {src_pin} -> LED1',
                     marker_at=(_E3_LANE + 13, L(19)))
    sum_desc = {'ha': 'S = A⊕B — 반가산기 진리표의 S 열', 'fa': 'S = A⊕B⊕Ci — 진리표 T3 의 S 열',
                'hs': 'D = A⊕B — 반감산기 진리표의 D 열', 'fs': 'D = A⊕B⊕Bi — 진리표 T7 의 D 열'}[circuit]
    if only(fa=1):
        sum_desc = '1단계에는 A⊕B 를 본다 — 임시 급전선은 다음 장(2걷기)이 뽑는다'
    bb.led_chain(c['a'], _E3_LED1, sum_tag, sum_desc, color_rgb=(210, 140, 0))

    # --- 우 S3: AND + 입력 갈래 ---
    if right_on:
        bb.draw_chip('74HC08', _E3_S3, block='right')
        if not sub:
            # A 갈래: 좌 d7 에서 칩 위 4행으로 올려 우 a4 → a10. 감산기는 인버터가
            # 대신 pin 1 을 먹인다 — 전감산기 `1걷기` 보드가 걷는 세 가닥 중 하나다
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
        if circuit == 'fs' and at(fs=2):
            bb.step_wire([(c['a'], L(9)), (c['a'], L(_E3_S2 + 2))], 'mid',
                         'A⊕B (74HC86 pin 3) -> 74HC04 pin 3 (NOT2)',
                         marker_at=(c['a'] - 20, L(15)))
            bb.step_wire([(c['d'], L(_E3_S2 + 3)), (c['d'], L(25)), (_E3_LANE_X, L(25)),
                          (_E3_LANE_X, L(13)), (r['a'], L(13))], 'mid',
                         "(A⊕B)' (74HC04 pin 4) -> 74HC08 pin 4 (AND2)",
                         marker_at=(_E3_LANE_X + 14, L(20)))

    if full:
        if circuit == 'fa' and at(fa=4):
            bb.step_wire([(c['a'], L(9)), (c['a'], L(6)), (r['c'], L(6)), (r['c'], L(13))], 'mid',
                         'A⊕B (74HC86 pin 3) -> 74HC08 pin 4 (AND2)',
                         marker_at=(r['c'] + 14, L(8)))
        if at(fa=4, fs=1):
            bb.step_wire([(c['c'], L(11)), (c['c'], L(14)), (r['a'], L(14))], 'sig',
                         f'입력 {cin} 갈래 -> 74HC08 pin 5 (AND2)', width=2,
                         marker_at=(c['j'] + 12, L(14) - 12))

    # --- 우 S4: OR (전가산기·전감산기) ---
    if or_on:
        bb.draw_chip('74HC32', _E3_S4, block='right')
        bb.step_wire([(r['d'], L(12)), (r['d'], L(_E3_S4 + 1))], 'mid',
                     'AND1 출력 (74HC08 pin 3) -> 74HC32 pin 2',
                     marker_at=(r['d'] + 16, L(18)))
        bb.step_wire([(r['b'], L(15)), (r['b'], L(_E3_S4))], 'mid',
                     'AND2 출력 (74HC08 pin 6) -> 74HC32 pin 1',
                     marker_at=(r['b'] - 16, L(18)))
    # LED2 급전 — 완성본은 최종 출력, 그 전 단계는 관측 노드에서 뽑는 임시 프로브다.
    # 우 c 열을 세로로 내려가는 한 가닥이라 셋 다 같은 꼴이다(ha·hs 완성본과도 같다).
    probe2 = {('fa', 3): (12, 'A·B = 74HC08 pin 3'),
              ('fa', 4): (15, '(A⊕B)·Ci = 74HC08 pin 6'),
              ('fs', 1): (12, "A'·B = 74HC08 pin 3")}.get((circuit, stage))
    if probe2 is not None:
        bb.step_wire([(r['c'], L(probe2[0])), (r['c'], L(_E3_LED2))], 'sig',
                     f'임시 급전: {probe2[1]} -> LED2 (다음 장 걷기에서 뽑는다)',
                     marker_at=(r['c'] - 16, L(20)))
    elif full and at(fa=5, fs=2):
        bb.step_wire([(r['c'], L(_E3_S4 + 2)), (r['c'], L(_E3_LED2))], 'sig',
                     f'{carry_tag} = 74HC32 pin 3 -> LED2',
                     marker_at=(r['c'] - 16, L(26)))
    elif not full and at(ha=2):
        bb.step_wire([(r['c'], L(12)), (r['c'], L(_E3_LED2))], 'sig',
                     f'{carry_tag} = 74HC08 pin 3 -> LED2',
                     marker_at=(r['c'] - 16, L(20)))
    carry_desc = {'ha': 'C = A·B — 반가산기 진리표의 C 열',
                  'fa': 'Co = A·B + (A⊕B)·Ci — 진리표 T3 의 Co 열',
                  'hs': "B = A'·B — 반감산기 진리표의 넷째 열 B (입력 B 와 같은 글자)",
                  'fs': "Bo = A'·B + (A⊕B)'·Bi — 진리표 T7 의 Bo 열"}[circuit]
    if probe2 is not None:
        carry_desc = f'이 단계에는 {probe2[1]} 을 본다 — 임시 급전선은 다음 장(걷기)이 뽑는다'
    elif not at(fa=5, fs=2, ha=2):
        carry_desc = '아직 급전하지 않는다 — 다음 단계에서 잇는다'
    bb.led_chain(r['c'], _E3_LED2, carry_tag, carry_desc, block='right')

    # S4 전원: OR 을 쓰는 회로(전가산기·전감산기)만
    if or_on:
        bb.connect_power(_E3_S4, block='right')
    # S2 전원: 인버터를 쓰는 회로(반감산기·전감산기)만
    if sub:
        bb.connect_power(_E3_S2, gnd_col='a')

    # --- 미사용 핀 등록 --- (그 단계에 실제로 쓰는 게이트만 사용으로 본다)
    xor_u = _E3_XOR2_UNUSED if (full and at(fa=2)) else _E3_XOR_UNUSED
    bb.mark_unused_inputs(xor_u[0], _E3_S1, chip='74HC86')
    bb.mark_unused_outputs(xor_u[1], _E3_S1, chip='74HC86')
    if right_on:
        and_u = _E3_XOR2_UNUSED if (full and at(fa=4)) else _E3_XOR_UNUSED
        bb.mark_unused_inputs(and_u[0], _E3_S3, block='right', chip='74HC08')
        bb.mark_unused_outputs(and_u[1], _E3_S3, block='right', chip='74HC08')
    if or_on:
        bb.mark_unused_inputs(_E3_XOR_UNUSED[0], _E3_S4, block='right', chip='74HC32')
        bb.mark_unused_outputs(_E3_XOR_UNUSED[1], _E3_S4, block='right', chip='74HC32')
    if sub:
        not_u = _E3_NOT2_UNUSED if (circuit == 'fs' and at(fs=2)) else _E3_NOT_UNUSED
        bb.mark_unused_inputs(not_u[0], _E3_S2, chip='74HC04')
        bb.mark_unused_outputs(not_u[1], _E3_S2, chip='74HC04')
    # 단계 노트는 **이 보드에서 무엇을 꽂는지** 를 말한다. 걷기 보드는 앞 회로를 그 단계로
    # 다시 그려 만들므로(`removal_board` 가 유령선을 얹는다) 그대로 두면 걷기 종이에
    # "5단계: … 74HC32 를 꽂아 완성한다" 가 찍힌다 — netlist 걷기 행("새로 꽂는 것은 없다")
    # 과 SKILL 의 "새 선도 순서표도 없다" 와 같은 면에서 부딪힌다. 유령 렌더면 건너뛴다.
    # 완성 경로(`stage is None`)는 애초에 노트가 없어 도장이 움직이지 않는다.
    note = None if bb.ghost is not None else _E3_STAGE_NOTE.get((circuit, stage))
    if note:
        bb.note(note)
    bb.note(led_note)
    bb.note(_E3_INPUT_NOTE)


def build_e3_ha(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-1 · 반가산기 (74HC86 XOR + 74HC08 AND). 범위 밖 — 사슬에 없다. 2단계.

      stage 1  74HC86(S1) + LED1. S = A⊕B
      stage 2  + 74HC08(S3, 우측) + A·B 갈래 + LED2 = 완성. C = A·B
    """
    bb = BreadboardRenderer(template_path, baseline=baseline, board=BOARD)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    if stage == 1:
        title = "실험 1-1: 반가산기 — 1단계 (XOR, S = A⊕B)"
    elif baseline is None:
        title = "실험 1-1: 반가산기 결선도"
    else:
        title = "실험 1-1: 반가산기 — 2단계 (AND 추가, 완성)"
    bb.set_header(title, "74HC86 (XOR) 게이트 1 → S · 74HC08 (AND) 게이트 1 → C · LED 2개, 330Ω 2개",
                  submit=baseline is None and stage is None)
    _e3_draw(bb, 'ha', stage)
    bb.export(output_path, max_row=36)
    return bb


def build_e3_fa(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-2 · 전가산기 (74HC86 ×2게이트 + 74HC08 ×2게이트 + 74HC32). netlist C2. 5단계.

    실험실 사슬의 첫 회로라 맨바닥에서 시작한다(반가산기는 조교 공지 `_350547_1` 로
    하지 않는다). 단계마다 관측 노드 하나이고 새 신호선이 셋이다 — 1·3·4단계는 LED
    급전선을 그 노드 핀으로 잠시 옮겨 보고, 그 선을 뽑는 일은 전용 걷기 보드
    (2걷기·4걷기·5걷기)가 지시한다.

      stage 1  74HC86(S1) XOR1 + A·B 입력 + LED1·LED2 사슬 + 임시 급전(pin 3). A⊕B
      stage 2  + Ci·pin3→pin4·pin6→LED1. S = A⊕B⊕Ci
      stage 3  + 74HC08(S3) AND1 (A·B 갈래) + 임시 급전(U2 pin 3). A·B
      stage 4  + AND2 (A⊕B·Ci 입력) + 임시 급전(U2 pin 6). (A⊕B)·Ci
      stage 5  + 74HC32(S4) OR + LED2 최종 급전 = 완성. Co
    """
    bb = BreadboardRenderer(template_path, baseline=baseline, board=BOARD)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    _e3_stage_check('fa', stage)
    # 손그림 제출 배너는 **완성본에만** 붙인다. 맨바닥에서 시작하는 첫 단계는
    # `baseline is None` 이라 옛 조건(`baseline is None`)으로는 배너를 달았는데,
    # 2026-09-20 단계 세분화 뒤 그 보드는 다음 단계에서 뽑을 임시 급전선이 붙은
    # 프로브 보드다 — 그것을 베껴 제출하면 틀린 그림을 낸다. 따라 그릴 원도는
    # `FINALS`(stage None) 뿐이다.
    title = _E3_FA_TITLE[stage] if stage is not None else "실험 1-2: 전가산기 결선도"
    bb.set_header(title, "74HC86 XOR 2개 + 74HC08 AND 2개 + 74HC32 OR · Co = A·B + (A⊕B)·Ci",
                  submit=baseline is None and stage is None)
    _e3_draw(bb, 'fa', stage)
    bb.export(output_path, max_row=36)
    return bb


def build_e3_hs(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-1 · 반감산기 (74HC86 XOR + 74HC04 NOT + 74HC08 AND). 범위 밖 — 사슬에 없다.

    조교 공지 `_350547_1` 로 실험실에서 하지 않는다. 완성본만 남는다 — 입력과 출력이
    같은 글자 `B` 인 유일한 회로라 가독성·손그림 테스트가 쓴다. 1단계는 없다
    (`_e3_draw` 가 거절한다).
    """
    bb = BreadboardRenderer(template_path, baseline=baseline, board=BOARD)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    title = "실험 2-1: 반감산기 결선도"
    bb.set_header(title, "74HC86 (XOR) → D · 74HC04 (NOT) + 74HC08 (AND) → 내림 수 B = A'·B (입력 B 와 같은 글자)",
                  submit=baseline is None and stage is None)
    _e3_draw(bb, 'hs', stage)
    bb.export(output_path, max_row=36)
    return bb


def build_e3_fs(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-2 · 전감산기 (네 칩 전부). netlist C4. 1걷기 보드 + 2단계(2걷기가 끼어 있다).

    전가산기(C2) 완성 상태에서 바꾼다 — 1걷기 보드에서 세 가닥을 뽑는다:
    AND1 pin 1 로 가던 A 갈래, AND2 pin 4 로 가던 A⊕B, 그리고 LED2 최종 급전선이다.
    마지막 것은 1단계에서 프로브가 된다(Bo 는 아직 뜻이 없다). `Ci` 점퍼는 그 자리
    그대로 `Bi` 가 되고 LED1 급전선도 그대로라 LED1 은 내내 D 를 보인다.

      stage 1  74HC04(S2) NOT1 + A→pin1·A'→U2 pin1 + 임시 급전(U2 pin 3). A'·B
      stage 2  + NOT2 (A⊕B→pin3, (A⊕B)'→U2 pin4) + LED2 최종 급전 = 완성. Bo

    걷기 보드는 `BOARDS` 의 `removal_board(...)` 가 만든다 — 이 빌더에 `build_*`
    래퍼는 없다. 1단계 앞(1걷기)과 2단계 앞(2걷기) 둘이다.
    """
    bb = BreadboardRenderer(template_path, baseline=baseline, board=BOARD)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    _e3_stage_check('fs', stage)
    title = _E3_FS_TITLE[stage] if stage is not None else "실험 2-2: 전감산기 결선도"
    bb.set_header(title, "74HC86 XOR 2 + 74HC04 NOT 2 + 74HC08 AND 2 + 74HC32 OR · Bo = A'·B + (A⊕B)'·Bi",
                  submit=baseline is None and stage is None)
    _e3_draw(bb, 'fs', stage)
    bb.export(output_path, max_row=36)
    return bb


# 절차 그림 사슬. 보드 n 의 기준선은 보드 n-1 의 배선이다 — 실험실에서 보드 위에
# 실제로 남아 있는 것. 첫 보드(C2 1단계)는 맨바닥에서 시작하므로 기준선이 없다.
#
# **선을 뽑는 자리마다 걷기 전용 보드가 한 장**이다 (2026-09-20 걷기 보드). 앞 상태가
# 전부 회색이고 뽑을 선만 빨간 점선 + 걷기 번호이며 새 선도 순서표도 없다. 회로 경계
# (C2 → C4)뿐 아니라 회로 **안**의 임시 프로브 급전선도 같다 — 2026-09-18 실험실에서
# 걷을 가닥이 footer 표에 글로만 있어 놓쳤고, 그것이 걷기 보드를 만든 근거였는데
# 회로 안의 뽑기를 바로 그 표로 보내고 있었다.
#
# C2 2단계 → 3단계에는 걷기 보드가 없다 — 그 전환은 걷는 선이 없다
# (`removal_board` 가 걷을 배선이 없으면 스스로 ValueError 로 거절한다).
BOARDS = [
    ("실험03_1-2_결선도_전가산기_1단계_XOR1.png", build_e3_fa, 1),
    ("실험03_1-2_결선도_전가산기_2걷기_LED1프로브.png",
     removal_board((build_e3_fa, 1), (build_e3_fa, 2),
                   "실험 1-2: 전가산기 — 2단계 걷기 (임시 급전선 1가닥)",
                   "A⊕B → LED1 임시 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험03_1-2_결선도_전가산기_2단계_S.png", build_e3_fa, 2),
    ("실험03_1-2_결선도_전가산기_3단계_AND1.png", build_e3_fa, 3),
    ("실험03_1-2_결선도_전가산기_4걷기_LED2프로브.png",
     removal_board((build_e3_fa, 3), (build_e3_fa, 4),
                   "실험 1-2: 전가산기 — 4단계 걷기 (임시 급전선 1가닥)",
                   "A·B → LED2 임시 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험03_1-2_결선도_전가산기_4단계_AND2.png", build_e3_fa, 4),
    ("실험03_1-2_결선도_전가산기_5걷기_LED2프로브.png",
     removal_board((build_e3_fa, 4), (build_e3_fa, 5),
                   "실험 1-2: 전가산기 — 5단계 걷기 (임시 급전선 1가닥)",
                   "(A⊕B)·Ci → LED2 임시 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험03_1-2_결선도_전가산기_5단계_Co.png", build_e3_fa, 5),
    ("실험03_2-2_결선도_전감산기_1걷기_세가닥.png",
     removal_board((build_e3_fa, 5), (build_e3_fs, 1),
                   "실험 2-2: 전감산기 — 1단계 걷기 (전가산기에서 걷는 선 3가닥)",
                   "A→74HC08 pin 1 갈래 · A⊕B→74HC08 pin 4 · LED2 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험03_2-2_결선도_전감산기_1단계_NOT.png", build_e3_fs, 1),
    ("실험03_2-2_결선도_전감산기_2걷기_LED2프로브.png",
     removal_board((build_e3_fs, 1), (build_e3_fs, 2),
                   "실험 2-2: 전감산기 — 2단계 걷기 (임시 급전선 1가닥)",
                   "A'·B → LED2 임시 급전선을 뽑는다 · 회색은 그대로 둔다"),
     None),
    ("실험03_2-2_결선도_전감산기_2단계_Bo.png", build_e3_fs, 2),
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
    """C2 1단계 — 74HC86 XOR1 + LED1 임시 급전. 노드 A⊕B."""
    return _e3_board(0, output_path, template_path)


def build_e3_fa_s2(output_path, template_path=None):
    """C2 2단계 — 2걷기 뒤에 Ci 와 XOR2 를 잇는다. 노드 S."""
    return _e3_board(2, output_path, template_path)


def build_e3_fa_s3(output_path, template_path=None):
    """C2 3단계 — 74HC08 AND1 + LED2 임시 급전. 노드 A·B."""
    return _e3_board(3, output_path, template_path)


def build_e3_fa_s4(output_path, template_path=None):
    """C2 4단계 — 4걷기 뒤에 AND2 입력 둘 + LED2 임시 급전. 노드 (A⊕B)·Ci."""
    return _e3_board(5, output_path, template_path)


def build_e3_fa_s5(output_path, template_path=None):
    """C2 5단계 — 5걷기 뒤에 74HC32 OR 과 LED2 최종 급전. 노드 Co, 완성."""
    return _e3_board(7, output_path, template_path)


def build_e3_fs_s1(output_path, template_path=None):
    """C4 1단계 — 1걷기 보드 뒤에 74HC04 NOT1 을 끼운다. 노드 A'·B."""
    return _e3_board(9, output_path, template_path)


def build_e3_fs_s2(output_path, template_path=None):
    """C4 2단계 — 2걷기 뒤에 NOT2 와 LED2 최종 급전. 노드 Bo, 완성."""
    return _e3_board(11, output_path, template_path)
