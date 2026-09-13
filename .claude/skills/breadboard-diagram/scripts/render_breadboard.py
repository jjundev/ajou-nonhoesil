import os
import sys
import argparse
import tempfile
from PIL import Image, ImageDraw, ImageFont

# 저장소 루트. 이 파일은 `<루트>/.claude/skills/breadboard-diagram/scripts/`
# 에 있다. **cwd 로 찾지 않는다** — 예전 후보 목록이 상대 경로여서 저장소
# 루트 밖에서 부르면 조용히 못 찾았고, 그 자리를 메우려고 남의 계정에서는
# 그냥 죽는 절대 경로가 하드코딩돼 있었다.
REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))

# 브레드보드 템플릿 정본. **`.claude/assets/` 가 이긴다.**
#
# 이 클래스의 `cols`·`r_y()` 픽셀 좌표는 이 한 장의 그림에 맞춰져 있다.
# 그래서 "같은 브레드보드 그림"이면 아무거나 써도 되는 게 아니다 —
# 2026-2 배포본 `강의노트/공지사항/Breadboard.pdf` 는 도면도 세로 좌표도
# 같지만(보드 상하단이 y=242·1317 로 일치) **가로가 중앙 기준 약 5% 넓다**.
# 좌우 끝 레일이 최대 19px 밀리는데 홀 간격이 17px 이라, 갈아끼우면 결선이
# 옆 홀에 그려진다. 그림 자체는 그럴듯하게 나오므로 눈으로는 안 잡힌다.
# 배포본으로 옮기려면 좌표표를 같이 다시 떠야 한다.
#
# 아카이브 사본은 지금 정본과 바이트가 같지만(md5 ae44279586294fc5…) 과거
# 학기 자료라 정리 대상이다. 최후 대체물로만 남긴다.
TEMPLATE_CANDIDATES = (
    '.claude/assets/Breadboard.jpg',
    'from_the_past/정리/강의노트/Breadboard.jpg',
    'from_the_past/정리/아카이브/강의노트/Breadboard.jpg',
)

# 좌표표가 묶여 있는 판본의 크기.
TEMPLATE_SIZE = (998, 1345)

# 폰트. macOS 경로만 박혀 있어 Windows 에서 렌더러가 통째로 죽었다 (2026-09-12).
# 있는 것을 순서대로 쓴다 — 한글은 Apple SD Gothic Neo → 맑은 고딕 → 나눔고딕,
# 영문은 Helvetica → Arial → DejaVu. 저장소 루트 밖의 절대 경로지만 폰트는
# 저장소가 들고 다닐 물건이 아니다.
FONT_CANDIDATES = {
    'kr': ('/System/Library/Fonts/AppleSDGothicNeo.ttc',
           'C:/Windows/Fonts/malgun.ttf',
           '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'),
    'en': ('/System/Library/Fonts/Helvetica.ttc',
           'C:/Windows/Fonts/arial.ttf',
           '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
}


def font_path(kind):
    """`kind`('kr'|'en') 의 첫 번째 실재 폰트 경로. 없으면 어디를 봤는지 적어 던진다."""
    for path in FONT_CANDIDATES[kind]:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f'{kind} 폰트를 찾지 못했다. 찾아본 곳:\n  ' + '\n  '.join(FONT_CANDIDATES[kind]))


def _font(kind, size):
    return ImageFont.truetype(font_path(kind), size)


def _default_template():
    """정본 템플릿 경로. 저장소 루트를 먼저 보고, 없으면 cwd 도 본다."""
    tried = []
    for rel in TEMPLATE_CANDIDATES:
        for base in (REPO_ROOT, os.getcwd()):
            path = os.path.join(base, rel)
            if path in tried:
                continue
            tried.append(path)
            if os.path.exists(path):
                return path
    raise FileNotFoundError(
        '브레드보드 템플릿을 찾지 못했습니다. 찾아본 곳:\n  ' + '\n  '.join(tried))


# ---------------------------------------------------------------------------
# 물리 좌표계 — `.claude/assets/Breadboard.jpg` 를 직접 측정한 값이다.
#
# 이전 판은 `r_y = 243 + (r-1)*17.15`, 좌측 GND 레일 x=163 처럼 **눈대중 값**을
# 썼다. 그림은 그럴듯했지만 배선 끝점이 홀 안에 들어가지 않았다 — 1행이 29px,
# 우측 f~j 열이 한 칸(16.5px) 통째로 어긋나 있었다. 홀을 세어가며 손으로 따라
# 그리라고 만든 그림에서 이건 치명적이다.
#
# 아래 값은 템플릿의 어두운 픽셀 군집 중심을 떠서 얻었다. 다시 뜨려면
# `tools/measure_template.py` 를 보라.
ROW0 = 272.0        # 1행 홀 중심 y
ROW_PITCH = 16.345  # 행 간격
BOARD_LEFT = 149     # 좌 보드 테두리 x. 이보다 왼쪽은 보드 밖 여백이다 (가독성 테스트의 BOARD_L)
ROW_MAX = 63        # 이 보드는 63행이다 (라벨은 1·10·20…60 만 찍혀 있다)

# 전원 레일은 5홀씩 묶여 있고 그 사이가 비어 있다. **그 빈 행에 배선을 끝내면
# 갈 데가 없다.** 위아래 끝(1·2·62·63)과 6행 주기의 빈 행이 여기 해당한다.
RAIL_GAP_ROWS = frozenset(
    {1, 2, 8, 14, 20, 26, 32, 38, 44, 50, 56, 62, 63})  # 실측값. 풀어 쓴다 —
# 검사 코드가 소스를 ast 로 읽어 이 목록을 그대로 가져다 쓴다

# 배선 색은 **넷뿐이다.** 이전 판은 한 장에 16색을 썼는데 그중 (0,110,170) 과
# (0,120,180), (200,0,0) 과 (220,20,20) 처럼 눈으로 구분되지 않는 쌍이 여럿이라
# 색이 정보를 나르지 않으면서 눈만 어지럽혔다. 손으로 그리는 사람 손에 있는
# 펜도 네 자루다.
WIRE = {
    'vcc': (200, 30, 30, 255),    # 빨강 — +5V
    'gnd': (30, 60, 200, 255),    # 파랑 — 0V(GND)
    'sig': (25, 25, 25, 255),     # 검정 — 입력·출력 신호
    'mid': (20, 130, 60, 255),    # 초록 — 칩과 칩 사이 중간 노드
}
KIND_KR = {'vcc': '+5V', 'gnd': '0V', 'sig': '신호', 'mid': '중간'}

# 앞 단계에서 그대로 두는 배선·부품의 색. 네 색 팔레트(`WIRE`)에 넣지 않는다 —
# 이것은 넷의 색이 아니라 "이번 단계에서 손대지 않는다" 는 표시다
KEEP = (165, 165, 165, 255)

# 계측기 리드는 **배선이 아니다.** 점퍼선으로 꽂는 게 아니라 프로브 팁과 집게로
# 문다. 그래서 위 네 색에 끼워 넣지 않고 회색 점선으로 따로 그리고, 순서표도
# '결선' 이 아니라 '계측' 표에 따로 쌓는다
PROBE = (105, 105, 110, 255)

# 전원 잭 세 개의 중심 x (템플릿 상단). y 는 원 아래끝 근처.
JACKS = {'red': 439, 'yellow': 603, 'gray': 766}
JACK_BOTTOM = 160

# 넷 라벨용 이름. 저장소가 한국어라 넷 판정문도 한국어로 나와야 한다
JACK_KR = {'red': '빨강', 'yellow': '노랑', 'gray': '회색'}


class BreadboardRenderer:
    def __init__(self, template_path=None, baseline=None):
        if template_path is None:
            template_path = _default_template()
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Breadboard template not found: {template_path}")

        self.base_im = Image.open(template_path).convert('RGBA')
        # 좌표표가 이 크기에 묶여 있다. 다른 판본이 들어오면 여기서 걸린다 —
        # 갈아끼운 그림은 결과가 그럴듯해서 눈으로는 안 잡히기 때문이다.
        if self.base_im.size != TEMPLATE_SIZE:
            raise ValueError(
                f'템플릿 크기가 {TEMPLATE_SIZE[0]}x{TEMPLATE_SIZE[1]} 가 아닙니다: '
                f'{self.base_im.size} ({template_path}).\n'
                'cols·r_y() 좌표는 정본 한 장에 맞춰져 있습니다. '
                '다른 판본을 쓰려면 좌표표를 다시 떠야 합니다.')
        self.im = self.base_im.copy()
        self.overlay = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.overlay)
        # 이미 그린 레일 브리지. 칩마다 connect_unused_inputs 를 부르면 같은
        # 레일쌍을 여러 번 잇게 되므로 한 번만 그린다
        self._bridged = set()
        # 실제로 꽂힌 브리지. `_bridged` 는 중복 방지 키(kind, x, x)라 **행이 없다**.
        # 행을 안 담으면 `wiring()` 이 1행을 주는데 1행은 레일 빈 행이라,
        # 손그림 검토가 참조 브리지마다 H1 치명을 헛낸다
        self.bridges = []
        # 어느 레일 스트립에 무엇이 닿았는지. 레일쌍 넷은 서로 **별개
        # 스트립**이라, +5V 를 한 레일에 넣고 칩 14번 핀을 다른 레일에 물리면
        # 그림은 멀쩡한데 전원이 안 간다. verify() 가 이걸로 잡는다
        self._touched = {'vcc': set(), 'gnd': set()}
        self._rail_uf = {}
        # 결선 순서표. 손으로 그리는 사람은 그림 전체를 한 번에 볼 필요 없이
        # 이 표를 위에서 아래로 지워가며 한 줄씩 그린다
        self.steps = []
        # 홀 점유표. (열 x, 행) -> 무엇이 꽂혀 있는가. 배선 끝점·부품 다리·칩 핀이
        # 전부 여기 등록되고 verify() 가 본다 — 끝점은 홀이어야 하고(R1), 한 홀에는
        # 리드 하나만 들어간다(R2). 2026-09-07 까지 verify() 는 주소 문자열을 파싱해
        # 레일 끝점의 빈 행만 봤고, 허공(x=95)에서 출발한 입력선이 그 틈으로 지나갔다
        self._leads = {}
        # 배선이 **지나가는** 홀. 비어 있지만 여기에 끝점을 두면 점이 선 아래
        # 깔린다 — free_rail_row() 가 피하고 verify() R3 가 끝점과 대조한다
        self._passed = set()
        self._not_holes = []
        self._double = []
        # 배선 구간 목록. (색, 꼭짓점들, 뜻). 서로 다른 배선이 같은 축 위에
        # 포개지면 그림에서 한 선으로 보인다 — 2026-09-07 실험 1-1 에서 입력 C 가
        # 초록 중간단 선에 삼켜져 다른 회로로 읽혔다. 'strict' 면 verify() 가
        # 던지고, 'warn' 이면 stderr 에 적고 overlap_warnings 에 남긴다
        self._segments = []
        self.overlap_policy = 'strict'
        self.overlap_warnings = []
        # 결선 순서표와 번호 원을 켜는 스위치. **지금은 13장 빌더가 전부 켠다** —
        # e1 계열도 e2 계열도 `enable_steps()` + `step_wire()` 에 네 색 팔레트(`WIRE`)를
        # 쓴다. 옛 `draw_wire()` 를 쓰는 빌더는 하나도 없다 (2026-09-10 확인)
        self.numbered = False
        # 보드 밖으로 뺀 규칙 문구. 배선이 아니라 배선의 *이유* 라서 손으로
        # 옮겨 그릴 대상이 아니다 — 보드 위에 두면 그릴 홀만 가린다
        self.notes = []
        # 계측기·신호원 접점. 결선표와 섞지 않는다
        self.probes = []
        # 입력 점퍼가 꽂힌 자리. 넷 검사가 레일 쪽 끝을 **가상 입력 노드**로
        # 바꿔 세는 데 쓴다 — `input_node()` 주석 참조
        self.inputs = []
        # 보드 안에 찍은 신호 이름 배지. (이름, 상자 (x0, y0, x1, y1), 가리키는 배선 번호 | None).
        # 가독성 테스트가 번호 원·배선·꽂힌 홀을 가리는지 본다
        self.tag_boxes = []
        # 번호 원의 상자. 같은 검사가 쓴다
        self.marker_boxes = []
        # 일부러 덜 그린 그림인가 (복합 회로 누적 1·2단계). '아무 데도 안 물렸다'
        # 갈래만 건너뛴다 — 칩 핀도 부품 다리도 아직 안 붙었을 수 있다. 같은
        # 스트립 점퍼도 전원 단락도 덜 그렸다고 봐줄 것이 아니다
        self.partial = False
        # 앞 보드의 `snapshot()`. 같은 홀 쌍의 배선·같은 홀의 LED 사슬은 회색으로
        # 그리고 번호를 주지 않는다 — 실험실에서는 그 선을 손대지 않는다.
        # 기준선에 있었는데 이번에 안 그린 것은 `removed()` 가 "걷는다" 로 낸다.
        # 실험01 실험실 기록(2026-09-11): 1-1→1-2 는 칩만 갈아끼우면 됐다
        self.baseline = baseline
        self.kept = []          # 그대로 두는 배선·부품의 desc
        self.swaps = []         # (앞 칩, 새 칩, block, pin1_row)
        self._keep_parts = False  # led_chain 이 기준선 사슬을 그리는 동안 참
        self.submit = True
        self.title = ""
        self.subtitle = ""

        self.font_title = _font('kr', 21)
        self.font_subtitle = _font('kr', 14)
        self.font_kr_bold = _font('kr', 12)
        self.font_kr_sm = _font('kr', 11)
        self.font_en_bold = _font('en', 12)
        self.font_en_sm = _font('en', 10)
        self.font_chip = _font('en', 11)
        self.font_num = _font('en', 9)
        self.font_step = _font('kr', 11)

        self._init_cols()
        # 그린 것을 **사실 그대로** 적어 둔다. 손그림 검토가 이걸 정답으로
        # 읽는다. `_leads` 의 뜻풀이 문자열을 파싱하게 두면 말이 바뀔 때마다
        # 검사기가 조용히 깨진다 — 검사기는 코드를 읽어야지 산문을 읽으면 안 된다
        self.chips = []
        self.leds = []
        self.resistors = []
        self.led_chains = []
        self.unused_inputs = []
        self.unused_outputs = []

        self._addr_map = self._build_addr_map()
        self._sym_map = self._build_sym_map()

    # ---------------- 좌표 ----------------

    def _init_cols(self):
        """열 좌표표. 템플릿 없이 좌표만 쓰려는 쪽(손그림 검토)이 있어
        `__init__` 에서 뽑아 놓는다. 이 표가 열 좌표의 **유일한 권위**다."""
        self.cols = {
            'left': {
                'gnd': 174, 'vcc': 190,
                'a': 239, 'b': 256, 'c': 272, 'd': 288, 'e': 305,
                'chip_x1': 310, 'chip_x2': 349,
                'f': 354, 'g': 370, 'h': 386, 'i': 403, 'j': 419,
                'mid_gnd': 468, 'mid_vcc': 484,
            },
            'right': {
                'mid_gnd': 542, 'mid_vcc': 558,
                'a': 607, 'b': 623, 'c': 640, 'd': 656, 'e': 672,
                'chip_x1': 677, 'chip_x2': 716,
                'f': 721, 'g': 738, 'h': 754, 'i': 770, 'j': 786,
                'gnd': 836, 'vcc': 852,
            },
        }
        # 레일 x -> 어느 전원인가. 넷 검사가 +5V 와 GND 가 한 넷이 됐는지 볼 때
        # 쓴다. 열 **이름**에서 뽑으므로 이 표가 유일한 권위라는 규칙을 지킨다
        self._rail_kind = {}
        for blk in self.cols.values():
            for key, x in blk.items():
                if 'gnd' in key:
                    self._rail_kind[x] = 'gnd'
                elif 'vcc' in key:
                    self._rail_kind[x] = 'vcc'

    def r_y(self, r):
        return int(round(ROW0 + (r - 1) * ROW_PITCH))

    @staticmethod
    def is_rail_row(r):
        return 1 <= r <= ROW_MAX and r not in RAIL_GAP_ROWS

    @staticmethod
    def _row_of(y):
        """y 좌표에 제일 가까운 행 번호. addr() 과 hole_at() 이 같은 식을 쓴다 — 한쪽만 고치면 갈린다."""
        return int(round((y - ROW0) / ROW_PITCH)) + 1

    def hole_at(self, x, y):
        """(x, y) 가 실제 홀이면 그 홀의 키 (열 x, 행), 아니면 None.

        레일은 5홀씩 묶여 빈 행이 있고, 단자대는 63행 전부 홀이다. 열·행 모두
        홀 중심에서 5px 안이어야 한다 — 열 피치가 16px 라 9px 로는 인접 열
        사이에 거부 구간이 없었다. 그 밖은 배선 통로거나 밀린 좌표다.
        """
        r = self._row_of(y)
        if not 1 <= r <= ROW_MAX:
            return None
        best = min(self._addr_map, key=lambda k: abs(k - x))
        if abs(best - x) > 5:
            return None
        if abs(y - self.r_y(r)) > 5:
            return None
        if '레일' in self._addr_map[best] and not self.is_rail_row(r):
            return None
        return (best, r)

    def _register_pass(self, points):
        """폴리라인이 지나가는 홀을 `_passed` 에 적는다 (양 끝점은 뺀다).

        2px 간격으로 훑어 `hole_at()` 에 걸리는 홀을 모은다 — 대각선도 같은
        식으로 잡힌다. 꺾이는 점이 홀 위에 있으면 그것도 '지나간 홀' 이다.
        """
        ends = {self.hole_at(*points[0]), self.hole_at(*points[-1])}
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** .5
            n = max(1, int(length / 2))
            for i in range(n + 1):
                t = i / n
                key = self.hole_at(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
                if key is not None and key not in ends:
                    self._passed.add(key)

    def _endpoints_under_wires(self, margin=6):
        """R3. 배선 끝점이나 부품 다리가 다른 배선 구간의 **중간**에 놓인 곳.

        점이 선 아래 깔리면 그 선에서 갈라지는 T 접속으로 읽힌다. 점퍼는 이어
        붙일 수 없으니 그런 접속은 없다 — **같은 넷이라도 봐주지 않는다.**
        2026-09-08 복합 회로 a7·a19 가 같은 넷이었고, 그래서 더 헷갈렸다.
        R4 가 같은 색 30px 이하를 밑동으로 봐주더라도 그 밑동의 끝점은 여기서
        걸린다 — 갈래는 옆 홀에서 세로로 뺀다.

        칩 핀 홀은 뺀다. 칩을 가로지르는 선은 핀 행을 지날 수밖에 없고 핀
        스텁은 회색이라 구분된다. 구간 양끝 `margin` px 안은 그 배선 자신의
        끝이라 뺀다 — 옆 홀(16px)에 나란히 끝나는 두 점퍼는 걸리지 않는다.
        """
        pts = []
        for i, (kind, points, desc) in enumerate(self._segments):
            for q in (points[0], points[-1]):
                pts.append((i, q, f'[{KIND_KR[kind]}] {desc}'))
        for (x, r), what in self._leads.items():
            if '다리' in what or '애노드' in what or '캐소드' in what:
                pts.append((None, (x, self.r_y(r)), f'[부품] {what}'))
        out = []
        for owner, (px, py), what in pts:
            for j, (kj, pj, dj) in enumerate(self._segments):
                if owner == j:
                    continue
                for (ax, ay), (bx, by) in zip(pj, pj[1:]):
                    dx, dy = bx - ax, by - ay
                    length = (dx * dx + dy * dy) ** .5
                    if length < 1:
                        continue
                    along = ((px - ax) * dx + (py - ay) * dy) / length
                    if along <= margin or length - along <= margin:
                        continue
                    if abs((px - ax) * dy - (py - ay) * dx) / length < 1.5:
                        out.append(f'{self.addr(px, py)} {what} ← 그 위를 지나는 [{KIND_KR[kj]}] {dj}')
        return sorted(set(out))

    def lead(self, x, y, what):
        """홀 (x, y) 에 리드 하나를 꽂는다.

        전원잭(y < 240)은 보드 밖의 유일한 합법 끝점이라 건너뛴다. 홀이 아니면
        R1 위반, 이미 차 있으면 R2 위반으로 적어 두고 verify() 가 한꺼번에 낸다
        — 그리는 도중에 던지면 어디까지 그렸는지 알 수 없다.
        """
        if y < 240 and any(abs(x - jx) < 30 for jx in JACKS.values()):
            return   # 전원잭 — 보드 밖의 유일한 합법 끝점
        key = self.hole_at(x, y)
        if key is None:
            self._not_holes.append(f'{what} — ({x:.0f}, {y:.0f}) = {self.addr(x, y)}')
            return
        prev = self._leads.get(key)
        if prev is not None:
            self._double.append(f'{self.addr(x, y)}: {prev} + {what}')
        else:
            self._leads[key] = what

    def free_rail_row(self, row, *xs):
        """`row` 에서 가장 가까운, `xs` 열의 홀이 전부 비어 있는 레일 행.

        `snap_rail_row()` 는 홀이 있는 행만 찾았다. 그래서 7행·8행에 나란히
        들어가는 입력 A·B 가 둘 다 7행 홀로 스냅돼 한 홀을 두고 다퉜고, 레일
        브리지 셋을 31행에 이으면 가운데 레일 31행에 점퍼 둘이 꽂혔다. 한 홀에
        리드 둘은 못 꽂는다 — 점유표를 보고 비어 있는 이웃으로 간다. 가까운
        순(같은 행, 위, 아래, 두 칸 위, …)이라 결과가 결정적이다.

        다른 배선이 **지나가는** 홀(`_passed`)도 찬 것으로 본다. pin 14 전원선이
        같은 행 중앙 GND 레일 홀 위를 지나는데 거기에 미사용 핀 접지선이 착지하면
        파란 점이 빨간 선 아래 깔린다 (R3). 먼저 그린 선이 지나간 자리는 비켜 간다.
        """
        for d in range(0, 8):
            for cand in ((row,) if d == 0 else (row - d, row + d)):
                if self.is_rail_row(cand) and all(
                        (x, cand) not in self._leads and (x, cand) not in self._passed for x in xs):
                    return cand
        raise ValueError(f'{row}행 근처에 빈 레일 홀이 없다: x={xs}')

    def _overlaps(self):
        """서로 다른 배선의 구간이 같은 축 위에 포개진 곳. 축 방향 구간만 본다.

        다른 색이면 8px 만 포개져도 잡는다. 같은 색은 30px(두 홀 폭 안)까지
        봐준다 — 같은 스트립의 옆 홀에 꽂은 두 번째 점퍼가 첫 점퍼 위를 되짚어
        여백으로 나가는 갈래 밑동이 그렇다. 다만 그 밑동은 굵은 선 아래 깔려
        "선 중간에서 얇은 선이 솟는" 그림이 되므로(2026-09-08 복합 회로 a7·a19
        지적) 봐준다고 해서 써도 되는 건 아니다 — 갈래는 옆 홀에서 세로로 뺀다.
        그 이상 같은 색으로 포개지면 두 넷이 한 선으로 보인다 (검정은 모든
        신호선의 색이다).
        """
        segs = []
        for i, (kind, pts, desc) in enumerate(self._segments):
            for a, b in zip(pts, pts[1:]):
                segs.append((i, kind, desc, a, b))
        out = []
        for i, ki, di, a, b in segs:
            for j, kj, dj, c, d in segs:
                if j <= i:
                    continue
                lim = 8 if ki != kj else 30
                where = None
                if abs(a[0] - b[0]) < .5 and abs(c[0] - d[0]) < .5 and abs(a[0] - c[0]) < 1.5:
                    lo = max(min(a[1], b[1]), min(c[1], d[1]))
                    hi = min(max(a[1], b[1]), max(c[1], d[1]))
                    if hi - lo > lim:
                        where = f'세로 {self.addr(a[0], lo)}~{self.addr(a[0], hi)}'
                elif abs(a[1] - b[1]) < .5 and abs(c[1] - d[1]) < .5 and abs(a[1] - c[1]) < 1.5:
                    lo = max(min(a[0], b[0]), min(c[0], d[0]))
                    hi = min(max(a[0], b[0]), max(c[0], d[0]))
                    if hi - lo > lim:
                        where = f'가로 {self.addr(lo, a[1])}~{self.addr(hi, a[1])}'
                if where:
                    out.append(f'{where} — [{KIND_KR[ki]}] {di} / [{KIND_KR[kj]}] {dj}')
        return out

    def _rail_xs(self):
        out = set()
        for block in self.cols.values():
            for key, x in block.items():
                if 'gnd' in key or 'vcc' in key:
                    out.add(x)
        return out

    def _uf_find(self, key):
        self._rail_uf.setdefault(key, key)
        while self._rail_uf[key] != key:
            self._rail_uf[key] = self._rail_uf[self._rail_uf[key]]
            key = self._rail_uf[key]
        return key

    def _uf_union(self, a, b):
        ra, rb = self._uf_find(a), self._uf_find(b)
        if ra != rb:
            self._rail_uf[rb] = ra

    def touch_rail(self, kind, x):
        """이 배선이 어느 전원 레일에 닿았는지 적어 둔다."""
        if kind in self._touched and x in self._rail_xs():
            self._touched[kind].add(x)

    def _build_addr_map(self):
        """x 좌표 -> 사람이 읽는 이름. 결선 순서표의 주소를 자동으로 만든다."""
        out = {}
        names = {'gnd': 'GND레일', 'vcc': 'VCC레일',
                 'mid_gnd': '중앙GND레일', 'mid_vcc': '중앙VCC레일'}
        for block, blabel in (('left', '좌'), ('right', '우')):
            for key, x in self.cols[block].items():
                if key.startswith('chip'):
                    continue
                out[x] = f'{blabel} {names.get(key, key)}'
        return out

    def _build_sym_map(self):
        """x 좌표 -> (블록, 열 이름). `_addr_map` 의 기계용 짝이다."""
        out = {}
        for block in ('left', 'right'):
            for key, x in self.cols[block].items():
                if key.startswith('chip'):
                    continue
                out[x] = (block, key)
        return out

    def sym(self, x, row):
        """(x, 행) -> (블록, 열 이름, 행). 홀이 아니면 None.

        `addr()` 이 사람이 읽는 '좌 b10' 을 만든다면 이쪽은 기계가 비교하는
        ('left', 'b', 10) 을 만든다. 허용치는 `hole_at()` 과 같은 5px 다 —
        열 피치가 16px 라 그보다 넓으면 인접 열 사이에 거부 구간이 없다.
        """
        best = min(self._sym_map, key=lambda k: abs(k - x))
        if abs(best - x) > 5:
            return None
        block, col = self._sym_map[best]
        return (block, col, row)

    def addr(self, x, y):
        """(x, y) 를 '좌 e7' 처럼 읽히는 주소로. 표에 그대로 들어간다."""
        if y < 240:
            return '전원잭'
        if x < 149:
            return '보드밖(입력)'
        if x > 880:
            return '보드밖'
        r = self._row_of(y)
        best = min(self._addr_map, key=lambda k: abs(k - x))
        if abs(best - x) > 9:
            # 홀이 아니라 배선 통로다. 분기점(T 접속)일 때만 여기 온다
            return '분기점'
        name = self._addr_map[best]
        return f'{name}{r}행' if '레일' in name else f'{name}{r}'

    # ---------------- 머리글 ----------------

    def set_header(self, title, subtitle, submit=True):
        """제목은 **잭 아래 빈 띠(y 165~238)** 에 넣는다.

        이전 판은 `[370,30,850,160]` 을 흰색으로 덮고 그 자리에 제목을 썼는데,
        하필 그 사각형 안에 **전원 잭 세 개가 들어 있었다.** 과거 예비보고서의
        결선도는 예외 없이 그 잭에서 보드까지 전원선을 그린다 — 실험대 전원이
        그 잭이기 때문이다. 덮어버리면 "5V 를 어디서 따오지"에서 막힌다.
        """
        self.title, self.subtitle = title, subtitle
        self.draw.text((28, 170), title, fill=(20, 40, 90, 255), font=self.font_title)
        self.draw.text((30, 200), subtitle, fill=(80, 90, 100, 255), font=self.font_subtitle)
        self.submit = submit
        line = ("※ 이 그림을 손으로 따라 그린 뒤 학번/이름/날짜를 자필로 적어 제출한다" if submit
                else "※ 체크리스트용 절차 그림 — 회색은 앞 단계에서 그대로 둔 것. 손그림은 완성본으로 그린다")
        self.draw.text((30, 220), line, fill=(180, 50, 50, 255), font=self.font_kr_sm)

    def connect_jacks(self, block='left'):
        """전원 잭 -> 보드 레일. 과거 결선도가 모두 그리던 선이다."""
        c = self.cols[block]
        r_v, r_g = self.free_rail_row(3, c['vcc']), self.free_rail_row(4, c['gnd'])
        self.step_wire([(JACKS['red'], JACK_BOTTOM), (JACKS['red'], 250),
                        (c['vcc'], 250), (c['vcc'], self.r_y(r_v))],
                       'vcc', '전원장치 +5V 잭', marker_at=(JACKS['red'] + 46, 118))
        self.step_wire([(JACKS['gray'], JACK_BOTTOM), (JACKS['gray'], 258),
                        (c['gnd'], 258), (c['gnd'], self.r_y(r_g))],
                       'gnd', '전원장치 0V 잭', marker_at=(JACKS['gray'] + 46, 118))
        self.note('잭 색과 전압 표기는 실험대 전원장치에서 직접 확인할 것 '
                  '(교안에 잭 색 규정이 없다). 가운데 노란 잭은 쓰지 않는다.')

    # ---------------- 낱개 그리기 ----------------

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def draw_badge(self, x, y, text, bg_col=(255, 255, 255, 235), text_col=(20, 20, 20, 255), font=None, pad=3):
        if font is None:
            font = self.font_kr_bold
        bbox = self.draw.textbbox((x, y), text, font=font)
        self.draw.rectangle([bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad], fill=bg_col, outline=text_col, width=1)
        self.draw.text((x, y), text, fill=text_col, font=font)

    def signal_tag(self, name, x, y, align='center', col=(20, 20, 20, 255), seg=None):
        """보드 안 **신호 이름** 배지 — 입력 A·B·C, 출력 L1·L2·X·Y·Z.

        2026-09 실험01 예보 조교 감점(-1): 손그림 결선도에 입력 A·B·C 위치 표기가
        없었다. 원도는 입력 이름을 보드 밖(x=12) 꼬리표에만 적었고, 학생은 보드
        판형 위만 따라 그려 그 글자가 옮겨지지 않았다. 신호 이름은 그림의 일부라
        이 함수로 보드 안에 둔다. 규칙 문구는 여전히 `note()` 로 보드 밖이다.

        `align='center'` 면 (x, y) 가 배지 중심, `'left'` 면 x 가 배지 상자의 왼쪽
        끝이다. `seg` 는 이 이름이 가리키는 배선의 `_segments` 번호 — 겹침 검사가
        그 선만 봐준다.
        """
        font, pad = self.font_en_bold, 2
        b = self.draw.textbbox((0, 0), name, font=font)
        w, h = b[2] - b[0], b[3] - b[1]
        left = x - w / 2 if align == 'center' else x + pad
        tx, ty = left - b[0], y - h / 2 - b[1]
        self.draw_badge(tx, ty, name, (255, 255, 255, 235), col, font=font, pad=pad)
        box = self.draw.textbbox((tx, ty), name, font=font)
        self.tag_boxes.append(
            (name, (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), seg))

    def draw_wire(self, points, color, width=3):
        """번호 없는 생짜 배선. **지금 이 함수를 부르는 빌더는 하나도 없다.**

        `_segments` 에도 `_leads` 에도 아무것도 남기지 않는다 — 그래서 이걸로 그린
        선은 `verify()` 를 통째로 우회한다. 끝점이 홀인지(R1), 한 홀에 리드가
        둘인지(R2), 다른 배선 아래 깔리는지(R3·R4), 무엇과 무엇을 잇는지(R5)
        아무도 보지 않는다. 순서표에도 안 오른다. `step_wire()` 를 써라.
        """
        self.draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            self.draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)

    def _dashed(self, points, color, width=2, dash=7, gap=5):
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            span = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if span == 0:
                continue
            ux, uy, t = (x1 - x0) / span, (y1 - y0) / span, 0.0
            while t < span:
                e = min(t + dash, span)
                self.draw.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)],
                               fill=color, width=width)
                t = e + gap

    def instrument(self, x, row, label, desc, block='left', lane_row=None):
        """계측기·신호원 접점. **배선이 아니다** — 점퍼로 꽂는 게 아니라
        프로브 팁이나 집게로 문다. 회색 점선으로 그리고 계측표에 따로 쌓는다.

        보드 왼쪽 여백으로 뺀다. `lane_row` 를 주면 여백 안(x=140)에서 꺾어
        그 행으로 옮긴다 — 접점 두 개가 이웃한 행이면 꼬리표가 겹치기 때문이다.
        """
        y = self.r_y(row)
        lane_y = self.r_y(lane_row) if lane_row else y
        pts = [(x, y), (140, y)] + ([(140, lane_y)] if lane_row else []) + [(100, lane_y)]
        self._dashed(pts, PROBE)
        self.draw.ellipse([x - 5, y - 5, x + 5, y + 5], outline=PROBE, width=2)
        n = len(self.probes) + 1
        self.draw_badge(12, lane_y - 8, f'{n}. {label}', (248, 248, 250, 240), PROBE,
                        font=self.font_kr_sm, pad=2)
        self.probes.append({'n': n, 'label': label, 'at': self.addr(x, y), 'desc': desc,
                            'sym': self.sym(x, row)})

    def instrument_note(self, label, at, desc):
        """그림에 그릴 자리가 없는 접점(회로에 꽂기 전 저항 측정 등)."""
        self.probes.append({'n': len(self.probes) + 1, 'label': label,
                            'at': at, 'desc': desc})

    def _marker(self, x, y, n, color):
        """배선 번호. 결선 순서표의 몇 번인지 가리킨다."""
        self.marker_boxes.append((x - 8, y - 8, x + 8, y + 8))
        self.draw.ellipse([x-8, y-8, x+8, y+8], fill=(255, 255, 255, 245), outline=color, width=2)
        t = str(n)
        bbox = self.draw.textbbox((0, 0), t, font=self.font_num)
        self.draw.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
                       t, fill=color, font=self.font_num)

    def enable_steps(self):
        self.numbered = True

    def step_wire(self, points, kind, desc, width=3, marker_at=None, count=1,
                  frm=None, to=None):
        """배선 하나 + 결선 순서표 한 줄.

        `desc` 는 짧은 뜻풀이만 준다 — 어디서 어디로 가는지는 좌표에서
        자동으로 뽑는다 ('좌 b7 -> 좌 GND레일7행').

        기준선(`baseline`)에 같은 (색, 끝점, 끝점) 이 있으면 **회색으로 그리고
        번호를 주지 않는다** — 앞 단계에서 꽂아 둔 그대로다. 점유표·구간·레일
        접촉은 똑같이 남긴다: 회색이어도 그림대로 꽂히는지는 verify() 가 본다.
        """
        key = (kind, self._endpoint(points[0]), self._endpoint(points[-1]))
        kept = self.baseline is not None and key in self.baseline['wires']
        color = KEEP if kept else WIRE[kind]
        self.draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            self.draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)
        for p in (points[0], points[-1]):
            self.lead(p[0], p[1], f'{KIND_KR[kind]} 배선 · {desc}')
            self.touch_rail(kind, p[0])
        self._segments.append((kind, [tuple(p) for p in points], desc))
        self._register_pass(points)
        if kept:
            self.kept.append(desc)
            return None
        if not self.numbered:
            return None

        n = len(self.steps) + 1
        if marker_at is None:
            (x0, y0), (x1, y1) = points[0], points[1] if len(points) > 1 else points[0]
            marker_at = ((x0 + x1) // 2, (y0 + y1) // 2)
        self._marker(marker_at[0], marker_at[1], n, color)

        frm = frm or self.addr(*points[0])
        to = to or self.addr(*points[-1])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def step_note(self, kind, frm, to, desc, count=1, marker_at=None):
        """그림에 이미 그려진 것을 표에 한 줄로 묶는다.

        `marker_at` 을 주면 보드 위에도 번호 원을 찍는다. **부품을 꽂는
        단계에는 반드시 준다** — 안 주면 표에는 번호가 있는데 그림에는 없어서,
        따라 그리는 사람이 그 차례에서 그림을 뒤지다 막힌다.
        """
        if self._keep_parts:
            self.kept.append(desc)      # 기준선 사슬의 부품 줄 — 번호 없이 회색
            return None
        if not self.numbered:
            return None
        n = len(self.steps) + 1
        if marker_at is not None:
            self._marker(marker_at[0], marker_at[1], n, WIRE[kind])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def draw_resistor(self, x, y1, y2, label="330Ω", bands=None):
        self.lead(x, y1, f'{label} 윗다리')
        self.lead(x, y2, f'{label} 아랫다리')
        self.resistors.append({'label': label,
                               'top': self.sym(x, self._row_of(y1)),
                               'bottom': self.sym(x, self._row_of(y2))})
        wire_col = KEEP if self._keep_parts else (100, 100, 100, 255)
        body_col = (215, 215, 215, 255) if self._keep_parts else (225, 195, 145, 255)
        if self._keep_parts:
            bands = [KEEP] * 4
        ymid = (y1 + y2) // 2
        self.draw.line([(x, y1), (x, ymid - 12)], fill=wire_col, width=2)
        self.draw.line([(x, ymid + 12), (x, y2)], fill=wire_col, width=2)
        self.draw.rectangle([x - 5, ymid - 12, x + 5, ymid + 12], fill=body_col, outline=(90, 70, 40, 255), width=1)
        if bands is None:
            if "1k" in label:
                bands = [(139, 69, 19, 255), (30, 30, 30, 255), (200, 20, 20, 255), (218, 165, 32, 255)]
            else:
                bands = [(204, 85, 0, 255), (204, 85, 0, 255), (139, 69, 19, 255), (218, 165, 32, 255)]
        for col, off in zip(bands, [-7, -2, 3, 8]):
            self.draw.line([(x - 4, ymid + off), (x + 4, ymid + off)], fill=col, width=2)

    def draw_led(self, x, y_anode, y_cathode, color_rgb=(230, 30, 30), label="LED"):
        self.lead(x, y_anode, f'{label} LED 애노드')
        self.lead(x, y_cathode, f'{label} LED 캐소드')
        self.leds.append({'tag': label,
                          'anode': self.sym(x, self._row_of(y_anode)),
                          'cathode': self.sym(x, self._row_of(y_cathode))})
        if self._keep_parts:
            color_rgb = KEEP[:3]
        ymid = (y_anode + y_cathode) // 2
        self.draw.line([(x, y_anode), (x, ymid - 8)], fill=(130, 130, 130, 255), width=2)
        self.draw.line([(x, ymid + 8), (x, y_cathode)], fill=(130, 130, 130, 255), width=2)
        self.draw.ellipse([x - 8, ymid - 8, x + 8, ymid + 8], fill=(*color_rgb, 240), outline=(255, 255, 255, 255), width=2)
        if label:
            self.signal_tag(label, x + 10, ymid, align='left', col=color_rgb)

    def led_chain(self, x, top_row, tag, desc, block='left', color_rgb=(220, 20, 20),
                  marker_dx=-21):
        """LED + 330Ω + GND 한 벌. `x` 는 **신호가 도착하는 열**이다.

        LED 는 그 옆 열, 저항은 그 다음 열에 꽂는다. 같은 행 a~e(또는 f~j)는
        한 노드라 어느 홀이든 이어지지만, **한 홀에는 다리 하나만** 들어간다.
        이전 판은 배선 끝·LED 애노드·LED 캐소드·저항 윗다리를 전부 한 열에
        포개 그렸다 — 그림대로면 한 홀에 둘씩 꽂아야 했다. 사슬은 빈 열 쪽으로
        자란다: 오른쪽에 두 열이 없으면(d 열) 왼쪽으로 간다.

        저항 아래 GND 점퍼는 저항 행에서 **레일에 가장 가까운 빈 홀**에서 뽑는다.
        LED 열에서 뽑으면 왼쪽으로 자란 사슬(도착 d → LED c → 저항 b)의 가로선이
        저항 아랫다리 b 위를 지나간다 — 검정 선 아래 다리가 깔리는 그림이다.

        보드 위에는 **신호 이름만** 붙인다 (L1, X, Z…) — `draw_led()` 가
        `signal_tag()` 로 찍는다. 'L2 최종 LED (L2=A·B·C)' 같은 긴 문구는 결선
        순서표로 내려보낸다 — 손으로 옮겨 그릴 것이 아니면서 정작 그릴 홀을
        가리기 때문이다.
        """
        c = self.cols[block]
        group = [c[k] for k in 'abcde'] if x <= c['e'] else [c[k] for k in 'fghij']
        i = group.index(x)
        step = 1 if i + 2 < len(group) else -1
        x_led, x_res = group[i + step], group[i + 2 * step]
        key = (self.sym(x_led, top_row), self.sym(x_led, top_row + 1),
               self.sym(x_res, top_row + 1), self.sym(x_res, top_row + 3))
        # 기준선에 같은 네 홀의 사슬이 있으면 LED·저항·GND 점퍼 전부 회색이고
        # 번호가 없다 — 앞 단계에서 꽂아 둔 그대로다. 플래그는 사슬을 그리는 동안만 선다
        self._keep_parts = self.baseline is not None and key in self.baseline['chains']
        try:
            y_a, y_k, y_r = self.r_y(top_row), self.r_y(top_row + 1), self.r_y(top_row + 3)
            self.draw_led(x_led, y_a, y_k, color_rgb, tag)
            self.draw_resistor(x_res, y_k, y_r, label="330Ω")
            self.led_chains.append({'tag': tag,
                                    'signal': self.sym(x, top_row),
                                    'anode': self.sym(x_led, top_row),
                                    'cathode': self.sym(x_led, top_row + 1),
                                    'res_top': self.sym(x_res, top_row + 1),
                                    'res_bottom': self.sym(x_res, top_row + 3)})
            self.step_note('sig', self.addr(x_led, y_a), self.addr(x_res, y_r),
                           f'{tag}: LED({self.addr(x_led, y_a)}→{self.addr(x_led, y_k)}) + '
                           f'330Ω({self.addr(x_res, y_k)}→{self.addr(x_res, y_r)}) 직렬 · {desc}',
                           marker_at=(x + marker_dx, y_k))
            x_gnd = self.nearest_gnd_rail(x_led, block)
            free = [x, x_led] + ([group[i + 3 * step]] if 0 <= i + 3 * step < len(group) else [])
            x_from = min(free, key=lambda h: abs(h - x_gnd))
            r_gnd = self.free_rail_row(top_row + 3, x_gnd)
            self.step_wire([(x_from, y_r), (x_gnd, self.r_y(r_gnd))],
                           'gnd', f'{tag} 저항 아래 -> GND',
                           width=2, marker_at=(x_from - 22, y_r + 2))
        finally:
            self._keep_parts = False

    # ---------------- 칩 ----------------

    def _vtext(self, xy, text, fill, font):
        """세로쓰기. 과거 결선도가 칩 이름을 이렇게 적었다 — 몸통 안에 넣으면
        핀 번호를 d·g 열 홀 위에 얹지 않아도 된다."""
        bbox = font.getbbox(text)
        w, h = bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4
        tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((2 - bbox[0], 2 - bbox[1]), text, fill=fill, font=font)
        rot = tmp.rotate(-90, expand=True)
        self.overlay.alpha_composite(rot, (int(xy[0] - rot.width / 2), int(xy[1] - rot.height / 2)))

    def draw_chip(self, name, start_row, block='left'):
        c = self.cols[block]
        x1, x2 = c['chip_x1'], c['chip_x2']
        y_top = self.r_y(start_row) - 8
        y_bot = self.r_y(start_row + 6) + 8

        # 기준선의 같은 자리에 같은 칩이 있으면 몸통을 회색으로 그린다 — 앞
        # 단계에서 꽂아 둔 그대로라는 뜻이다(footer 범례 "회색 = 앞 단계에서
        # 그대로 둔다"). 배선·LED 사슬과 같은 규칙을 칩에도 적용한다.
        prev = (self.baseline['chips'].get((block, start_row))
                if self.baseline is not None else None)
        kept_chip = self.baseline is not None and prev == name
        body_fill = (200, 200, 200, 255) if kept_chip else (30, 33, 36, 255)
        body_outline = KEEP if kept_chip else (130, 140, 150, 255)
        # 몸통이 밝아지면 흰 글씨는 안 보인다 — 진한 회색으로 바꿔 pin 번호·
        # 이름을 계속 읽을 수 있게 한다
        text_fill = (55, 55, 55, 255) if kept_chip else (255, 255, 255, 255)
        num_fill = (90, 90, 90, 255) if kept_chip else (215, 215, 215, 255)

        self.draw.rectangle([x1, y_top, x2, y_bot], fill=body_fill, outline=body_outline, width=2)
        notch_w = (x2 - x1) // 3
        self.draw.arc([x1 + notch_w, y_top - 6, x2 - notch_w, y_top + 6], 0, 180, fill=(200, 200, 200, 255), width=2)
        self._vtext(((x1 + x2) / 2, (y_top + y_bot) / 2), name, text_fill, self.font_chip)

        # 핀 번호는 **몸통 안쪽**에 찍는다. 이전 판은 e-15 / f+6 에 찍어서
        # d 열과 g 열 홀을 가렸다 — 정작 배선을 꽂는 자리다
        for i in range(7):
            y = self.r_y(start_row + i)
            self.draw.line([(c['e'], y), (x1, y)], fill=(170, 170, 170, 255), width=3)
            self.draw.line([(x2, y), (c['f'], y)], fill=(170, 170, 170, 255), width=3)
            self.draw.text((x1 + 3, y - 6), str(i + 1), fill=num_fill, font=self.font_num)
            rt = str(14 - i)
            w = self.draw.textbbox((0, 0), rt, font=self.font_num)[2]
            self.draw.text((x2 - 3 - w, y - 6), rt, fill=num_fill, font=self.font_num)
            self.lead(c['e'], y, f'{name} pin {i + 1}')
            self.lead(c['f'], y, f'{name} pin {14 - i}')

        pins = {}
        for i in range(7):
            pins[i + 1] = self.sym(c['e'], start_row + i)
            pins[14 - i] = self.sym(c['f'], start_row + i)
        self.chips.append({'label': name, 'block': block,
                           'pin1_row': start_row, 'pins': pins})
        if self.baseline is not None:
            if kept_chip:
                self.kept.append(f'{name} 칩 그대로')
            elif prev is None:
                # 빈 자리에 새로 꽂는다 — 뽑을 것이 없으니 "교체"라고 하지 않는다
                self.swaps.append((prev, name, block, start_row))
                self.step_note('sig', '(빈 자리)', f'꽂는다: {name}',
                               f'{"좌" if block == "left" else "우"} {start_row}행에 새로 꽂는다',
                               marker_at=((x1 + x2) // 2, y_top + 12))
            else:
                # 같은 자리의 칩이 다르다 — 실험실에서 첫 번째로 할 일이다
                self.swaps.append((prev, name, block, start_row))
                # 번호 원은 칩 몸통 안, 위쪽 가장자리 근처에 찍는다 — 몸통 위 행은
                # 홀이 있고(복합회로에서는 가로 배선도 지나가) 원이 겹쳐 가린다
                self.step_note('sig', f'뽑는다: {prev}', f'꽂는다: {name}',
                               f'{"좌" if block == "left" else "우"} {start_row}행 칩 교체',
                               marker_at=((x1 + x2) // 2, y_top + 12))

    def bridge_rails(self, x_a, x_b, row, kind='gnd', label=None):
        """물리적으로 분리된 전원 레일 모듈 둘을 잇는 점퍼.

        이 템플릿의 레일쌍(좌 174/190, 중앙좌 468/484, 중앙우 542/558,
        우 836/852)은 각각 **별개 스트립**이다. 칩 7번 핀을 좌측 GND 레일에
        내리고 미사용 입력을 중앙 GND 레일에 내리면 두 레일이 이어져 있지
        않아 미사용 입력이 뜬다. 그 점퍼를 명시적으로 그린다.
        """
        key = (kind, min(x_a, x_b), max(x_a, x_b))
        if key in self._bridged:
            return
        self._bridged.add(key)
        row = self.free_rail_row(row, x_a, x_b)
        self._uf_union(x_a, x_b)
        self.bridges.append((kind, self.sym(x_a, row), self.sym(x_b, row)))
        y = self.r_y(row)
        self.step_wire([(x_a, y), (x_b, y)], kind,
                       '레일 브리지',
                       marker_at=((x_a + x_b) // 2, y - 12))

    def connect_power(self, start_row, block='left', gnd_marker_at=None, gnd_col='d'):
        """pin 14 -> +5V, pin 7 -> GND. `gnd_marker_at` 은 pin 7 번호 원 자리를
        빌더가 지정할 때만 준다 — 기본 자리(레일과 d열 사이, 한 행 위)에 다른
        배선의 모서리가 오는 경우다. `gnd_col` 은 pin 7 접지선이 출발하는 열로,
        `connect_unused_inputs(col=)` 과 같은 이유로 바꾼다.

        어느 레일로 가는지는 블록마다 다르다. 좌측 보드는 f~j 쪽(pin 8~14)이
        중앙 레일에, a~e 쪽(pin 1~7)이 바깥 왼쪽 레일에 붙는다. 우측 보드는
        좌우가 뒤집힌다 — 이전 판은 좌측 기준 배선을 우측에도 그대로 써서
        복합회로 빌더가 전원 배선을 손으로 다시 썼다.

        점퍼는 핀 홀 바로 옆(d·g 열)에서 출발한다 — e·f 열 홀에는 칩 다리가
        꽂혀 있다. `connect_unused_inputs()` 가 처음부터 그렇게 했다.
        """
        c = self.cols[block]
        x_vcc = c['mid_vcc'] if block == 'left' else c['vcc']
        x_gnd = c['gnd'] if block == 'left' else c['mid_gnd']
        r14 = self.free_rail_row(start_row, x_vcc)
        self.step_wire([(c['g'], self.r_y(start_row)), (x_vcc, self.r_y(r14))],
                       'vcc', 'pin 14 -> +5V 레일',
                       marker_at=((c['g'] + x_vcc) // 2, self.r_y(start_row) - 11))
        r7 = self.free_rail_row(start_row + 6, x_gnd)
        self.step_wire([(c[gnd_col], self.r_y(start_row + 6)), (x_gnd, self.r_y(r7))],
                       'gnd', 'pin 7 -> GND 레일',
                       marker_at=gnd_marker_at or ((c['d'] + x_gnd) // 2, self.r_y(start_row + 6) - 11))

    def nearest_gnd_rail(self, x, block='left'):
        """그 자리에서 제일 가까운 GND 레일. 좌우 블록은 a~e 쪽과 f~j 쪽에
        붙는 레일이 서로 뒤집혀 있어서 블록 이름만으로는 못 고른다."""
        c = self.cols[block]
        return min((c['gnd'], c['mid_gnd']), key=lambda xr: abs(xr - x))

    def nearest_vcc_rail(self, x, block='left'):
        c = self.cols[block]
        return min((c['vcc'], c['mid_vcc']), key=lambda xr: abs(xr - x))

    def connect_unused_inputs(self, pins, start_row, block='left', bridge_row=None,
                              chip='', rail='gnd', col='d'):
        """미사용 입력핀을 전원 레일로. 여러 가닥이지만 표에는 **한 줄**로 묶는다.

        `rail='vcc'` 면 GND 가 아니라 +5V 로 올린다. 실험02 교안 p8 도면이
        미사용 입력 일부를 VCC 로 묶으라고 지정한다 — CMOS 입력은 뜨면 안 될
        뿐이지 어느 쪽으로 묶든 상관없고, 도면을 그대로 따르는 편이 대조하기 쉽다.

        `col` 은 pin 1~7 쪽 접지선이 출발하는 열이다 (기본 d — 핀 홀 e 바로 옆).
        그 열 위로 다른 세로선이 지나가면(복합 회로의 초록 A'·B 선이 d열을 탄다)
        접지선 끝점이 그 선 아래 깔리므로 빈 열로 옮긴다.

        착지는 **자기 행에 레일 홀이 있는 핀부터** 한다. 빈 행(8·14·20행)의 핀은
        이웃 행으로 밀리는데, 그 핀이 먼저 착지하면 정작 그 행의 주인 핀이 밀린다.
        """
        c = self.cols[block]
        placed = []
        for p in pins:
            if 1 <= p <= 7:
                placed.append((start_row + (p - 1), c[col], p))
            elif 8 <= p <= 14:
                placed.append((start_row + (14 - p), c['g'], p))
        order = sorted(range(len(placed)), key=lambda i: (not self.is_rail_row(placed[i][0]), i))
        for row, x_pin, p in (placed[i] for i in order):
            pick = self.nearest_vcc_rail if rail == 'vcc' else self.nearest_gnd_rail
            x_rail = pick(x_pin, block)
            r_rail = self.free_rail_row(row, x_rail)
            col = WIRE[rail]
            self.draw.line([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], fill=col, width=2)
            self._segments.append((rail, [(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))],
                                   f'{chip} pin {p} 미사용 입력'))
            self._register_pass([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))])
            self.draw.ellipse([x_pin-3, self.r_y(row)-3, x_pin+3, self.r_y(row)+3], fill=col)
            self.draw.ellipse([x_rail-3, self.r_y(r_rail)-3, x_rail+3, self.r_y(r_rail)+3], fill=col)
            self.lead(x_pin, self.r_y(row), f'{chip} pin {p} 미사용 입력 접지선')
            self.lead(x_rail, self.r_y(r_rail), f'{chip} pin {p} 미사용 입력 접지선')
            self.touch_rail(rail, x_rail)
            self.unused_inputs.append({'chip': chip, 'pin': p, 'rail': rail,
                                       'block': block, 'pin1_row': start_row})

        pin_str = ", ".join(str(p) for p in pins)
        self.step_note(rail, f'{chip} pin {pin_str}',
                       '가까운 +5V 레일' if rail == 'vcc' else '가까운 GND 레일',
                       '미사용 입력 풀업' if rail == 'vcc' else '미사용 입력 접지',
                       count=len(pins))

        if rail == 'gnd' and any(8 <= p <= 14 for p in pins):
            if bridge_row is None:
                print(f"[WARN] {block} 블록 미사용 입력 {pin_str} 이 중앙 GND 레일에 "
                      f"내려갔는데 bridge_row 가 없다 — 7번 핀 레일과 이어지지 않아 "
                      f"뜬다. 빌더에서 bridge_row 를 넘겨라", file=sys.stderr)
            else:
                self.bridge_rails(c['mid_gnd'], c['gnd'], bridge_row, kind='gnd')

    def mark_unused_outputs(self, pins, start_row, block='left', chip=''):
        """미사용 출력은 **아무것도 그리지 않는다.** 개방이 곧 배선 없음이다.

        이전 판은 핀마다 'Pin 8: NC (개방)' 배지를 보드 위에 찍었다. 손으로
        옮겨 그릴 것이 하나도 없는 문구가 정작 그릴 홀을 덮었다.
        """
        for p in pins:
            self.unused_outputs.append({'chip': chip, 'pin': p,
                                        'block': block, 'pin1_row': start_row})
        pin_str = ", ".join(str(p) for p in pins)
        self.note(f'{chip} 미사용 출력 pin {pin_str} 은 **아무 데도 연결하지 않는다** '
                  f'— 개방(NC). GND 로 내리거나 출력끼리 묶으면 칩이 상한다.')

    def mark_unused_inputs(self, pins, start_row, block='left', chip=''):
        """미사용 게이트 입력을 **개방**으로 등록한다. 아무것도 그리지 않는다.

        2026-09-11 실험01 실측: 미사용 입력을 접지하지 않아도 진리표가 같았고,
        접지선은 NAND 순서표 20줄 중 12줄이었다. 학교 규정도 아니다(운영계획서
        3.2 6) 은 손그림·학번·이름·날짜만 요구한다). 그래서 뺀다 — 교안이
        미사용 핀 처리를 지시한 주차(실험02 p8)만 `connect_unused_inputs` 로
        그린다. **사용하는 게이트의 입력은 여전히 반드시 물린다** — 그쪽이
        R5ⓒ 가 잡는 진짜 결함이다.
        """
        for p in pins:
            self.unused_inputs.append({'chip': chip, 'pin': p, 'rail': None,
                                       'block': block, 'pin1_row': start_row})
        pin_str = ", ".join(str(p) for p in pins)
        self.note(f'{chip} 미사용 입력 pin {pin_str} 은 접지하지 않는다 — 결과에 영향 '
                  '없음(실험01 실측). 사용하는 게이트의 입력만 반드시 물린다.')

    # ---------------- 내보내기 ----------------

    def _wrap(self, text, font, max_w):
        out, line = [], ''
        for ch in text:
            if self.draw.textlength(line + ch, font=font) > max_w and line:
                out.append(line)
                line = ch
            else:
                line += ch
        if line:
            out.append(line)
        return out

    def _draw_footer(self, im, y0):
        """보드 아래 흰 띠에 **범례 + 결선 순서표**.

        보드 위에서 걷어낸 규칙 문구가 여기로 내려온다. 손으로 그리는 사람은
        그림 전체를 한 번에 볼 필요 없이 이 표를 위에서 아래로 지워가며
        한 줄씩 그린다 — 30가닥을 동시에 보는 문제가 사라진다.
        """
        d = ImageDraw.Draw(im)
        x_pad = 28
        d.line([(x_pad, y0), (998 - x_pad, y0)], fill=(190, 195, 200, 255), width=1)
        y = y0 + 14

        # 색 규칙 범례는 순서표를 켠 그림에만 붙인다. 지금은 13장 빌더가 전부
        # 켜므로 전부 붙고, 전부 참이다 — e1·e2 가릴 것 없이 `WIRE` 네 색만 쓴다
        if self.numbered:
            d.text((x_pad, y), "배선 색 규칙", fill=(20, 40, 90, 255), font=self.font_kr_bold)
            x = x_pad + 84
            for kind in ('vcc', 'gnd', 'sig', 'mid'):
                d.line([(x, y + 7), (x + 24, y + 7)], fill=WIRE[kind], width=4)
                d.text((x + 30, y), KIND_KR[kind], fill=(60, 60, 60, 255), font=self.font_step)
                x += 96
            if self.probes:
                for k in range(0, 24, 12):
                    d.line([(x + k, y + 7), (x + k + 7, y + 7)], fill=PROBE, width=3)
                d.text((x + 30, y), '계측기(점선 — 꽂는 게 아니라 문다)',
                       fill=(60, 60, 60, 255), font=self.font_step)
            y += 24

        for n in self.notes:
            for ln in self._wrap('· ' + n.replace('**', ''), self.font_step, 998 - 2 * x_pad):
                d.text((x_pad, y), ln, fill=(90, 70, 70, 255), font=self.font_step)
                y += 15
        if self.baseline is not None:
            d.text((x_pad, y),
                   f'· 회색 = 앞 단계에서 그대로 둔다 ({len(self.kept)}개). 번호 = 이번 단계에서 새로 한다',
                   fill=(90, 90, 90, 255), font=self.font_step)
            y += 15
            gone = self.removed()
            if gone:
                y += 6
                d.text((x_pad, y), "앞 단계에서 걷는다 — 먼저 뽑고 ☐ 를 채운다",
                       fill=(160, 30, 30, 255), font=self.font_kr_bold)
                y += 20
                for g in gone:
                    d.rectangle([x_pad, y + 2, x_pad + 11, y + 13],
                                outline=(120, 125, 130, 255), width=1)
                    lines = self._wrap('걷기: ' + g, self.font_step, 998 - 2 * x_pad - 20)[:2]
                    for k, ln in enumerate(lines):
                        d.text((x_pad + 18, y + k * 14), ln, fill=(160, 30, 30, 255), font=self.font_step)
                    y += max(18, len(lines) * 14 + 4)
        y += 8

        if not (self.numbered and self.steps):
            return self._draw_probe_table(d, y, x_pad) if self.probes else y

        d.line([(x_pad, y), (998 - x_pad, y)], fill=(225, 228, 232, 255), width=1)
        y += 12
        d.text((x_pad, y), "결선 순서 — 위에서 아래로 한 줄씩 그리고 ☐ 를 채운다",
               fill=(20, 40, 90, 255), font=self.font_kr_bold)
        y += 22

        col_w = (998 - 2 * x_pad) // 2
        text_w = col_w - 58
        blocks = []
        for st in self.steps:
            mult = f" x{st['count']}" if st['count'] > 1 else ""
            blocks.append((st, self._wrap(f"{st['frm']} → {st['to']}{mult} · {st['desc']}",
                                          self.font_step, text_w)[:2]))

        # 두 단으로 나눈다. 줄 수 기준으로 갈라야 단 높이가 맞는다
        total = sum(len(b[1]) for b in blocks)
        half, acc, cut = (total + 1) // 2, 0, len(blocks)
        for i, b in enumerate(blocks):
            if acc >= half:
                cut = i
                break
            acc += len(b[1])

        bottom = y
        for ci, chunk in enumerate((blocks[:cut], blocks[cut:])):
            cx, cy = x_pad + ci * col_w, y
            for st, lines in chunk:
                d.rectangle([cx, cy + 2, cx + 11, cy + 13], outline=(120, 125, 130, 255), width=1)
                self._marker_on(d, cx + 28, cy + 8, st['n'], WIRE[st['kind']])
                for k, ln in enumerate(lines):
                    d.text((cx + 42, cy + k * 14), ln, fill=(45, 45, 45, 255), font=self.font_step)
                cy += max(18, len(lines) * 14 + 4)
            bottom = max(bottom, cy)
        y = bottom + 14
        return self._draw_probe_table(d, y, x_pad) if self.probes else y + 10

    def _draw_probe_table(self, d, y, x_pad):
        """계측표. 결선표와 **따로** 쌓는다 — 프로브는 꽂는 게 아니라 무는 것이라
        결선 순서에 섞으면 조원이 점퍼선을 찾게 된다."""
        d.line([(x_pad, y), (998 - x_pad, y)], fill=(225, 228, 232, 255), width=1)
        y += 12
        d.text((x_pad, y), "계측 · 신호원 — 어디에 무는가 (배선이 아니다)",
               fill=(20, 40, 90, 255), font=self.font_kr_bold)
        y += 22
        for pr in self.probes:
            d.rectangle([x_pad, y + 2, x_pad + 11, y + 13], outline=(120, 125, 130, 255), width=1)
            d.text((x_pad + 20, y), f"{pr['n']}.", fill=PROBE, font=self.font_step)
            lines = self._wrap(f"{pr['label']} → {pr['at']} · {pr['desc']}",
                               self.font_step, 998 - 2 * x_pad - 60)[:2]
            for k, ln in enumerate(lines):
                d.text((x_pad + 42, y + k * 14), ln, fill=(45, 45, 45, 255), font=self.font_step)
            y += max(18, len(lines) * 14 + 4)
        return y + 10

    def _marker_on(self, d, x, y, n, color):
        d.ellipse([x-8, y-8, x+8, y+8], fill=(255, 255, 255, 245), outline=color, width=2)
        t = str(n)
        bbox = d.textbbox((0, 0), t, font=self.font_num)
        d.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
               t, fill=color, font=self.font_num)

    def _endpoint(self, p):
        """배선 끝점 -> `('jack', 색)` 또는 `('hole', (블록, 열, 행))`. `wiring()`
        과 기준선 비교가 **같은 규칙**을 써야 해서 한 자리에 둔다."""
        x, y = p
        if y < 240 and any(abs(x - jx) < 30 for jx in JACKS.values()):
            color = min(JACKS, key=lambda k: abs(JACKS[k] - x))
            return ('jack', color)
        return ('hole', self.sym(x, self._row_of(y)))

    def _sym_addr(self, end):
        """`_endpoint()` 출력 -> '좌 b10' 처럼 읽히는 주소. `addr()` 과 같은 말이다."""
        if end[0] == 'jack':
            return '전원잭'
        block, col, row = end[1]
        name = self._addr_map[self.cols[block][col]]
        return f'{name}{row}행' if '레일' in name else f'{name}{row}'

    def snapshot(self):
        """이 보드의 배선·사슬·칩을 **다음 보드의 기준선**으로 쓸 수 있게 낸다."""
        w = self.wiring()
        return {
            'wires': {(x['kind'], x['frm'], x['to']): x['desc'] for x in w['wires']},
            'chains': {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom']): ch['tag']
                       for ch in w['chains']},
            'chips': {(ch['block'], ch['pin1_row']): ch['label'] for ch in w['chips']},
        }

    def removed(self):
        """기준선에 있었는데 이번 보드에 없는 것 — 실험실에서 **걷을** 것."""
        if self.baseline is None:
            return []
        drawn = {(k, self._endpoint(pts[0]), self._endpoint(pts[-1]))
                 for k, pts, _ in self._segments}
        out = []
        for key, desc in self.baseline['wires'].items():
            if key not in drawn:
                out.append(f'{self._sym_addr(key[1])} → {self._sym_addr(key[2])} · {desc}')
        here = {(c['block'], c['pin1_row']) for c in self.chips}
        for key, label in self.baseline['chips'].items():
            if key not in here:
                out.append(f'칩 {label} ({"좌" if key[0] == "left" else "우"} {key[1]}행) 뽑는다')
        chains = {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom'])
                  for ch in self.led_chains}
        for key, tag in self.baseline['chains'].items():
            if key not in chains:
                out.append(f'LED {tag} 사슬 ({self._sym_addr(("hole", key[0]))}~'
                           f'{self._sym_addr(("hole", key[3]))}) 뽑는다')
        return out

    def wiring(self):
        """이 그림이 무엇을 어디에 꽂았는지 **기호 좌표**로 낸다.

        손그림 검토(`review-hand-diagram`)가 정답으로 쓴다. 픽셀이 아니라
        (블록, 열, 행) 으로 내는 이유는 손그림 전사가 '좌 b10' 같은 주소로
        적히기 때문이다 — 양쪽을 같은 말로 맞춰야 비교가 된다.

        `overlaps` 는 `verify()` 가 채운다. `export()` 를 거친 렌더러면 차 있고,
        아니면 비어 있다. 참조 그림에서 **잘 안 보이는 선**을 판정문에 주석으로
        달기 위한 것이다 — 복합회로의 A 갈래가 초록 Z 선 아래 깔려 있어서
        따라 그린 사람이 통째로 빠뜨렸다.
        """
        wires = [{'kind': kind, 'desc': desc,
                  'frm': self._endpoint(pts[0]), 'to': self._endpoint(pts[-1])}
                 for kind, pts, desc in self._segments]
        return {
            'chips': list(self.chips),
            'wires': wires,
            'inputs': [dict(i) for i in self.inputs],
            'leds': list(self.leds),
            'resistors': list(self.resistors),
            'chains': list(self.led_chains),
            'unused_inputs': list(self.unused_inputs),
            'unused_outputs': list(self.unused_outputs),
            'bridges': list(self.bridges),
            'overlaps': list(self.overlap_warnings),
        }

    def input_node(self, name, x, row):
        """**방금 그린 배선**을 입력 점퍼로 적어 둔다 (`_input_jumper` 가 부른다).

        입력 점퍼는 지금 GND 레일에 꽂혀 있다 — 0 을 준 자리를 그린 것이고,
        1 을 줄 때는 레일 쪽 끝만 VCC 레일로 옮긴다. 넷 검사가 이걸 레일
        연결로 세면 입력 A·B·C 가 GND 와 한 넷이 되어 "pin 1 이 입력 A 에
        물렸는가" 를 물을 수 없다. 그래서 그 끝을 가상 입력 노드로 바꿔 센다.

        넷을 정하는 것은 `seg` 하나다. `x`·`row` 는 좌표를 뜻하는 인자가 아니라
        **직전 세그먼트가 정말 그 홀에서 끝났는지 확인하는 단언**이다 — "이
        함수는 `step_wire()` 바로 뒤에 온다" 는 관례를 여기서 강제한다. 관례로
        두면 사이에 배선 한 줄이 끼는 순간 엉뚱한 세그먼트의 끝이 가상 노드로
        바뀌고, 그림은 멀쩡하게 나온다.
        """
        seg = len(self._segments) - 1
        assert seg >= 0, f'input_node({name}) 앞에 step_wire() 가 없다'
        ex, ey = self._segments[seg][1][-1]
        end, here = self.sym(ex, self._row_of(ey)), self.sym(x, row)
        assert end == here, (
            f'input_node({name}) 이 가리키는 홀 {here} 이 직전 배선의 끝점 {end} 과 '
            f'다르다 — input_node() 는 그 입력 점퍼를 그린 step_wire() 바로 뒤에 와야 한다')
        self.inputs.append({'name': name, 'at': here, 'seg': seg})

    _AE = ('a', 'b', 'c', 'd', 'e')
    _FJ = ('f', 'g', 'h', 'i', 'j')

    def _strip(self, sym):
        """기호 좌표 -> 스트립 키. **홀이 아니라 스트립이 넷의 단위다.**

        단자대는 한 행의 a~e 가 한 스트립, f~j 가 또 한 스트립이다 (가운데
        골이 갈라 놓는다). 전원 레일은 열 하나가 통째로 한 스트립이라 행이
        없다 — 레일쌍 넷이 서로 별개 스트립인 것은 x 가 다르기 때문이다.
        """
        if sym is None:
            return None
        block, col, row = sym
        if col in self._AE:
            return (block, 'ae', row)
        if col in self._FJ:
            return (block, 'fj', row)
        return ('rail', self.cols[block][col])

    def _pin_label(self, ch, p):
        """칩 핀의 넷 라벨. 한 그림에 같은 칩이 둘이면(`e2_tpd`) 행으로 갈린다."""
        return f"{ch['label']}#{ch['pin1_row']} pin {p}"

    def _lead_labels(self):
        """부품 다리의 (넷 라벨, 기호 좌표) 목록. LED 두 다리, 저항 두 다리.

        `nets()` 와 R5ⓒ 가 **같은 말**을 써야 해서 한 자리에 둔다 — 한쪽만
        고치면 "뜬 다리" 판정이 자기 라벨을 넷에서 못 찾고 조용히 넘어간다.
        """
        out = []
        for led in self.leds:
            out.append((f"LED {led['tag']} 애노드", led['anode']))
            out.append((f"LED {led['tag']} 캐소드", led['cathode']))
        for i, r in enumerate(self.resistors, 1):
            out.append((f"저항{i}({r['label']}) 윗다리", r['top']))
            out.append((f"저항{i}({r['label']}) 아랫다리", r['bottom']))
        return out

    def nets(self, substitute_inputs=True):
        """그린 것을 **전기적 넷**으로 묶어 낸다.

        -> `[{'labels': {'74HC32#10 pin 1', '입력 A', ...}, 'rails': {'vcc'}}, ...]`

        `_leads` 는 홀 단위라 이 층위를 못 본다 — 같은 스트립의 다른 홀에 꽂은
        두 점퍼는 홀이 다르지만 **전기적으로 한 점**이다. 2026-09-09 의 결함
        둘이 정확히 그 틈으로 지나갔다.

        `desc` 문자열은 읽지 않는다. `chips`·`leds`·`resistors`·`_segments`·
        `inputs` 라는 **구조**만 읽는다 — 말이 바뀔 때 조용히 깨지지 않도록.

        `substitute_inputs=False` 면 입력 점퍼의 레일 끝을 **치환하지 않는다.**
        치환된 넷은 "무엇이 무엇에 물렸는가" 를 묻기 위한 것이라 그 배선이 실재로
        잇고 있는 레일을 지운다 — 그림 그대로 꽂았을 때의 단락(R5ⓑ)은 지우지
        않은 넷에서만 보인다. 라벨·뜬 핀 판정은 치환한 넷을 쓴다.
        """
        uf = {}

        def find(k):
            uf.setdefault(k, k)
            while uf[k] != k:
                uf[k] = uf[uf[k]]
                k = uf[k]
            return k

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                uf[rb] = ra

        members = {}

        def put(strip, label):
            if strip is not None:
                members.setdefault(strip, set()).add(label)
                find(strip)

        for ch in self.chips:
            for p, sym in ch['pins'].items():
                put(self._strip(sym), self._pin_label(ch, p))
        for label, sym in self._lead_labels():
            put(self._strip(sym), label)
        for x, name in self._addr_map.items():
            if x in self._rail_xs():
                put(('rail', x), name)

        # 입력 점퍼는 레일 쪽 끝을 가상 노드로 바꾼다 (`input_node()` 참조).
        # 끄면 그린 그대로 — 레일 끝이 레일로 남는다
        sub = {}
        if substitute_inputs:
            for inp in self.inputs:
                sub[inp['seg']] = ('input', inp['name'])
                put(('input', inp['name']), f"입력 {inp['name']}")

        for i, (kind, pts, desc) in enumerate(self._segments):
            ends = []
            for p in (pts[0], pts[-1]):
                if p[1] < 240 and any(abs(p[0] - jx) < 30 for jx in JACKS.values()):
                    color = min(JACKS, key=lambda k: abs(JACKS[k] - p[0]))
                    ends.append(('jack', color))
                    put(('jack', color), f'{JACK_KR[color]} 잭')
                else:
                    ends.append(self._strip(self.sym(p[0], self._row_of(p[1]))))
            if i in sub:
                ends = [sub[i] if e is not None and e[0] == 'rail' else e for e in ends]
            if ends[0] is None or ends[1] is None:
                continue   # 홀이 아닌 끝점은 R1 이 따로 잡는다
            union(ends[0], ends[1])

        groups = {}
        for strip in list(uf):
            groups.setdefault(find(strip), []).append(strip)
        out = []
        for strips in groups.values():
            labels = set()
            rails = set()
            for st in strips:
                labels |= members.get(st, set())
                if st[0] == 'rail':
                    rails.add(self._rail_kind.get(st[1]))
            out.append({'labels': labels, 'rails': rails - {None}})
        return out

    def verify(self):
        """그림대로 꽂을 수 있는지 검사한다. 내보내기 직전에 돈다.

        좌표표가 어긋나도, 선이 허공에서 출발해도 그림은 그럴듯하게 나온다 —
        눈으로는 안 잡힌다. 2026-09-07 까지는 주소 문자열에 '레일' 이 든 끝점의
        빈 행만 봤고, 허공(x=95)에서 온 입력선은 '보드밖(입력)' 이라는 이름을
        달고 그 틈으로 지나갔다. 지금은 점유표(`_leads`)를 본다.

        R1  모든 끝점은 실제 홀이다 (전원잭만 예외).
        R2  한 홀에는 리드 하나만 들어간다 — 점퍼·부품 다리·칩 핀 전부.
        R3  배선 끝점·부품 다리 위를 다른 배선이 지나가지 않는다 — 넷 무관.
        R4  서로 다른 배선이 같은 축 위에 포개지지 않는다 (`overlap_policy`).
        R5  넷이 말이 된다 — 같은 스트립 안에서 끝나는 점퍼가 없고, +5V 와
            GND 가 한 넷이 아니며(치환하지 않은 넷에서 본다), 아무 데도 안 물린
            칩 핀도 부품 다리도 없다.
        R6  배선이 자기 스트립 안을 달리는 구간이 없다 — 뒤쪽 홀에서 출발하면
            되는 우회다. R5ⓐ 가 양 끝점만 보는 틈으로 지나간 부류다.
        그리고 레일 연결성 — 같은 전원을 나르는 레일이 브리지로 이어져 있는가.

        R1~R4 는 전부 **기하**다. 2026-09-09 까지 "이 배선이 무엇을 잇는가" 는
        아무도 안 봤고, 그 틈으로 결함 둘이 지나갔다 — 복합 회로의 `우 a10 →
        우 b10` 은 같은 스트립 안이라 아무 일도 안 하면서 74HC32 pin 1 을 뜬
        채로 뒀고, 실험02 Rn 은 1kΩ 아랫다리가 pin 5 행에 앉아 +5V 를 GND 로
        직결시켰다. 더 나쁜 것은 R3 를 통과시키려는 재배치가 첫 결함을 만들었고
        검사는 오히려 통과로 바뀌었다는 점이다. 그래서 R5 를 넣었다.
        """
        bad = [f'홀이 아니다: {s}' for s in self._not_holes]
        bad += [f'한 홀에 리드 둘: {s}' for s in self._double]
        bad += [f'끝점이 다른 배선 아래 깔린다: {s}' for s in self._endpoints_under_wires()]

        # R4. 다른 배선끼리 같은 축 위에 포개지면 그림에서 한 선으로 보인다.
        # overlap_warnings 는 **이번 verify() 의 결과**다 — 포개짐이 없으면 비운다.
        # 축 위 포개짐은 한쪽 끝점이 상대 구간 안에 있다는 뜻이라 R3 에도 걸린다 —
        # R4 는 "두 넷이 한 선으로 보인다" 는 진단을 덧붙이는 역할이고, 경고 모드는
        # R4 문구만 낮춘다 (R3 는 그래도 던진다)
        overlaps = self._overlaps()
        self.overlap_warnings = overlaps
        if overlaps:
            msg = '배선이 포개졌다:\n  ' + '\n  '.join(overlaps)
            if self.overlap_policy == 'strict':
                bad.append(msg)
            else:
                print(f'[WARN] {msg}', file=sys.stderr)
        if bad:
            raise AssertionError('그림대로 꽂을 수 없다:\n  ' + '\n  '.join(bad))

        # R5. 넷 검사. 여기까지는 전부 기하였다 — 그림대로 꽂을 수는 있지만
        # 꽂아 봐야 회로가 아닌 그림을 여기서 잡는다
        r5 = []
        input_segs = {inp['seg'] for inp in self.inputs}
        for i, (kind, pts, desc) in enumerate(self._segments):
            if i in input_segs:
                continue   # 입력 점퍼의 레일 끝은 가상 노드다 (`input_node()`)
            a = self._strip(self.sym(pts[0][0], self._row_of(pts[0][1])))
            b = self._strip(self.sym(pts[-1][0], self._row_of(pts[-1][1])))
            if a is not None and a == b:
                r5.append(f'같은 스트립 안에서 끝나는 점퍼(전기적으로 무의미): {desc}')

        # R6. 자기 스트립 안을 달리는 구간. 꺾임점 둘이 같은 스트립이면 그
        # 구간은 전기적으로 없는 것과 같다 — 뒤쪽 홀에서 출발하면 그만이다.
        # R5ⓐ 는 배선의 **양 끝점**만 봐서, 자기 스트립 안을 지나다 밖으로
        # 나가는 배선은 끝점이 서로 달라 통과했다. 2026-09-10 OR 의 ⑪ 갈래
        # (`좌 c12 → 좌 a12 → 좌 a24`)가 그 틈으로 이틀을 살아남았다.
        for kind, pts, desc in self._segments:
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                if self.hole_at(ax, ay) is None or self.hole_at(bx, by) is None:
                    continue   # 잭(보드 밖)이나 여백을 지나는 구간은 볼 것이 없다
                sa = self._strip(self.sym(ax, self._row_of(ay)))
                sb = self._strip(self.sym(bx, self._row_of(by)))
                if sa is not None and sa == sb:
                    r5.append(f'자기 스트립 안을 달리는 구간(없어도 되는 우회): '
                              f'{self.addr(ax, ay)} -> {self.addr(bx, by)} · {desc}')

        nets = self.nets()
        # 단락만은 **치환하지 않은 넷**에서 본다. 입력 점퍼가 지금 꽂혀 있는
        # 레일은 가상 노드가 아니라 실재 배선이다 — 그 점퍼가 꽂힌 스트립이
        # 이미 VCC 에 물려 있으면 그림 그대로가 GND↔VCC 직결인데, 치환한 넷에서는
        # 그 레일이 지워져 아무 일도 없어 보인다
        for net in self.nets(substitute_inputs=False):
            if {'vcc', 'gnd'} <= net['rails']:
                r5.append('+5V 와 GND 가 한 넷이다 — 단락: '
                          + ', '.join(sorted(net['labels'])))

        # 아무 데도 안 물린 것. 넷에 자기 라벨 하나뿐이면 그림에는 있으되
        # 회로에는 없다. 미사용 출력(개방 NC)과 계측기가 무는 자리는 뺀다 —
        # 실험02 는 점퍼가 아니라 프로브로 신호를 넣고 뺀다. 덜 그린
        # 그림(`partial`)도 통째로 뺀다: 칩 핀도 부품 다리도 아직 안 붙었을 수 있다
        probe_strips = {self._strip(p['sym']) for p in self.probes if p.get('sym')}
        # 면제 키에 **칩 라벨이 없다.** 넣으면 `build_e2_tpd` 가 깨진다 — 거기서
        # `draw_chip` 라벨은 '74HC04' 인데 `mark_unused_outputs(chip='U2')` 라
        # 키가 어긋나고, U2 의 미사용 출력 6개가 전부 뜬 핀 오탐이 된다.
        # 그리고 "같은 블록·같은 pin1_row 에 칩 둘은 없다" 는 것은 관례가 아니라
        # **R2 가 강제한다** — 그렇게 두면 `draw_chip` 이 e·f 열 홀에 리드를 둘씩
        # 꽂아 `_double` 에 걸리고, 그건 R5 보다 먼저 던진다
        open_pins = {(u['block'], u['pin1_row'], u['pin']) for u in self.unused_outputs}
        # 개방으로 등록한 미사용 입력(`mark_unused_inputs`, rail None)도 뜬 핀이
        # 아니다. 접지한 것(rail 'gnd'/'vcc')은 배선이 있으므로 여기 올 일이 없다
        open_pins |= {(u['block'], u['pin1_row'], u['pin'])
                      for u in self.unused_inputs if u.get('rail') is None}
        # (라벨, 스트립, 조사, 무엇이라 부를지). 칩 핀만 보던 것을 부품 다리까지 넓혔다 —
        # 양끝이 다 빈 스트립에 걸친 저항은 아무 규칙도 안 보고 지나갔고, 그림대로
        # 꽂으면 무부하 V_OL 을 재게 되는데 **실험실에서는 아무 이상이 없어 보인다.**
        # 짝이 있는 다리는 넷에 라벨이 둘 이상이라(예: {저항1(1kΩ) 윗다리, 좌
        # VCC레일}) 오탐이 나지 않는다
        checked = []
        if not self.partial:
            for ch in self.chips:
                for p, sym in ch['pins'].items():
                    if (ch['block'], ch['pin1_row'], p) in open_pins:
                        continue
                    checked.append((self._pin_label(ch, p), self._strip(sym), '이', '뜬 핀'))
            for label, sym in self._lead_labels():
                checked.append((label, self._strip(sym), '가', '뜬 다리'))
        for lab, strip, josa, what in checked:
            if strip in probe_strips:
                continue
            for net in nets:
                if lab in net['labels']:
                    if len(net['labels']) == 1:
                        r5.append(f'{lab} {josa} 아무 데도 안 물렸다 — {what}')
                    break

        if r5:
            raise AssertionError('넷이 틀렸다:\n  ' + '\n  '.join(r5))

        # 레일 연결성. 같은 전원을 나르는 레일들이 브리지로 이어져 있지
        # 않으면, 그림대로 꽂았을 때 전원이 안 간다. 눈으로는 절대 안 잡힌다 —
        # 레일마다 배선이 얌전히 꽂혀 있고 색도 맞기 때문이다
        for kind in ('vcc', 'gnd'):
            rails = self._touched[kind]
            if len(rails) <= 1:
                continue
            groups = {}
            for x in rails:
                groups.setdefault(self._uf_find(x), []).append(x)
            if len(groups) > 1:
                desc = ' / '.join(
                    '+'.join(sorted(self._addr_map.get(x, str(x)) for x in g))
                    for g in groups.values())
                raise AssertionError(
                    f'{KIND_KR[kind]} 레일이 끊겨 있다 — 브리지가 없다: {desc}\n'
                    '  레일쌍 넷은 별개 스트립이다. bridge_rails() 로 이어라.')

    def export(self, output_path, max_row=35):
        self.verify()
        final_im = Image.alpha_composite(self.im, self.overlay)
        board_h = self.r_y(max_row) + 20
        board = final_im.crop((0, 0, 998, board_h)).convert('RGB')

        canvas = Image.new('RGB', (998, board_h + 1400), (255, 255, 255))
        canvas.paste(board, (0, 0))
        used = self._draw_footer(canvas, board_h)
        out = canvas.crop((0, 0, 998, min(used, canvas.height)))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out.save(output_path)
        print(f"[SUCCESS] Exported: {output_path} "
              f"({out.size[0]}x{out.size[1]}, 결선 {len(self.steps)}단계)")


def _tag(bb, x, y, text, col=(60, 60, 60, 255)):
    """보드 **밖** 꼬리표 — 꽂을 자리(`입력 A → b7`). 신호 이름은 `signal_tag()` 가 보드 안에 둔다."""
    bb.draw_badge(x, y, text, (255, 255, 255, 235), col, font=bb.font_kr_sm, pad=2)


def _input_jumper(bb, c, row, name, target, marker=(130, 0), col='b'):
    """입력 한 줄: **좌 GND 레일 홀 → 같은 행 `col` 열(기본 b)**. GND(=0) 자리를 그린 것이다.

    `col` 은 같은 스트립에 **두 번째 점퍼(갈래)** 를 꽂을 때 쓴다. 갈래를 옆 홀에
    꽂되 그 갈래가 입력선 위를 되짚어 나가면 밑동이 굵은 입력선 아래 깔려
    "굵은 선 중간에서 얇은 선이 솟는" 그림이 된다 (2026-09-08 지적). 그래서
    입력선은 a 열에서 멈추고 갈래는 b 열에서 **세로로** 빠져나가게 한다.

    이전 판은 보드 밖 x=95 허공에서 선을 끌어왔다. 브레드보드 그림에서 홀이
    아닌 데서 나오는 선은 꽂을 데가 없다 — 따라 그리는 사람이 왼쪽 끝을 어디에
    꽂아야 하는지 알 수 없었다. netlist 공통 규칙(입력은 +5V 나 GND 에 직접
    물린다)대로 레일 홀에서 출발시키고, 1 을 줄 때는 레일 쪽 끝만 빨간 VCC
    레일로 옮겨 꽂는다고 범례에 적는다.

    레일에 홀이 없는 행(8·14·20행 따위)이나 이웃 입력이 이미 쓴 홀은
    `free_rail_row()` 가 피해 준다 — 7행·8행에 나란히 들어가는 A·B 는 B 가
    9행 홀에서 비스듬히 들어간다. `connect_unused_inputs()` 와 같은 관례다.

    번호 원은 기본으로 **레일 왼쪽 x=130, 행 높이 그대로** 둔다. 선이 레일에서
    시작하니 그 자리는 비어 있고, 선과 같은 높이라 어느 줄 번호인지 바로 읽힌다.
    단 템플릿에 행 번호가 인쇄된 10·20·30행은 거기가 막혀 있으니 레일과 a열
    사이 여백 `(215, ±13)` 으로 피한다. 꼬리표에는 꽂을 자리(b10)를 그대로
    적는다 — 왼쪽 눈금이 10·20·30 뿐이라 이름만 있으면 홀을 세어야 한다.

    **이름은 보드 안에도 적는다** — 레일 쪽 끝 옆, 보드 좌 테두리와 좌 GND 레일
    사이 여백이다(`signal_tag()`). 2026-09 실험01 예보가 "입력 A·B·C 위치 표기가
    없다" 로 감점됐다(-1) — 이름이 보드 밖 꼬리표에만 있었고 학생은 판형 위만
    따라 그렸다. 레일과 a 열 사이 여백은 쓰지 않는다: 복합 회로의 Z 급전선(x=212)이
    10~25행을 세로로 지나고, 번호 원 `(215, ±13)` 도 거기 앉는다(2026-09-14 실측).
    """
    r_rail = bb.free_rail_row(row, c['gnd'])
    bb.step_wire([(c['gnd'], bb.r_y(r_rail)), (c[col], bb.r_y(row))], 'sig',
                 f'입력 {name} -> {target} · 1 이면 레일 쪽 끝을 +5V 레일로 옮긴다',
                 marker_at=(marker[0], bb.r_y(row) + marker[1]))
    bb.input_node(name, c[col], row)
    _tag(bb, 12, bb.r_y(row) - 8, f"입력 {name} → {col}{row}")
    # 신호 이름은 보드 안, 레일 쪽 끝 옆. 0/1 을 바꿀 때 옮겨 꽂는 바로 그 끝이다
    bb.signal_tag(name, (BOARD_LEFT + c['gnd']) / 2, bb.r_y(r_rail),
                  seg=len(bb._segments) - 1)


# ---------------------------------------------------------------------------
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
E1_BOARDS = [
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
E1_FINALS = [
    ("실험01_1-2_결선도_3입력_OR.png", build_e1_or),
    ("실험01_2-1_결선도_3입력_NAND.png", build_e1_nand),
    ("실험01_2-2_결선도_3입력_NOR.png", build_e1_nor),
    ("실험01_3_결선도_복합논리회로.png", build_e1_comb),
]


def _e1_baseline(index, template_path=None):
    """`E1_BOARDS[index]` 의 기준선 = 바로 앞 보드의 `snapshot()`. 첫 보드는 None.

    앞 보드는 기준선 **없이** 그린다 — 배선 집합은 기준선과 무관하므로(색과
    번호만 달라진다) 재귀가 없다. 임시 파일에 그리고 버린다.
    """
    if index == 0:
        return None
    _name, fn, stage = E1_BOARDS[index - 1]
    with tempfile.TemporaryDirectory() as d:
        return fn(os.path.join(d, 'prev.png'), template_path, stage=stage).snapshot()


def _e1_board(index, output_path, template_path=None):
    _name, fn, stage = E1_BOARDS[index]
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


def build_e1_all(output_dir, template_path=None):
    """실험 1 결선도 13장 — 절차 9장(기준선 사슬) + 완성본 4장(기준선 없음)."""
    os.makedirs(output_dir, exist_ok=True)
    base = None
    for filename, fn, stage in E1_BOARDS:
        bb = fn(os.path.join(output_dir, filename), template_path, stage=stage, baseline=base)
        base = bb.snapshot()
    for filename, fn in E1_FINALS:
        fn(os.path.join(output_dir, filename), template_path)
    print(f"[SUCCESS] 실험01 결선도 {len(E1_BOARDS) + len(E1_FINALS)}장 생성: {output_dir}")


# ---------------------------------------------------------------------------
# 실험 2 · CMOS 회로의 전기적 특성
#
# 실험 1 과 성격이 다르다. **정답표가 없다** — LED 가 켜지는지 보는 게 아니라
# 함수발생기로 흔들고 오실로스코프·DMM 으로 읽는다. 그래서 그림에 두 층이 더
# 필요하다.
#
#   · 배선(점퍼선으로 꽂는 것)   -> `step_wire`, 결선 순서표
#   · 계측(프로브·집게로 무는 것) -> `instrument`, 계측표, 회색 점선
#
# 둘을 한 표에 섞으면 조원이 프로브 자리에 점퍼선을 찾는다.
#
# 미사용 입력 처리도 실험 1 과 다르다. 교안 p8 도면이 **일부는 GND, 일부는
# VCC** 로 묶으라고 지정한다 (pin 3·5 -> GND / pin 9·11·13 -> VCC). CMOS 입력은
# 뜨지만 않으면 어느 쪽이든 되지만, 도면대로 따라야 실험실에서 대조가 된다.
#
# 근거: `보고서/실험02/결선도/netlist.md` (C1~C5), `체크리스트/명세.md`.

_E2_UNUSED_GND = [3, 5]        # 교안 p8: 미사용 입력 중 GND 로 내리는 것
_E2_UNUSED_VCC = [9, 11, 13]   # 교안 p8: VCC 로 올리는 것
_E2_UNUSED_OUT = [4, 6, 8, 10, 12]


def _e2_power(bb, block='left'):
    """잭 -> 바깥 레일 -> 중앙 레일. 레일쌍은 별개 스트립이라 브리지가 필수다."""
    c = bb.cols[block]
    bb.connect_jacks()
    bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
    bb.bridge_rails(c['vcc'], c['mid_vcc'], 30, kind='vcc')


def _e2_unused(bb, start_row, chip, block='left'):
    """교안 p8 의 미사용핀 처리 한 벌."""
    bb.connect_unused_inputs(_E2_UNUSED_GND, start_row, block=block, chip=chip, rail='gnd')
    bb.connect_unused_inputs(_E2_UNUSED_VCC, start_row, block=block, chip=chip, rail='vcc')
    bb.mark_unused_outputs(_E2_UNUSED_OUT, start_row, block=block, chip=chip)


def _build_e2_vtc(output_path, template_path, chip, title, subtitle, extra_notes=()):
    """E2.P1 / E2.P2 공통. **배선이 글자 그대로 같고 칩만 바뀐다** — 통제
    실험이라 함수발생기 설정·프로브 위치·미사용핀 처리를 하나도 안 바꾼다.
    바꾸면 그림 차이가 칩 때문인지 설정 때문인지 갈리지 않는다."""
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header(title, subtitle)
    c = bb.cols['left']
    r = 10

    bb.draw_chip(chip, r)
    _e2_power(bb)
    bb.connect_power(r)
    _e2_unused(bb, r, chip)

    # pin 1 은 함수발생기가 물고, pin 2 는 아무 부하 없이 프로브만 문다.
    # 점퍼선으로 꽂을 배선이 전원과 미사용핀뿐이다
    bb.instrument(c['a'], r, '함수발생기 + CH1 (X축)',
                  f'사인파 Vpp 5V · 오프셋 2.5V · {chip} pin 1 (= V_IN)', lane_row=5)
    bb.instrument(c['a'], r + 1, 'CH2 (Y축)',
                  f'{chip} pin 2 (= V_OUT). 부하 없음 — 프로브만 문다', lane_row=7)
    bb.instrument_note('두 프로브 접지 클립', '공통 GND 레일', '보드 GND 와 같은 노드')

    bb.note('오프셋 2.5V 를 빼먹으면 입력이 -2.5V 까지 내려간다. 데이터시트 LIMITING '
            'VALUES 가 V_I < -0.5V 에서 입력 보호 다이오드에 전류가 흐른다고 못박는다 — '
            '함수발생기가 전류를 제한하지 않으면 입력단이 상한다.')
    bb.note('오실로스코프를 X-Y 로 둔다: [Horiz] → 시간 모드 → XY (매뉴얼 p46~p47). '
            'CH1/CH2 를 바꿔 물면 곡선이 90도 돈다 — 오프셋을 잠깐 올렸다 내려서 '
            '곡선이 **좌우로** 움직이면 제대로 문 것이다.')
    for t in extra_notes:
        bb.note(t)
    bb.export(output_path, max_row=31)


def build_e2_inv(output_path, template_path=None):
    """실험 2-1 · Inverter 입출력 특성 (74HC04 VTC). netlist C1."""
    return _build_e2_vtc(
        output_path, template_path, '74HC04',
        "실험 2-1: Inverter 입출력 특성 (VTC)",
        "74HC04 (Hex Inverter) · 오실로스코프 X-Y 모드 (CH1=V_IN, CH2=V_OUT)")


def build_e2_schmitt(output_path, template_path=None):
    """실험 2-2 · Schmitt-trigger 입출력 특성 (74HC14). netlist C2."""
    return _build_e2_vtc(
        output_path, template_path, '74HC14',
        "실험 2-2: Schmitt-trigger 입출력 특성 (히스테리시스)",
        "74HC14 (Schmitt-trigger Hex Inverter) · 실험 2-1 과 배선이 같고 칩만 바뀐다",
        extra_notes=(
            '실험 2-1 의 통제 실험이다. 배선·함수발생기 설정·프로브 위치를 하나도 '
            '바꾸지 않는다. 바꾸면 그림 차이가 칩 때문인지 설정 때문인지 갈리지 않는다.',
            '칩을 바꿔 꽂을 때 전원을 내린다. 전원이 살아 있는 채로 DIP 를 뽑으면 '
            '핀이 순서대로 빠지면서 입력에만 전원이 걸린 순간이 생긴다.',
            '74HC14 는 74HC04 와 핀 배치가 같다 (Nexperia Rev. 10 §6.2 확인).'))


def _build_e2_dc(output_path, template_path, mode):
    """E2.P3-1(Rn) / E2.P3-2(Rp). **부하 저항의 위치가 이 항목의 전부다.**

    Rn: pin 1 -> VCC (입력 HIGH -> 출력 LOW). R1 이 VCC 와 출력 사이 -> 출력이
        전류를 빨아들이는 sinking. NMOS 도통 저항에 걸린 전압이 V_OL.
    Rp: pin 1 -> GND (입력 LOW -> 출력 HIGH). R1 이 출력과 GND 사이 -> sourcing.
        PMOS 도통 저항에서 잃은 만큼 V_OH 가 VCC 보다 낮아진다.

    위아래를 뒤집은 것뿐이고 **바뀌는 곳은 두 군데다** (pin 1 이 붙는 레일,
    R1 의 반대쪽이 붙는 레일).
    """
    rn = (mode == 'Rn')
    rail = 'vcc' if rn else 'gnd'
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header(
        f"실험 2-3{'(1)' if rn else '(2)'}: CMOS DC 특성 — {mode}",
        f"74HC04 · {'NMOS' if rn else 'PMOS'} 온저항 · 1kΩ 부하를 "
        f"{'VCC 와 출력 사이' if rn else '출력과 GND 사이'} 에 둔다 "
        f"· 출력이 {'sinking (V_OL)' if rn else 'sourcing (V_OH)'}")
    c = bb.cols['left']
    r = 10

    bb.draw_chip('74HC04', r)
    _e2_power(bb)
    bb.connect_power(r)

    # pin 1 을 레일에 직결한다. CMOS 입력은 전류를 거의 안 먹으므로 저항이 필요없다.
    # **a열에서** 뽑는다 — b열은 R1 이 칩 위로 올라가며 지나간다
    x_rail = (bb.nearest_vcc_rail if rn else bb.nearest_gnd_rail)(c['a'], 'left')
    bb.step_wire([(c['a'], bb.r_y(r)), (x_rail, bb.r_y(bb.free_rail_row(r, x_rail)))], rail,
                 f"pin 1 -> {'+5V' if rn else 'GND'} 직결 "
                 f"(입력 {'HIGH' if rn else 'LOW'} -> 출력 {'LOW' if rn else 'HIGH'} 고정)",
                 marker_at=(c['b'] - 30, bb.r_y(r) - 12))

    # R1 = 1kΩ. 아랫다리는 pin 2 행(a~e 는 한 줄이 한 노드다), 윗다리는 **칩 위
    # 빈 행**(r-2 = 8행)이다. 2026-09-09 까지 아랫다리가 r+4 = 14행에 있었는데
    # 그 행은 pin 5 다 — 같은 스트립에 R1 반대쪽 전원 점퍼와 pin 5 접지선이
    # 함께 꽂혀 Rn 에서 +5V 가 GND 로 직결됐다. 칩은 10~16행을 다 쓰므로
    # 저항은 칩 행 **밖**으로 나가야 한다.
    # 저항이 b열인 이유: 레일이 왼쪽이라 b열에서 레일로 가는 점퍼가 a열 홀 위를
    # 지난다. 다리를 a에 두면 그 점퍼가 다리 위를 지나 R3 다 (`led_chain` 과 같은 규칙)
    bb.draw_resistor(c['b'], bb.r_y(r - 2), bb.r_y(r + 1), label="1kΩ")
    bb.step_note('sig', bb.addr(c['b'], bb.r_y(r + 1)), bb.addr(c['b'], bb.r_y(r - 2)),
                 'R1 = 1kΩ 꽂기 (pin 2 와 같은 행에서 시작해 칩 위 빈 행으로)',
                 marker_at=(c['c'], (bb.r_y(r - 2) + bb.r_y(r + 1)) // 2))
    x_far = (bb.nearest_vcc_rail if rn else bb.nearest_gnd_rail)(c['a'], 'left')
    bb.step_wire([(c['a'], bb.r_y(r - 2)), (x_far, bb.r_y(bb.free_rail_row(r - 2, x_far)))], rail,
                 f"R1 반대쪽 -> {'+5V' if rn else 'GND'} 레일",
                 marker_at=(c['a'] - 30, bb.r_y(r - 2) + 10))

    _e2_unused(bb, r, '74HC04')

    bb.instrument_note('S1 · DMM 저항(Ω) 모드', 'R1 양끝',
                       '**회로에 꽂기 전에** R1 실저항을 잰다. 꽂은 채로 재면 IC 를 '
                       '통한 우회 경로가 병렬로 붙어 값이 틀린다')
    bb.instrument(c['c'], r + 1, 'S2 · DMM DCV (+)',
                  f"74HC04 pin 2 = V_out (= {'V_OL' if rn else 'V_OH'}). (-) 는 공통 GND",
                  lane_row=6)
    if rn:
        bb.instrument(c['d'], r + 1, 'S3 · DMM DCV — R1 양단',
                      '(+) VCC 레일, (-) pin 2. R1 양단 전압에서 I_OL 을 낸다', lane_row=20)
    else:
        bb.instrument_note('S3 · DMM DCV', 'VCC 레일 ↔ 공통 GND',
                           'VCC 실측. Rp 의 분자가 (VCC - V_OH) 라 공칭 5.00V 를 쓰면 '
                           '두 큰 수의 차에서 오차가 커진다')

    if rn:
        bb.note('pin 2(출력)를 VCC 에 **직결하면 안 된다.** 반드시 R1 을 거친다 — '
                '직결하면 도통한 NMOS 를 통해 VCC 가 GND 로 단락된다.')
        bb.note('R1 양단 전압 / R1 = I_OL. V_OL / I_OL = Rn.')
    else:
        bb.note('R1 이 pin 2 와 GND 사이에 있으므로 **R1 양단 전압 = V_out** 이다. '
                '따라서 I_OH = V_out / R1 이고 DMM 접점이 Rn 쪽보다 하나 줄어든다.')
        bb.note('(VCC - V_OH) / I_OH = Rp. 보통 Rp > Rn 이고, 그것이 상승 천이가 '
                '하강 천이보다 느린 원인이다 — 실험 2-4 의 지연 비대칭이 여기서 나온다.')
    bb.note('전류계를 쓸 거면 **반드시 직렬로** 넣는다. 저항이나 전원에 병렬로 대면 '
            '전류계가 VCC 를 단락시켜 퓨즈가 나간다.')
    bb.export(output_path, max_row=31)


def build_e2_rn(output_path, template_path=None):
    """실험 2-3 (1) · CMOS DC 특성 — Rn. netlist C3."""
    return _build_e2_dc(output_path, template_path, 'Rn')


def build_e2_rp(output_path, template_path=None):
    """실험 2-3 (2) · CMOS DC 특성 — Rp. netlist C4."""
    return _build_e2_dc(output_path, template_path, 'Rp')


def build_e2_tpd(output_path, template_path=None):
    """실험 2-4 · 전파지연 tpd (74HC04 두 개). netlist C5.

    **체인이 핀 번호 순서로 흐르지 않는다.** `pin 6` 에서 `pin 13` 으로 건너뛴 뒤
    번호를 거슬러 내려온다 (교안 p13 회로도를 900dpi 로 렌더해 확정).

        1 →2 · 3 →4 · 5 →6 · 13→12 · 11→10 · 9 →8

    CH1(pin 4) 과 CH2(pin 8) 사이에 인버터가 **4단** 있다. 핀 번호만 보고
    `1→2, 3→4, 5→6, 9→8` 로 짐작하면 2단으로 세게 되고 게이트당 t_pd 가 정확히
    2배로 나온다 — 이 주차에서 가장 비싼 실수다. 배선이 아니라 계산에서 틀리므로
    실험실에서는 아무 이상이 없어 보인다.
    """
    bb = BreadboardRenderer(template_path)
    bb.enable_steps()
    bb.set_header("실험 2-4: CMOS AC 특성 — 전파지연 t_pd",
                  "74HC04 두 개 · U1 은 인버터 6개 직렬 체인, U2 는 최종단 부하 · CH1=pin 4, CH2=pin 8")
    c_l, c_r = bb.cols['left'], bb.cols['right']
    r1, r2 = 7, 10   # U1 좌측 7행, U2 우측 10행

    bb.draw_chip('74HC04', r1, block='left')
    bb.draw_chip('74HC04', r2, block='right')

    bb.connect_jacks()
    bb.bridge_rails(c_l['gnd'], c_l['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['mid_gnd'], c_r['mid_gnd'], 31, kind='gnd')
    bb.bridge_rails(c_r['mid_gnd'], c_r['gnd'], 31, kind='gnd')
    bb.bridge_rails(c_l['vcc'], c_l['mid_vcc'], 33, kind='vcc')
    bb.bridge_rails(c_l['mid_vcc'], c_r['vcc'], 33, kind='vcc')
    bb.connect_power(r1, block='left')
    bb.connect_power(r2, block='right')

    # U1 체인. 인접 핀끼리는 짧은 점퍼 넷, 6->13 하나만 칩을 가로지른다
    bb.step_wire([(c_l['b'], bb.r_y(8)), (c_l['b'], bb.r_y(9))], 'mid',
                 '1단 출력 pin 2 -> 2단 입력 pin 3', width=4,
                 marker_at=(c_l['b'] - 20, bb.r_y(8) + 8))
    bb.step_wire([(c_l['b'], bb.r_y(10)), (c_l['b'], bb.r_y(11))], 'mid',
                 '2단 출력 pin 4 -> 3단 입력 pin 5', width=4,
                 marker_at=(c_l['b'] - 20, bb.r_y(10) + 8))
    # 3단 출력 pin 6 (12행, a~e 쪽) -> 4단 입력 pin 13 (8행, f~j 쪽). 칩 위로 넘긴다
    bb.step_wire([(c_l['c'], bb.r_y(12)), (c_l['c'], bb.r_y(5)),
                  (c_l['h'], bb.r_y(5)), (c_l['h'], bb.r_y(8))], 'mid',
                 '3단 출력 pin 6 -> 4단 입력 pin 13 (칩을 가로지르는 유일한 긴 점퍼)',
                 marker_at=(c_l['e'] + 6, bb.r_y(5) - 12))
    bb.step_wire([(c_l['g'], bb.r_y(9)), (c_l['g'], bb.r_y(10))], 'mid',
                 '4단 출력 pin 12 -> 5단 입력 pin 11', width=4,
                 marker_at=(c_l['g'] + 20, bb.r_y(9) + 8))
    bb.step_wire([(c_l['g'], bb.r_y(11)), (c_l['g'], bb.r_y(12))], 'mid',
                 '5단 출력 pin 10 -> 6단 입력 pin 9', width=4,
                 marker_at=(c_l['g'] + 20, bb.r_y(11) + 8))

    # U1 pin 8 (6단 출력, 13행 f~j 쪽) -> U2 pin 1 (우측 10행 a~e 쪽)
    bb.step_wire([(c_l['i'], bb.r_y(13)), (c_l['i'], bb.r_y(4)),
                  (c_r['a'], bb.r_y(4)), (c_r['a'], bb.r_y(10))], 'sig',
                 'U1 최종단 pin 8 -> U2 pin 1 (게이트 입력 부하)',
                 marker_at=(c_r['a'] - 70, bb.r_y(4) - 12))

    # U2 는 논리에 관여하지 않는다. pin 1 만 받고 나머지는 도면대로 묶는다
    bb.connect_unused_inputs(_E2_UNUSED_GND, r2, block='right', chip='U2', rail='gnd')
    bb.connect_unused_inputs(_E2_UNUSED_VCC, r2, block='right', chip='U2', rail='vcc')
    bb.mark_unused_outputs([2] + _E2_UNUSED_OUT, r2, block='right', chip='U2')

    bb.instrument(c_l['a'], r1, '함수발생기', 'U1 pin 1 (체인 입력)', lane_row=17)
    bb.instrument(c_l['d'], 10, 'CH1', 'U1 pin 4 = 2단 출력. 여기가 지연 측정 시작점',
                  lane_row=19)
    bb.instrument(c_l['h'], 13, 'CH2', 'U1 pin 8 = 6단 출력. CH1 과 사이에 인버터 4단',
                  lane_row=21)
    bb.instrument_note('두 프로브 접지 클립', '공통 GND 레일', '보드 GND 와 같은 노드')

    bb.note('U1 에는 **미사용 입력핀이 없다.** 인버터 6개를 전부 쓰므로 14핀이 모두 '
            '물린다. 다른 항목의 습관대로 pin 3·5 를 GND 로 내리면 체인이 끊긴다.')
    bb.note('긴 점퍼(pin 6 -> pin 13)가 빠지면 뒤 4단이 전부 죽고 pin 8 이 뜬다. '
            '화면에는 CH2 가 노이즈처럼 흔들리는 모습으로 나타나지, 지연이 이상한 '
            '모습으로 나타나지 않는다.')
    bb.note('CH1 과 CH2 사이는 **4단**이다 (5→6, 13→12, 11→10, 9→8). 핀 번호만 보고 '
            '2단으로 세면 게이트당 t_pd 가 정확히 2배로 나온다. 짝수 단이라 두 파형은 '
            '동상이고, Δt = 2·t_PHL + 2·t_PLH 이므로 둘을 분리할 수 없다 — 평균만 얻는다.')
    bb.note('U2 는 논리에 관여하지 않는다. U1 최종단에 게이트 입력 부하 하나를 '
            '더하는 것이 전부이고, U2 pin 2 는 개방이다.')
    bb.export(output_path, max_row=34)


def build_e2_all(output_dir, template_path=None):
    """실험 2의 모든 결선도 5종을 지정된 디렉토리에 일괄 렌더링"""
    os.makedirs(output_dir, exist_ok=True)
    targets = [
        ("실험02_결선도_인버터_입출력특성.png", build_e2_inv),
        ("실험02_결선도_슈미트트리거_입출력특성.png", build_e2_schmitt),
        ("실험02_결선도_DC특성_Rn.png", build_e2_rn),
        ("실험02_결선도_DC특성_Rp.png", build_e2_rp),
        ("실험02_결선도_전파지연_tpd.png", build_e2_tpd),
    ]
    for filename, func in targets:
        p = os.path.join(output_dir, filename)
        func(p, template_path)
    print(f"[SUCCESS] All 5 diagrams for 실험02 generated in: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Breadboard Diagram Generator")
    parser.add_argument("--circuit", required=True, choices=[
        "e1_and", "e1_or", "e1_or_s1", "e1_nand", "e1_nand_s1", "e1_nand_s2",
        "e1_nor", "e1_nor_s1", "e1_nor_s2",
        "e1_comb", "e1_comb_s1", "e1_comb_s2", "e1_comb_s3", "e1_all",
        "e2_inv", "e2_schmitt", "e2_rn", "e2_rp", "e2_tpd", "e2_all"
    ], help="Circuit ID to render")
    parser.add_argument("--output", required=True, help="Output PNG path (or directory path for e2_all)")
    parser.add_argument("--template", default=None, help="Path to Breadboard.jpg")
    args = parser.parse_args()

    dispatch = {
        "e1_and": build_e1_and,
        "e1_or": build_e1_or,
        "e1_or_s1": build_e1_or_s1,
        "e1_nand": build_e1_nand,
        "e1_nand_s1": build_e1_nand_s1,
        "e1_nand_s2": build_e1_nand_s2,
        "e1_nor": build_e1_nor,
        "e1_nor_s1": build_e1_nor_s1,
        "e1_nor_s2": build_e1_nor_s2,
        "e1_comb": build_e1_comb,
        "e1_comb_s1": build_e1_comb_s1,
        "e1_comb_s2": build_e1_comb_s2,
        "e1_comb_s3": build_e1_comb_s3,
        "e1_all": build_e1_all,
        "e2_inv": build_e2_inv,
        "e2_schmitt": build_e2_schmitt,
        "e2_rn": build_e2_rn,
        "e2_rp": build_e2_rp,
        "e2_tpd": build_e2_tpd,
        "e2_all": build_e2_all,
    }
    dispatch[args.circuit](args.output, args.template)

if __name__ == "__main__":
    main()
