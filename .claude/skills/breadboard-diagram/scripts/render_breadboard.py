import os
import re
import sys
import glob
import json
import types
import hashlib
import argparse
import tempfile
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

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
# 있는 것을 순서대로 쓴다 — 한글은 Apple SD Gothic Neo → 본고딕 → 함초롬돋움 →
# 맑은 고딕 → 나눔고딕, 영문은 Helvetica → Arial → DejaVu. 저장소 루트 밖의
# 절대 경로지만 폰트는 저장소가 들고 다닐 물건이 아니다.
#
# 2026-09-19: 맑은 고딕에 U+2295 ⊕ 가 없어 결선도 부제·꼬리표가 □ 로 찍혔다
# (`(A⊕B)·Ci` 가 `(A□B)·Ci` 로 나가고 줄바꿈도 어긋났다). 그래서 Windows 에서 한글과
# ⊕ 를 **둘 다** 가진 폰트를 맑은 고딕 앞에 세우고, `font_path()` 가 글리프까지
# 확인해 못 그리는 후보는 건너뛴다 — 있기만 한 폰트를 고르면 같은 일이 되풀이된다.
#
# 다만 글리프 검사는 **하드/소프트로 갈린다**. 처음에는 ☐ 까지 하드로 넣었는데, 맑은
# 고딕밖에 없는 보통의 Windows 에서는 모든 후보가 밀려 렌더러가 통째로
# `FileNotFoundError` 로 죽었다 — 체크칸 하나 때문에 그림을 아예 못 뽑는 건 과하다.
# 하드(`REQUIRED_GLYPHS`)가 빠진 후보만 버리고, 소프트(`PREFERRED_GLYPHS`)는 그것까지
# 되는 후보를 **선호**하되 없으면 경고 한 줄만 남기고 쓴다.
FONT_CANDIDATES = {
    'kr': ('/System/Library/Fonts/AppleSDGothicNeo.ttc',
           'C:/Windows/Fonts/NotoSansKR-VF.ttf',
           'C:/Windows/Fonts/HANDotum.ttf',
           'C:/Windows/Fonts/malgun.ttf',
           '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'),
    'en': ('/System/Library/Fonts/Helvetica.ttc',
           'C:/Windows/Fonts/arial.ttf',
           '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
}

# 하드 — 이게 빠진 후보는 **버린다**. ⊕ 부제·배선 뜻풀이, → 주소, · 머리표, ※ 꼬리표.
# 하나라도 □ 로 나가면 식이 딴 글자가 되거나 주소를 못 읽는다.
REQUIRED_GLYPHS = {'kr': '⊕→·※', 'en': ''}

# 소프트 — 있으면 좋다. ☐ 체크칸은 □ 로 나가도 뜻이 안 바뀌고 자리도 같다. 하드를
# 통과한 후보 중 이것까지 되는 첫 후보를 고르고, 아무도 없으면 경고만 하고 쓴다.
PREFERRED_GLYPHS = {'kr': '☐', 'en': ''}

# 소프트 글리프 경고를 이미 낸 폰트 — 렌더 한 장에 `font_path()` 가 여러 번 불린다.
_SOFT_WARNED = set()

# 글리프가 없을 때 폰트가 대신 그리는 .notdef 를 부르는 글자. 유니코드가
# 비문자로 못박아 두어(U+FFFE) 어떤 폰트에도 진짜 글리프가 없다.
_NOTDEF = '\ufffe'


def _glyph_mask(font, ch):
    """`ch` 한 글자의 렌더 결과 — (크기, 픽셀). 같은 폰트 안에서만 견준다."""
    mask = font.getmask(ch, mode='L')
    return (mask.size, bytes(mask))


def _covers(path, chars):
    """`path` 폰트가 `chars` 를 **전부** 진짜 글리프로 그리는가.

    .notdef(`\\ufffe`) 와 똑같이 그려지는 글자는 없는 것으로 본다. Pillow 만 쓴다 —
    폰트 테이블을 읽는 의존성을 새로 들이지 않으려고 그림을 직접 견준다.

    못 여는 파일이면 `OSError` 를 그대로 올린다 — "글리프가 없다" 와 "폰트가 아니다"
    는 다른 사고라 부르는 쪽이 갈라 적어야 한다.
    """
    font = ImageFont.truetype(path, 20)
    notdef = _glyph_mask(font, _NOTDEF)
    return all(_glyph_mask(font, ch) != notdef for ch in chars)


def font_path(kind):
    """`kind`('kr'|'en') 의 첫 번째 쓸 만한 폰트 경로.

    실재하기만 해서는 안 되고 `REQUIRED_GLYPHS[kind]`(하드)를 다 그려야 한다 — 맑은
    고딕은 한글은 되고 ⊕ 는 안 되어 그림이 조용히 □ 로 나갔다(2026-09-19).
    `PREFERRED_GLYPHS[kind]`(소프트)는 **선호**일 뿐이다: 하드를 통과한 후보 중 소프트
    까지 되는 첫 후보를 고르고, 아무도 없으면 하드를 통과한 첫 후보를 쓰며 stderr 에
    경고 한 줄을 남긴다. 소프트 때문에 렌더러를 죽이지 않는다.

    하드를 통과한 후보가 하나도 없을 때만 던진다. 어디를 봤는지, 어느 후보가 글리프
    때문에 밀렸는지, 어느 후보는 아예 못 열었는지 갈라 적는다.
    """
    hard, soft = REQUIRED_GLYPHS[kind], PREFERRED_GLYPHS[kind]
    skipped, unreadable, fallback = [], [], None
    for path in FONT_CANDIDATES[kind]:
        if not os.path.exists(path):
            continue
        try:
            if not _covers(path, hard):
                skipped.append(path)
                continue
            if _covers(path, soft):
                return path
        except OSError:
            unreadable.append(path)
            continue
        if fallback is None:
            fallback = path
    if fallback is not None:
        if fallback not in _SOFT_WARNED:
            _SOFT_WARNED.add(fallback)
            missing = ''.join(ch for ch in soft if not _covers(fallback, ch))
            print(f'[font] {fallback} 에 {missing} 가 없어 그 자리는 □ 로 찍힌다 — '
                  f'뜻은 안 바뀌니 그대로 간다', file=sys.stderr)
        return fallback
    msg = f'{kind} 폰트를 찾지 못했다. 찾아본 곳:\n  ' + '\n  '.join(FONT_CANDIDATES[kind])
    if unreadable:
        msg += ('\n열지 못한 후보(폰트가 아니거나 깨졌다):\n  ' + '\n  '.join(unreadable))
    if skipped:
        msg += (f'\n글리프 {hard!r} 가 없어 건너뛴 후보:\n  ' + '\n  '.join(skipped))
    raise FileNotFoundError(msg)


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
BOARD_RIGHT = 880    # 우 보드 테두리 x. 이보다 오른쪽은 보드 밖 여백이다 (addr() 의 '보드밖' 경계와 같다)

# R7. 칩 한쪽에 꽂히는 리드 한도. 한쪽 = 핀 행 7개 × 그쪽 자유 열 4개(a~d 또는 g~j) = 28홀.
# 2026-09-18 실험03: 네 칩이 게이트 1·2 만 써서 74HC86 왼쪽에 11리드가 몰렸고 오른쪽은
# pin 14 전원선 하나였다 — 꽂기도, 꽂았는지 보기도 힘들었다. 8 이면 실험03 왼쪽 11 은
# 걸리고, 게이트를 좌·우로 나눈 전가산기(좌 7·우 5)는 통과한다.
SIDE_LEAD_MAX = 8
SIDE_COLS = {'a': ('a', 'b', 'c', 'd'), 'f': ('g', 'h', 'i', 'j')}
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

# 걷기 보드에서 **뽑는** 배선의 색. footer "앞 단계에서 걷는다" 표와 같은 빨강이다.
# `WIRE` 팔레트에 넣지 않는다 — 넷의 색이 아니라 "이 그림에서 뽑는다" 는 표시다.
# 2026-09-18 실험03: 걷을 두 가닥이 footer 표에만 있어 실험실에서 놓쳤다
REMOVE = (160, 30, 30, 255)

# 계측기 리드는 **배선이 아니다.** 점퍼선으로 꽂는 게 아니라 프로브 팁과 집게로
# 문다. 그래서 위 네 색에 끼워 넣지 않고 회색 점선으로 따로 그리고, 순서표도
# '결선' 이 아니라 '계측' 표에 따로 쌓는다
PROBE = (105, 105, 110, 255)

# 단계 하나가 꽂는 **새 신호선**의 상한. 2026-09-20 단계 세분화: 관측 노드 하나 =
# 단계 하나이고 새 신호선은 셋 이하다 — 확인이 실패했을 때 용의자가 그 셋이다.
# 전원·GND·레일 브리지·잭·LED 사슬 부품·칩 꽂기는 **기반**이라 세지 않는다: 회로가
# 바뀌어도 그대로 있는 것들이고 첫 단계에 한꺼번에 꽂는다.
STAGE_WIRE_BUDGET = 3

# 전원 잭 세 개의 중심 x (템플릿 상단). y 는 원 아래끝 근처.
JACKS = {'red': 439, 'yellow': 603, 'gray': 766}
JACK_BOTTOM = 160

# 넷 라벨용 이름. 저장소가 한국어라 넷 판정문도 한국어로 나와야 한다
JACK_KR = {'red': '빨강', 'yellow': '노랑', 'gray': '회색'}


def _boxes_touch(a, b):
    """두 상자 (x0, y0, x1, y1) 가 겹치는가. 걷기 번호 원 자리 잡기에 쓴다."""
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


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
        # 기준선 대비 **새로 꽂는 신호선**의 key. 예산(`STAGE_WIRE_BUDGET`)의 지표다.
        # `content()` 에는 넣지 않는다 — 넣으면 기존 PNG 스물두 장의 도장이 바뀐다.
        self.new_signal = []
        # R7·R8 정책. 'strict' 가 기본 — 칩 한쪽 리드가 SIDE_LEAD_MAX 를 넘거나(R7) 같은
        # 블록 두 칩 사이 배선이 쪽을 바꾸면(R8) verify() 가 막는다. 'legacy' 는 R7(2026-09-20)
        # 이전에 승인·제출된 실험01~03 빌더만 쓴다 — 승인본을 다시 그리지 않으려는
        # 것이지 면허가 아니다. tests/test_breadboard_physical.py 가 실험 4 이상은 전부
        # strict 인지 본다. content() 에 들지 않아 도장은 그대로다.
        self.density_policy = 'strict'
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
        # 스트립 점퍼도 전원 단락도 덜 그렸다고 봐줄 것이 아니다.
        # 걷기 보드에서는 프로퍼티(`partial` setter)가 False 를 받아도 True 로 남긴다 —
        # 아래 `self.ghost` 를 먼저 정해 두어야 setter 가 그것을 볼 수 있다
        self._partial = False
        # 앞 보드의 `snapshot()`. 같은 홀 쌍의 배선·같은 홀의 LED 사슬은 회색으로
        # 그리고 번호를 주지 않는다 — 실험실에서는 그 선을 손대지 않는다.
        # 기준선에 있었는데 이번에 안 그린 것은 `removed()` 가 "걷는다" 로 낸다.
        # 실험01 실험실 기록(2026-09-11): 1-1→1-2 는 칩만 갈아끼우면 됐다
        self.baseline = baseline
        self.kept = []          # 그대로 두는 배선·부품의 desc
        self.swaps = []         # (앞 칩, 새 칩, block, pin1_row)
        self._keep_parts = False  # led_chain 이 기준선 사슬을 그리는 동안 참
        # 걷기 보드 — 기준선 dict 의 `ghost` 키 `{'wires': {key: n}, 'title', 'subtitle'}`.
        # `step_wire()` 가 그 key 를 만나면 점유표·구간에 안 남기고 `ghost_layer` 에 빨간
        # 점선으로 그린다. 뽑은 선의 핀이 뜨는 것이 정상이라 `partial` 이다.
        # 기준선 dict 에 키를 얹는 이유: `set_header()` 가 제목을 즉시 그려 사후에 못 바꾸고,
        # 빌더 시그니처를 늘리면 세 주차 스물세 빌더를 고쳐야 한다. `removal_board()` 가 만든다
        self.ghost = (baseline or {}).get('ghost')
        self.ghost_layer = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.ghost_drawn = {}     # key -> n. export() 가 빌더가 안 그린 key 를 잡는다
        if self.ghost is not None:
            self.partial = True
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

    @property
    def partial(self):
        return self._partial

    @partial.setter
    def partial(self, value):
        """걷기 보드는 정의상 `partial` 이다 — 내려도 다시 올린다.

        걷어낸 가닥의 핀은 아무 데도 안 물린다(74HC08 pin 1·4). 그게 이 그림의 요점인데
        `verify()` R5 는 뜬 핀을 오류로 잡는다. 주차 파일들은 `bb.partial = st < 3`
        처럼 단계로 값을 정하므로, 생성자가 켜 둔 것을 빌더가 뒤에서 도로 내린다
        (2026-09-19 실험03 걷기 보드가 이걸로 PNG 재생성에서 죽었다). 세 주차 스물세
        빌더에 `or bb.ghost` 를 덧대는 대신 여기서 한 번 막는다.
        """
        self._partial = bool(value) or getattr(self, 'ghost', None) is not None

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
        if x > BOARD_RIGHT:
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

        걷기 보드(ghost 모드)는 앞 회로 빌더가 부르는 제목 대신 `ghost` 의 제목을 쓴다 —
        빌더는 자기가 걷기 보드로 렌더되는지 모른다.
        """
        if self.ghost is not None:
            title, subtitle, submit = self.ghost['title'], self.ghost['subtitle'], False
        self.title, self.subtitle = title, subtitle
        self.draw.text((28, 170), title, fill=(20, 40, 90, 255), font=self.font_title)
        self.draw.text((30, 200), subtitle, fill=(80, 90, 100, 255), font=self.font_subtitle)
        self.submit = submit
        if submit:
            line = "※ 이 그림을 손으로 따라 그린 뒤 학번/이름/날짜를 자필로 적어 제출한다"
        elif self.ghost is not None:
            line = "※ 걷기 그림 — 빨간 점선만 뽑는다(전원을 끄고). 회색은 그대로 둔다. 새로 꽂는 것은 없다"
        else:
            line = "※ 체크리스트용 절차 그림 — 회색은 앞 단계에서 그대로 둔 것. 손그림은 완성본으로 그린다"
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

    def _dashed(self, points, color, width=2, dash=7, gap=5, draw=None):
        d = draw or self.draw
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            span = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            if span == 0:
                continue
            ux, uy, t = (x1 - x0) / span, (y1 - y0) / span, 0.0
            while t < span:
                e = min(t + dash, span)
                d.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)],
                       fill=color, width=width)
                t = e + gap

    def instrument(self, x, row, label, desc, block='left', lane_row=None, name=None):
        """계측기·신호원 접점. **배선이 아니다** — 점퍼로 꽂는 게 아니라
        프로브 팁이나 집게로 문다. 회색 점선으로 그리고 계측표에 따로 쌓는다.

        보드 왼쪽 여백으로 뺀다. `lane_row` 를 주면 여백 안(x=140)에서 꺾어
        그 행으로 옮긴다 — 접점 두 개가 이웃한 행이면 꼬리표가 겹치기 때문이다.

        `name` 은 교안 회로도가 그 접점에 붙인 신호 이름이다(실험02 `VIN`·`VOUT`·
        `CH1`·`CH2`). 주면 **보드 안에도** 배지로 적는다 — 꼬리표만 보드 밖에 두면
        판형 위만 따라 그리는 손그림에서 이름이 빠진다(2026-09 실험01 조교 감점과
        같은 꼴, 2026-09-14 실험02 pre_review_round3). 자리는 그 접점과 같은
        스트립의 끝 여백이다: 칩 왼쪽 스트립(a~e)이면 레일과 a 열 사이, 오른쪽
        스트립(f~j)이면 j 열 바깥. 한 행의 다섯 홀은 한 노드라 스트립 끝에 적어도
        같은 핀을 가리킨다.
        """
        y = self.r_y(row)
        lane_y = self.r_y(lane_row) if lane_row else y
        pts = [(x, y), (140, y)] + ([(140, lane_y)] if lane_row else []) + [(100, lane_y)]
        self._dashed(pts, PROBE)
        self.draw.ellipse([x - 5, y - 5, x + 5, y + 5], outline=PROBE, width=2)
        n = len(self.probes) + 1
        self.draw_badge(12, lane_y - 8, f'{n}. {label}', (248, 248, 250, 240), PROBE,
                        font=self.font_kr_sm, pad=2)
        entry = {'n': n, 'label': label, 'at': self.addr(x, y), 'desc': desc,
                 'sym': self.sym(x, row)}
        if name:
            entry['name'] = name
            c = self.cols[block]
            if x < c['chip_x1']:
                rail = max(v for k, v in c.items()
                           if ('gnd' in k or 'vcc' in k) and v < c['a'])
                # 가운데서 1.5px 왼쪽 — 3~4행 사이 번호 원(b 열 - 20)과 붙지 않게
                self.signal_tag(name, (rail + c['a']) / 2 - 1.5, y, col=PROBE)
            else:
                self.signal_tag(name, c['j'] + 6, y, align='left', col=PROBE)
        self.probes.append(entry)

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

    def _marker_removed(self, x, y, n):
        """걷기 번호 — 빨간 채움·흰 숫자. 순서표 원(흰 바탕·색 테두리)과 구분된다."""
        self.marker_boxes.append((x - 8, y - 8, x + 8, y + 8))
        self._marker_on(self.draw, x, y, n, REMOVE, filled=True)

    def _ghost_wire(self, points, n):
        """걷기 보드의 뽑을 배선. 유령 레이어에 빨간 점선, overlay 에 걷기 번호 원.

        점유표·구간·레일 접촉에 아무것도 안 남긴다 — 이 선은 이제 없는 것이고, 그 홀에
        다음 회로의 새 선이 앉을 수 있다(실험03 좌 d7·a9). 끝점 원도 안 찍는다.
        번호 원은 가장 긴 구간의 중점에, 기존 원과 겹치면 그 구간을 따라 옮긴다.
        """
        self._dashed(points, REMOVE, width=4, dash=9, gap=6,
                     draw=ImageDraw.Draw(self.ghost_layer))
        if len(points) < 2:
            self._marker_removed(points[0][0], points[0][1], n)
            return
        (x0, y0), (x1, y1) = max(zip(points, points[1:]),
                                 key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        span = max(1.0, ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
        ux, uy = (x1 - x0) / span, (y1 - y0) / span
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        x, y = mx, my
        for k in (0, 24, -24, 48):
            x, y = mx + ux * k, my + uy * k
            box = (x - 8, y - 8, x + 8, y + 8)
            if not any(_boxes_touch(box, b) for b in self.marker_boxes):
                break
        self._marker_removed(int(x), int(y), n)

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
        if self.ghost is not None and key in self.ghost['wires']:
            n = self.ghost['wires'][key]
            self._ghost_wire(points, n)
            self.ghost_drawn[key] = n
            return None
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
        if not kept and kind in ('sig', 'mid'):
            self.new_signal.append(key)
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
        # 기준선에 같은 (색, 끝점, 끝점) 이 있으면 `step_wire` 와 같은 규칙으로 회색이다
        # — 실험02 C1→C2 는 칩만 갈아 끼우므로 pull 선 다섯 가닥이 전부 그대로다.
        # 전부 회색이면 순서표에 번호 대신 "그대로 둔다" 로 남긴다
        kept_lines = 0
        for row, x_pin, p in (placed[i] for i in order):
            pick = self.nearest_vcc_rail if rail == 'vcc' else self.nearest_gnd_rail
            x_rail = pick(x_pin, block)
            r_rail = self.free_rail_row(row, x_rail)
            key = (rail, self._endpoint((x_pin, self.r_y(row))),
                   self._endpoint((x_rail, self.r_y(r_rail))))
            kept = self.baseline is not None and key in self.baseline['wires']
            kept_lines += kept
            col = KEEP if kept else WIRE[rail]
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
        desc = '미사용 입력 풀업' if rail == 'vcc' else '미사용 입력 접지'
        if placed and kept_lines == len(placed):
            self.kept.append(f'{chip} pin {pin_str} {desc}')
        else:
            self.step_note(rail, f'{chip} pin {pin_str}',
                           '가까운 +5V 레일' if rail == 'vcc' else '가까운 GND 레일',
                           desc, count=len(pins))

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
        미사용 핀 처리를 지시한 주차(실험02 p9)만 `connect_unused_inputs` 로
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
            if self.ghost is not None:
                for k in range(0, 24, 12):
                    d.line([(x + k, y + 7), (x + k + 7, y + 7)], fill=REMOVE, width=3)
                d.text((x + 30, y), '뽑는다 (빨간 점선 · 빨간 번호)',
                       fill=(60, 60, 60, 255), font=self.font_step)
                x += 190
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
            if self.ghost is not None:
                line = (f'· 회색 = 그대로 둔다 ({len(self.kept)}개). '
                        '빨간 점선 + 빨간 번호 = 이 그림에서 뽑는다. 새로 꽂는 것은 없다')
            else:
                line = (f'· 회색 = 앞 단계에서 그대로 둔다 ({len(self.kept)}개). '
                        '번호 = 이번 단계에서 새로 한다')
            d.text((x_pad, y), line, fill=(90, 90, 90, 255), font=self.font_step)
            y += 15
            wires = self.removals()
            others = self.removed()[len(wires):]
            if wires or others:
                y += 6
                d.text((x_pad, y), "앞 단계에서 걷는다 — 먼저 뽑고 ☐ 를 채운다",
                       fill=REMOVE, font=self.font_kr_bold)
                y += 20
                for r in wires:
                    d.rectangle([x_pad, y + 2, x_pad + 11, y + 13],
                                outline=(120, 125, 130, 255), width=1)
                    x_text = x_pad + 18
                    if self.ghost is not None:
                        # 그림 위 빨간 원과 같은 번호 — 걷기 보드에서만. 보통 보드는
                        # 그림에 원이 없어 번호가 가리킬 데가 없다
                        self._marker_on(d, x_pad + 28, y + 8, r['n'], REMOVE, filled=True)
                        x_text = x_pad + 42
                    lines = self._wrap(f"걷기: {r['addr']} · {r['desc']}", self.font_step,
                                       998 - x_text - x_pad)[:2]
                    for k, ln in enumerate(lines):
                        d.text((x_text, y + k * 14), ln, fill=REMOVE, font=self.font_step)
                    y += max(18, len(lines) * 14 + 4)
                for g in others:
                    d.rectangle([x_pad, y + 2, x_pad + 11, y + 13],
                                outline=(120, 125, 130, 255), width=1)
                    lines = self._wrap('걷기: ' + g, self.font_step, 998 - 2 * x_pad - 20)[:2]
                    for k, ln in enumerate(lines):
                        d.text((x_pad + 18, y + k * 14), ln, fill=REMOVE, font=self.font_step)
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

    def _marker_on(self, d, x, y, n, color, filled=False):
        """번호 원. `filled` 면 색 채움·흰 숫자 — 걷기 번호가 순서표 번호와 헷갈리지 않게."""
        fill, text = ((color, (255, 255, 255, 255)) if filled
                      else ((255, 255, 255, 245), color))
        d.ellipse([x-8, y-8, x+8, y+8], fill=fill, outline=color, width=2)
        t = str(n)
        bbox = d.textbbox((0, 0), t, font=self.font_num)
        d.text((x - (bbox[2]-bbox[0])/2 - bbox[0], y - (bbox[3]-bbox[1])/2 - bbox[1]),
               t, fill=text, font=self.font_num)

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
        """이 보드의 배선·사슬·칩을 **다음 보드의 기준선**으로 쓸 수 있게 낸다.

        끝점 기호만 담는다 — 꼭짓점은 여기 없다. 걷기 보드(`removal_board`)는 앞 회로
        빌더를 **다시 돌려** 그리므로 살아 있는 빌더의 꼭짓점을 쓴다(`_ghost_wire`).
        """
        w = self.wiring()
        return {
            'wires': {(x['kind'], x['frm'], x['to']): x['desc'] for x in w['wires']},
            'chains': {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom']): ch['tag']
                       for ch in w['chains']},
            'chips': {(ch['block'], ch['pin1_row']): ch['label'] for ch in w['chips']},
        }

    def removals(self):
        """기준선에 있었는데 이번 보드에 없는 **배선** — 걷기 번호를 매겨 낸다.

        순서는 기준선(앞 보드)의 그리기 순서라 결정적이다. netlist 단계 표가 이
        번호(걷기 ①·②)를 인용한다. 칩·사슬은 여기 없고 `removed()` 에만 있다 —
        칩 교체는 순서표에 이미 번호 원이 있다.

        꼭짓점은 내지 않는다 — 걷기 보드는 앞 회로 빌더를 다시 돌려 그리므로 그림은
        살아 있는 빌더의 꼭짓점으로 그려진다(`_ghost_wire`).
        """
        if self.baseline is None:
            return []
        drawn = {(k, self._endpoint(pts[0]), self._endpoint(pts[-1]))
                 for k, pts, _ in self._segments}
        out = []
        for key, desc in self.baseline['wires'].items():
            if key in drawn:
                continue
            out.append({'n': len(out) + 1, 'key': key,
                        'addr': f'{self._sym_addr(key[1])} → {self._sym_addr(key[2])}',
                        'desc': desc})
        return out

    def removed(self):
        """기준선에 있었는데 이번 보드에 없는 것 — 실험실에서 **걷을** 것. 배선 → 칩 →
        사슬 순의 문자열. 배선 줄은 `removals()` 와 같은 순서·같은 수다."""
        if self.baseline is None:
            return []
        out = [f"{r['addr']} · {r['desc']}" for r in self.removals()]
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

    def side_leads(self):
        """칩마다 양쪽(a~d / g~j) 핀 행 7개에 꽂힌 리드 수 — R7 의 지표.

        점유표(`_leads`)만 읽는다. 칩 핀(e·f 열)은 그 칩 자신이라 빼고, 지나가는
        선(`_passed`)은 꽂는 것이 아니라 뺀다. `wiring()` 에 넣지 않는다 — `content()`
        가 `wiring()` 을 통째로 해시하므로 필드 하나만 더해도 지난 주차 도장이 전부
        깨진다.
        """
        out = []
        for ch in self.chips:
            c = self.cols[ch['block']]
            rows = range(ch['pin1_row'], ch['pin1_row'] + 7)
            for side, names in SIDE_COLS.items():
                xs = {c[k] for k in names}
                holes = sorted((h for h in self._leads if h[0] in xs and h[1] in rows),
                               key=lambda h: (h[1], h[0]))
                out.append({'chip': ch['label'], 'block': ch['block'],
                            'pin1_row': ch['pin1_row'], 'side': side, 'count': len(holes),
                            'addrs': [self.addr(x, self.r_y(r)) for x, r in holes]})
        return out

    def chip_side_of(self, end):
        """`_endpoint()` 결과가 어느 칩의 어느 쪽 핀 스트립인가.

        칩 행 범위(pin1_row~+6) 안의 a~d 열이면 그 칩의 'a' 쪽, g~j 열이면 'f' 쪽 — 같은 행
        a~e / f~j 는 한 스트립이라 그 홀에 꽂은 것은 그 핀에 꽂은 것이다. e·f(칩 다리)·칩 행
        밖·레일·잭은 None. 같은 이름의 칩이 두 자리에 앉을 수 있어(실험02 t_pd) `pin1_row` 로
        구분한다.
        """
        if end[0] != 'hole' or end[1] is None:
            return None
        blk, col, row = end[1]
        for ch in self.chips:
            if ch['block'] == blk and ch['pin1_row'] <= row <= ch['pin1_row'] + 6:
                for side, names in SIDE_COLS.items():
                    if col in names:
                        return {'chip': ch['label'], 'block': blk, 'pin1_row': ch['pin1_row'], 'side': side}
                return None
        return None

    def cross_side_wires(self):
        """R8 의 지표 — 같은 블록의 **서로 다른 두 칩** 핀 스트립을 잇는 배선 중 양 끝 쪽이 다른 것.

        2026-09-20 격리 시험판(게이트를 무조건 1·4 로 나눈 판)에서 `좌 a9 → 좌 h19`(A⊕B → NOT2),
        `우 g13 → 우 b21`(AND2 → OR) 같은 X자가 생겼다 — 승인본 실험01~03 완성본 7장은 0건,
        시험 전용 `build_e2_tpd` 한 가닥만 예외(`tests/test_breadboard_physical.py`
        `KNOWN_CROSS_SIDE`). 같은 칩 안의 사슬(XOR1→XOR2)은 나누기의 대가라 보지 않고, 다른
        블록 사이는 차선으로 건너므로 보지 않는다. 가닥 단위로 본다 — 중계 스트립을 거친 두
        가닥은 못 본다. 넷 단위 검사는 별건. `wiring()` 에 넣지 않는다 — 도장.
        """
        out = []
        for _kind, pts, desc in self._segments:
            a = self.chip_side_of(self._endpoint(pts[0]))
            b = self.chip_side_of(self._endpoint(pts[-1]))
            if not a or not b or a['block'] != b['block']:
                continue
            if (a['chip'], a['pin1_row']) == (b['chip'], b['pin1_row']) or a['side'] == b['side']:
                continue
            out.append({'frm': self.addr(*pts[0]), 'to': self.addr(*pts[-1]), 'desc': desc,
                        'from_side': a, 'to_side': b})
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
            # 이름 붙은 계측 지점 — 입력 점퍼도 LED 도 없는 주차(실험02)의 H15 대상
            'probes': [{'name': p['name'], 'at': p['at']}
                       for p in self.probes if p.get('name')],
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
        R7  칩 한쪽(핀 행 7 × 자유 열 4)에 꽂힌 리드가 SIDE_LEAD_MAX 를 넘지 않는다
            (`density_policy`). 실험01~03 승인본만 'legacy' 로 끈다.
        R8  같은 블록의 두 칩을 잇는 배선은 쪽(a~d / g~j)을 바꾸지 않는다 — 게이트는 신호가
            오는 쪽으로 배정한다(SKILL §4a). `density_policy` 가 함께 끈다.
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

        # R7. 칩 한쪽에 리드가 몰리지 않는다 — 2026-09-18 실험03 에서 네 칩이 게이트 1·2 만
        # 써서 74HC86 왼쪽에 11리드가 몰렸다. 게이트를 좌·우로 나눠 배정하면 풀린다(SKILL §4a).
        if self.density_policy not in ('strict', 'legacy'):
            raise ValueError(f"density_policy 는 'strict' 또는 'legacy' 다: {self.density_policy!r}")
        if self.density_policy == 'strict':
            for s in self.side_leads():
                if s['count'] > SIDE_LEAD_MAX:
                    blk = '좌' if s['block'] == 'left' else '우'
                    side_kr = '왼쪽' if s['side'] == 'a' else '오른쪽'
                    bad.append(f"R7 칩 한쪽 밀집: {s['chip']}({blk} {s['pin1_row']}행) {side_kr} "
                               f"{s['count']}리드 > {SIDE_LEAD_MAX}: {', '.join(s['addrs'])}")

        # R8. 같은 블록 두 칩 사이 배선이 반대쪽으로 건너지 않는다 — 2026-09-20 격리 시험판의
        # X자. 게이트를 신호가 오는 쪽으로 배정하면 생기지 않는다(SKILL §4a).
        if self.density_policy == 'strict':
            for w in self.cross_side_wires():
                bad.append(f"R8 칩 사이 엇갈림: {w['frm']} → {w['to']} · {w['desc']} — "
                           f"{w['from_side']['chip']} {w['from_side']['side']}쪽 → "
                           f"{w['to_side']['chip']} {w['to_side']['side']}쪽")
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

    def content(self):
        """도장에 드는 것 — 이 그림이 **무엇을** 싣는가. 주차 파일이 넘긴 문자열과 홀
        주소뿐이다. 픽셀·글꼴·줄바꿈 결과·엔진 범례 문구는 넣지 않는다 — 기계마다
        글꼴이 달라도 같은 결선이면 같은 도장이 나와야 한다.

        `verify()` 뒤에 불러야 `wiring()['overlaps']` 가 찬다 — `export()` 가 그렇게 한다.
        """
        out = {
            'title': self.title, 'subtitle': self.subtitle, 'submit': self.submit,
            'notes': list(self.notes),
            'steps': list(self.steps),
            'probes': list(self.probes),
            'kept': len(self.kept) if self.baseline is not None else None,
            'removed': self.removed(),
            'wiring': self.wiring(),
        }
        if self.ghost is not None:
            # 걷기 보드에서만 든다 — 다른 보드의 도장은 그대로라 재생성 범위가 안 번진다
            out['ghost'] = [(r['n'], r['addr']) for r in self.removals()]
        return out

    def stamp(self):
        blob = json.dumps(self.content(), ensure_ascii=False, sort_keys=True, default=_jsonable)
        return 'v1:' + hashlib.sha256(blob.encode('utf-8')).hexdigest()

    def export(self, output_path, max_row=35):
        self.verify()
        if self.ghost is not None:
            missing = [f'{self._sym_addr(k[1])} → {self._sym_addr(k[2])}'
                       for k in self.ghost['wires'] if k not in self.ghost_drawn]
            assert not missing, (
                f'걷기 대상 배선을 앞 빌더가 그리지 않았다: {missing} — '
                'removal_board 의 prev 빌더·stage 가 기준선을 만든 것과 같아야 한다')
            # 반대쪽도 본다 — 유령 목록이 실제로 걷히는 배선의 부분집합이어도 안 된다.
            # 번호 없는 가닥이 조용히 사라지면 그림이 무엇을 뽑는지 말해 주지 않는다.
            listed = set(self.ghost['wires'])
            actual = {r['key'] for r in self.removals()}
            extra = [self._sym_addr(k[1]) + ' → ' + self._sym_addr(k[2])
                     for k in actual - listed]
            gone = [self._sym_addr(k[1]) + ' → ' + self._sym_addr(k[2])
                    for k in listed - actual]
            assert not (extra or gone), (
                f'걷기 목록과 실제로 걷히는 배선이 다르다 — 목록에 없는데 걷히는 것: '
                f'{extra}, 목록에 있는데 안 걷히는 것: {gone} — '
                'removal_board 의 nxt 빌더가 기준선을 만든 prev 와 짝이 맞아야 한다')
        # 유령선은 템플릿과 overlay 사이 — 회색 선·칩·새 선이 유령선을 덮는다
        final_im = Image.alpha_composite(Image.alpha_composite(self.im, self.ghost_layer),
                                         self.overlay)
        board_h = self.r_y(max_row) + 20
        board = final_im.crop((0, 0, 998, board_h)).convert('RGB')

        canvas = Image.new('RGB', (998, board_h + 1400), (255, 255, 255))
        canvas.paste(board, (0, 0))
        used = self._draw_footer(canvas, board_h)
        out = canvas.crop((0, 0, 998, min(used, canvas.height)))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        info = PngInfo()
        info.add_text(STAMP_KEY, self.stamp())
        out.save(output_path, pnginfo=info)
        staged = self.partial or self.baseline is not None
        print(f"[SUCCESS] Exported: {output_path} "
              f"({out.size[0]}x{out.size[1]}, 결선 {len(self.steps)}단계, "
              f"새 신호선 {len(self.new_signal)} · 걷는 선 {len(self.removals())})")
        if staged and len(self.new_signal) > STAGE_WIRE_BUDGET:
            # 막지 않는다 — 저작 중에는 넘는 보드를 그려 봐야 어디서 쪼갤지 보인다.
            # 주차 보드 테스트(`tests/test_breadboard_boards.py`)가 승인을 막는다.
            print(f"[WARN] 새 신호선이 {len(self.new_signal)} 가닥이다 "
                  f"(예산 {STAGE_WIRE_BUDGET}) — 관측 노드 하나로 단계를 더 쪼갠다")


def _tag(bb, x, y, text, col=(60, 60, 60, 255)):
    """보드 **밖** 꼬리표 — 꽂을 자리(`입력 A → b7`). 신호 이름은 `signal_tag()` 가 보드 안에 둔다."""
    bb.draw_badge(x, y, text, (255, 255, 255, 235), col, font=bb.font_kr_sm, pad=2)


def _input_jumper(bb, c, row, name, target, marker=None, col=None, side='a'):
    """입력 한 줄: **그쪽 GND 레일 홀 → 같은 행 `col` 열**. GND(=0) 자리를 그린 것이다.

    `side` 는 입력이 들어가는 핀이 칩의 어느 쪽인가다 — `'a'`(핀 1~7, a~e 쪽) 또는
    `'f'`(핀 8~14, f~j 쪽). 레일은 그쪽에 붙은 GND 다: 좌 블록은 a 쪽이 바깥 174, f 쪽이
    중앙 468 이고 우 블록은 뒤집혀 a 쪽이 중앙 542, f 쪽이 바깥 836 이다. 열 기본값은
    a 쪽 `b`, f 쪽 `i`(핀 홀 e·f 옆 d·g 는 전원선 자리라 한 칸 띈다 — `connect_power`).
    2026-09-18 실험03 에서 네 칩이 게이트 1·2 만 써 왼쪽에 11리드가 몰렸다(R7) — 게이트를
    좌·우로 나누면 오른쪽 게이트의 입력이 이 분기를 쓴다.

    아래는 좌 바깥 레일(side='a', 좌 블록) 의 경우다 — 다른 세 레일의 배지·번호 원
    자리는 본문 주석에 있다.

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
    assert side in ('a', 'f'), f"side 는 'a' 또는 'f' 다: {side!r}"
    block = 'left' if c is bb.cols['left'] else 'right'
    if side == 'a':
        x_rail = c['gnd'] if block == 'left' else c['mid_gnd']
        col = col or 'b'
    else:
        x_rail = c['mid_gnd'] if block == 'left' else c['gnd']
        col = col or 'i'
    r_rail = bb.free_rail_row(row, x_rail)
    y_rail, y_row = bb.r_y(r_rail), bb.r_y(row)
    # 신호 이름 배지와 번호 원의 기본 자리 — 레일 바깥 여백. 좌 바깥 레일은 보드 좌
    # 테두리~레일 사이(기존), 우 바깥 레일은 VCC 레일(852)~보드 우 테두리 사이, 중앙 레일 둘은
    # 중앙 레일쌍 사이 여백(좌 중앙 VCC 484 ~ 우 중앙 GND 542)이다. 번호 원은 좌·우
    # 바깥이면 보드 밖 같은 행, 중앙이면 배지 위 18px 다 — 여백이 58px 라 나란히 못 놓는다.
    if x_rail == bb.cols['left']['gnd']:
        badge_x, default_marker = (BOARD_LEFT + x_rail) / 2, (130, 0)
    elif x_rail == bb.cols['right']['gnd']:
        badge_x, default_marker = (bb.cols['right']['vcc'] + BOARD_RIGHT) / 2, (BOARD_RIGHT + 24, 0)
    else:
        # 중앙 레일 둘(좌 중앙 468·우 중앙 542)이 이 자리를 같이 쓴다 — 같은 행에 좌 f쪽
        # 입력과 우 a쪽 입력을 함께 넣으면 배지와 번호 원이 서로 위에 겹친다(58px 여백은
        # 한 번에 입력 한 행만 받는다). 배지 겹침은 가독성 테스트가 잡는다.
        badge_x = (bb.cols['left']['mid_vcc'] + bb.cols['right']['mid_gnd']) / 2
        default_marker = (badge_x, -18)
    mx, dy = marker or default_marker
    p0, p1 = (x_rail, y_rail), (c[col], y_row)
    # 걷기 보드(`removal_board`)가 이 점퍼를 걷는 장이면 `step_wire` 는 유령선만 그리고
    # 곧장 돌아온다 — 점유표도 구간도 레일 접촉도 안 남긴다. 꽂혀 있지 않은 선이다.
    # `step_wire` 와 **같은 식**으로 판정한다(회색 유지선·번호 끔도 None 을 돌려주니
    # 반환값으로는 못 가른다).
    ghosted = bb.ghost is not None and (
        'sig', bb._endpoint(p0), bb._endpoint(p1)) in bb.ghost['wires']
    bb.step_wire([p0, p1], 'sig',
                 f'입력 {name} -> {target} · 1 이면 레일 쪽 끝을 +5V 레일로 옮긴다',
                 marker_at=(mx, y_row + dy))
    if not ghosted:
        # 이 점퍼는 `kind='sig'` 로 그린다(넷 검사가 입력을 GND 와 한 넷으로 세면 안
        # 되니까) — 그래서 `step_wire` 가 `touch_rail` 을 안 부르고, 레일 연결성 검사가
        # 이 레일을 아예 안 본다. 중앙 GND 468·우 바깥 GND 836 에 매달린 입력이 접지된
        # 레일과 안 이어져 있어도 verify() 가 통과하던 자리라 여기서 직접 찍는다
        # (2026-09-20). 걷는 점퍼에는 찍지 않는다 — 안 꽂힌 선 때문에 브리지를 내놓으라
        # 하게 된다. `input_node` 도 마찬가지다: 세그먼트가 안 쌓여 직전 배선(엉뚱한
        # 것)의 끝을 가상 입력 노드로 바꾸려다 단언에 걸린다.
        bb.touch_rail('gnd', x_rail)
        bb.input_node(name, c[col], row)
    _tag(bb, 12, y_row - 8, f"입력 {name} → {'우 ' if block == 'right' else ''}{col}{row}")
    # 신호 이름은 보드 안, 레일 쪽 끝 옆. 0/1 을 바꿀 때 옮겨 꽂는 바로 그 끝이다
    bb.signal_tag(name, badge_x, y_rail, seg=len(bb._segments) - 1)


# ---------------------------------------------------------------------------
# 주차 결선 파일 — `보고서/실험NN/결선도/배치.py`
#
# 엔진은 주차를 모른다. 주차마다 결선(칩 자리·배선 순서·단계)은 그 실험 폴더의
# `배치.py` 에 있고, 엔진은 그 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를
# 뽑기만 한다. 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.

BOARD_FILE = '배치.py'

# 도장 — PNG 텍스트 청크. 그림이 **무엇을** 싣는가의 해시(`BreadboardRenderer.content()`).
# 글꼴·줄바꿈은 들지 않는다 — 기계가 달라도 선과 문구가 같으면 도장이 같다.
# `tests/test_breadboard_boards.py` 가 커밋된 PNG 의 도장을 지금 코드와 맞댄다.
STAMP_KEY = 'breadboard-stamp'


def _jsonable(o):
    """`json.dumps` 가 모르는 값 — 집합은 정렬해 목록으로, 나머지는 문자열로."""
    return sorted(o, key=repr) if isinstance(o, (set, frozenset)) else str(o)


def read_stamp(path):
    """PNG 에 찍힌 도장. 없으면 None. `text` 는 PNG 전용 속성이라 다른 형식이면 없다."""
    with Image.open(path) as im:
        return getattr(im, 'text', {}).get(STAMP_KEY)


def _config():
    """`scripts.lab.config` — 실험 폴더 경로 규칙의 정본. 엔진은 스킬 폴더에 있어
    import 경로에 저장소 루트가 없을 수 있다."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    from scripts.lab import config
    return config


def board_path(experiment):
    """실험 번호 → 그 주차 결선 파일의 절대 경로. 있는지는 보지 않는다."""
    return os.path.join(REPO_ROOT, _config().experiment_dir(experiment), '결선도', BOARD_FILE)


def board_numbers(root=None):
    """결선 파일이 있는 실험 번호, 오름차순. 폴더 이름을 `experiment_folder_name` 으로
    되돌려 같을 때만 센다 — 이름 규칙은 config 한 곳에 있다."""
    cfg = _config()
    out = []
    for p in glob.glob(os.path.join(root or REPO_ROOT, cfg.EXPERIMENT_BASE, '*', '결선도', BOARD_FILE)):
        name = os.path.basename(os.path.dirname(os.path.dirname(p)))
        m = re.search(r'(\d+)$', name)
        try:
            if m and cfg.experiment_folder_name(int(m.group(1))) == name:
                out.append(int(m.group(1)))
        except ValueError:
            continue
    return sorted(out)


def load_board_file(path, name=None):
    """주차 결선 파일 하나를 모듈로 불러온다.

    그 파일의 `from render_breadboard import …` 는 **이 엔진**을 가리킨다. 테스트와
    대조기는 엔진을 `importlib` 로 여러 번 로드하고 `sys.modules` 에 올리지 않는다 —
    불러오는 동안만 이 엔진의 전역 이름을 담은 모듈을 그 자리에 끼웠다가 되돌린다.
    그래서 주차 파일의 `BreadboardRenderer` 는 이 엔진의 클래스와 같은 객체다.
    불러오는 동안 바이트코드를 쓰지 않는다 — 보고서 폴더에 `__pycache__` 가 생긴다.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(name or 'board', os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    view = types.ModuleType('render_breadboard')
    view.__dict__.update(globals())
    saved, saved_flag = sys.modules.get('render_breadboard'), sys.dont_write_bytecode
    sys.modules['render_breadboard'] = view
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = saved_flag
        if saved is None:
            sys.modules.pop('render_breadboard', None)
        else:
            sys.modules['render_breadboard'] = saved
    return mod


def load_board(experiment):
    return load_board_file(board_path(experiment), f'board_e{experiment}')


def fresh_board(fn):
    """`rebuild: true` 회로(netlist)의 첫 보드 빌더를 만든다 — 기준선을 버리고 부른다.

    앞 회로의 신호선을 전부 뽑고 새로 짓는 경계라, 앞 보드를 기준선으로 이으면 그
    배선이 전부 '걷는다' 로 잡혀 단계 보드가 선을 걷게 된다(`test_단계_보드는_아무것도_
    걷지_않는다`). 전부 뽑으므로 걷기 보드도 없다 — 체크리스트 배너가 지시한다.
    돌려주는 클로저는 표준 빌더 시그니처라 `BOARDS` 에 그대로 들어간다(2026-09-27, 실험04).
    """
    def build(output_path, template_path=None, stage=None, baseline=None):
        return fn(output_path, template_path, stage=stage, baseline=None)
    build.__name__ = f'fresh_{getattr(fn, "__name__", "board")}'
    return build


def stage_budget(board):
    """주차 `board` 의 단계 예산 — 기본은 `STAGE_WIRE_BUDGET`(셋).

    주차 파일이 `STAGE_WIRE_BUDGET` 을 두면 그 값을 쓴다. 칩 구조상 셋으로는 관측
    노드 하나를 세울 수 없는 주차의 예외다 — 실험04 는 4입력 NAND 라 입력 넷과
    관측선 하나가 한꺼번에 있어야 한다(2026-09-27 결정, 예산 = 게이트 입력 수 + 1).
    **이유(`STAGE_WIRE_BUDGET_REASON`)가 없으면 거절한다** — 숫자만 올리면 예산이
    조용히 풀리고, 무엇 때문에 풀었는지 다음 주차가 알 수 없다.
    """
    value = getattr(board, 'STAGE_WIRE_BUDGET', None)
    if value is None:
        return STAGE_WIRE_BUDGET
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f'주차 STAGE_WIRE_BUDGET 은 양의 정수여야 한다: {value!r}')
    if not str(getattr(board, 'STAGE_WIRE_BUDGET_REASON', '') or '').strip():
        raise ValueError('주차 STAGE_WIRE_BUDGET 예외에는 STAGE_WIRE_BUDGET_REASON 이 있어야 한다 '
                         '— 왜 셋으로 관측 노드 하나를 세울 수 없는지 적는다')
    return value


def removal_board(prev, nxt, title, subtitle):
    """걷기 보드 빌더를 만든다. `prev`·`nxt` 는 `(빌더, stage)`.

    앞 회로(`prev`)를 전부 회색으로 그리고, 다음 회로(`nxt`)에 없는 배선만 빨간 점선 +
    걷기 번호로 그린다. 새 선은 없다. **선을 뽑는 자리마다 한 장** — 회로 경계뿐
    아니라 같은 회로 안의 인접 단계에서 임시 프로브 급전선을 뽑을 때도 같다.

    돌려주는 클로저는 표준 빌더 시그니처라 `BOARDS` 에 그대로 들어간다. `__module__` 이
    엔진이라 주차 파일의 `build_*` 열거(`tests/_boards.py`)에 안 잡힌다 — 걷기 보드는
    `steps` 가 비어 가독성 검사(`steps > 0`)의 대상이 아니다. 주차 파일에 `build_` 로
    시작하는 래퍼를 두지 않는다.

    `baseline` 을 안 넘기면 앞 보드를 임시 렌더해 스스로 만든다 — 단계 래퍼
    (`_eN_board`)가 그렇게 부른다. 사슬(`build_all`)은 앞 보드의 snapshot 을 넘긴다.

    클로저는 `stage` 를 **거절한다** — 앞뒤 회로의 단계는 `prev`·`nxt` 로 이미 정해져
    있어서, 호출 쪽이 또 주면 조용히 무시돼 엉뚱한 단계의 걷기 그림이 나간다.
    """
    prev_fn, prev_stage = prev
    nxt_fn, nxt_stage = nxt

    def build(output_path, template_path=None, stage=None, baseline=None):
        assert stage is None, ('걷기 보드는 stage 를 받지 않는다 — '
                               'prev/nxt 의 stage 는 removal_board() 인자로 준다')
        with tempfile.TemporaryDirectory() as d:
            base = baseline or prev_fn(os.path.join(d, 'prev.png'), template_path,
                                       stage=prev_stage).snapshot()
            nb = nxt_fn(os.path.join(d, 'next.png'), template_path,
                        stage=nxt_stage, baseline=base)
            wires = {r['key']: r['n'] for r in nb.removals()}
        if not wires:
            raise ValueError(f'{title}: 걷을 배선이 없다 — 걷기 보드가 필요 없는 경계다')
        ghost = dict(base, ghost={'wires': wires, 'title': title, 'subtitle': subtitle})
        return prev_fn(output_path, template_path, stage=prev_stage, baseline=ghost)

    build.__name__ = f'removal_{nxt_fn.__name__}'
    return build


def build_all(board, output_dir, template_path=None):
    """주차 결선 파일 `board` 의 결선도를 전부 뽑는다 — 절차 사슬 `BOARDS` 는 앞 보드를
    기준선으로 이어 그리고(회색·걷기 표), 완성본 `FINALS` 는 기준선 없이 그린다.
    `{파일명: 도장}` 을 돌려준다(사슬 순서, 그다음 완성본)."""
    os.makedirs(output_dir, exist_ok=True)
    made, base = {}, None
    for filename, fn, stage in board.BOARDS:
        bb = fn(os.path.join(output_dir, filename), template_path, stage=stage, baseline=base)
        if bb is None:
            raise TypeError(
                f"{filename}: 빌더 {fn.__name__} 가 렌더러를 돌려주지 않는다 — "
                "빌더 끝에 `return bb` 가 있어야 한다")
        base = bb.snapshot()
        made[filename] = bb.stamp()
    for filename, fn in board.FINALS:
        bb = fn(os.path.join(output_dir, filename), template_path)
        if bb is None:
            raise TypeError(
                f"{filename}: 빌더 {fn.__name__} 가 렌더러를 돌려주지 않는다 — "
                "빌더 끝에 `return bb` 가 있어야 한다")
        made[filename] = bb.stamp()
    return made


def main():
    parser = argparse.ArgumentParser(description="Breadboard Diagram Generator")
    parser.add_argument("--experiment", type=int, required=True,
                        help="실험 번호 — 보고서/실험NN/결선도/배치.py 의 결선도를 전부 뽑는다")
    parser.add_argument("--output", default=None,
                        help="출력 폴더 (기본: 그 배치.py 가 있는 결선도 폴더)")
    parser.add_argument("--template", default=None, help="Path to Breadboard.jpg")
    args = parser.parse_args()
    try:
        path = board_path(args.experiment)
    except ValueError as e:
        parser.error(str(e))
    if not os.path.exists(path):
        parser.error(f"주차 결선 파일이 없다: {path}")
    out = args.output or os.path.dirname(path)
    made = build_all(load_board(args.experiment), out, args.template)
    print(f"[SUCCESS] {_config().experiment_folder_name(args.experiment)} "
          f"결선도 {len(made)}장 생성: {out}")


if __name__ == "__main__":
    main()
