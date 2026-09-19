# 실험02 결선 — 엔진 `render_breadboard.py --experiment 2` 이
# 이 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를 뽑는다.
# 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.
import os
import tempfile

from render_breadboard import BreadboardRenderer


# 실험 2 · CMOS 회로의 전기적 특성 — 2026-2 배포본(12쪽) 기준, 2026-09-13 재저작
#
# 실험 1 과 성격이 다르다. **정답표가 없다** — LED 가 켜지는지 보는 게 아니라
# 함수발생기로 흔들고 오실로스코프로 읽는다. 그래서 그림에 두 층이 있다.
#
#   · 배선(점퍼선으로 꽂는 것)   -> `step_wire`, 결선 순서표
#   · 계측(프로브·집게로 무는 것) -> `instrument`, 계측표, 회색 점선
#
# 둘을 한 표에 섞으면 조원이 프로브 자리에 점퍼선을 찾는다.
#
# 미사용 입력 처리도 실험 1 과 다르다. 교안 p9 가 "사용하지 않는 핀의 입력 값은
# Vcc 또는 GND에 연결 (Pull up/Pull down)" 이라 명시하고, 그 그림과 p12 의 U2 가
# **pin 3·5 -> GND / pin 9·11·13 -> VCC** 로 그려져 있다. 도면대로 따라야
# 실험실에서 대조가 된다.
#
# 두 회로가 칩 자리를 공유한다. 정본은 netlist 의 `kind: layout` 표이고 이
# 상수는 사본이다 — `tests/test_breadboard_wiring.py` 가 둘을 맞댄다.
#
#   S1 좌 7행  : C1 74HC04 · C2 74HC14 (U1)
#
# 교안 실험 2(t_pd, `build_e2_tpd`)는 조교 공지 `_350547_1`(2026-09-14)로 실험실에서
# 하지 않는다. 빌더는 완성본만 남긴다 — 사슬에는 없고, 한 그림에 같은 칩 두
# 패키지(`74HC04#7`·`#18`)가 앉는 유일한 사례라 넷·가독성·손그림 테스트가 쓴다.
# 그 U2 자리는 슬롯표 밖이라 `_E2_TPD_U2_ROW` 로 따로 둔다.
#
# 근거: `보고서/실험02/결선도/netlist.md` (C1·C2), `체크리스트/명세.md`.

E2_SLOTS = {'S1': ('left', 7)}
_E2_S1 = E2_SLOTS['S1'][1]
_E2_TPD_U2_ROW = 18   # 범위 밖 build_e2_tpd 의 부하 칩(U2) 자리 — 슬롯표에 없다
_E2_UNUSED_GND = [3, 5]        # 교안 p9 그림: 미사용 입력 중 GND 로 내리는 것
_E2_UNUSED_VCC = [9, 11, 13]   # 교안 p9 그림: VCC 로 올리는 것
_E2_UNUSED_OUT = [4, 6, 8, 10, 12]
_E2_XY_NOTE = ('오실로스코프 X-Y 모드: "Horiz > 좌측 아래 버튼" (교안 p10 머리글). CH1 이 '
               '가로축(Vin), CH2 가 세로축(Vout) — 축 배정은 통상 정의라 실험실 기종에서 '
               '확인한다 (netlist M8).')
_E2_GND_NOTE = ('함수발생기 -, CH1 -, CH2 - 는 전부 좌 GND 레일에 문다 — 전원장치 0V 와 '
                '같은 노드다 (회로도의 접지 기호는 전부 같은 GND).')


def _e2_frame(bb):
    """잭 + VCC 브리지. 세 회로가 같은 홀을 쓴다 — 기준선 비교로 회색이 된다.

    GND 브리지는 **없다.** 이 주차의 접지 끝점(pin 7, pull-down 3·5, 잭)은 전부
    좌 바깥 GND 레일 하나에 앉는다 — 끝점이 없는 레일을 잇는 브리지는 따라 그릴
    가닥만 늘린다(2026-09-12 격리 재생성 교훈). VCC 는 잭이 바깥 레일, pin 14 와
    pull-up 이 중앙 레일이라 브리지가 필요하다.
    """
    c = bb.cols['left']
    bb.connect_jacks()
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 27, kind='vcc')


def _e2_vtc(bb, chip):
    """C1·C2 공통 — S1 칩 하나, 게이트 1 만 쓴다. 점퍼로 꽂는 배선은 전원과
    미사용 입력 pull 뿐이고, pin 1 은 함수발생기가, pin 2 는 프로브가 문다.

    두 회로가 **같은 헬퍼를 같은 순서로** 부르므로 C2 는 C1 기준선에서 배선
    전부가 회색이 되고 순서표 첫 줄이 칩 교체 한 줄이다.
    """
    c = bb.cols['left']
    bb.draw_chip(chip, _E2_S1)
    _e2_frame(bb)
    bb.connect_power(_E2_S1)
    bb.connect_unused_inputs(_E2_UNUSED_GND, _E2_S1, chip=chip, rail='gnd')
    bb.connect_unused_inputs(_E2_UNUSED_VCC, _E2_S1, chip=chip, rail='vcc')
    bb.mark_unused_outputs(_E2_UNUSED_OUT, _E2_S1, chip=chip)
    # 보드 안 이름은 교안 p10·p11 회로도의 신호 이름 그대로다
    bb.instrument(c['a'], _E2_S1, '함수발생기 + CH1 (가로축)',
                  f'사인파 Vpp 5V · offset 2.5V (교안 p10) · {chip} pin 1 = Vin',
                  lane_row=4, name='VIN')
    bb.instrument(c['a'], _E2_S1 + 1, 'CH2 (세로축)',
                  f'{chip} pin 2 = Vout · 부하 없음, 프로브만 문다', lane_row=11,
                  name='VOUT')
    bb.instrument_note('함수발생기 -, CH1 -, CH2 -', '좌 GND 레일', '전원장치 0V 와 같은 노드')
    bb.note(_E2_XY_NOTE)
    bb.note('미사용 입력은 교안 p9 그림대로 pin 3·5 → GND, pin 9·11·13 → VCC (netlist M6). '
            '사용하는 게이트 1 의 입력 pin 1 은 함수발생기가 문다 — 띄워두지 않는다.')
    bb.note(_E2_GND_NOTE)


def build_e2_inv(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-1 · Inverter 입출력 특성 (74HC04, X-Y). netlist C1. 첫 보드 — 완성본 겸용."""
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    bb.set_header("실험 1-1: Inverter 입출력 특성 결선도",
                  "74HC04 (Hex Inverter) 게이트 1 · 오실로스코프 X-Y 모드 (CH1 = Vin, CH2 = Vout)",
                  submit=baseline is None)
    _e2_vtc(bb, '74HC04')
    bb.export(output_path, max_row=31)
    return bb


def build_e2_schmitt(output_path, template_path=None, stage=None, baseline=None):
    """실험 1-2 · Schmitt-trigger 입출력 특성 (74HC14). netlist C2. C1 과 배선이 같다.

    Nexperia 74HC14 Rev. 10 (2024-02-29) §6.2: 입력 1,3,5,9,11,13 / 출력 2,4,6,8,
    10,12 / GND 7 / VCC 14 — 74HC04 와 같은 배치라 칩만 갈아 끼운다.
    """
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    bb.set_header("실험 1-2: Schmitt-trigger 입출력 특성 결선도" if baseline is None
                  else "실험 1-2: Schmitt-trigger — 1단계 (칩 교체)",
                  "74HC14 (Hex Schmitt inverter) · C1 과 배선이 같다 — 칩만 갈아 끼운다",
                  submit=baseline is None)
    _e2_vtc(bb, '74HC14')
    bb.note('74HC14 는 74HC04 와 핀 배치가 같다 (Nexperia 74HC14 Rev. 10 §6.2). 전원을 끄고 '
            '칩만 갈아 끼운다 — 선은 하나도 안 걷는다. 신호원·X-Y 설정도 그대로다 (교안 p11).')
    bb.export(output_path, max_row=31)
    return bb


def build_e2_tpd(output_path, template_path=None, stage=None, baseline=None):
    """실험 2 · CMOS AC 특성 — t_pd (74HC04 두 패키지). 범위 밖 — 회귀 사례로만 남는다.

      stage 1  U1(S1) 체인 6단 + 전원(S1·S2 둘 다). CH1 = pin 4, CH2 = pin 8
      stage 2  + U2(S2) 부하 = 완성

    체인이 핀 번호 순서로 흐르지 않는다 — pin 6 에서 pin 13 으로 건너뛴 뒤 번호를
    거슬러 내려온다 (교안 p12 회로도, 600dpi vision 판독):

        1→2 · 3→4 · 5→6 · 13→12 · 11→10 · 9→8

    CH1(pin 4)~CH2(pin 8) 사이는 4→5, 6→13, 12→11, 10→9 의 **4 단**이다. 단 수는
    측정값에서 역산하지 않고 이 점퍼 넷을 세어 확인한다.
    """
    st = 2 if stage is None else stage
    bb = BreadboardRenderer(template_path, baseline=baseline)
    bb.enable_steps()
    bb.density_policy = 'legacy'   # R7(2026-09-20) 이전 승인본 — 도장 고정, 재작성 안 함
    bb.partial = st < 2
    title = {1: "실험 2: CMOS AC 특성 — 1단계 (U1 체인, CH1 = pin 4 · CH2 = pin 8)",
             2: "실험 2: CMOS AC 특성 (t_pd) 결선도" if baseline is None
                else "실험 2: CMOS AC 특성 — 2단계 (U2 부하, 완성)"}[st]
    bb.set_header(title,
                  "74HC04 두 패키지 · U1 인버터 6단 직렬, U2 는 체인 끝 부하 · 사각파 Vpp 5V, 1MHz",
                  submit=baseline is None)
    c = bb.cols['left']
    r1, r2 = _E2_S1, _E2_TPD_U2_ROW

    bb.draw_chip('74HC04', r1)
    _e2_frame(bb)
    bb.connect_power(r1)
    # U2 자리 전원 두 가닥 — 회로가 바뀌어도 그대로인 선이라 1단계에 미리 꽂는다
    bb.connect_power(r2)

    # U1 체인. 인접 핀끼리는 짧은 점퍼 넷, 6->13 하나만 칩 위(5행)로 넘긴다.
    # a 열은 프로브 자리(pin 1·4), b 열은 짧은 점퍼, c 열은 긴 점퍼 — 서로 안 겹친다
    bb.step_wire([(c['b'], bb.r_y(r1 + 1)), (c['b'], bb.r_y(r1 + 2))], 'mid',
                 '1단 출력 pin 2 -> 2단 입력 pin 3', width=4,
                 marker_at=(c['b'] - 20, bb.r_y(r1 + 1) + 8))
    bb.step_wire([(c['b'], bb.r_y(r1 + 3)), (c['b'], bb.r_y(r1 + 4))], 'mid',
                 '2단 출력 pin 4 -> 3단 입력 pin 5', width=4,
                 marker_at=(c['b'] - 20, bb.r_y(r1 + 3) + 8))
    bb.step_wire([(c['c'], bb.r_y(r1 + 5)), (c['c'], bb.r_y(r1 - 2)),
                  (c['h'], bb.r_y(r1 - 2)), (c['h'], bb.r_y(r1 + 1))], 'mid',
                 '3단 출력 pin 6 -> 4단 입력 pin 13 (칩 위로 넘기는 긴 점퍼)',
                 marker_at=(c['e'] + 6, bb.r_y(r1 - 2) - 12))
    bb.step_wire([(c['g'], bb.r_y(r1 + 2)), (c['g'], bb.r_y(r1 + 3))], 'mid',
                 '4단 출력 pin 12 -> 5단 입력 pin 11', width=4,
                 marker_at=(c['g'] + 20, bb.r_y(r1 + 2) + 8))
    bb.step_wire([(c['g'], bb.r_y(r1 + 4)), (c['g'], bb.r_y(r1 + 5))], 'mid',
                 '5단 출력 pin 10 -> 6단 입력 pin 9', width=4,
                 marker_at=(c['g'] + 20, bb.r_y(r1 + 4) + 8))

    # 보드 안 이름: 교안 p12 회로도의 `VIN`, 본문 "CH1에 U1의 4번 핀을, CH2에 U1의 8번 핀을"
    bb.instrument(c['a'], r1, '함수발생기',
                  '사각파 Vpp 5V · 1MHz (교안 p12) · U1 pin 1 = VIN', lane_row=4, name='VIN')
    bb.instrument(c['a'], r1 + 3, 'CH1',
                  'U1 pin 4 = 2단 출력 · 지연 측정 시작점 (교안 p12)', lane_row=11,
                  name='CH1')
    bb.instrument(c['h'], r1 + 6, 'CH2',
                  'U1 pin 8 = 6단 출력 · CH1 과 사이에 인버터 4단 (교안 p12)', lane_row=16,
                  name='CH2')
    bb.instrument_note('함수발생기 -, CH1 -, CH2 -', '좌 GND 레일', '전원장치 0V 와 같은 노드')

    if st == 1:
        bb.note('1단계: U1 체인만 본다. CH1(pin 4)·CH2(pin 8) 둘 다 1MHz 사각파가 보이고 '
                '같은 방향으로 움직이면(짝수 단) 2단계로 간다. U2 자리 전원 두 가닥은 미리 꽂는다.')
    else:
        bb.draw_chip('74HC04', r2)
        # U1 pin 8 (13행 f~j 쪽) -> U2 pin 1 (18행 a~e 쪽). 두 칩 사이 빈 15행으로 건넌다
        bb.step_wire([(c['i'], bb.r_y(r1 + 6)), (c['i'], bb.r_y(r1 + 8)),
                      (c['b'], bb.r_y(r1 + 8)), (c['b'], bb.r_y(r2))], 'sig',
                     'U1 최종단 pin 8 -> U2 pin 1 (게이트 입력 부하)',
                     marker_at=(c['e'] + 6, bb.r_y(r1 + 8) - 12))
        bb.connect_unused_inputs(_E2_UNUSED_GND, r2, chip='U2', rail='gnd')
        bb.connect_unused_inputs(_E2_UNUSED_VCC, r2, chip='U2', rail='vcc')
        bb.mark_unused_outputs([2] + _E2_UNUSED_OUT, r2, chip='U2')
        bb.note('U2 는 게이트 1 입력만 받는다 — "체인 끝 부하" 는 회로도 해석이지 교안 원문이 '
                '아니다. pin 2 는 개방, 나머지 입력은 교안 p12 회로도대로 3·5 → GND, 9·11·13 → VCC.')

    bb.note('U1 에는 미사용 입력이 없다 — 인버터 6개를 전부 쓰므로 14핀이 모두 물린다. '
            'C2 의 pull 선(3·5 → GND, 9·11·13 → VCC)은 걷는다 (아래 "앞 단계에서 걷는다").')
    bb.note('CH1~CH2 사이는 4단 (4→5, 6→13, 12→11, 10→9). 짝수 단이라 두 파형은 같은 방향이고 '
            'Δt = 2·t_PHL + 2·t_PLH 다 — 1단 환산은 Δt/4. 단 수는 점퍼를 세어 확인한다.')
    bb.note('교안 p12 는 사각파의 offset 을 적지 않는다. 0~5V 로 두려면 offset '
            '2.5V 가 필요하다 — CH1 로 Vin 이 0~5V 인지 먼저 본다.')
    bb.note(_E2_GND_NOTE)
    bb.export(output_path, max_row=31)
    return bb


# 절차 그림 사슬. 보드 n 의 기준선은 보드 n-1 의 배선이다 — 실험실에서 보드 위에
# 실제로 남아 있는 것. 첫 보드(C1)는 기준선이 없어 완성본을 겸한다.
BOARDS = [
    ("실험02_1-1_결선도_인버터_입출력특성.png", build_e2_inv, None),
    ("실험02_1-2_결선도_슈미트트리거_입출력특성_1단계_칩교체.png", build_e2_schmitt, None),
]

# 완성본 — 기준선 없이 전부 색. 예비보고서에 싣고 손으로 따라 그리는 원도다.
FINALS = [
    ("실험02_1-2_결선도_슈미트트리거_입출력특성.png", build_e2_schmitt),
]


def _e2_baseline(index, template_path=None):
    """`BOARDS[index]` 의 기준선 = 바로 앞 보드의 `snapshot()`. 첫 보드는 None."""
    if index == 0:
        return None
    _name, fn, stage = BOARDS[index - 1]
    with tempfile.TemporaryDirectory() as d:
        return fn(os.path.join(d, 'prev.png'), template_path, stage=stage).snapshot()


def _e2_board(index, output_path, template_path=None):
    _name, fn, stage = BOARDS[index]
    return fn(output_path, template_path, stage=stage,
              baseline=_e2_baseline(index, template_path))


def build_e2_schmitt_s1(output_path, template_path=None):
    """C2 1단계 — C1 에서 칩만 갈아 끼운다. 새 배선 0가닥."""
    return _e2_board(1, output_path, template_path)
