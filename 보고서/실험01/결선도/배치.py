# 실험01 결선 — 엔진 `render_breadboard.py --experiment 1` 이
# 이 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를 뽑는다.
# 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.
import os
import tempfile

from render_breadboard import BreadboardRenderer, _input_jumper


# 실험 1 · 기본 게이트 — 슬롯 고정 배치
#
# 다섯 회로가 칩 자리를 공유한다 (`docs/plans/2026-09-12-결선도-단계화-슬롯고정-설계.md`).
# 정본은 netlist 의 `kind: layout` 표이고 이 상수는 그 사본이다 —
# `tests/test_breadboard_wiring.py` 가 둘을 맞댄다.
#
#   S1 좌 7행  : C1 74HC08 · C2 74HC32 · C3 74HC08 · C4 74HC32 · C5 74HC04
#   S2 좌 18행 : C3 74HC00 · C4 74HC02 · C5 74HC08
#   S3 우 10행 : C5 74HC32
#
# 입력 A 는 b7, B 는 b8(C1~C4)/b19(C5). 중간단 L1 은 c9→c14 갈래 + c14 사슬.
# 최종 L2(C5 에서는 Z) 는 a25 사슬 — 다섯 회로가 같은 사슬을 쓴다.
# 실험실 기록(2026-09-11): 1-1→1-2 는 칩만 갈아끼우면 되는데 그림이 회로마다
# 달라 전부 걷었다. 같은 홀을 쓰면 기준선 비교로 그 사실이 그림에 보인다.
E1_SLOTS = {'S1': ('left', 7), 'S2': ('left', 18), 'S3': ('right', 10)}
_S1, _S2, _S3 = E1_SLOTS['S1'][1], E1_SLOTS['S2'][1], E1_SLOTS['S3'][1]
_E1_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
                  '빨간 +5V 레일로 옮겨 꽂는다. 띄워두지 않는다.')


def _e1_frame(bb):
    """잭 + 좌측 레일 브리지. 다섯 회로가 같은 홀을 쓴다 — 기준선 비교로 회색이 된다."""
    c = bb.cols['left']
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')


def _e1_front(bb, chip, op):
    """S1 칩 + 전원 + 입력 A·B + 중간단 L1. C1~C4 의 공통 앞단.

    L1 갈래는 c9 에서 곧게 내린다 — a 열은 C3·C4 의 칩 사이 연결(a9→a18/a19)이,
    d 열은 C1·C2 의 pin 3→4 점퍼(d9→d10)가, b 열은 입력 끝점이 쓴다.
    """
    c = bb.cols['left']
    bb.draw_chip(chip, _S1)
    _e1_frame(bb)
    bb.connect_power(_S1)
    _input_jumper(bb, c, 7, 'A', f'{chip} pin 1')
    _input_jumper(bb, c, 8, 'B', f'{chip} pin 2')
    bb.step_wire([(c['c'], bb.r_y(9)), (c['c'], bb.r_y(14))], 'mid',
                 '중간단 확인용 갈래', width=2, marker_at=(c['c'] + 18, bb.r_y(11)))
    bb.led_chain(c['c'], 14, "L1", f"중간단 A{op}B — 켜지는지 눈으로만 본다",
                 color_rgb=(210, 140, 0))


def _e1_single(bb, chip, op):
    """C1·C2 — 한 칩 2단 캐스케이드. 최종 L2 급전은 a12→a25 (a 열만 비어 있다)."""
    c = bb.cols['left']
    _e1_front(bb, chip, op)
    bb.step_wire([(c['d'], bb.r_y(9)), (c['d'], bb.r_y(10))], 'mid',
                 f'1단 출력 A{op}B -> 2단 입력 (pin 3 -> pin 4)', width=4,
                 marker_at=(c['d'] - 18, bb.r_y(10) + 9))
    _input_jumper(bb, c, 11, 'C', f'{chip} pin 5')
    bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(25))], 'sig',
                 '최종 출력 pin 6 -> L2', marker_at=(c['a'] - 20, bb.r_y(20)))
    bb.led_chain(c['a'], 25, "L2", f"최종 출력 L2 = A{op}B{op}C — 진리표 검증 대상")
    bb.mark_unused_inputs([9, 10, 12, 13], _S1, chip=chip)
    bb.mark_unused_outputs([8, 11], _S1, chip=chip)
    bb.note(_E1_INPUT_NOTE)


def build_e1_and(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-1 · 3입력 AND (74HC08 2단 캐스케이드). netlist C1. 단계 없음 — 첫 보드다."""
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    bb.set_header("실험 1-1: 3-Input AND Gate 결선도",
                  "74HC08 (Quad 2-Input AND) 한 개를 2단으로 · LED 마다 330Ω 직렬",
                  submit=baseline is None)
    _e1_single(bb, "74HC08", "·")
    bb.export(output_path, max_row=31)
    return bb


def build_e1_or(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-2 · 3입력 OR (74HC32). netlist C2. C1 과 배선이 같다 — 칩만 바꾼다.

    Nexperia 74HC32 Rev. 10 (2025-04-30) §5.2: `1A~4A = 1,4,9,12` / `1B~4B =
    2,5,10,13` / `1Y~4Y = 3,6,8,11` / GND 7 / VCC 14 — 74HC08 과 같은 배치다.
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    bb.set_header("실험 1-2: 3-Input OR Gate 결선도" if baseline is None
                  else "실험 1-2: 3-Input OR — 1단계 (칩 교체)",
                  "74HC32 (Quad 2-Input OR) 한 개를 2단으로 · C1 과 배선이 같다",
                  submit=baseline is None)
    _e1_single(bb, "74HC32", "+")
    bb.export(output_path, max_row=31)
    return bb


def _e1_two_chip(bb, front, back, op, stage, back_in_row, back_in_label,
                 c_row, c_pin, out_row, out_col, back_unused_in, back_unused_out):
    """C3·C4 — 앞단(S1) + 뒷단(S2).

    stage 1 은 앞단만 검사한다: L1 = A{op}B 네 조합. 뒷단 전원 점퍼는 이때
    미리 꽂는다 — 회로가 바뀌어도 그 두 가닥은 그대로다. L2 사슬은 남겨 두고
    급전선만 걷는다(기준선 비교가 그 사실을 그림에 적는다).
    """
    c = bb.cols['left']
    _e1_front(bb, front, op)
    bb.connect_power(_S2)
    bb.mark_unused_inputs([4, 5, 9, 10, 12, 13], _S1, chip=front)
    bb.mark_unused_outputs([6, 8, 11], _S1, chip=front)
    if stage == 1:
        bb.partial = True
        bb.led_chain(c['a'], 25, "L2", "아직 급전하지 않는다 — 2단계에서 잇는다")
        bb.note(f'1단계: {front} 게이트1 만 검사한다. L1 = A{op}B 를 네 조합 전부 본다.')
        bb.note(_E1_INPUT_NOTE)
        return
    bb.draw_chip(back, _S2)
    bb.step_wire([(c['a'], bb.r_y(9)), (c['a'], bb.r_y(back_in_row))], 'mid',
                 f'A{op}B -> {back} {back_in_label} (칩 사이 연결)',
                 marker_at=(c['a'] - 20, bb.r_y(13)))
    _input_jumper(bb, c, c_row, 'C', f'{back} pin {c_pin}', marker=(215, +13))
    bb.step_wire([(c[out_col], bb.r_y(out_row)), (c[out_col], bb.r_y(25))], 'sig',
                 f'최종 출력 {back} -> L2', marker_at=(c[out_col] + 18, bb.r_y(22)))
    bb.led_chain(c['a'], 25, "L2", f"최종 출력 L2 = (A{op}B{op}C)' — 진리표 검증 대상")
    bb.mark_unused_inputs(back_unused_in, _S2, chip=back)
    bb.mark_unused_outputs(back_unused_out, _S2, chip=back)
    bb.note(_E1_INPUT_NOTE)


def build_e1_nand(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-1 · 3입력 NAND (74HC08 앞단 + 74HC00 뒷단). netlist C3. 2단계."""
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    if stage == 1:
        title = "실험 2-1: 3-Input NAND — 1단계 (앞단 AND 검사)"
    elif baseline is None:
        title = "실험 2-1: 3-Input NAND Gate 결선도"
    else:
        title = "실험 2-1: 3-Input NAND — 2단계 (뒷단 NAND, 완성)"
    bb.set_header(title, "74HC08 (AND 앞단) + 74HC00 (NAND 뒷단) · LED 마다 330Ω 직렬",
                  submit=baseline is None)
    # 74HC00 게이트1: 1,2 -> 3. 출력 pin 3 은 20행이고 a 열이 비어 있다
    _e1_two_chip(bb, "74HC08", "74HC00", "·", stage,
                 back_in_row=18, back_in_label="pin 1", c_row=19, c_pin=2,
                 out_row=20, out_col='a',
                 back_unused_in=[4, 5, 9, 10, 12, 13], back_unused_out=[6, 8, 11])
    bb.export(output_path, max_row=31)
    return bb


def build_e1_nor(output_path, template_path=None, stage=None, baseline=None):
    """실험 2-2 · 3입력 NOR (74HC32 앞단 + 74HC02 뒷단). netlist C4. 2단계.

    **74HC02 는 출력이 1번 핀이다** (2,3 -> 1). A+B 는 pin 2(19행), C 는 pin 3
    (20행), 출력 pin 1(18행)은 c 열로 내린다 — a 열은 a9→a19 가 지난다.
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    if stage == 1:
        title = "실험 2-2: 3-Input NOR — 1단계 (앞단 OR 검사)"
    elif baseline is None:
        title = "실험 2-2: 3-Input NOR Gate 결선도"
    else:
        title = "실험 2-2: 3-Input NOR — 2단계 (뒷단 NOR, 완성)"
    bb.set_header(title, "74HC32 (OR 앞단) + 74HC02 (NOR 뒷단) · 74HC02 는 출력이 1번 핀",
                  submit=baseline is None)
    _e1_two_chip(bb, "74HC32", "74HC02", "+", stage,
                 back_in_row=19, back_in_label="pin 2 (1번 아님!)", c_row=20, c_pin=3,
                 out_row=18, out_col='c',
                 back_unused_in=[5, 6, 8, 9, 11, 12], back_unused_out=[4, 10, 13])
    bb.note('74HC02 는 핀 배치가 다르다 — 입력이 2·3 / 5·6 / 8·9 / 11·12, 출력이 1·4·10·13. '
            '나머지 넷과 반대다.')
    bb.export(output_path, max_row=31)
    return bb


def build_e1_comb(output_path, template_path=None, stage=None, baseline=None):
    """실험 3 · 복합 논리회로. netlist C5. 칩 하나 = 단계 하나.

      stage 1  74HC04(S1) + Z LED. pin 3 은 임시로 입력 A 에서(c7→c9) — Z = A'
      stage 2  + 74HC08(S2). 임시 점퍼를 걷고 A'·B 경로 — Z = (A'·B)'
      stage 3  + 74HC32(S3) + X·Y LED = 완성. X ≡ Z 자체 검산

    Z LED 는 앞 회로들의 L2 사슬(a25) 그대로다. 전원·브리지는 세 슬롯 전부
    1단계에서 꽂는다 — 회로가 바뀌어도 그대로인 선이다.
    """
    st = 3 if stage is None else stage
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    bb.partial = st < 3
    title = {1: "실험 3: 복합 논리회로 — 1단계 (인버터, Z = A')",
             2: "실험 3: 복합 논리회로 — 2단계 (AND 추가, Z = (A'·B)')",
             3: "실험 3: 복합 논리회로 결선도 (X, Y, Z 동시 관찰)" if baseline is None
                else "실험 3: 복합 논리회로 — 3단계 (OR 추가, 완성)"}[st]
    bb.set_header(title, "74HC04 (NOT) + 74HC08 (AND) + 74HC32 (OR) · LED 3개 · 330Ω 3개",
                  submit=baseline is None)
    c, r = bb.cols['left'], bb.cols['right']

    bb.draw_chip("74HC04", _S1)
    _e1_frame(bb)
    bb.connect_power(_S1)
    bb.connect_power(_S2)
    # 우측 블록 레일. 31행은 좌우 중앙GND 브리지가, 33·34행은 우측 바깥 레일이
    # 쓴다 — 30행에 두면 우 a30·c30(Y 사슬 저항 아래) 위를 지난다 (R3)
    bb.bridge_rails(c['mid_gnd'], r['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(r['mid_gnd'], r['gnd'], 33, kind='gnd')
    bb.bridge_rails(c['mid_vcc'], r['vcc'], 34, kind='vcc')
    bb.connect_power(_S3, block='right')
    _input_jumper(bb, c, 7, 'A', '74HC04 pin 1')
    # Z LED 급전: b10 → 여백 212 → a25. a 열은 A'(a8→a18)가, c 열은 A'·B(c20→c9)가
    # 지나고 d10 은 Z→우측 점퍼가 쓴다. 212 는 19행에서 입력 B 선을 가로지른다 (교차는 허용)
    bb.step_wire([(c['b'], bb.r_y(10)), (212, bb.r_y(10)), (212, bb.r_y(25)), (c['a'], bb.r_y(25))],
                 'sig', 'Z (74HC04 pin 4) -> Z LED', marker_at=(c['a'] - 20, bb.r_y(16)))
    bb.led_chain(c['a'], 25, "Z", "Z = (A'·B)' — X 와 항상 같아야 한다", color_rgb=(210, 20, 80))
    if st == 1:
        bb.step_wire([(c['c'], bb.r_y(7)), (c['c'], bb.r_y(9))], 'sig',
                     '임시: 입력 A 갈래 -> 74HC04 pin 3 (2단계에서 걷는다)',
                     marker_at=(c['c'] + 18, bb.r_y(8)))
        bb.note("1단계: 인버터 2단(pin 3→4)을 검사한다. pin 3 을 A 에 임시로 물려 Z = A' 를 A=0,1 로 본다.")
    if st >= 2:
        bb.draw_chip("74HC08", _S2)
        _input_jumper(bb, c, 19, 'B', '74HC08 pin 2', marker=(215, +13))
        bb.step_wire([(c['a'], bb.r_y(8)), (c['a'], bb.r_y(18))], 'mid',
                     "A' (74HC04 pin 2) -> 74HC08 pin 1", marker_at=(c['a'] - 20, bb.r_y(13)))
        bb.step_wire([(c['c'], bb.r_y(20)), (c['c'], bb.r_y(9))], 'mid',
                     "A'·B (74HC08 pin 3) -> 74HC04 pin 3", marker_at=(c['c'] + 18, bb.r_y(15)))
        bb.mark_unused_inputs([4, 5, 9, 10, 12, 13], _S2, chip='74HC08')
        bb.mark_unused_outputs([6, 8, 11], _S2, chip='74HC08')
    if st == 2:
        bb.note("2단계: 74HC08 게이트1 + 인버터1·2. Z = (A'·B)' 를 네 조합 전부 본다.")
    if st >= 3:
        bb.draw_chip("74HC32", _S3, block='right')
        # A 갈래: 7행 스트립의 c7 에서 세로로 5행까지 올려 판 위를 가로지른다
        bb.step_wire([(c['c'], bb.r_y(7)), (c['c'], bb.r_y(5)), (577, bb.r_y(5)),
                      (577, bb.r_y(13)), (r['a'], bb.r_y(13))], 'sig',
                     '입력 A 갈래 -> 74HC32 pin 4', width=2, marker_at=(577 + 14, bb.r_y(5) - 12))
        bb.step_wire([(r['d'], bb.r_y(13)), (r['d'], bb.r_y(10))], 'sig',
                     '입력 A 갈래 -> 74HC32 pin 1', width=2, marker_at=(r['b'], bb.r_y(12)))
        # B 갈래: 19행 스트립의 d19 에서 세로로 17행까지, 여백 228 로 6행까지 올려 우 b14
        bb.step_wire([(c['d'], bb.r_y(19)), (c['d'], bb.r_y(17)), (228, bb.r_y(17)), (228, bb.r_y(6)),
                      (r['b'] + 8, bb.r_y(6)), (r['b'] + 8, bb.r_y(14)), (r['b'], bb.r_y(14))],
                     'sig', '입력 B 갈래 -> 74HC32 pin 5', width=2, marker_at=(577 + 14, bb.r_y(6) + 10))
        # Z → 우측: d10 에서 칩을 가로질러 f·g 사이(362)에서 11행으로 내려 우 b11
        bb.step_wire([(c['d'], bb.r_y(10)), (362, bb.r_y(10)), (362, bb.r_y(11)), (r['b'], bb.r_y(11))],
                     'mid', "Z (74HC04 pin 4) -> 74HC32 pin 2", width=2,
                     marker_at=(c['d'] + 40, bb.r_y(10) - 12))
        bb.step_wire([(r['c'], bb.r_y(12)), (r['c'], bb.r_y(22))], 'sig',
                     '74HC32 pin 3 -> X LED', marker_at=(r['c'] - 18, bb.r_y(18)))
        bb.led_chain(r['c'], 22, "X", "X = A + Z — Z 와 다르면 배선 오류",
                     block='right', color_rgb=(220, 120, 0))
        bb.step_wire([(r['a'], bb.r_y(15)), (r['a'], bb.r_y(27))], 'sig',
                     '74HC32 pin 6 -> Y LED', marker_at=(r['a'] - 20, bb.r_y(21)))
        bb.led_chain(r['a'], 27, "Y", "Y = A + B", block='right', color_rgb=(20, 150, 50))
        bb.mark_unused_inputs([9, 10, 12, 13], _S3, block='right', chip='74HC32')
        bb.mark_unused_outputs([8, 11], _S3, block='right', chip='74HC32')
        bb.note("Z 와 X 는 부울대수로 항등이다 (X = A + (A'·B)' = A + B' = Z). "
                "두 LED 가 서로 다르게 켜지면 배선이 틀린 것이다 — 공짜 자체 검산.")
    bb.mark_unused_inputs([5, 9, 11, 13], _S1, chip='74HC04')
    bb.mark_unused_outputs([6, 8, 10, 12], _S1, chip='74HC04')
    bb.note('입력 A·B 두 개뿐이다. 교안 p15 회로도에 C 입력은 없다.')
    bb.note(_E1_INPUT_NOTE)
    bb.export(output_path, max_row=34)
    return bb


# 절차 그림 사슬. 보드 n 의 기준선은 보드 n-1 의 배선이다 — 실험실에서 보드 위에
# 실제로 남아 있는 것. 첫 보드(C1)는 기준선이 없어 완성본을 겸한다.
BOARDS = [
    ("실험01_1-1_결선도_3입력_AND.png", build_e1_and, None),
    ("실험01_1-2_결선도_3입력_OR_1단계_칩교체.png", build_e1_or, None),
    ("실험01_2-1_결선도_3입력_NAND_1단계_앞단AND.png", build_e1_nand, 1),
    ("실험01_2-1_결선도_3입력_NAND_2단계_뒷단NAND.png", build_e1_nand, None),
    ("실험01_2-2_결선도_3입력_NOR_1단계_앞단OR.png", build_e1_nor, 1),
    ("실험01_2-2_결선도_3입력_NOR_2단계_뒷단NOR.png", build_e1_nor, None),
    ("실험01_3_결선도_복합논리회로_1단계_인버터.png", build_e1_comb, 1),
    ("실험01_3_결선도_복합논리회로_2단계_AND.png", build_e1_comb, 2),
    ("실험01_3_결선도_복합논리회로_3단계_OR.png", build_e1_comb, None),
]

# 완성본 — 기준선 없이 전부 색. 예비보고서에 싣고 손으로 따라 그리는 원도다.
# 회색이 섞인 단계 그림을 원도로 쓰면 따라 그리는 사람이 회색 선을 빠뜨린다
FINALS = [
    ("실험01_1-2_결선도_3입력_OR.png", build_e1_or),
    ("실험01_2-1_결선도_3입력_NAND.png", build_e1_nand),
    ("실험01_2-2_결선도_3입력_NOR.png", build_e1_nor),
    ("실험01_3_결선도_복합논리회로.png", build_e1_comb),
]


def _e1_baseline(index, template_path=None):
    """`BOARDS[index]` 의 기준선 = 바로 앞 보드의 `snapshot()`. 첫 보드는 None.

    앞 보드는 기준선 **없이** 그린다 — 배선 집합은 기준선과 무관하므로(색과
    번호만 달라진다) 재귀가 없다. 임시 파일에 그리고 버린다.
    """
    if index == 0:
        return None
    _name, fn, stage = BOARDS[index - 1]
    with tempfile.TemporaryDirectory() as d:
        return fn(os.path.join(d, 'prev.png'), template_path, stage=stage).snapshot()


def _e1_board(index, output_path, template_path=None):
    _name, fn, stage = BOARDS[index]
    return fn(output_path, template_path, stage=stage,
              baseline=_e1_baseline(index, template_path))


def build_e1_or_s1(output_path, template_path=None):
    """C2 1단계 — C1 에서 칩만 갈아끼운다. 새 배선 0가닥."""
    return _e1_board(1, output_path, template_path)


def build_e1_nand_s1(output_path, template_path=None):
    """C3 1단계 — 앞단 74HC08 만. L1 = A·B 네 조합."""
    return _e1_board(2, output_path, template_path)


def build_e1_nand_s2(output_path, template_path=None):
    """C3 2단계 — 74HC00 을 더해 완성."""
    return _e1_board(3, output_path, template_path)


def build_e1_nor_s1(output_path, template_path=None):
    """C4 1단계 — 앞단 74HC32 만. L1 = A+B 네 조합."""
    return _e1_board(4, output_path, template_path)


def build_e1_nor_s2(output_path, template_path=None):
    """C4 2단계 — 74HC02 를 더해 완성."""
    return _e1_board(5, output_path, template_path)


def build_e1_comb_s1(output_path, template_path=None):
    """C5 1단계 — 74HC04 + Z LED, 임시 점퍼로 Z = A'."""
    return _e1_board(6, output_path, template_path)


def build_e1_comb_s2(output_path, template_path=None):
    """C5 2단계 — 74HC08 추가, Z = (A'·B)'."""
    return _e1_board(7, output_path, template_path)


def build_e1_comb_s3(output_path, template_path=None):
    """C5 3단계 — 74HC32 추가, 완성."""
    return _e1_board(8, output_path, template_path)
