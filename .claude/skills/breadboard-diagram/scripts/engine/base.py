# 결선도 엔진 조각 — 템플릿·글꼴·배율·색·판형.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

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
