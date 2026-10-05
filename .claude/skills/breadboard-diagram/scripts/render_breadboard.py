import os
import re
import sys
import glob
import json
import types
import hashlib
import argparse
import tempfile
import copy
import bisect
import itertools
import math
from dataclasses import dataclass
from functools import lru_cache
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


# 출력 배율. 좌표는 전부 정본 템플릿(998px 폭) 기준으로 계산하고, **그리는 순간에만**
# 이 배율을 곱한다(`_ScaledDraw`·`_ScaledFont`). 2026-09-28 사용자: 태블릿에서 998px 그림의
# 글자가 작아 확대해야 읽혔다. 정본 `Breadboard.jpg` 는 998px 한 장뿐이라 격자·로고는
# 확대해 깔고, 선·칩·글자·번호 원·결선 목록은 이 배율로 새로 그려 선명하다.
SCALE = 2


class _ScaledFont:
    """논리 크기로 부르고 SCALE 배 크기로 그리는 폰트. 치수는 논리 단위로 돌려준다."""

    def __init__(self, path, size):
        self.size = size
        self.real = ImageFont.truetype(path, size * SCALE)

    def getbbox(self, text, *a, **k):
        return tuple(v / SCALE for v in self.real.getbbox(text, *a, **k))

    def getlength(self, text, *a, **k):
        return self.real.getlength(text, *a, **k) / SCALE


def _sc(v):
    """좌표(숫자·점·점 목록)에 SCALE 을 곱한다."""
    if isinstance(v, (int, float)):
        return v * SCALE
    return type(v)(_sc(x) for x in v) if isinstance(v, (tuple, list)) else v


class _ScaledDraw:
    """`ImageDraw` 를 감싼다 — 논리 좌표를 받아 SCALE 배 캔버스에 그린다."""

    def __init__(self, image):
        self._d = ImageDraw.Draw(image)

    @staticmethod
    def _kw(k):
        k = dict(k)
        if 'width' in k:
            k['width'] = max(1, round(k['width'] * SCALE))
        if isinstance(k.get('font'), _ScaledFont):
            k['font'] = k['font'].real
        return k

    def line(self, xy, *a, **k):
        return self._d.line(_sc(xy), *a, **self._kw(k))

    def rectangle(self, xy, *a, **k):
        return self._d.rectangle(_sc(xy), *a, **self._kw(k))

    def ellipse(self, xy, *a, **k):
        return self._d.ellipse(_sc(xy), *a, **self._kw(k))

    def polygon(self, xy, *a, **k):
        return self._d.polygon(_sc(xy), *a, **self._kw(k))

    def arc(self, xy, start, end, *a, **k):
        return self._d.arc(_sc(xy), start, end, *a, **self._kw(k))

    def text(self, xy, text, *a, **k):
        return self._d.text(_sc(xy), text, *a, **self._kw(k))

    def textbbox(self, xy, text, *a, **k):
        return tuple(v / SCALE for v in self._d.textbbox(_sc(xy), text, *a, **self._kw(k)))

    def textlength(self, text, *a, **k):
        return self._d.textlength(text, *a, **self._kw(k)) / SCALE


def _font(kind, size):
    return _ScaledFont(font_path(kind), size)


def _default_template(spec=None):
    """판형 양식 경로. 후보를 저장소 루트에서 먼저 보고, 없으면 cwd 도 본다.

    **다른 판형으로 넘어가지 않는다** — v2 양식이 없는데 v1 로 그리면 열 표와 그림이 어긋난
    채 그럴듯하게 나온다. 후보가 다 없으면 멈춘다.
    """
    spec = spec or board_spec(DEFAULT_BOARD)
    tried = []
    for rel in spec.template:
        for base in (REPO_ROOT, os.getcwd()):
            path = os.path.join(base, rel)
            if path in tried:
                continue
            tried.append(path)
            if os.path.exists(path):
                return path
    raise FileNotFoundError(
        f'브레드보드 템플릿({spec.name})을 찾지 못했습니다. 찾아본 곳:\n  ' + '\n  '.join(tried))


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

# **입력** 신호 이름 배지의 색 — 이 색으로 채운 상자에 흰 화살촉(선이 뻗는 쪽)과 흰 글자. 네 배선색(빨강·
# 파랑·검정·초록)과 출력 LED 의 빨강, 유지선 회색, 계측 회색 어느 것과도 겹치지 않는
# 보라다. 2026-09-29 실험04 MUX: 입력 여섯이 흰 바탕 검정 글자라 흰 번호 원 41 개 사이에
# 묻혔다. 화살촉(▶·◀)은 글리프가 아니라 다각형이다 — 이모지·기호 글리프는 기계마다 □ 가 되고
# 손그림에 못 옮긴다
INPUT = (110, 40, 160, 255)
INPUT_TRI = 4.5   # 화살촉 폭. 좌 바깥 여백(v1 보드 테두리 149 ~ GND 레일 174 = 25px, v2 144 ~ 176 = 32px)에
                  # `D0` 배지가 들어가는 상한이다 — 글자 15 + 화살촉 4.5 + 틈 1 + 좌우 여백 1·1 = 22.5

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


# ---------------------------------------------------------------------------
# 판형 버전 — 버전마다 짝으로 바뀌는 것을 한 객체에 묶는다. 렌더러 본문은 `self.spec` 만
# 읽고 버전 이름으로 분기하지 않는다.
#
# v1 = `.claude/assets/Breadboard.jpg` — 실험01~04 전용. 숫자는 위 모듈 상수 그대로이고,
#      그 상수들(`ROW0`·`BOARD_LEFT`·`JACKS`…)은 v1 의 별칭으로 남는다(손그림 검토·테스트가 읽는다).
# v2 = `.claude/assets/breadboard_v2/` — 실험05 부터. 숫자는 `geometry.json` 에서만 읽는다 —
#      베껴 적으면 판형을 다시 뽑았을 때 한쪽만 바뀐다. 가운데 레일이 2열 하나뿐이라 두
#      블록이 같은 x 를 `mid_gnd`·`mid_vcc` 로 부른다.
# 설계: docs/plans/2026-10-02-브레드보드-v2-구조-설계.md

BOARD_VERSIONS = ('v1', 'v2')
# `board` 를 안 넘기면 쓰는 판형 — 실물 보드가 v2 다. v1 주차(01~04)는 `배치.py` 에 `BOARD = 'v1'` 을 적어 둔다
DEFAULT_BOARD = 'v2'

V2_GEOMETRY = os.path.join(REPO_ROOT, '.claude', 'assets', 'breadboard_v2', 'geometry.json')

# geometry.json 의 잭 이름 -> 렌더러 잭 키. 키는 v1 그대로다 — 끝점 기호 `('jack', 'red')` 가
# 도장과 손그림 전사 문법(`전원잭(빨강)`)에 들어 있다
_V2_JACK_KEYS = {'+5V': 'red', 'yellow': 'yellow', '0V': 'gray'}

# v1 열 표 — `Breadboard.jpg` 실측(2026-09-07). 옛 `_init_cols` 의 표를 그대로 옮겼다
_V1_COLS = {
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


@dataclass(frozen=True)
class BoardSpec:
    """판형 하나에 묶인 값. 렌더러는 이것만 보고 그린다."""
    name: str               # 'v1' | 'v2'
    template: tuple         # 양식 후보 경로(저장소 루트 기준 또는 절대). 앞에서부터 쓴다
    size: tuple             # 양식 크기 (w, h) — 좌표표가 이 크기에 묶여 있다
    row0: float             # 1행 홀 중심 y
    row_pitch: float        # 행 간격
    board_left: int         # 보드 좌·우 테두리 x — 이 밖은 여백
    board_right: int
    jacks: dict             # 잭 키 -> 중심 x
    jack_bottom: int        # 잭 선이 출발하는 y
    jack_y_max: int         # 이보다 위이고 잭 x 30px 안이면 잭 — 보드 밖의 유일한 합법 끝점
    jack_route_y: tuple     # (+5V 선, 0V 선) 이 보드 위 테두리 바로 안쪽을 가로지르는 y
    jack_marker_y: int      # 잭 선 번호 원의 y (x 는 잭 + 46)
    cols: dict              # 열 표 — {'left': {...}, 'right': {...}}
    mid_badge_x: float      # 가운데 레일에서 출발하는 입력 점퍼의 이름 배지 x
    chip_blocks: tuple      # 칩을 둘 수 있는 블록 (R9)
    led_only_blocks: tuple  # LED 사슬만 두는 블록 (R10). 비면 R10 을 안 돈다
    sha256: str = None      # 양식 PNG 해시. 있으면 대조한다 — 다시 뽑은 PNG 를 잡는다
    readability: bool = False   # 읽기 규칙 R11~R14 과 번호 원 자동 자리. v2 만 켠다 — v1 승인본은 소급 안 함


_V1 = BoardSpec(
    name='v1', template=TEMPLATE_CANDIDATES, size=TEMPLATE_SIZE,
    row0=ROW0, row_pitch=ROW_PITCH, board_left=BOARD_LEFT, board_right=BOARD_RIGHT,
    jacks=dict(JACKS), jack_bottom=JACK_BOTTOM,
    # 보드 위 테두리 y=242 바로 위가 잭 영역이고, 잭 선은 242 + 8·16 에서 가로지른다
    jack_y_max=240, jack_route_y=(250, 258), jack_marker_y=118,
    cols=_V1_COLS,
    # 좌 중앙 VCC 484 ~ 우 중앙 GND 542 사이 여백의 가운데
    mid_badge_x=(_V1_COLS['left']['mid_vcc'] + _V1_COLS['right']['mid_gnd']) / 2,
    chip_blocks=('left', 'right'), led_only_blocks=())


def _spec_from_geometry(path):
    """v2 판형 사양을 `geometry.json` 에서 짓는다. 행 수·레일 빈 행·잭 이름이 렌더러가 아는 것과
    다르면 멈춘다 — 판형이 바뀐 것이다. 양식 PNG 는 그 파일 옆에 있다."""
    if not os.path.exists(path):
        raise FileNotFoundError(f'v2 판형 좌표 파일이 없다: {path} — v1 로 넘어가지 않는다')
    with open(path, encoding='utf-8') as f:
        g = json.load(f)
    if g.get('rows') != ROW_MAX or set(g.get('rail_gap_rows', ())) != set(RAIL_GAP_ROWS):
        raise ValueError(f'{path}: 행 수·레일 빈 행이 렌더러({ROW_MAX}행, '
                         f'{sorted(RAIL_GAP_ROWS)})와 다르다')
    cols = {'left': {}, 'right': {}}
    for c in g['columns']:
        side, key = c['name'].split('.')
        if side == 'mid':
            # 가운데 레일은 한 열을 두 블록이 같은 이름으로 부른다 — 넷 단위가 ('rail', x) 라
            # 이것만으로 한 넷이다(설계 §2)
            cols['left'][f'mid_{key}'] = cols['right'][f'mid_{key}'] = c['x']
        else:
            cols[side][key] = c['x']
    for blk in cols.values():
        # 칩 몸통은 e·f 핀 열 안쪽 5px — v1 의 310·349 가 같은 식이다(305+5, 354-5)
        blk['chip_x1'], blk['chip_x2'] = blk['e'] + 5, blk['f'] - 5
    try:
        jacks = {_V2_JACK_KEYS[j['name']]: j['center_x'] for j in g['jacks']}
    except KeyError as e:
        raise ValueError(f'{path}: 모르는 잭 이름 {e} — {sorted(_V2_JACK_KEYS)} 중 하나다') from None
    bottoms = {j['bottom_y'] for j in g['jacks']}
    centers = {j['center_y'] for j in g['jacks']}
    if len(bottoms) != 1 or len(centers) != 1:
        raise ValueError(f'{path}: 잭 높이가 제각각이다 — 잭 선 경로가 하나로 안 정해진다')
    top = g['border']['top']
    return BoardSpec(
        name='v2',
        template=(os.path.join(os.path.dirname(os.path.abspath(path)), g['png']),),
        size=(g['image']['width'], g['image']['height']),
        row0=float(g['row1_center_y']), row_pitch=float(g['row_pitch']),
        board_left=g['border']['left'], board_right=g['border']['right'],
        jacks=jacks, jack_bottom=bottoms.pop(),
        # 잭 영역은 보드 위 테두리 위, 잭 선은 테두리 + 8·16 에서 가로지른다 — v1 과 같은 식
        jack_y_max=top, jack_route_y=(top + 8, top + 16), jack_marker_y=centers.pop(),
        cols=cols,
        # 입력선은 가운데 레일에서 왼쪽(좌 블록 f~j)으로 뻗는다 — 배지는 반대쪽 여백, 가운데
        # VCC 와 우 a 열 사이에 둔다
        mid_badge_x=(cols['left']['mid_vcc'] + cols['right']['a']) / 2,
        chip_blocks=('left',), led_only_blocks=('right',),
        sha256=g['png_sha256'], readability=True)


@lru_cache(maxsize=None)
def board_spec(name='v1'):
    """판형 버전 이름 -> `BoardSpec`. v2 는 처음 부를 때 `geometry.json` 을 읽는다."""
    if name == 'v1':
        return _V1
    if name == 'v2':
        return _spec_from_geometry(V2_GEOMETRY)
    raise ValueError(f'판형 버전은 {BOARD_VERSIONS} 중 하나다: {name!r}')


def _hole_columns(cols):
    """열 표 -> {x: (블록, 열 이름)}. 칩 몸통 경계(`chip_x1`·`chip_x2`)는 홀이 아니라 뺀다.
    두 블록이 같은 x 를 부르면(v2 가운데 레일) 먼저 나온 `left` 를 남긴다."""
    out = {}
    for block in ('left', 'right'):
        for key, x in cols[block].items():
            if not key.startswith('chip'):
                out.setdefault(x, (block, key))
    return out


def column_table(board=DEFAULT_BOARD):
    """판형 `board` 의 홀 열 — x -> (블록, 열 이름). 손그림 검토가 렌더러를 띄우지 않고 읽는다."""
    return _hole_columns(board_spec(board).cols)


def _shared_of(cols):
    """두 블록이 같은 x 로 부르는 홀 열 — v2 가운데 레일. v1 은 빈 집합이다."""
    left = {x for k, x in cols['left'].items() if not k.startswith('chip')}
    right = {x for k, x in cols['right'].items() if not k.startswith('chip')}
    return left & right


def shared_columns(board=DEFAULT_BOARD):
    """판형 `board` 에서 두 블록이 나눠 쓰는 열의 x. 손그림 검토의 격자 라벨이 접두어를 뺄 때 쓴다."""
    return _shared_of(board_spec(board).cols)


class BreadboardRenderer:
    def __init__(self, template_path=None, baseline=None, layer=None, board=DEFAULT_BOARD):
        # 판형 버전. 주차 `배치.py` 의 `BOARD` 를 빌더가 그대로 넘긴다 — `build_all` 이 대조한다
        self.board = board
        self.spec = board_spec(board)
        if template_path is None:
            template_path = _default_template(self.spec)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Breadboard template not found: {template_path}")

        self.base_im = Image.open(template_path).convert('RGBA')
        # 좌표표가 이 크기에 묶여 있다. 다른 판본이 들어오면 여기서 걸린다 —
        # 갈아끼운 그림은 결과가 그럴듯해서 눈으로는 안 잡히기 때문이다.
        w, h = self.spec.size
        if self.base_im.size != self.spec.size:
            raise ValueError(
                f'템플릿 크기가 {w}x{h} 가 아닙니다: '
                f'{self.base_im.size} ({template_path}).\n'
                'cols·r_y() 좌표는 정본 한 장에 맞춰져 있습니다. '
                '다른 판본을 쓰려면 좌표표를 다시 떠야 합니다.')
        if self.spec.sha256 is not None:
            with open(template_path, 'rb') as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            if digest != self.spec.sha256:
                raise ValueError(
                    f'{self.board} 양식 PNG 의 해시가 geometry.json 의 png_sha256 과 다르다: '
                    f'{template_path}.\n판형을 다시 뽑았으면 1배(1200x1600)인지, '
                    'hand_grid.detect_grid 가 0px 로 맞는지 확인하고 png_sha256 을 같이 고친다')
        # 정본은 998px 한 장뿐이다 — 격자·로고는 확대해 깐다(`SCALE` 주석). NEAREST 는 픽셀을
        # 그대로 늘려 원본과 같은 모양이다. LANCZOS 는 JPEG 잡티까지 매끈하게 늘려 PNG 가
        # 장당 2.3MB 로 커졌다(NEAREST 는 1.1MB 안팎, 2026-09-28 실측)
        self.im = self.base_im.resize((w * SCALE, h * SCALE), Image.NEAREST)
        self.overlay = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.draw = _ScaledDraw(self.overlay)
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
        # 번호 원의 **자리** — 그렸든 안 그렸든(층 그림의 흐린·숨긴 번호, 기준선 회색 선). v2 자동
        # 자리(`_auto_marker`)는 이것을 피한다. 그려진 원만 피하면 층 그림과 완성본의 자리가
        # 갈라져, 완성본은 통과하는데 층 그림이 R11 로 멈춘다(2026-10-04 검토). `readability` 만
        self._marker_slots = []
        # 보드 밖 입력 꼬리표(`_tag`) 상자 — (글, (x0, y0, x1, y1)). 같은 행 입력이 둘이면
        # 꼬리표가 포개진다(2026-09-28 실험04 C2 S1·D) — `_input_jumper` 가 이걸 보고 비킨다
        self.margin_tag_boxes = []
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
        self._pull_parts = False  # led_chain 이 걷기 보드가 뽑는 사슬을 그리는 동안 참
        # 걷기 보드 — 기준선 dict 의 `ghost` 키 `{'wires': {key: n}, 'title', 'subtitle'}`.
        # 사슬째 뽑는 LED 사슬이 있으면 `'chains': {사슬 key: tag}` 도 든다.
        # `step_wire()` 가 그 key 를 만나면 점유표·구간에 안 남기고 `ghost_layer` 에 빨간
        # 점선으로 그린다. 뽑은 선의 핀이 뜨는 것이 정상이라 `partial` 이다.
        # 기준선 dict 에 키를 얹는 이유: `set_header()` 가 제목을 즉시 그려 사후에 못 바꾸고,
        # 빌더 시그니처를 늘리면 세 주차 스물세 빌더를 고쳐야 한다. `removal_board()` 가 만든다
        self.ghost = (baseline or {}).get('ghost')
        self.ghost_layer = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.ghost_drawn = {}     # key -> n. export() 가 빌더가 안 그린 key 를 잡는다
        self.ghost_chains_drawn = set()   # 사슬 key. export() 가 안 그린 사슬을 잡는다
        if self.ghost is not None:
            self.partial = True
        # 따라 그리기 층 — (lo, hi). 완성본 빌더를 그대로 돌리되 번호 lo 앞 배선은 회색·번호
        # 없이, lo~hi 는 색·완성본 번호로, hi 뒤는 버리는 판(`_hidden_draw`)에 그린다.
        # 안 보이는 배선도 점유표·구간·결선 순서표에는 남긴다 — 빼면 뒤 배선의
        # `free_rail_row()` 가 다른 행을 골라 완성본과 다른 그림이 된다(2026-09-28 팀원 전달용).
        # 기준선 사슬과 섞지 않는다 — 기준선의 회색은 "실험실에서 손대지 않는다" 는 다른 뜻이다
        if layer is not None:
            if baseline is not None:
                raise ValueError('layer 는 기준선 없는 완성본에만 준다 — baseline 과 함께 못 준다')
            ok = (isinstance(layer, tuple) and len(layer) == 2
                  and all(type(v) is int for v in layer) and 1 <= layer[0] <= layer[1])
            if not ok:
                raise ValueError(f'layer 는 1 <= lo <= hi 인 정수 쌍이어야 한다: {layer!r}')
        self.layer = layer
        self._hidden_draw = (_ScaledDraw(Image.new('RGBA', self.im.size, (0, 0, 0, 0)))
                             if layer is not None else None)
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
        # 칩마다 이름 글자 상자(논리 좌표) — R14. 글꼴 따라 달라지는 픽셀이라 `chips`(도장에 든다)와 따로 둔다
        self.chip_label_boxes = []
        self.leds = []
        self.resistors = []
        self.led_chains = []
        self.unused_inputs = []
        self.unused_outputs = []

        self._addr_map = self._build_addr_map()
        self._sym_map = self._build_sym_map()

    def _layer_view(self, n):
        """따라 그리기 층에서 번호 n 배선의 모양 — 'shown'(색·번호) · 'faded'(회색) · 'hidden'."""
        if self.layer is None:
            return 'shown'
        lo, hi = self.layer
        if n < lo:
            return 'faded'
        if n > hi:
            return 'hidden'
        return 'shown'

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
        """열 좌표표 — 판형 사양(`self.spec.cols`)의 사본. 렌더러 안에서는 이 표가 열 좌표의
        **유일한 권위**다. 손그림 검토는 같은 사양을 `column_table()` 로 읽는다."""
        self.cols = copy.deepcopy(self.spec.cols)
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
        return int(round(self.spec.row0 + (r - 1) * self.spec.row_pitch))

    @staticmethod
    def is_rail_row(r):
        return 1 <= r <= ROW_MAX and r not in RAIL_GAP_ROWS

    def _row_of(self, y):
        """y 좌표에 제일 가까운 행 번호. addr() 과 hole_at() 이 같은 식을 쓴다 — 한쪽만 고치면 갈린다."""
        return int(round((y - self.spec.row0) / self.spec.row_pitch)) + 1

    def hole_at(self, x, y):
        """(x, y) 가 실제 홀이면 그 홀의 키 (열 x, 행), 아니면 None.

        레일은 5홀씩 묶여 빈 행이 있고, 단자대는 63행 전부 홀이다. 열·행 모두
        홀 중심에서 5px 안이어야 한다 — 열 피치가 16px 라 9px 로는 인접 열
        사이에 거부 구간이 없었다. 그 밖은 배선 통로거나 밀린 좌표다.
        v2 는 열 24px·행 19px 라 5px 허용치가 더 넉넉하다.
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

    def _jack_at(self, x, y):
        """(x, y) 가 전원 잭이면 그 잭 키('red'·'yellow'·'gray'), 아니면 None.

        잭은 보드 밖의 유일한 합법 끝점이다. `lead`·`_endpoint`·`nets` 가 같은 규칙을 써야 해서
        한 자리에 둔다 — 판형마다 잭 자리와 보드 위 테두리가 다르다(`self.spec`).
        """
        s = self.spec
        if y < s.jack_y_max and any(abs(x - jx) < 30 for jx in s.jacks.values()):
            return min(s.jacks, key=lambda k: abs(s.jacks[k] - x))
        return None

    def lead(self, x, y, what):
        """홀 (x, y) 에 리드 하나를 꽂는다.

        전원잭(`_jack_at`)은 보드 밖의 유일한 합법 끝점이라 건너뛴다. 홀이 아니면
        R1 위반, 이미 차 있으면 R2 위반으로 적어 두고 verify() 가 한꺼번에 낸다
        — 그리는 도중에 던지면 어디까지 그렸는지 알 수 없다.
        """
        if self._jack_at(x, y) is not None:
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

    def _shared_xs(self):
        """두 블록이 같은 x 로 부르는 열(v2 가운데 레일). v1 은 빈 집합이다."""
        return _shared_of(self.cols)

    def touch_rail(self, kind, x):
        """이 배선이 어느 전원 레일에 닿았는지 적어 둔다."""
        if kind in self._touched and x in self._rail_xs():
            self._touched[kind].add(x)

    def _build_addr_map(self):
        """x 좌표 -> 사람이 읽는 이름. 결선 순서표의 주소를 자동으로 만든다.

        두 블록이 같은 x 로 부르는 열(v2 가운데 레일)은 좌·우 접두어 없이 한 번만 적는다 —
        한 레일이다(설계 §3). v1 은 그런 열이 없어 이름이 그대로다.
        """
        names = {'gnd': 'GND레일', 'vcc': 'VCC레일',
                 'mid_gnd': '중앙GND레일', 'mid_vcc': '중앙VCC레일'}
        shared = self._shared_xs()
        out = {}
        for x, (block, key) in _hole_columns(self.cols).items():
            name = names.get(key, key)
            out[x] = name if x in shared else f"{'좌' if block == 'left' else '우'} {name}"
        return out

    def _build_sym_map(self):
        """x 좌표 -> (블록, 열 이름). `_addr_map` 의 기계용 짝이다. 두 블록이 같은 x 를 부르면
        (v2 가운데 레일) `left` 다."""
        return _hole_columns(self.cols)

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
        s = self.spec
        if y < s.jack_y_max:
            return '전원잭'
        if x < s.board_left:
            return '보드밖(입력)'
        if x > s.board_right:
            return '보드밖'
        r = self._row_of(y)
        best = min(self._addr_map, key=lambda k: abs(k - x))
        # 9px 는 v1 열 피치(16)의 절반 남짓이고 v2(24)에서도 절반보다 작다
        if abs(best - x) > 9:
            # 홀이 아니라 배선 통로다. 분기점(T 접속)일 때만 여기 온다
            return '분기점'
        name = self._addr_map[best]
        return f'{name}{r}행' if '레일' in name else f'{name}{r}'

    # ---------------- 머리글 ----------------

    def set_header(self, title, subtitle, submit=True):
        """제목·부제는 **그리지 않는다** — 사이드카 JSON 으로 가고 체크리스트가 싣는다
        (2026-09-28 읽기면 개편: 그림에 구운 글자는 태블릿에서 작고 체크할 수 없었다).

        걷기 보드(ghost 모드)는 앞 회로 빌더가 부르는 제목 대신 `ghost` 의 제목을 쓴다 —
        빌더는 자기가 걷기 보드로 렌더되는지 모른다.
        """
        if self.ghost is not None:
            title, subtitle, submit = self.ghost['title'], self.ghost['subtitle'], False
        self.title, self.subtitle = title, subtitle
        self.submit = submit

    def connect_jacks(self, block='left'):
        """전원 잭 -> 보드 레일. 과거 결선도가 모두 그리던 선이다.

        잭 아래 끝에서 내려와 보드 위 테두리 바로 안쪽(`spec.jack_route_y`)을 가로질러 레일로
        간다. v1 은 테두리 242 + 8·16 = 250·258, v2 는 304 + 8·16 = 312·320 — 같은 식이다.
        """
        c, s = self.cols[block], self.spec
        y_v, y_g = s.jack_route_y
        r_v, r_g = self.free_rail_row(3, c['vcc']), self.free_rail_row(4, c['gnd'])
        self.step_wire([(s.jacks['red'], s.jack_bottom), (s.jacks['red'], y_v),
                        (c['vcc'], y_v), (c['vcc'], self.r_y(r_v))],
                       'vcc', '전원장치 +5V 잭', marker_at=(s.jacks['red'] + 46, s.jack_marker_y))
        self.step_wire([(s.jacks['gray'], s.jack_bottom), (s.jacks['gray'], y_g),
                        (c['gnd'], y_g), (c['gnd'], self.r_y(r_g))],
                       'gnd', '전원장치 0V 잭', marker_at=(s.jacks['gray'] + 46, s.jack_marker_y))

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

    def signal_tag(self, name, x, y, align='center', col=(20, 20, 20, 255), seg=None,
                   arrow=None):
        """보드 안 **신호 이름** 배지 — 입력 A·B·C, 출력 L1·L2·X·Y·Z.

        2026-09 실험01 예보 조교 감점(-1): 손그림 결선도에 입력 A·B·C 위치 표기가
        없었다. 원도는 입력 이름을 보드 밖(x=12) 꼬리표에만 적었고, 학생은 보드
        판형 위만 따라 그려 그 글자가 옮겨지지 않았다. 신호 이름은 그림의 일부라
        이 함수로 보드 안에 둔다. 규칙 문구는 여전히 `note()` 로 보드 밖이다.

        `align='center'` 면 (x, y) 가 배지 중심, `'left'` 면 x 가 배지 상자의 왼쪽
        끝이다. `seg` 는 이 이름이 가리키는 배선의 `_segments` 번호 — 겹침 검사가
        그 선만 봐준다.

        `arrow='left'|'right'` 는 입력 표지다 — `col` 로 채운 상자에 흰 화살촉과 흰 글자.
        화살촉은 점퍼선이 뻗는 쪽 끝에서 그쪽을 가리킨다(`D0▶`·`◀E`) — 중앙 여백의
        배지는 이것으로 좌·우 어느 블록으로 들어가는지 갈린다. 좌우 여백을 1 로 줄여
        화살촉 자리를 낸다(`INPUT_TRI`). 상자(겹침 검사 대상)는 화살촉까지 덮는다.
        """
        assert arrow in (None, 'left', 'right'), f"arrow 는 None·'left'·'right' 다: {arrow!r}"
        font, pad = self.font_en_bold, 2
        b = self.draw.textbbox((0, 0), name, font=font)
        w, h = b[2] - b[0], b[3] - b[1]
        hpad = 1 if arrow else pad
        tri, gap = (INPUT_TRI, 1) if arrow else (0, 0)
        full = tri + gap + w
        left = x - full / 2 if align == 'center' else x + hpad
        lead = tri + gap if arrow == 'left' else 0     # 글자 앞에 오는 화살촉 몫
        tx, ty = left + lead - b[0], y - h / 2 - b[1]
        box = self.draw.textbbox((tx, ty), name, font=font)
        box = (box[0] - lead - hpad, box[1] - pad,
               box[2] + (tri + gap - lead) + hpad, box[3] + pad)
        if arrow:
            self.draw.rectangle(box, fill=col, outline=col, width=1)
            cy = (box[1] + box[3]) / 2
            if arrow == 'right':
                x0 = box[2] - hpad - tri
                tip = [(x0, cy - h * 0.4), (x0 + tri, cy), (x0, cy + h * 0.4)]
            else:
                x0 = box[0] + hpad
                tip = [(x0 + tri, cy - h * 0.4), (x0, cy), (x0 + tri, cy + h * 0.4)]
            self.draw.polygon(tip, fill=(255, 255, 255, 255))
            self.draw.text((tx, ty), name, fill=(255, 255, 255, 255), font=font)
        else:
            self.draw_badge(tx, ty, name, (255, 255, 255, 235), col, font=font, pad=pad)
        self.tag_boxes.append((name, box, seg))

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
        # x=140·100·12 는 좌 여백 안이다 — v1 테두리 149, v2 144 둘 다 그 오른쪽이라 판형과 무관하다
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
                     draw=_ScaledDraw(self.ghost_layer))
        if len(points) < 2:
            self._marker_removed(points[0][0], points[0][1], n)
            return
        (x0, y0), (x1, y1) = max(zip(points, points[1:]),
                                 key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
        span = max(1.0, ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
        ux, uy = (x1 - x0) / span, (y1 - y0) / span
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        x, y = mx, my
        if self.spec.readability:
            # v2: 다른 번호 원만이 아니라 꽂힌 홀·칩 몸통도 피한다(R11). 2026-10-05 배치 탐색 8걷기 —
            # 유령선 번호 원이 중앙 GND 레일 홀을 덮었다. 구간을 따라 4px 씩 가운데부터 훑는다
            for k in sorted(range(-int(span / 2) + 8, int(span / 2) - 7, 4), key=lambda k: (abs(k), k)):
                cx, cy = int(mx + ux * k), int(my + uy * k)    # 찍는 자리(정수)로 잰다 — 반 행 선은 .5 다
                box = (cx - 8, cy - 8, cx + 8, cy + 8)
                if (not any(_boxes_touch(box, b) for b in self.marker_boxes)
                        and not any(box[0] - 1 <= hx <= box[2] + 1 and box[1] - 1 <= self.r_y(hr) <= box[3] + 1
                                    for hx, hr in self._leads)
                        and not any(_boxes_touch(box, b) for b, _cx, _ch in self._chip_bodies())):
                    self._marker_removed(cx, cy, n)
                    return
        for k in (0, 24, -24, 48):
            x, y = mx + ux * k, my + uy * k
            box = (x - 8, y - 8, x + 8, y + 8)
            if not any(_boxes_touch(box, b) for b in self.marker_boxes):
                break
        self._marker_removed(int(x), int(y), n)

    def step_wire(self, points, kind, desc, width=3, marker_at=None, count=1,
                  frm=None, to=None, marker_near=None):
        """배선 하나 + 결선 순서표 한 줄.

        `desc` 는 짧은 뜻풀이만 준다 — 어디서 어디로 가는지는 좌표에서
        자동으로 뽑는다 ('좌 b7 -> 좌 GND레일7행').

        기준선(`baseline`)에 같은 (색, 끝점, 끝점) 이 있으면 **회색으로 그리고
        번호를 주지 않는다** — 앞 단계에서 꽂아 둔 그대로다. 점유표·구간·레일
        접촉은 똑같이 남긴다: 회색이어도 그림대로 꽂히는지는 verify() 가 본다.

        따라 그리기 층(`layer`)이면 번호로 모양을 정한다(`_layer_view`). 어느 모양이든
        점유표·구간·결선 순서표에는 남는다 — 번호와 뒤 배선 자리가 완성본과 같아야 한다.

        `marker_near` 는 엔진 고정 부품(전원선·LED 사슬·입력 점퍼)의 기본 자리다 — v2 는 그 자리가
        R11 에 걸리면 가까운 빈 자리로 비킨다(`_settle_marker`). `marker_at` 은 빌더가 고른 자리라
        그대로 찍는다.
        """
        if marker_near is not None and not self.spec.readability and marker_at is None:
            marker_at = marker_near
        key = (kind, self._endpoint(points[0]), self._endpoint(points[-1]))
        if self.ghost is not None and key in self.ghost['wires']:
            n = self.ghost['wires'][key]
            self._ghost_wire(points, n)
            self.ghost_drawn[key] = n
            return None
        kept = self.baseline is not None and key in self.baseline['wires']
        view = self._layer_view(len(self.steps) + 1) if self.numbered and not kept else 'shown'
        draw = self._hidden_draw if view == 'hidden' else self.draw
        color = KEEP if kept or view == 'faded' else WIRE[kind]
        draw.line(points, fill=color, width=width, joint='curve')
        for p in (points[0], points[-1]):
            draw.ellipse([p[0]-3, p[1]-3, p[0]+3, p[1]+3], fill=color)
        for p in (points[0], points[-1]):
            self.lead(p[0], p[1], f'{KIND_KR[kind]} 배선 · {desc}')
            self.touch_rail(kind, p[0])
        self._segments.append((kind, [tuple(p) for p in points], desc))
        self._register_pass(points)
        if not kept and kind in ('sig', 'mid'):
            self.new_signal.append(key)
        if self.spec.readability:
            # 자리는 보이든 말든 늘 정한다 — 같은 선 순서면 완성본·층 그림·단계 그림이 같은 자리다
            if marker_at is None and marker_near is not None:
                marker_at = self._settle_marker(*marker_near, own=len(self._segments) - 1)
            if marker_at is None:
                marker_at = self._auto_marker(len(self._segments) - 1)
                if marker_at is None:
                    print(f'[WARN] 번호 원 자동 자리 없음 — {desc}: 옛 자리(첫 구간 가운데)에 찍는다. '
                          'R11 에 걸리면 marker_at 을 직접 주거나 경로를 바꾼다', file=sys.stderr)
            if marker_at is not None:
                self._marker_slots.append((marker_at[0] - 8, marker_at[1] - 8,
                                           marker_at[0] + 8, marker_at[1] + 8))
        if kept:
            self.kept.append(desc)
            return None
        if not self.numbered:
            return None

        n = len(self.steps) + 1
        if view == 'shown':
            if marker_at is None:
                (x0, y0), (x1, y1) = points[0], points[1] if len(points) > 1 else points[0]
                marker_at = ((x0 + x1) // 2, (y0 + y1) // 2)
            self._marker(marker_at[0], marker_at[1], n, color)

        frm = frm or self.addr(*points[0])
        to = to or self.addr(*points[-1])
        self.steps.append({'n': n, 'kind': kind, 'frm': frm, 'to': to,
                           'desc': desc, 'count': count})
        return n

    def step_note(self, kind, frm, to, desc, count=1, marker_at=None, marker_near=None):
        """그림에 이미 그려진 것을 표에 한 줄로 묶는다.

        `marker_at` 을 주면 보드 위에도 번호 원을 찍는다. **부품을 꽂는
        단계에는 반드시 준다** — 안 주면 표에는 번호가 있는데 그림에는 없어서,
        따라 그리는 사람이 그 차례에서 그림을 뒤지다 막힌다. `marker_near` 는 `step_wire` 와 같다.
        """
        if marker_near is not None and marker_at is None:
            marker_at = (self._settle_marker(*marker_near) if self.spec.readability and not self._pull_parts
                         else marker_near)
        if self.spec.readability and marker_at is not None and not self._pull_parts:
            self._marker_slots.append((marker_at[0] - 8, marker_at[1] - 8,
                                       marker_at[0] + 8, marker_at[1] + 8))
        if self._keep_parts:
            self.kept.append(desc)      # 기준선 사슬의 부품 줄 — 번호 없이 회색
            return None
        if self._pull_parts:
            return None                 # 걷기 보드가 뽑는 사슬 — 새로 꽂는 것이 아니다
        if not self.numbered:
            return None
        n = len(self.steps) + 1
        if marker_at is not None and self._layer_view(n) == 'shown':
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
        if self._pull_parts:
            wire_col, body_col, bands = REMOVE, (240, 200, 200, 255), [REMOVE] * 4
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
        lead_col = (130, 130, 130, 255)
        if self._pull_parts:
            color_rgb, lead_col = REMOVE[:3], REMOVE
        ymid = (y_anode + y_cathode) // 2
        self.draw.line([(x, y_anode), (x, ymid - 8)], fill=lead_col, width=2)
        self.draw.line([(x, ymid + 8), (x, y_cathode)], fill=lead_col, width=2)
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
        # 걷기 보드가 사슬째 뽑는 사슬(`ghost['chains']`)은 LED·저항을 걷기 빨강으로 칠하고
        # 점선 상자로 두른다 — 번호는 GND 점퍼(유령선)가 받는다. 선만 빨갛고 부품이 회색이면
        # 그림이 "부품은 둔다" 로 읽힌다(2026-09-29 실험04 8걷기, 사용자)
        self._pull_parts = self.ghost is not None and key in self.ghost.get('chains', {})
        self._keep_parts = (self.baseline is not None and key in self.baseline['chains']
                            and not self._pull_parts)
        try:
            y_a, y_k, y_r = self.r_y(top_row), self.r_y(top_row + 1), self.r_y(top_row + 3)
            self.draw_led(x_led, y_a, y_k, color_rgb, tag)
            self.draw_resistor(x_res, y_k, y_r, label="330Ω")
            if self._pull_parts:
                x0, x1 = min(x_led, x_res) - 12, max(x_led, x_res) + 12
                self._dashed([(x0, y_a - 12), (x1, y_a - 12), (x1, y_r + 12), (x0, y_r + 12),
                              (x0, y_a - 12)], REMOVE, width=3, dash=7, gap=5,
                             draw=_ScaledDraw(self.ghost_layer))
                self.ghost_chains_drawn.add(key)
            self.led_chains.append({'tag': tag,
                                    'signal': self.sym(x, top_row),
                                    'anode': self.sym(x_led, top_row),
                                    'cathode': self.sym(x_led, top_row + 1),
                                    'res_top': self.sym(x_res, top_row + 1),
                                    'res_bottom': self.sym(x_res, top_row + 3)})
            self.step_note('sig', self.addr(x_led, y_a), self.addr(x_res, y_r),
                           f'{tag}: LED({self.addr(x_led, y_a)}→{self.addr(x_led, y_k)}) + '
                           f'330Ω({self.addr(x_res, y_k)}→{self.addr(x_res, y_r)}) 직렬 · {desc}',
                           marker_near=(x + marker_dx, y_k))
            x_gnd = self.nearest_gnd_rail(x_led, block)
            free = [x, x_led] + ([group[i + 3 * step]] if 0 <= i + 3 * step < len(group) else [])
            x_from = min(free, key=lambda h: abs(h - x_gnd))
            r_gnd = self.free_rail_row(top_row + 3, x_gnd)
            self.step_wire([(x_from, y_r), (x_gnd, self.r_y(r_gnd))],
                           'gnd', f'{tag} 저항 아래 -> GND',
                           width=2, marker_near=(x_from - 22, y_r + 2))
        finally:
            self._keep_parts = False
            self._pull_parts = False

    # ---------------- 칩 ----------------

    def _vtext(self, xy, text, fill, font):
        """세로쓰기. 과거 결선도가 칩 이름을 이렇게 적었다 — 몸통 안에 넣으면
        핀 번호를 d·g 열 홀 위에 얹지 않아도 된다."""
        real = font.real if isinstance(font, _ScaledFont) else font
        bbox = real.getbbox(text)
        pad = 2 * SCALE
        w, h = bbox[2] - bbox[0] + 2 * pad, bbox[3] - bbox[1] + 2 * pad
        tmp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((pad - bbox[0], pad - bbox[1]), text, fill=fill, font=real)
        rot = tmp.rotate(-90, expand=True)
        self.overlay.alpha_composite(rot, (int(xy[0] * SCALE - rot.width / 2),
                                           int(xy[1] * SCALE - rot.height / 2)))

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
        label_at = ((x1 + x2) / 2, (y_top + y_bot) / 2)
        self._vtext(label_at, name, text_fill, self.font_chip)
        # 세로로 돌린 이름 글자가 차지하는 상자(논리 좌표, `_vtext` 의 여백 2 포함) — R14
        lb = self.font_chip.getbbox(name)
        half_w, half_h = (lb[3] - lb[1]) / 2 + 2, (lb[2] - lb[0]) / 2 + 2
        label_box = (label_at[0] - half_w, label_at[1] - half_h,
                     label_at[0] + half_w, label_at[1] + half_h)

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
        self.chip_label_boxes.append((label_box, self.chips[-1]))
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

        v1 기준 — 이 템플릿의 레일쌍(좌 174/190, 중앙좌 468/484, 중앙우 542/558,
        우 836/852)은 각각 **별개 스트립**이다. 칩 7번 핀을 좌측 GND 레일에
        내리고 미사용 입력을 중앙 GND 레일에 내리면 두 레일이 이어져 있지
        않아 미사용 입력이 뜬다. 그 점퍼를 명시적으로 그린다.
        v2 는 가운데 레일이 하나라 좌 바깥 ↔ 가운데 두 가닥이면 된다. 같은 열을 이으면 오류다.
        """
        if x_a == x_b:
            raise ValueError(f'같은 레일 열을 잇는 브리지다(x={x_a}, {self._addr_map.get(x_a)}) — '
                             '두 블록이 이름만 다르게 부르는 한 레일이다. 브리지할 것이 없다')
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
                       marker_near=((c['g'] + x_vcc) // 2, self.r_y(start_row) - 11))
        r7 = self.free_rail_row(start_row + 6, x_gnd)
        self.step_wire([(c[gnd_col], self.r_y(start_row + 6)), (x_gnd, self.r_y(r7))],
                       'gnd', 'pin 7 -> GND 레일', marker_at=gnd_marker_at,
                       marker_near=((c['d'] + x_gnd) // 2, self.r_y(start_row + 6) - 11))

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
        # 따라 그리기 층 — 가닥이 여럿이어도 번호는 뒤의 `step_note` 하나라 그 번호로 정한다
        view = self._layer_view(len(self.steps) + 1) if self.numbered else 'shown'
        draw = self._hidden_draw if view == 'hidden' else self.draw
        for row, x_pin, p in (placed[i] for i in order):
            pick = self.nearest_vcc_rail if rail == 'vcc' else self.nearest_gnd_rail
            x_rail = pick(x_pin, block)
            r_rail = self.free_rail_row(row, x_rail)
            key = (rail, self._endpoint((x_pin, self.r_y(row))),
                   self._endpoint((x_rail, self.r_y(r_rail))))
            kept = self.baseline is not None and key in self.baseline['wires']
            kept_lines += kept
            col = KEEP if kept or view == 'faded' else WIRE[rail]
            draw.line([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], fill=col, width=2)
            self._segments.append((rail, [(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))],
                                   f'{chip} pin {p} 미사용 입력'))
            self._register_pass([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))])
            draw.ellipse([x_pin-3, self.r_y(row)-3, x_pin+3, self.r_y(row)+3], fill=col)
            draw.ellipse([x_rail-3, self.r_y(r_rail)-3, x_rail+3, self.r_y(r_rail)+3], fill=col)
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

    # ---------------- 내보내기 ----------------

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
        color = self._jack_at(x, y)
        if color is not None:
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

    # ---------------- 읽기 규칙 R11~R14 (spec.readability, v2) ----------------
    #
    # 2026-10-03 실험04 v2 시험판(`docs/plans/2026-10-03-실험04-v2-시험판-결과.md`)은 R1~R10 을
    # 다 통과했는데 **따라 그릴 수 없었다**(사용자). 번호 원이 끝점 홀을 덮었고 — 기본 자리가
    # 첫 구간 가운데인데 첫 구간이 반 행(9.5px) 토막이었다 — 검정 선이 검정 홀 열 위를 지나가
    # 꽂힌 것인지 지나가는 것인지 안 보였다. 칩 넷이 한 블록에 몰리는 v2 에서 처음 드러났다.
    # v1 승인본(실험01~04)은 소급하지 않는다.

    def _chip_bodies(self):
        """칩마다 (몸통 상자, 칩 기둥 가운데 x, 칩) — 몸통은 e·f 핀 열 안쪽, pin 1 행 위 ~ pin 7 행 아래."""
        out = []
        for ch in self.chips:
            c = self.cols[ch['block']]
            box = (c['chip_x1'] - 1, self.r_y(ch['pin1_row']) - 10,
                   c['chip_x2'] + 1, self.r_y(ch['pin1_row'] + 6) + 10)
            out.append((box, (c['e'] + c['f']) / 2, ch))
        return out

    @staticmethod
    def _seg_in_box(a, b, box):
        """구간 ab 가 상자 **안쪽**을 지나가는가 — 2px 간격으로 훑는다(대각선도 잡는다)."""
        x0, y0, x1, y1 = box
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / 2) + 1
        return any(x0 < a[0] + (b[0] - a[0]) * t / n < x1 and y0 < a[1] + (b[1] - a[1]) * t / n < y1
                   for t in range(n + 1))

    def _marker_clear(self, x, y, own=None, pad=2):
        """(x, y) 에 번호 원을 찍으면 아무것도 안 가리는가 — 꽂힌 홀, 다른 번호 원, 칩 몸통,
        `own` 번째가 아닌 배선."""
        box = (x - 8 - pad, y - 8 - pad, x + 8 + pad, y + 8 + pad)
        if any(box[0] <= hx <= box[2] and box[1] <= self.r_y(hr) <= box[3] for hx, hr in self._leads):
            return False
        # 그려진 원이 아니라 정해진 **자리**를 피한다 — 층 그림에서 흐리게 둔 앞 번호도 완성본에선 있다
        if any(not (box[2] <= m[0] or m[2] <= box[0] or box[3] <= m[1] or m[3] <= box[1])
               for m in self._marker_slots + self.marker_boxes):
            return False
        if any(not (box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1])
               for b, _cx, _ch in self._chip_bodies()):
            return False
        return not any(i != own and self._seg_in_box(a, b, box)
                       for i, (_k, pts, _d) in enumerate(self._segments)
                       for a, b in zip(pts, pts[1:]))

    def _auto_marker(self, idx):
        """`_segments[idx]` 의 번호 원 자리 — R11 을 지키는 첫 점. 가로 구간을 먼저, 그다음 긴
        구간 순으로 가운데부터 4px 씩 밖으로 훑는다. 세로 차선 한복판에 앉은 원은 이웃 차선을
        막는다(시험판 MUX U1 pin 8 임시선). 자리가 없으면 None — 호출자가 옛 자리에 찍고
        verify() 의 R11 이 멈춘다."""
        pts = self._segments[idx][1]
        segs = sorted(zip(pts, pts[1:]), key=lambda s: (abs(s[0][1] - s[1][1]) > .5,
                                                        -(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))))
        for a, b in segs:
            length = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5
            if length < 24:
                continue
            mid = length / 2
            for off in range(0, int(mid - 12) + 1, 4):     # +1: 길이 24~25 구간도 가운데 한 점은 본다
                for t in sorted({mid - off, mid + off}):
                    x = round(a[0] + (b[0] - a[0]) * t / length)
                    y = round(a[1] + (b[1] - a[1]) * t / length)
                    if self._marker_clear(x, y, own=idx):
                        return (x, y)
        return None

    # 엔진 고정 부품 번호 원이 비킬 때 훑는 자리 — 4px 격자, 32px 안, 가까운 순(동률은 가로 먼저)
    _SETTLE_OFFSETS = sorted(((dx, dy) for dx in range(-32, 33, 4) for dy in range(-32, 33, 4)
                              if (dx, dy) != (0, 0)),
                             key=lambda d: (d[0] ** 2 + d[1] ** 2, abs(d[1]), d[0], d[1]))

    def _marker_fits(self, x, y, own=None):
        """(x, y) 번호 원이 `marker_problems()` 에 안 걸리는가 — 꽂힌 홀, 다른 번호 원(자리), 칩 몸통,
        배선 둘 이상(자기 배선 포함), 그리고 이미 그린 신호 이름 배지."""
        box = (x - 8, y - 8, x + 8, y + 8)
        if any(box[0] - 1 <= hx <= box[2] + 1 and box[1] - 1 <= self.r_y(hr) <= box[3] + 1
               for hx, hr in self._leads):
            return False
        if any(not (box[2] <= m[0] or m[2] <= box[0] or box[3] <= m[1] or m[3] <= box[1])
               for m in self._marker_slots + self.marker_boxes):
            return False
        if any(not (box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1])
               for b, _cx, _ch in self._chip_bodies()):
            return False
        if any(_boxes_touch(box, b) for _n, b, _seg in self.tag_boxes):
            return False
        under = sum(1 for _k, pts, _d in self._segments
                    if any(self._seg_in_box(a, b, box) for a, b in zip(pts, pts[1:])))
        return under <= 1

    def _settle_marker(self, x, y, own=None):
        """엔진 고정 부품의 번호 원 자리 — 기본 자리 (x, y) 가 R11 을 지키면 그대로(지금 그림이 안
        바뀐다), 아니면 가까운 순으로 아무것도 안 가리는 자리. 없으면 기본 자리 — verify() 가 멈춘다.
        2026-10-05 배치 탐색: 입력 행이 LED 행 바로 아래면 입력 점퍼 원이 LED 사슬 원과 겹쳤다."""
        if self._marker_fits(x, y, own):
            return (x, y)
        for dx, dy in self._SETTLE_OFFSETS:
            cx, cy = x + dx, y + dy
            if self._marker_clear(cx, cy, own=own) and self._marker_fits(cx, cy, own):
                return (cx, cy)
        return (x, y)

    def marker_problems(self):
        """R11 — 번호 원이 가리는 것: 꽂힌 홀(끝점·부품 다리), 다른 번호 원, 칩 몸통(칩 이름·핀
        번호), 그리고 **둘 이상의** 배선(원은 자기 배선 위에 앉으니 둘째부터는 남의 것이다)."""
        out = []
        boxes = self.marker_boxes
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            at = f'번호 원({x0 + 8},{y0 + 8})'
            for (hx, hr), what in self._leads.items():
                if x0 - 1 <= hx <= x1 + 1 and y0 - 1 <= self.r_y(hr) <= y1 + 1:
                    out.append(f'{at} 이 꽂힌 홀 {self.addr(hx, self.r_y(hr))} 을 가린다')
            for b in boxes[i + 1:]:
                if not (x1 <= b[0] or b[2] <= x0 or y1 <= b[1] or b[3] <= y0):
                    out.append(f'{at} 과 번호 원({b[0] + 8},{b[1] + 8}) 이 겹친다')
            for b, _cx, ch in self._chip_bodies():
                if not (x1 <= b[0] or b[2] <= x0 or y1 <= b[1] or b[3] <= y0):
                    out.append(f"{at} 이 칩 {ch['label']}({ch['pin1_row']}행) 몸통을 가린다")
            under = [d for _k, pts, d in self._segments
                     if any(self._seg_in_box(a, b, (x0, y0, x1, y1)) for a, b in zip(pts, pts[1:]))]
            if len(under) > 1:
                out.append(f'{at} 아래 배선 {len(under)}가닥: {", ".join(under)}')
        return out

    def wires_over_holes(self):
        """R12 — 신호선(`sig`·`mid`)이 끝점 말고 지나가는 홀. 검정 선이 검정 홀 위를 지나가면 거기
        꽂힌 것인지 지나가는 것인지 안 보인다. 전원·GND·레일 브리지·잭 선과 입력 점퍼(레일에서
        같은 행으로 곧게 들어온다)는 안 본다."""
        input_segs = {inp['seg'] for inp in self.inputs}
        out = []
        for i, (kind, pts, desc) in enumerate(self._segments):
            if kind not in ('sig', 'mid') or i in input_segs:
                continue
            ends = {self.hole_at(*pts[0]), self.hole_at(*pts[-1])}
            seen = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / 2))
                for t in range(n + 1):
                    h = self.hole_at(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n)
                    if h is not None and h not in ends and h not in seen:
                        seen.append(h)
            if seen:
                out.append(f"{desc}: {', '.join(self.addr(x, self.r_y(r)) for x, r in seen[:4])}"
                           + (f' 외 {len(seen) - 4}' if len(seen) > 4 else ''))
        return out

    def needless_body_crossings(self):
        """R13 — 양 끝이 칩 기둥의 같은 쪽인데 그 칩 몸통을 가로지르는 신호선. 칩 이름·핀 번호를
        덮고 쓸데없이 돌아간다. 양 끝이 다른 쪽(칩 안 a↔f 이어 가기, a쪽 출력 → LED)이면 한 번은
        건너야 하므로 안 본다. 가로로 건너는 것만이 아니라 몸통 상자에 **들어가기만** 해도 본다 —
        e·f 사이 골을 세로로 타는 선은 홀이 없어 R12 가 못 보고 칩 이름·핀 번호를 길게 덮는다
        (2026-10-04 검토)."""
        out = []
        for kind, pts, desc in self._segments:
            if kind not in ('sig', 'mid'):
                continue
            for box, cx, ch in self._chip_bodies():
                if (pts[0][0] < cx) != (pts[-1][0] < cx):
                    continue
                if any(self._seg_in_box(a, b, box) for a, b in zip(pts, pts[1:])):
                    out.append(f"{desc} — 칩 {ch['label']}({ch['pin1_row']}행)")
        return out

    def wires_over_chip_labels(self):
        """R14 — 칩 이름 글자 위를 지나는 배선. R13 이 허용한 칩 안 a↔f 이어 가기도 이름
        한복판을 건너면 '7⁴HC20' 처럼 읽혀 어느 칩인지 안 보인다(2026-10-04 실험04 v2 시험판
        검토). 이름은 몸통 가운데(pin 4 행 둘레)에 세로로 적히므로 이어 가기는 그 위아래 반 행
        — pin 1~3 이나 pin 5~7 사이 — 으로 건넌다. 전원선도 본다 — 가리는 것은 색과 무관하다."""
        out = []
        for _kind, pts, desc in self._segments:
            for box, ch in self.chip_label_boxes:
                if any(self._seg_in_box(a, b, box) for a, b in zip(pts, pts[1:])):
                    out.append(f"{desc} — 칩 {ch['label']}({ch['pin1_row']}행)")
        return out

    def _zone(self, end, shared):
        """끝점이 어느 블록 편인가 — 단자대·바깥 레일은 그 블록, 두 블록이 같이 쓰는 레일
        (`shared`, v2 가운데)과 잭·여백은 None."""
        if end[0] != 'hole' or end[1] is None:
            return None
        block, col, _row = end[1]
        return None if self.cols[block][col] in shared else block

    def block_crossings(self):
        """R10 의 지표 — 양 끝이 서로 다른 블록인 배선. 레일↔레일 전원 브리지는 안 든다(설계 §5)
        — 가운데 레일은 어느 블록도 아니고, 좌 바깥 ↔ 우 바깥 브리지는 양 끝이 레일이라 뺀다.
        `wiring()` 에 넣지 않는다 — 도장."""
        shared, out = self._shared_xs(), []
        for _kind, pts, desc in self._segments:
            a, b = self._endpoint(pts[0]), self._endpoint(pts[-1])
            za, zb = self._zone(a, shared), self._zone(b, shared)
            if {za, zb} != {'left', 'right'}:
                continue
            if self._strip(a[1])[0] == 'rail' and self._strip(b[1])[0] == 'rail':
                continue
            out.append({'ends': {za: a[1], zb: b[1]}, 'desc': desc,
                        'frm': self.addr(*pts[0]), 'to': self.addr(*pts[-1])})
        return out

    def _block_role_violations(self):
        """R10 — LED 전용 블록으로 건너는 선은 칩 핀 스트립 → LED 사슬 신호 스트립뿐이고, 건너는
        선끼리 위아래 순서가 LED 순서와 같다(설계 §5).

        핀 방향표가 없어 '출력' 인지는 보지 않는다(2026-10-03 결정) — LED 에 무엇이 물렸는지는
        R5 와 netlist 대조가 본다. `spec.led_only_blocks` 가 비면(v1) 아무것도 안 낸다.
        """
        led_blocks = self.spec.led_only_blocks
        if not led_blocks:
            return []
        chip_strips = {self._strip(sym) for ch in self.chips
                       if ch['block'] in self.spec.chip_blocks for sym in ch['pins'].values()}
        led_strips = {self._strip(ch['signal']) for ch in self.led_chains
                      if ch['signal'] is not None and ch['signal'][0] in led_blocks}
        bad, ok = [], []
        for w in self.block_crossings():
            led_end = next((s for z, s in w['ends'].items() if z in led_blocks), None)
            chip_end = next((s for z, s in w['ends'].items() if z not in led_blocks), None)
            if (led_end is None or chip_end is None
                    or self._strip(chip_end) not in chip_strips
                    or self._strip(led_end) not in led_strips):
                bad.append(f"R10 블록 건너기 위반: {w['frm']} → {w['to']} · {w['desc']} — "
                           "블록을 건너는 선은 칩 핀 스트립에서 LED 사슬 스트립으로만 간다")
            else:
                ok.append((led_end[2], chip_end[2], w))
        ok.sort(key=lambda t: t[0])
        for (_l1, c1, w1), (_l2, c2, w2) in zip(ok, ok[1:]):
            if c1 > c2:
                bad.append(f"R10 건너는 선 엇갈림: {w1['frm']} → {w1['to']} / "
                           f"{w2['frm']} → {w2['to']} — 칩 쪽 행 순서를 LED 순서와 맞춘다")
        return bad

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
                color = self._jack_at(*p)
                if color is not None:
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
        R9  칩은 판형이 허용한 블록에만 둔다(`spec.chip_blocks`) — v2 는 좌 블록만.
        R10 LED 전용 블록(`spec.led_only_blocks`, v2 는 우)으로 건너는 선은 칩 핀 스트립 →
            LED 사슬 신호 스트립뿐이고, 건너는 선끼리 위아래 순서가 LED 순서와 같다. 핀
            방향표가 없어 '출력' 인지는 안 본다. v1 은 R9 가 두 블록을 다 허용하고 R10 이
            비어 있어 실험01~04 가 그대로다.
        R11 번호 원이 꽂힌 홀·다른 번호 원·칩 몸통·남의 배선을 가리지 않는다.
        R12 신호선은 끝점 말고 홀 위를 지나지 않는다 — 닿은 홀은 전부 꽂는 홀이다.
        R13 양 끝이 칩의 같은 쪽인 신호선은 그 칩 몸통을 건너지 않는다.
        R14 어떤 배선도 칩 이름 글자 위를 지나지 않는다 — 칩 안 이어 가기도 이름 위아래로 건넌다.
            R11~R14 는 `spec.readability`(v2)만 돈다 — 2026-10-03 실험04 v2 시험판.
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
        # R9·R10. 블록 역할 — 판형이 정한다(`spec.chip_blocks`·`led_only_blocks`). v2 는 칩을
        # 좌 블록에만 두고 우 블록에는 LED 사슬만 둔다(설계 §5)
        allowed = '·'.join('좌' if b == 'left' else '우' for b in self.spec.chip_blocks)
        for ch in self.chips:
            if ch['block'] not in self.spec.chip_blocks:
                blk = '좌' if ch['block'] == 'left' else '우'
                bad.append(f"R9 칩 블록 위반: {ch['label']}({blk} {ch['pin1_row']}행) — "
                           f"{self.board} 판형은 칩을 {allowed} 블록에만 둔다")
        bad += self._block_role_violations()
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

        # R11~R14. 읽기 규칙 — 꽂을 수 있고 회로도 맞는데 **따라 그릴 수 없는** 그림
        # (2026-10-03 실험04 v2 시험판, 사용자). 기하·넷·레일보다 뒤에 본다 — 그것들이
        # 틀린 그림의 읽기는 따질 필요가 없다. v2(`spec.readability`)만
        if self.spec.readability:
            rd = [f'R11 번호 원 가림: {p}' for p in self.marker_problems()]
            rd += [f'R12 신호선이 홀 위를 지난다: {p}' for p in self.wires_over_holes()]
            rd += [f'R13 칩 몸통을 쓸데없이 건넌다: {p}' for p in self.needless_body_crossings()]
            rd += [f'R14 배선이 칩 이름을 가린다: {p}' for p in self.wires_over_chip_labels()]
            if rd:
                raise AssertionError('따라 그릴 수 없다:\n  ' + '\n  '.join(rd))

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
        if self.board != 'v1':
            # v2 부터만 든다 — v1 도장은 그대로이고, 결선이 같아도 판형을 바꾸면 도장이 바뀐다
            out['board'] = self.board
        if self.layer is not None:
            # 층 보드에서만 든다 — 완성본 도장은 그대로다
            out['layer'] = list(self.layer)
        if self.ghost is not None:
            # 걷기 보드에서만 든다 — 다른 보드의 도장은 그대로라 재생성 범위가 안 번진다
            out['ghost'] = [(r['n'], r['addr']) for r in self.removals()]
            if self.ghost.get('chains'):
                # 사슬째 뽑는 걷기 보드에서만 든다 — 옛 걷기 보드 도장은 그대로다
                out['ghost_chains'] = self._ghost_chain_lines()
        return out

    def _ghost_chain_lines(self):
        """걷기 보드가 사슬째 뽑는 LED 사슬 — 번호 없는 한 줄씩. 그리기 순서대로."""
        chains = self.ghost.get('chains', {}) if self.ghost is not None else {}
        return [f'LED {chains[k]} 사슬 ({self._sym_addr(("hole", k[0]))}~'
                f'{self._sym_addr(("hole", k[3]))}) 의 LED·330Ω 을 뽑는다 (빨간 점선 상자)'
                for k in chains]

    def sidecar(self):
        """그림 옆에 실을 글자 — 체크리스트가 읽는다. PNG 에는 보드만 있다(2026-09-28).

        걷기 번호는 걷기 보드에서만 준다 — 그 보드만 그림에 빨간 번호 원이 있다. 칩·사슬
        걷기(`removed()` 의 배선 뒤쪽)는 번호가 없다.
        """
        ghost = self.ghost is not None
        wires = self.removals()
        removals = [{'n': r['n'] if ghost else None, 'text': f"{r['addr']} · {r['desc']}"}
                    for r in wires]
        removals += [{'n': None, 'text': g} for g in self.removed()[len(wires):]]
        removals += [{'n': None, 'text': g} for g in self._ghost_chain_lines()]
        side = {
            'schema': SIDECAR_SCHEMA,
            'title': self.title,
            'subtitle': self.subtitle,
            'kept': len(self.kept) if self.baseline is not None else None,
            'steps': [{'n': s['n'], 'kind': s['kind'], 'from': s['frm'], 'to': s['to'],
                       'desc': s['desc'], 'count': s['count']} for s in self.steps],
            'removals': removals,
            'probes': [{'n': p['n'], 'label': p['label'], 'at': p['at'], 'desc': p['desc']}
                       for p in self.probes],
        }
        if self.board != 'v1':
            # v2 부터만 든다. 커밋된 v1 사이드카는 바이트로 대조된다(`CommittedPngs`) — 없으면 v1 이다
            side['board'] = self.board
        return side

    def stamp(self):
        # v2 = 보드만 담은 PNG(2026-09-28). 접두어가 바뀌어 옛 PNG 는 전부 stale 로 잡힌다
        blob = json.dumps(self.content(), ensure_ascii=False, sort_keys=True, default=_jsonable)
        return 'v2:' + hashlib.sha256(blob.encode('utf-8')).hexdigest()

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
            undrawn = [self.ghost['chains'][k] for k in self.ghost.get('chains', {})
                       if k not in self.ghost_chains_drawn]
            assert not undrawn, (
                f'걷기 대상 LED 사슬을 앞 빌더가 그리지 않았다: {undrawn} — '
                'removal_board 의 prev 빌더·stage 가 기준선을 만든 것과 같아야 한다')
        # 유령선은 템플릿과 overlay 사이 — 회색 선·칩·새 선이 유령선을 덮는다
        final_im = Image.alpha_composite(Image.alpha_composite(self.im, self.ghost_layer),
                                         self.overlay)
        board_h = self.r_y(max_row) + 20
        out = final_im.crop((0, 0, self.spec.size[0] * SCALE, board_h * SCALE)).convert('RGB')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        info = PngInfo()
        info.add_text(STAMP_KEY, self.stamp())
        out.save(output_path, pnginfo=info)
        with open(os.path.splitext(output_path)[0] + '.json', 'w', encoding='utf-8') as f:
            json.dump(self.sidecar(), f, ensure_ascii=False, indent=1)
            f.write('\n')
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
    """보드 **밖** 꼬리표 — 꽂을 자리(`입력 A → b7`). 신호 이름은 `signal_tag()` 가 보드 안에 둔다.

    앞 꼬리표와 겹치면 겹치지 않을 때까지 아래로 내린다 — 같은 행에 입력이 둘이면(실험04
    C2 의 S1·D, 31행) 뒤 꼬리표가 앞 것을 정확히 덮어 한 입력의 자리가 사라졌다."""
    font, pad = bb.font_kr_sm, 2

    def box(y_):
        b = bb.draw.textbbox((x, y_), text, font=font)
        return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)

    def hits(b):
        return any(not (b[2] <= o[0] or o[2] <= b[0] or b[3] <= o[1] or o[3] <= b[1])
                   for _, o in bb.margin_tag_boxes)

    while hits(box(y)):
        y += 1
    bb.draw_badge(x, y, text, (255, 255, 255, 235), col, font=font, pad=pad)
    bb.margin_tag_boxes.append((text, box(y)))


def _input_jumper(bb, c, row, name, target, marker=None, col=None, side='a'):
    """입력 한 줄: **그쪽 GND 레일 홀 → 같은 행 `col` 열**. GND(=0) 자리를 그린 것이다.

    `side` 는 입력이 들어가는 핀이 칩의 어느 쪽인가다 — `'a'`(핀 1~7, a~e 쪽) 또는
    `'f'`(핀 8~14, f~j 쪽). 레일은 그쪽에 붙은 GND 다: 좌 블록은 a 쪽이 바깥 174, f 쪽이
    중앙 468 이고 우 블록은 뒤집혀 a 쪽이 중앙 542, f 쪽이 바깥 836 이다(v1 기준. v2 는 가운데 레일이 하나라 좌 f 쪽과 우 a 쪽이 같은 레일이다). 열 기본값은
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
    # 신호 이름 배지와 번호 원의 기본 자리 — 레일 바깥 여백. 좌 바깥 레일은 보드 좌 테두리~레일
    # 사이, 우 바깥 레일은 VCC 레일~보드 우 테두리 사이, 가운데 레일은 판형이 정한
    # `spec.mid_badge_x`(v1: 좌 중앙 VCC 484 ~ 우 중앙 GND 542 의 가운데, v2: 가운데 VCC ~ 우 a 열의
    # 가운데)다. 번호 원은 좌·우 바깥이면 보드 밖 같은 행, 가운데면 배지 위 18px 다 — 여백이
    # 52~58px 라 나란히 못 놓는다.
    s = bb.spec
    if x_rail == bb.cols['left']['gnd']:
        badge_x, default_marker = (s.board_left + x_rail) / 2, (130, 0)
    elif x_rail == bb.cols['right']['gnd']:
        badge_x, default_marker = (bb.cols['right']['vcc'] + s.board_right) / 2, (s.board_right + 24, 0)
    else:
        # 가운데 레일(v1 은 좌 중앙 468·우 중앙 542 둘, v2 는 하나)이 이 자리를 같이 쓴다 — 같은
        # 행에 입력 둘을 넣으면 배지와 번호 원이 서로 위에 겹친다(가운데 여백은 한 번에 입력 한
        # 행만 받는다). 배지 겹침은 가독성 테스트가 잡는다.
        badge_x = s.mid_badge_x
        default_marker = (badge_x, -18)
    mx, dy = marker or default_marker
    pin = {'marker_at': (mx, y_row + dy)} if marker else {'marker_near': (mx, y_row + dy)}
    p0, p1 = (x_rail, y_rail), (c[col], y_row)
    # 걷기 보드(`removal_board`)가 이 점퍼를 걷는 장이면 `step_wire` 는 유령선만 그리고
    # 곧장 돌아온다 — 점유표도 구간도 레일 접촉도 안 남긴다. 꽂혀 있지 않은 선이다.
    # `step_wire` 와 **같은 식**으로 판정한다(회색 유지선·번호 끔도 None 을 돌려주니
    # 반환값으로는 못 가른다).
    ghosted = bb.ghost is not None and (
        'sig', bb._endpoint(p0), bb._endpoint(p1)) in bb.ghost['wires']
    bb.step_wire([p0, p1], 'sig',
                 f'입력 {name} -> {target} · 1 이면 레일 쪽 끝을 +5V 레일로 옮겨요', **pin)
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
    _tag(bb, 12, y_row - 8, f"입력 {name} → {'우 ' if block == 'right' else ''}{col}{row}",
         col=INPUT)
    # 신호 이름은 보드 안, 레일 쪽 끝 옆. 0/1 을 바꿀 때 옮겨 꽂는 바로 그 끝이다
    bb.signal_tag(name, badge_x, y_rail, col=INPUT, seg=len(bb._segments) - 1,
                  arrow='right' if c[col] > x_rail else 'left')


# ---------------------------------------------------------------------------
# 배선기 (v2) — 배선표(어느 핀을 어느 핀에)만 받아 경로와 번호 원 자리를 고른다.
#
# 2026-10-03 실험04 v2 시험판(`tests/fixtures/board_v2_e4/배치.py`)에서 태어나 2026-10-04 엔진으로
# 올라왔다(`docs/plans/2026-10-04-v2-배선기-밀도-설계.md`). 칩 넷이 좌 블록 한 줄에 서면 a~d / g~j
# 열이 끝점으로 차서 손좌표로는 R3·R4 가 쏟아진다. 가로는 반 행, 세로는 홀 열 사이나 여백 차선을 탄다.
# 차선 x 값(212~260, 542~660)은 v2 판형 기하에 맞춘 것이라 v1 에서는 안 부른다.


def _dip_pin_row(k, pin):
    """칩 pin 1 행 `k` 에서 DIP-14 핀 `pin` 이 앉는 행."""
    return k + pin - 1 if pin <= 7 else k + 14 - pin


def _dip_side(pin):
    return 'a' if pin <= 7 else 'f'


# 밀도 가중치 λ — 비용 = 길이 + 40·꺾임 + 400·몸통횡단 + λ·밀도증분(px). 0 이면 밀도를 안 본다.
# 값은 `python -m scripts.lab.route_sweep` 로 정한다(설계 #11: 길이 +15% 안에서 밀도 최소).
# 2026-10-04 스윕: MUX 길이 348→355칸·밀도 26.4→20.6, DMUX 303→304·14.3→6.3. λ 1·2 는 MUX 밀도가
# 다시 늘고(먼저 깐 선이 뒤 선을 모른다) λ 4·8 은 MUX 가 막혔다.
DENSITY_WEIGHT = 0.5
_RERANK_TOP = 400   # 정적 순위 앞 몇 개만 밀도로 다시 매기나 — 나머지는 정적 순서 그대로


_STRIP_COLS = {'a': 'abcd', 'f': 'ghij'}


def _end_holes(bb, chips, end):
    """배선 끝 하나가 꽂힐 수 있는 홀 후보 [(x, y)]. `end` 는 ('U5', 13) 또는 ('LED', top_row)."""
    L, R = bb.cols['left'], bb.cols['right']
    if end[0] == 'LED':
        return [(R['a'], bb.r_y(end[1]))]
    k, pin = chips[end[0]], end[1]
    row = _dip_pin_row(k, pin)
    return [(L[c], bb.r_y(row)) for c in _STRIP_COLS[_dip_side(pin)]
            if (L[c], row) not in bb._leads and (L[c], row) not in bb._passed]


def _lanes(bb, led):
    """세로선이 달릴 x 후보. 홀 열 자체와 홀 열 사이(±12), 좌 여백·가운데 여백 차선.
    칩 몸통(e~f 사이)은 뺀다 — 세로선이 칩 위를 덮는다. LED 로 가는 선은 가운데 여백만 쓴다."""
    L = bb.cols['left']
    mid = [x for x in range(542, 660, 6) if min(abs(x - L['mid_gnd']), abs(x - L['mid_vcc'])) > 4]
    xs = [L[c] for c in 'abcdghij'] + [L[c] + 12 for c in 'abcghi'] + [L['j'] + 12]
    xs += [212, 224, 236, 248, 260]
    if led:
        return sorted(set(mid + [L[c] for c in 'ghij'] + [L[c] + 12 for c in 'ghi']))
    return sorted(set(xs + [x for x in mid if x < L['mid_gnd']]))


def _axis(a, b):
    if abs(a[0] - b[0]) < .5:
        return 'v'
    if abs(a[1] - b[1]) < .5:
        return 'h'
    return None


def _on_seg(p, a, b, margin=6):
    """엔진 `_endpoints_under_wires` 와 같은 식 — p 가 구간 ab 의 **중간** 위에 있는가."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = (dx * dx + dy * dy) ** .5
    if length < 1:
        return False
    along = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length
    if along <= margin or length - along <= margin:
        return False
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / length < 1.5


def _clean(path):
    out = []
    for p in path:
        if out and abs(out[-1][0] - p[0]) < .5 and abs(out[-1][1] - p[1]) < .5:
            continue
        if len(out) >= 2 and _axis(out[-2], out[-1]) and _axis(out[-2], out[-1]) == _axis(out[-1], p):
            out[-1] = p
            continue
        out.append(p)
    return out


def _holes_passed(a, b, xs, xset, pitch, row0):
    """축 구간 ab 가 덮는 홀 수(양 끝 제외) — 홀 열 위 세로선, 행 위 가로선. 덮인 홀은
    뒤 배선의 끝점이 될 수 없어서(R3) 길게 덮을수록 뒤 배선이 갈 데가 없어진다."""
    if abs(a[0] - b[0]) < .5:
        if round(a[0]) not in xset:
            return 0
        lo, hi = sorted((a[1], b[1]))
        return max(0, math.ceil((hi - 1 - row0) / pitch) - math.floor((lo + 1 - row0) / pitch) - 1)
    f = (a[1] - row0) / pitch % 1
    if .05 < f < .95:
        return 0
    lo, hi = sorted((a[0], b[0]))
    return bisect.bisect_left(xs, hi - 1) - bisect.bisect_right(xs, lo + 1)


def _coster(bb):
    xs = sorted(round(x) for x in bb._addr_map)
    xset, pitch, row0 = set(xs), bb.spec.row_pitch, bb.spec.row0
    L = bb.cols['left']
    bodies = [(bb.r_y(ch['pin1_row']) - 10, bb.r_y(ch['pin1_row'] + 6) + 10) for ch in bb.chips]

    def body_crossings(path):
        """칩 몸통(e~f 사이)을 가로지르는 가로 구간 수 — 칩 이름·핀 번호를 덮는다. 칩 안
        a↔f 이어 가기는 한 번은 건너야 하지만 칩 사이 선이 몸통을 넘을 이유는 없다."""
        n = 0
        for a, b in zip(path, path[1:]):
            if abs(a[1] - b[1]) < .5 and min(a[0], b[0]) < L['e'] and max(a[0], b[0]) > L['f']:
                n += sum(1 for y0, y1 in bodies if y0 <= a[1] <= y1)
        return n

    def cost(path):
        """(덮는 홀 수, 길이 + 꺾임 벌점). 덮는 홀이 하나라도 있으면 `_route` 가 버린다 — 검정
        선이 검정 홀 위를 지나면 꽂힌 것인지 지나가는 것인지 안 보인다(2026-10-03 사용자)."""
        over = sum(_holes_passed(a, b, xs, xset, pitch, row0) for a, b in zip(path, path[1:]))
        c = 40 * (len(path) - 2) + 400 * body_crossings(path)
        for a, b in zip(path, path[1:]):
            c += abs(a[0] - b[0]) + abs(a[1] - b[1])
        return over, c
    return cost


def _valid(bb, path, others_pts, segs):
    # R6 — 두 점이 다 같은 스트립의 홀이면 그 구간은 전기적으로 없는 것과 같다
    for a, b in zip(path, path[1:]):
        sa = bb._strip(bb.sym(a[0], bb._row_of(a[1]))) if bb.hole_at(*a) else None
        sb = bb._strip(bb.sym(b[0], bb._row_of(b[1]))) if bb.hole_at(*b) else None
        if sa is not None and sa == sb:
            return False
        if _axis(a, b) is None:
            return False
    # 칩 이름 글자 위를 지나지 않는다(엔진 R14) — 이어 가기는 이름 위아래 반 행으로 건넌다
    for box, _ch in bb.chip_label_boxes:
        if any(bb._seg_in_box(a, b, box) for a, b in zip(path, path[1:])):
            return False
    # 꺾임점이 리드가 있는 홀 위에 앉으면 안 된다
    for c in path[1:-1]:
        h = bb.hole_at(*c)
        if h is not None and h in bb._leads:
            return False
    # 새 선의 끝점이 기존 선 아래
    for q in (path[0], path[-1]):
        for _k, pts in segs:
            for a, b in zip(pts, pts[1:]):
                if _on_seg(q, a, b):
                    return False
    # 기존 끝점·부품 다리가 새 선 아래
    for q in others_pts:
        for a, b in zip(path, path[1:]):
            if _on_seg(q, a, b):
                return False
    # 이미 찍힌 번호 원 아래로 지나가거나 그 아래 홀에 꽂지 않는다 — 원이 선·끝점을 가린다
    for m in bb.marker_boxes:
        x0, y0, x1, y1 = m[0] - 1, m[1] - 1, m[2] + 1, m[3] + 1
        for a, b in zip(path, path[1:]):
            if (min(a[0], b[0]) < x1 and max(a[0], b[0]) > x0
                    and min(a[1], b[1]) < y1 and max(a[1], b[1]) > y0):
                return False
    # 꺾임점이 남의 선에 닿거나 남의 꺾임점이 새 선에 닿지 않는다 — 끝과 끝이 맞닿은 두 선은
    # 한 가닥으로 읽힌다(2026-10-04, R4 는 2px 이하 겹침을 봐줘서 못 본다)
    for c in path[1:-1]:           # 끝점(홀)끼리는 R2·단계 겹침을 위에서 따로 본다
        for _k, pts in segs:
            if any(abs(c[0] - q[0]) < 1.5 and abs(c[1] - q[1]) < 1.5 for q in pts) or                     any(_on_seg(c, a, b, margin=0) for a, b in zip(pts, pts[1:])):
                return False
    for _k, pts in segs:
        for q in pts[1:-1]:
            if any(_on_seg(q, a, b, margin=0) for a, b in zip(path, path[1:])):
                return False
    # 같은 축 포개짐(R4) — 색과 무관하게 8px 로 본다
    for a, b in zip(path, path[1:]):
        ax = _axis(a, b)
        for _k, pts in segs:
            for c, d in zip(pts, pts[1:]):
                if _axis(c, d) != ax:
                    continue
                if ax == 'v' and abs(a[0] - c[0]) < 1.5:
                    lo = max(min(a[1], b[1]), min(c[1], d[1]))
                    hi = min(max(a[1], b[1]), max(c[1], d[1]))
                    if hi - lo > 2:
                        return False
                if ax == 'h' and abs(a[1] - c[1]) < 1.5:
                    lo = max(min(a[0], b[0]), min(c[0], d[0]))
                    hi = min(max(a[0], b[0]), max(c[0], d[0]))
                    if hi - lo > 2:
                        return False
    return True


def _route(bb, chips, frm, to):
    """`frm`→`to` 의 가장 싼 합법 경로와 번호 원 자리."""
    for found in _routes(bb, chips, frm, to):
        return found
    raise AssertionError(f'경로 없음: {frm} -> {to}')


def _routes(bb, chips, frm, to, density_weight=0.0):
    """`frm`→`to` 의 합법 경로를 싼 순으로 낸다. 후보는 [A, (A.x, y1), (X, y1), (X, y2), (B.x, y2), B]
    꼴이다 — y1·y2 는 끝 행 또는 반 행 위아래, X 는 `_lanes()`."""
    led = to[0] == 'LED'
    srcs, dsts = _end_holes(bb, chips, frm), _end_holes(bb, chips, to)
    others = []
    segs = [(k, pts) for k, pts, _d in bb._segments]
    for _k, pts, _d in bb._segments:
        others += [pts[0], pts[-1]]
    for (x, r), what in bb._leads.items():
        if '다리' in what or '애노드' in what or '캐소드' in what:
            others.append((x, bb.r_y(r)))
    chip_rows = tuple(ch['pin1_row'] for ch in bb.chips)
    placed = _placed_signal_segs(bb) if density_weight else []
    order = _rerank(_ordered(bb, chip_rows, tuple(srcs), tuple(dsts), led), placed,
                    bb.spec.row_pitch, density_weight)
    for p in order:
        if _valid(bb, p, others, segs):
            p = list(p)
            m = _marker_spot(bb, p)
            if m is not None:          # 번호 원을 찍을 데가 없는 경로는 따라 그릴 수 없다
                yield p, m


_ORDERED = {}


def _ordered(bb, chip_rows, srcs, dsts, led):
    """후보 경로를 싼 순으로 — 덮는 홀이 있는 것은 뺀다. 비용은 칩 자리와 끝 홀에만 달렸고 깔린
    배선과 무관해서, 수리(`_plan`)가 같은 선을 다시 깔 때 그대로 쓴다."""
    key = (bb.spec.name, chip_rows, srcs, dsts, led)
    if key in _ORDERED:
        return _ORDERED[key]
    half = bb.spec.row_pitch / 2
    # 가로 통로: 끝 행 그대로, 또는 반 행 위아래로 ±0.5·1.5·…·4.5 행 — 칩 안쪽 통로가 차면
    # 칩 위아래 행을 돌아간다
    ds = (0,) + tuple(s * half * n for n in (1, 3, 5, 7, 9) for s in (-1, 1))
    lo_y, hi_y = bb.r_y(1), bb.r_y(63)
    cands = []
    for A in srcs:
        for B in dsts:
            for d1 in ds:
                for d2 in ds:
                    if not (lo_y <= A[1] + d1 <= hi_y and lo_y <= B[1] + d2 <= hi_y):
                        continue
                    y1, y2 = A[1] + d1, B[1] + d2
                    for X in _lanes(bb, led) + [A[0], B[0]]:
                        p = _clean([A, (A[0], y1), (X, y1), (X, y2), (B[0], y2), B])
                        cands.append(p)
    cost = _coster(bb)
    scored = [(cost(p), p) for p in set(map(tuple, cands))]
    out = [(c, p) for (_over, c), p in sorted((s for s in scored if s[0][0] == 0),
                                              key=lambda s: (s[0][1], s[1]))]
    _ORDERED[key] = out
    return out


def _rerank(scored, placed, pitch, weight, top=_RERANK_TOP):
    """정적 순위 [(비용, 경로)] 의 앞 `top` 개를 `비용 + weight·밀도증분` 으로 다시 매긴다. 뒤는
    정적 순서 그대로. weight 0 이면 순서가 안 바뀐다 — 정적 정렬 열쇠도 (비용, 경로) 다."""
    if not weight:
        return [p for _c, p in scored]
    head = sorted(scored[:top], key=lambda s: (s[0] + weight * _density_cost(s[1], placed, pitch), s[1]))
    return [p for _c, p in head] + [p for _c, p in scored[top:]]


_R = 8   # 번호 원 반지름 (엔진 `_marker` 상자 ±8)


def _box_clear(bb, x, y, path_pts):
    """(x, y) 에 번호 원을 찍으면 아무것도 안 가리는가. 판정은 엔진 `_marker_clear`(R11 과 같은
    식)이고, 이 선은 아직 안 그렸으니 제 끝점 두 홀만 더 본다."""
    if any(abs(hx - x) <= _R + 2 and abs(hy - y) <= _R + 2 for hx, hy in (path_pts[0], path_pts[-1])):
        return False
    return bb._marker_clear(x, y)


def _marker_spot(bb, path):
    """경로 위에서 번호 원 자리. 엔진 기본(첫 구간 가운데)은 배선기 경로의 첫 토막이 반 행
    (9.5px)짜리라 원이 끝점 홀을 덮는다(2026-10-03 사용자 지적). 긴 구간 가운데부터 4px 씩
    밖으로 훑어 `_box_clear` 인 첫 점을 쓴다."""
    # 가로 구간 먼저 — 세로 차선 한복판에 앉은 원은 6px 간격 이웃 차선 셋을 막아 뒤 배선이
    # 갈 데가 없어진다(MUX U1 pin 8 임시선). 그다음 긴 구간 순.
    segs = sorted(zip(path, path[1:]), key=lambda s: (_axis(*s) != 'h',
                                                      -(abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))))
    for a, b in segs:
        length = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if length < 2 * _R + 8:
            continue
        mid = length / 2
        for off in range(0, int(mid - _R - 4), 4):
            for t in {mid - off, mid + off}:
                f = t / length
                x, y = round(a[0] + (b[0] - a[0]) * f), round(a[1] + (b[1] - a[1]) * f)
                if _box_clear(bb, x, y, path):
                    return (x, y)
    return None


_REPAIR_BACK, _REPAIR_ALTS = 4, 8   # 막히면 직전 몇 가닥을, 가닥마다 몇 후보까지 바꿔 보는가


def route_plan(build_fixed, chips, wires, board='v2', density_weight=None):
    """superset 판(모든 단계의 고정물 + 앞 선)에서 선마다 경로와 번호 원 자리를 정한다 — `wires`
    순서대로. 번호 원도 superset 에서 정하므로 단계 그림마다 같은 자리다. v2 판형만.

    앞 선이 가장 싼 자리를 먼저 가져가 뒤 선이 막히면, 직전 `_REPAIR_BACK` 가닥 중 **한 가닥만**
    다음 후보로 바꾸고 그 뒤를 다시 깐다. 칩 이름을 피하면(R14) 칩 하나를 건널 수 있는 반 행이
    pin 1~3·5~7 사이 넷뿐이라, 한 칩 안 이어 가기가 셋이면 싼 자리부터 고르다 막힌다(2026-10-04
    MUX U1). 아무 데로나 되돌아가는 탐색은 가짓수가 터져 10분을 넘겼다."""
    if not board_spec(board).readability:
        raise ValueError(f'route_plan 은 v2 판형만 고른다(차선이 v2 기하다): {board!r}')
    w = DENSITY_WEIGHT if density_weight is None else density_weight

    def board_(upto):
        bb = BreadboardRenderer(None, board=board)
        bb.enable_steps()
        build_fixed(bb, None, superset=True)
        for (_s, _e, kind, _f, _t, desc), (p, m) in zip(wires, upto):
            bb.step_wire(p, kind, desc, marker_at=m)
        return bb

    def greedy(start, upto, stop):
        """`upto` 뒤로 `stop` 가닥째까지 가장 싼 경로를 깐다. 막히면 None."""
        bb, plans = board_(upto), list(upto)
        for _s, _e, kind, frm, to, desc in wires[start:stop + 1]:
            found = next(_routes(bb, chips, frm, to, w), None)
            if found is None:
                return None
            bb.step_wire(found[0], kind, desc, marker_at=found[1])
            plans.append(found)
        return plans

    plans, bb = [], board_([])
    while len(plans) < len(wires):
        i = len(plans)
        _s, _e, kind, frm, to, desc = wires[i]
        found = next(_routes(bb, chips, frm, to, w), None)
        if found is not None:
            bb.step_wire(found[0], kind, desc, marker_at=found[1])
            plans.append(found)
            continue
        for j in range(i - 1, max(-1, i - 1 - _REPAIR_BACK), -1):
            _s, _e, _k, frm_j, to_j, _d = wires[j]     # 수리할 앞 선 — 막힌 선의 frm·to 는 메시지에 남긴다
            alts = itertools.islice(_routes(board_(plans[:j]), chips, frm_j, to_j, w), 1, 1 + _REPAIR_ALTS)
            for alt in alts:
                more = greedy(j + 1, plans[:j] + [alt], i)
                if more is not None:
                    plans = more
                    break
            else:
                continue
            break
        else:
            raise AssertionError(f'경로 없음: {frm} -> {to} ({desc})')
        bb = board_(plans)
    return plans


def draw_routed(bb, wires, plans, stage):
    for (s, e, kind, _frm, _to, desc), (p, m) in zip(wires, plans):
        if stage is None:
            if e is not None:
                continue
        elif not (s <= stage and (e is None or stage <= e)):
            continue
        bb.step_wire(p, kind, desc, marker_at=m)

def _axis_segs(pts):
    """축 정렬 구간만 [(축, 고정 좌표, lo, hi)] 로. 사선 구간은 밀도에서 뺀다."""
    out = []
    for a, b in zip(pts, pts[1:]):
        if abs(a[0] - b[0]) < .5:
            out.append(('v', a[0], min(a[1], b[1]), max(a[1], b[1])))
        elif abs(a[1] - b[1]) < .5:
            out.append(('h', a[1], min(a[0], b[0]), max(a[0], b[0])))
    return out


def _crowding(sa, sb, pitch):
    """두 축 구간이 1칸보다 가깝게 나란히 달린 정도(px) — 겹친 길이 × (1 − 간격/칸). 간격 0 은
    포개짐이라 R4 가 따로 본다. 2026-10-04 사용자: 빽빽함 = 가까운 평행선, 가까울수록 무겁게."""
    if sa[0] != sb[0]:
        return 0.0
    gap = abs(sa[1] - sb[1])
    if gap <= .5 or gap >= pitch:
        return 0.0
    over = min(sa[3], sb[3]) - max(sa[2], sb[2])
    return over * (1 - gap / pitch) if over > 0 else 0.0


def _density_cost(path, placed, pitch):
    """새 경로가 이미 깔린 신호선 구간(`_axis_segs` 꼴) 옆을 얼마나 붙어 달리는가(px)."""
    return sum(_crowding(s, t, pitch) for s in _axis_segs(path) for t in placed)


def _placed_signal_segs(bb):
    return [s for kind, pts, _d in bb._segments if kind in ('sig', 'mid') for s in _axis_segs(pts)]


def wire_metrics(bb):
    """신호선(sig·mid)의 길이(칸)·꺾임·밀도(칸). 밀도는 서로 다른 두 선의 구간 쌍마다 `_crowding`
    을 더한다 — 한 선 안의 구간끼리는 안 센다. 전원·GND·브리지는 안 본다."""
    p = bb.spec.row_pitch
    wires = [pts for kind, pts, _d in bb._segments if kind in ('sig', 'mid')]
    segs = [_axis_segs(pts) for pts in wires]
    length = sum(math.dist(a, b) for pts in wires for a, b in zip(pts, pts[1:]))
    bends = sum(max(len(pts) - 2, 0) for pts in wires)
    dens = sum(_crowding(s, t, p)
               for i in range(len(segs)) for j in range(i + 1, len(segs))
               for s in segs[i] for t in segs[j])
    return {'length': length / p, 'bends': bends, 'density': dens / p}


# ---------------------------------------------------------------------------
# 배치기 (v2) — 칩 슬롯 행·LED 윗행·브리지 행을 고른다
#
# 배선기(`route_plan`)는 자리를 받아 길만 고른다. 배치기는 그 자리 자체를 고른다 — 근사 비용으로
# 후보 전부의 순위를 매기고 앞 `PLACE_TOP` 개만 route_plan 으로 실측한다. 저작 때
# `python -m scripts.lab.place_search <배치.py>` 로 한 번 돌리고, 고른 자리는 주차 `LAYOUT` 과 netlist
# `kind: layout` 표에 옮겨 적는다. 설계: `docs/plans/2026-10-05-v2-배치기-설계.md`.
#
# layout = {'slots': {슬롯: pin 1 행}, 'leds': {회로: {태그: 윗행}}, 'bridge': [GND 행, VCC 행]}
# — 보고서 JSON 과 그대로 맞대려고 리스트·문자열 키만 쓴다.

# 배선기가 아는 칩 — `_dip_pin_row` 가 DIP-14 를 가정한다. 16핀(74HC138 따위)·7-segment 는 배선기부터 넓힌다
DIP14 = frozenset({'74HC00', '74HC02', '74HC04', '74HC08', '74HC10', '74HC11', '74HC20',
                   '74HC21', '74HC27', '74HC32', '74HC74', '74HC86'})
PLACE_GMIN = 3      # 칩 사이 최소 빈 행 — 실물에서 손이 들어갈 여유(2026-10-05 사용자 N2)
PLACE_GMAX = 6
PLACE_STARTS = tuple(range(3, 9))   # 맨 위 칩 pin 1 행 후보
PLACE_TOP = 8       # 근사 순위 앞 몇 개를 route_plan 으로 실측하나 (한 판에 약 1분)
PLACE_ROUNDS = 3
LED_SPAN = 4        # LED 사슬 한 벌 = 윗행 ~ 윗행+3 (LED 두 행 + 저항 아랫다리)
PLACE_ROW_LAST = 61  # 칩·LED·브리지가 쓸 마지막 행 — 62·63 은 레일 빈 행
PLACE_REPORT = '배치탐색.md'


@dataclass(frozen=True)
class PlaceCircuit:
    """배치기가 보는 회로 하나.

    `chips` 칩 → 슬롯, `models` 칩 → 모델(`DIP14`), `leds` LED 태그 위→아래(R10 — 진리표 열 순서,
    2026-10-05 사용자 N3), `wires` 는 `route_plan` 꼴이되 LED 끝은 태그 `('LED', 'L1')`.
    `fixed(bb, stage, superset, layout)` 는 칩·전원·입력·LED 사슬·브리지를 `layout` 자리에 그린다.
    `inputs` 는 입력 점퍼가 꽂히는 (칩, 핀) — f쪽이면 가운데 GND 레일의 그 행을 쓴다."""
    name: str
    chips: dict
    models: dict
    leds: tuple
    wires: tuple
    fixed: object
    inputs: tuple = ()


def layout_key(layout):
    """layout → 캐시 열쇠(키 정렬 JSON)."""
    return json.dumps(layout, sort_keys=True, ensure_ascii=False)


def place_check(circuit):
    """배치기가 다룰 수 있는 회로인가. 아니면 ValueError."""
    bad = sorted({m for m in circuit.models.values() if m not in DIP14})
    if bad:
        raise ValueError(f'{circuit.name}: 배치기는 14핀 칩만 놓는다(`_dip_pin_row` 가 DIP-14 가정) — {bad}')
    tags = {end[1] for w in circuit.wires for end in (w[3], w[4]) if end[0] == 'LED'}
    unknown = sorted(tags - set(circuit.leds))
    if unknown:
        raise ValueError(f'{circuit.name}: leds 에 없는 LED 태그 {unknown}')


def place_chips(circuit, layout):
    """칩 → pin 1 행."""
    return {chip: layout['slots'][slot] for chip, slot in circuit.chips.items()}


def place_wires(circuit, layout):
    """LED 태그 끝을 그 회로의 LED 윗행으로 바꾼 `route_plan` 배선표."""
    rows = layout['leds'].get(circuit.name, {})

    def end(e):
        return ('LED', rows[e[1]]) if e[0] == 'LED' else e
    return [(s, e, kind, end(f), end(t), desc) for s, e, kind, f, t, desc in circuit.wires]


def place_hash(circuits, slots, gmin=PLACE_GMIN):
    """배선표 지문(16자리). 바뀌면 배치를 다시 찾아야 한다 — `fixed` 함수는 안 본다."""
    body = {'slots': list(slots), 'gmin': gmin, 'circuits': [
        {'name': c.name, 'chips': c.chips, 'models': c.models, 'leds': list(c.leds),
         'wires': [list(w) for w in c.wires], 'inputs': [list(i) for i in c.inputs]}
        for c in circuits]}
    text = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


@lru_cache(maxsize=None)
def _place_geom():
    s = board_spec('v2')
    return s.cols['left'], s.cols['right'], s.row_pitch


def place_wire_cost(chips, wire):
    """선 하나의 근사 비용(px) — 끝 홀 후보 사이 최소 맨해튼 + 40·꺾임 + 400·몸통(배선기 `_coster` 와
    같은 상수). 꺾임은 행이 다르거나 가운데를 건너면(LED — R12 때문에 반 행으로 돈다) 2, 몸통은 쪽이
    다른 같은 칩 안 선이나 a쪽 출력 → LED 면 1. 경로·점유는 안 본다 — 순위만 매긴다."""
    L, R, pitch = _place_geom()
    _s, _e, _k, frm, to, _d = wire

    def holes(end):
        if end[0] == 'LED':
            return [(R['a'], end[1])], None
        row = _dip_pin_row(chips[end[0]], end[1])
        side = _dip_side(end[1])
        return [(L[c], row) for c in _STRIP_COLS[side]], side

    ha, sa = holes(frm)
    hb, sb = holes(to)
    dist = min(abs(xa - xb) + abs(ra - rb) * pitch for xa, ra in ha for xb, rb in hb)
    led = 'LED' in (frm[0], to[0])
    bends = 2 if led or ha[0][1] != hb[0][1] else 0
    if led:
        body = 1 if 'a' in (sa, sb) else 0
    else:
        body = 1 if frm[0] == to[0] and sa != sb else 0
    return dist + 40 * bends + 400 * body


def mid_rail_rows(circuit, slots, bridge):
    """가운데 레일에서 이미 쓰는 행 — 칩 pin 14 전원선(그 행 GND 홀 위를 지나 VCC 에 꽂힌다), 브리지
    둘, f쪽 입력 점퍼. LED GND 점퍼가 여기 착지하면 `free_rail_row` 가 옆 행으로 비켜 사선이 된다."""
    used = {slots[s] for s in circuit.chips.values()}
    rows = used | set(bridge)
    for chip, pin in circuit.inputs:
        if _dip_side(pin) == 'f':
            rows.add(_dip_pin_row(slots[circuit.chips[chip]], pin))
    return rows


def bridge_rows(slots):
    """브리지 두 가닥 [GND 행, VCC 행] — 맨 아래 칩 아래로 2행 이상 띄운 첫 연속 비간극 두 행.
    브리지는 좌 블록을 가로지르니 칩 행에 오면 핀 위를 지난다. 자리가 없으면 None."""
    r = max(slots.values()) + 6 + 3
    while r + 1 <= PLACE_ROW_LAST:
        if r not in RAIL_GAP_ROWS and r + 1 not in RAIL_GAP_ROWS:
            return [r, r + 1]
        r += 1
    return None


def led_rows(circuit, slots, bridge):
    """회로의 LED 윗행 {태그: 행} — DP.

    태그 순서대로 위→아래(R10, N3), 사슬끼리 `LED_SPAN` 행 이상, 윗행+3(저항 아랫다리 = GND 점퍼
    출발 행)이 레일 빈 행·가운데 레일 사용 행이 아니다(GND 점퍼가 곧다). 그 LED 로 가는 선(모든 단계
    — MUX L1 처럼 임시 급전과 최종 Y 를 같이 받는 LED 도 그냥 더한다)의 근사 비용 합이 가장 작은
    조합, 동률이면 위쪽. LED 가 없으면 {}, 다 놓을 수 없으면 None."""
    if not circuit.leds:
        return {}
    chips = {c: slots[s] for c, s in circuit.chips.items()}
    busy = RAIL_GAP_ROWS | mid_rail_rows(circuit, slots, bridge)
    tops = [t for t in range(3, PLACE_ROW_LAST - LED_SPAN + 2) if t + LED_SPAN - 1 not in busy]
    # 태그마다 그 LED 로 가는 선만 — 후보 수천 개 × 윗행 56개마다 배선표 전체를 훑지 않게
    mine = {tag: [w for w in circuit.wires if ('LED', tag) in (w[3], w[4])] for tag in circuit.leds}

    def cost(tag, top):
        def sub(e):
            return ('LED', top) if e == ('LED', tag) else e
        return sum(place_wire_cost(chips, (s, e, k, sub(f), sub(t), d)) for s, e, k, f, t, d in mine[tag])

    prev = None
    for tag in circuit.leds:
        here = [cost(tag, t) for t in tops]
        if prev is None:
            cur = [(c, (t,)) for c, t in zip(here, tops)]
        else:
            cur, best, j = [], None, 0
            for t, c in zip(tops, here):
                while j < len(tops) and tops[j] + LED_SPAN <= t:
                    if prev[j] is not None and (best is None or prev[j] < best):
                        best = prev[j]
                    j += 1
                cur.append(None if best is None else (best[0] + c, best[1] + (t,)))
        prev = cur
    done = [x for x in prev if x is not None]
    if not done:
        return None
    return dict(zip(circuit.leds, min(done)[1]))


def place_r10_ok(circuit, chips, leds):
    """단계마다 LED 로 건너는 선의 칩 쪽 행 순서가 LED 위아래 순서와 같은가 — `verify()` R10 을 미리
    본다. 단계 k 에 살아 있는 선 = `s <= k` 이고 끝 단계가 없거나 `k <= e` (`draw_routed` 와 같다)."""
    stages = {w[0] for w in circuit.wires} | {w[1] for w in circuit.wires if w[1] is not None}
    for st in sorted(stages):
        live = []
        for s, e, _k, f, t, _d in circuit.wires:
            if not (s <= st and (e is None or st <= e)):
                continue
            for led, chip in ((t, f), (f, t)):
                if led[0] == 'LED' and chip[0] != 'LED':
                    live.append((leds[led[1]], _dip_pin_row(chips[chip[0]], chip[1])))
        live.sort()
        if any(c1 > c2 for (_a, c1), (_b, c2) in zip(live, live[1:])):
            return False
    return True


def slot_candidates(slots, gmin=PLACE_GMIN, gmax=PLACE_GMAX, starts=PLACE_STARTS):
    """슬롯 → pin 1 행 후보 [dict]. 순서(순열, N4) × 맨 위 행 × 칩 사이 빈 행 gmin~gmax. 칩 행 k 나
    k+6 이 레일 빈 행이면 버린다 — pin 14·pin 7 전원선이 옆 행으로 비켜 사선이 된다. 브리지 둘
    자리가 없어도 버린다."""
    out = []
    for order in itertools.permutations(slots):
        for k0 in starts:
            for gaps in itertools.product(range(gmin, gmax + 1), repeat=len(slots) - 1):
                rows = [k0]
                for g in gaps:
                    rows.append(rows[-1] + 7 + g)
                if any(k in RAIL_GAP_ROWS or k + 6 in RAIL_GAP_ROWS for k in rows):
                    continue
                cand = dict(zip(order, rows))
                if bridge_rows(cand) is not None:
                    out.append(cand)
    return out


def place_proxy(circuits, slots):
    """슬롯 후보 하나 → (근사 비용 합, layout). 회로마다 LED 행을 DP 로 고른다. LED 를 못 놓거나
    R10 이 미리 어긋나거나, 입력 점퍼가 꽂히는 핀 행이 레일 빈 행이면(점퍼가 옆 행으로 비켜 사선)
    None."""
    for c in circuits:
        if any(_dip_pin_row(slots[c.chips[chip]], pin) in RAIL_GAP_ROWS for chip, pin in c.inputs):
            return None
    bridge = bridge_rows(slots)
    layout = {'slots': dict(slots), 'leds': {}, 'bridge': bridge}
    total = 0.0
    for c in circuits:
        leds = led_rows(c, slots, bridge)
        if leds is None:
            return None
        chips = place_chips(c, layout)
        if not place_r10_ok(c, chips, leds):
            return None
        layout['leds'][c.name] = leds
        total += sum(place_wire_cost(chips, w) for w in place_wires(c, layout))
    return total, layout


_PLACE_PATHS = {}


def place_paths(circuit, layout, density_weight=None):
    """`layout` 자리에서 `route_plan` 경로 — 회로·배선표·자리·λ 마다 한 번(엔진 안 캐시). 주차 빌더와
    배치기가 같은 캐시를 쓴다."""
    w = DENSITY_WEIGHT if density_weight is None else density_weight
    key = (circuit.name, place_hash([circuit], ()), layout_key(layout), w)
    if key not in _PLACE_PATHS:
        def fixed(bb, stage, superset=False):
            circuit.fixed(bb, stage, superset, layout)
        _PLACE_PATHS[key] = route_plan(fixed, place_chips(circuit, layout), place_wires(circuit, layout),
                                       board='v2', density_weight=w)
    return _PLACE_PATHS[key]


def place_metrics(circuit, layout, density_weight=None):
    """superset 판(모든 단계의 선 — 학생이 그 회로를 꽂는 동안 꽂는 선 전부)의 `wire_metrics`."""
    plans = place_paths(circuit, layout, density_weight)
    bb = BreadboardRenderer(None, board='v2')
    bb.enable_steps()
    circuit.fixed(bb, None, True, layout)
    for (_s, _e, kind, _f, _t, desc), (p, m) in zip(place_wires(circuit, layout), plans):
        bb.step_wire(p, kind, desc, marker_at=m)
    return wire_metrics(bb)


def _place_measure(circuits, layout):
    """회로마다 superset 지표를 더한다. 막히면 {'blocked': 첫 줄}."""
    tot = {'length': 0.0, 'bends': 0, 'density': 0.0}
    try:
        for c in circuits:
            m = place_metrics(c, layout)
            for k in tot:
                tot[k] += m[k]
    except AssertionError as e:
        return {'blocked': str(e).splitlines()[0]}
    return tot


def place_verify(module, layout, out_dir):
    """주차 모듈의 `BOARDS` 사슬(기준선 이어 가며, `RESTART` 에서 끊고)과 `FINALS` 를 `layout` 으로 다
    그려 본다 — `verify()`(R1~R14) 가 막으면 '보드: 사유' 한 줄, 통과하면 None. 모듈 `LAYOUT` 은
    그리는 동안만 바꾼다(빌더가 전역 `LAYOUT` 을 읽는다)."""
    saved, name = module.LAYOUT, None
    module.LAYOUT = layout
    try:
        base = None
        for name, fn, stage in module.BOARDS:
            if name in getattr(module, 'RESTART', ()):
                base = None
            bb = fn(os.path.join(out_dir, name), None, stage=stage, baseline=base)
            base = bb.snapshot()
        for name, fn in module.FINALS:
            fn(os.path.join(out_dir, name))
    except AssertionError as e:
        lines = [x.strip() for x in str(e).splitlines() if x.strip()]
        return f'{name}: ' + ' '.join(lines[:2])
    finally:
        module.LAYOUT = saved
    return None


def place_module_hash(module):
    return place_hash(module.PLACE, module.SLOTS, getattr(module, 'GMIN', PLACE_GMIN))


def _serial_map(fn, items):
    return [fn(x) for x in items]


def place_plan(module, top=PLACE_TOP, rounds=PLACE_ROUNDS, gmin=None, out_dir=None,
               measure=None, verify=None, mapper=None, chunk=1):
    """주차 모듈의 칩 행·LED 행·브리지 행을 고른다.

    1. 슬롯 후보 전부를 근사 비용(`place_proxy`)으로 줄 세운다.
    2. 지금 `LAYOUT`(기준)과 앞 `top` 개를 실측한다(`measure`, 기본 `_place_measure` — route_plan).
    3. 막히지 않고 기준보다 짧고 밀도 합이 기준 이하인 것을 길이 순으로 `verify`(기본 `place_verify` —
       단계 사슬 전부) 해 처음 통과한 것을 고른다. 없으면 다음 `top` 개, `rounds` 번까지. 그래도 없을
       때만 기준을 verify 해 고른다 — 기준이 1라운드에서 먼저 통과해 뒤 라운드를 막지 않게(2026-10-05
       사용자). 기준보다 긴 배치는 고르지 않는다(N1).
    병렬: `mapper(fn, items) -> [fn(x)…]`(기본 차례대로) 로 라운드마다 실측을 한 묶음에 돌리고(1라운드
    묶음에 기준도 든다), verify 는 길이 순으로 `chunk` 개씩 함께 돌려 통과한 것 중 가장 짧은 것을 고른다
    — chunk=1 과 같은 답이다. `place_search --jobs` 가 프로세스 풀을 넘긴다(2026-10-05 사용자).
    돌려주는 값 {'hash', 'layout', 'rows'} — rows 는 실측한 후보마다 {'rank', 'proxy', 'layout',
    'length', 'bends', 'density' | 'blocked', 'status'}."""
    circuits, slots = list(module.PLACE), tuple(module.SLOTS)
    for c in circuits:
        place_check(c)
    gmin = getattr(module, 'GMIN', PLACE_GMIN) if gmin is None else gmin
    measure = measure or (lambda lay: _place_measure(circuits, lay))
    if verify is None:
        tmp = out_dir or tempfile.mkdtemp()

        def verify(lay):
            return place_verify(module, lay, tmp)
    ranked = sorted((r for r in (place_proxy(circuits, s) for s in slot_candidates(slots, gmin))
                     if r is not None), key=lambda r: (r[0], layout_key(r[1])))
    mapper = mapper or _serial_map
    base, rows, chosen, seen = None, [], None, {layout_key(module.LAYOUT)}
    for r in range(rounds):
        todo = [] if base else [dict(rank='기준', proxy=None, layout=module.LAYOUT)]
        for i in range(r * top, min((r + 1) * top, len(ranked))):
            proxy, lay = ranked[i]
            if layout_key(lay) in seen:
                continue
            seen.add(layout_key(lay))
            todo.append(dict(rank=i + 1, proxy=round(proxy), layout=lay))
        for x, m in zip(todo, mapper(measure, [x['layout'] for x in todo])):
            x.update(m)
        rows += todo
        if base is None:
            base = rows[0]
            if 'blocked' in base:
                raise AssertionError(f"기준 LAYOUT 이 막힌다 — {base['blocked']}")
            limit = base['density'] + 1e-9
        ok = sorted((x for x in rows[1:] if 'blocked' not in x and 'status' not in x
                     and x['density'] <= limit and x['length'] < base['length']),
                    key=lambda x: (x['length'], x['density'], layout_key(x['layout'])))
        for j in range(0, len(ok), chunk):
            part = ok[j:j + chunk]
            for x, why in zip(part, mapper(verify, [x['layout'] for x in part])):
                if why is not None:
                    x['status'] = f'verify: {why}'
                elif chosen is None:
                    x['status'], chosen = '✔ 고름', x
                else:
                    x['status'] = '통과 — 더 짧은 것을 고름'
            if chosen is not None:
                break
        if chosen is not None:
            break
    if chosen is None:
        why = mapper(verify, [base['layout']])[0]
        base['status'] = '✔ 고름' if why is None else f'verify: {why}'
        if why is None:
            chosen = base
    for x in rows:
        x.setdefault('status', f"막힘: {x['blocked']}" if 'blocked' in x
                     else '밀도 초과' if x['density'] > limit
                     else '기준보다 김' if x is not base and x['length'] >= base['length'] else '')
    if chosen is None:
        raise AssertionError('고를 배치가 없다 — ' + rows[-1]['status'])
    return {'hash': place_hash(circuits, slots, gmin), 'layout': chosen['layout'], 'rows': rows}


def place_report(result, title):
    """`배치탐색.md` 본문. 첫 JSON 블록(지문·고른 layout)을 테스트가 읽는다 — 손으로 고치지 않는다."""
    head = json.dumps({'hash': result['hash'], 'layout': result['layout']},
                      ensure_ascii=False, indent=1, sort_keys=True)
    lines = [f'# 배치 탐색 — {title}', '',
             '`python -m scripts.lab.place_search <배치.py>` 가 쓴다. 배선표가 바뀌면 다시 돌린다 — '
             '고른 layout 은 `배치.py` 의 `LAYOUT` 과 netlist `kind: layout` 표에 옮겨 적는다.', '',
             '```json', head, '```', '',
             '길이·밀도는 superset 판(모든 단계의 선) 칸 단위, 회로 합이다. 기준 = 탐색 시점 `LAYOUT`.', '',
             '| 순위 | 근사(px) | 길이 | 꺾임 | 밀도 | 슬롯 | LED | 결과 |',
             '|---|---|---|---|---|---|---|---|']
    for x in result['rows']:
        slots = ' '.join(f'{k}:{v}' for k, v in sorted(x['layout']['slots'].items()))
        leds = ' '.join(f'{t}:{r}' for c in sorted(x['layout']['leds'])
                        for t, r in x['layout']['leds'][c].items())
        proxy = '' if x['proxy'] is None else x['proxy']
        if 'blocked' in x:
            lines.append(f"| {x['rank']} | {proxy} | — | — | — | {slots} | {leds} | {x['status']} |")
        else:
            lines.append(f"| {x['rank']} | {proxy} | {x['length']:.1f} | {x['bends']} | "
                         f"{x['density']:.1f} | {slots} | {leds} | {x['status']} |")
    return '\n'.join(lines) + '\n'


def read_place_report(path):
    """`배치탐색.md` 의 첫 JSON 블록 → {'hash', 'layout'}."""
    with open(path, encoding='utf-8') as f:
        text = f.read()
    m = re.search(r'```json\n(.*?)\n```', text, re.S)
    if not m:
        raise ValueError(f'{path}: JSON 블록이 없다')
    return json.loads(m.group(1))


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
# PNG 옆 JSON 의 스키마. 체크리스트(`scripts/lab/render.py`)가 같은 문자열을 따로 들고
# 대조한다 — 그쪽은 이 모듈을 import 하지 않는다
SIDECAR_SCHEMA = 'breadboard-sidecar/v1'


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
    board = getattr(mod, 'BOARD', DEFAULT_BOARD)
    if board not in BOARD_VERSIONS:
        raise ValueError(f'{path}: BOARD 는 {BOARD_VERSIONS} 중 하나다: {board!r}')
    return mod


def load_board(experiment):
    path = board_path(experiment)
    mod = load_board_file(path, f'board_e{experiment}')
    require_board(mod, experiment, path)
    return mod


def require_board(board, experiment, label):
    """주차 `배치.py` 는 `BOARD` 를 꼭 적는다. 빠뜨리면 렌더러 기본값(`DEFAULT_BOARD`)으로 그려져
    v1 주차(`config.BOARD_V2_FROM` 앞)가 아무도 모른 채 v2 그림으로 나가고, v2 주차도 기본값이
    바뀌는 날 같은 일을 겪는다. 실험 번호가 정하는 판형과 달라도 적어 두면 연다."""
    want = _config().default_board(experiment)
    if not hasattr(board, 'BOARD'):
        raise ValueError(f"{label}: 실험{experiment} 부터 판형은 {want} 다 — 머리에 BOARD = '{want}' 를 "
                         "두고 빌더마다 BreadboardRenderer(..., board=BOARD) 로 넘긴다")


def board_version(board):
    """주차 결선 모듈의 판형 — 모듈 상수 `BOARD`, 없으면 렌더러 기본값(`DEFAULT_BOARD`)."""
    return getattr(board, 'BOARD', DEFAULT_BOARD)


def check_board(board, bb, label):
    """빌더가 그린 판형이 주차 `BOARD` 와 같은가. 빌더가 `board=BOARD` 를 빠뜨리면 v2 주차가 v1
    그림으로 **조용히** 나간다 — `build_all` 과 손그림 참조(`hand_compare.reference_diagram`)가
    부른다."""
    want = board_version(board)
    if bb.board != want:
        raise ValueError(f"{label}: 주차 BOARD 는 '{want}' 인데 렌더러는 '{bb.board}' 판형이다 — "
                         "빌더가 BreadboardRenderer(..., board=BOARD) 로 넘겨야 한다")


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
            here = {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom'])
                    for ch in nb.led_chains}
            chains = {k: tag for k, tag in base['chains'].items() if k not in here}
        if not wires:
            raise ValueError(f'{title}: 걷을 배선이 없다 — 걷기 보드가 필요 없는 경계다')
        spec = {'wires': wires, 'title': title, 'subtitle': subtitle}
        if chains:
            # 사슬째 뽑는 경계(실험04 8걷기) — 없으면 키를 안 둬 옛 걷기 보드 도장이 그대로다
            spec['chains'] = chains
        ghost = dict(base, ghost=spec)
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
        check_board(board, bb, filename)
        base = bb.snapshot()
        made[filename] = bb.stamp()
    for filename, fn in board.FINALS:
        bb = fn(os.path.join(output_dir, filename), template_path)
        if bb is None:
            raise TypeError(
                f"{filename}: 빌더 {fn.__name__} 가 렌더러를 돌려주지 않는다 — "
                "빌더 끝에 `return bb` 가 있어야 한다")
        check_board(board, bb, filename)
        made[filename] = bb.stamp()
    return made


def main():
    parser = argparse.ArgumentParser(description="Breadboard Diagram Generator")
    parser.add_argument("--experiment", type=int, required=True,
                        help="실험 번호 — 보고서/실험NN/결선도/배치.py 의 결선도를 전부 뽑는다")
    parser.add_argument("--output", default=None,
                        help="출력 폴더 (기본: 그 배치.py 가 있는 결선도 폴더)")
    parser.add_argument("--template", default=None, help="양식 이미지 경로 (기본: 주차 BOARD 의 양식 — v1 Breadboard.jpg, v2 breadboard_v2/Breadboard_v2.png)")
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
