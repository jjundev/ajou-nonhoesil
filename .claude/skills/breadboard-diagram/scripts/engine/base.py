# 결선도 엔진 조각 — 템플릿·글꼴·배율·색·판형.
# 단독으로 import 하지 않는다. `../render_breadboard.py` 가 조각들을 `_PARTS` 순서대로 자기
# 이름공간에서 실행한다 — 앞 조각의 이름(import·상수·함수)을 import 없이 그대로 쓴다.

# v1 브레드보드 템플릿 정본 — `.claude/assets/` 가 이긴다. 좌표표는 이 한 장에 맞춰져 있다.
# 2026-2 배포본 `Breadboard.pdf` 는 가로가 약 5% 넓어 갈아끼우면 결선이 옆 홀에 그려진다(눈으로는
# 안 잡힌다) — 옮기려면 좌표표를 다시 뜬다. 아카이브 사본은 최후 대체물이다.
TEMPLATE_CANDIDATES = (
    '.claude/assets/Breadboard.jpg',
    'from_the_past/정리/강의노트/Breadboard.jpg',
    'from_the_past/정리/아카이브/강의노트/Breadboard.jpg',
)

TEMPLATE_SIZE = (998, 1345)

# 폰트 후보 — 있는 것을 순서대로. 한글은 Apple SD Gothic Neo → 본고딕 → 함초롬돋움 → 맑은 고딕 → 나눔고딕.
# 맑은 고딕은 ⊕ 가 없어 □ 로 찍혔다(2026-09-19) — 그래서 `font_path()` 가 글리프까지 본다. 하드
# (`REQUIRED_GLYPHS`)가 빠진 후보는 버리고, 소프트(`PREFERRED_GLYPHS`)는 선호만 한다 — ☐ 하나 때문에
# 맑은 고딕뿐인 PC 에서 렌더러가 통째로 죽었다.
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

# 하드 — 빠진 후보는 버린다. □ 로 나가면 식(⊕)·주소(→)를 못 읽는다.
REQUIRED_GLYPHS = {'kr': '⊕→·※', 'en': ''}

# 소프트 — ☐ 체크칸은 □ 로 나가도 뜻이 같다. 없으면 경고만 한다.
PREFERRED_GLYPHS = {'kr': '☐', 'en': ''}

# 소프트 글리프 경고를 이미 낸 폰트 — 렌더 한 장에 `font_path()` 가 여러 번 불린다.
_SOFT_WARNED = set()

# .notdef 를 부르는 글자 — 유니코드 비문자라 어떤 폰트에도 진짜 글리프가 없다.
_NOTDEF = '\ufffe'


def _glyph_mask(font, ch):
    """`ch` 한 글자의 렌더 결과 — (크기, 픽셀). 같은 폰트 안에서만 견준다."""
    mask = font.getmask(ch, mode='L')
    return (mask.size, bytes(mask))


def _covers(path, chars):
    """`path` 폰트가 `chars` 를 전부 진짜 글리프로 그리는가 — .notdef 와 같은 그림이면 없는 것.
    Pillow 만 쓴다. 못 여는 파일은 `OSError` 를 올린다 — "글리프 없음" 과 "폰트 아님" 은 다른 사고다.
    """
    font = ImageFont.truetype(path, 20)
    notdef = _glyph_mask(font, _NOTDEF)
    return all(_glyph_mask(font, ch) != notdef for ch in chars)


def font_path(kind):
    """`kind`('kr'|'en') 의 첫 번째 쓸 만한 폰트 경로. 하드 글리프를 다 그리는 후보 중 소프트까지
    되는 첫 후보, 없으면 하드만 되는 첫 후보(stderr 경고 한 줄). 하드를 통과한 후보가 없을 때만
    던지고, 못 연 후보와 글리프로 밀린 후보를 갈라 적는다.
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


# 출력 배율 — 좌표는 정본 템플릿 기준으로 계산하고 그리는 순간에만 곱한다(`_ScaledDraw`·`_ScaledFont`).
# 2026-09-28 사용자: 태블릿에서 글자가 작았다.
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


class _NullDraw:
    """긋지 않는 붓 — 글자 치수(`textbbox`)만 진짜 붓에 묻고 나머지는 버린다."""

    def __init__(self, real):
        self._real = real

    def textbbox(self, *a, **k):
        return self._real.textbbox(*a, **k)

    def __getattr__(self, name):
        return lambda *a, **k: None


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


def _hand_noise(rng):
    """누적 길이 s -> [-1, 1] 매끈한 떨림 — 사인 셋을 가중치 합으로 나눈다."""
    waves = [(rng.uniform(40, 160), rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1))
             for _ in range(3)]
    total = sum(w for _, _, w in waves)
    return lambda s: sum(w * math.sin(2 * math.pi * s / lam + ph) for lam, ph, w in waves) / total


def _hand_polyline(points, rng, amp=2.0, step=6.0, ramp=12.0):
    """손그림 모사 배선 — 축마다 따로 ±amp 떨린 촘촘한 점열. 양 끝점은 입력 그대로(홀 위)고
    끝에서 `ramp` 동안 진폭을 0 에서 올린다."""
    pts = [tuple(map(float, p)) for p in points]
    nx, ny = _hand_noise(rng), _hand_noise(rng)
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    out, s0 = [pts[0]], 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.dist((x0, y0), (x1, y1))
        n = max(1, math.ceil(seg / step))
        for i in range(1, n + 1):
            t = i / n
            s = s0 + seg * t
            k = amp * min(1.0, s / ramp, (total - s) / ramp)
            out.append((x0 + (x1 - x0) * t + k * nx(s), y0 + (y1 - y0) * t + k * ny(s)))
        s0 += seg
    out[-1] = pts[-1]
    return out


def _hand_width(width, rng):
    """마커 한 가닥의 굵기 — 기본의 0.7~1.3 배, 가닥 안에서는 일정."""
    return max(1, round(width * rng.uniform(0.7, 1.3)))


def _hand_dot(p, r, rng):
    """끝점 도트 상자 — 축마다 반지름 ±1px."""
    rx, ry = r + rng.uniform(-1, 1), r + rng.uniform(-1, 1)
    return [p[0] - rx, p[1] - ry, p[0] + rx, p[1] + ry]


def _font(kind, size):
    return _ScaledFont(font_path(kind), size)


def _default_template(spec=None):
    """판형 양식 경로 — 저장소 루트, 그다음 cwd. 다른 판형으로 넘어가지 않는다 — 열 표와 그림이
    어긋난 채 그럴듯하게 나온다."""
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
# v1 물리 좌표계 — `Breadboard.jpg` 의 홀 픽셀 군집 중심을 실측했다(눈대중 값은 끝점이 홀 밖이었다).
# 다시 뜨려면 `tools/measure_template.py`.
ROW0 = 272.0        # 1행 홀 중심 y
ROW_PITCH = 16.345  # 행 간격
BOARD_LEFT = 149     # 좌 보드 테두리 x. 이보다 왼쪽은 보드 밖 여백이다 (가독성 테스트의 BOARD_L)
BOARD_RIGHT = 880    # 우 보드 테두리 x. 이보다 오른쪽은 보드 밖 여백이다 (addr() 의 '보드밖' 경계와 같다)

# R7. 칩 한쪽에 꽂히는 리드 한도(한쪽 자유 열 a~d 또는 g~j). 2026-09-18 실험03 74HC86 왼쪽 11리드가
# 꽂기 힘들었다 — 8 이면 그것은 걸리고 좌·우로 나눈 전가산기(좌 7·우 5)는 통과한다.
SIDE_LEAD_MAX = 8
SIDE_COLS = {'a': ('a', 'b', 'c', 'd'), 'f': ('g', 'h', 'i', 'j')}
ROW_MAX = 63        # 이 보드는 63행이다 (라벨은 1·10·20…60 만 찍혀 있다)

# 전원 레일의 빈 행 — 여기서 끝난 배선은 갈 데가 없다.
RAIL_GAP_ROWS = frozenset(
    {1, 2, 8, 14, 20, 26, 32, 38, 44, 50, 56, 62, 63})  # 실측값. 풀어 쓴다 —
# 검사 코드가 소스를 ast 로 읽어 이 목록을 그대로 가져다 쓴다

# 배선 색은 넷뿐이다 — 16색 시절엔 구분 안 되는 쌍이 많았다. 입력 점퍼만 kind 'sig' 그대로
# 배지 색 `INPUT`(보라)으로 칠한다(2026-10-06) — 0/1 을 바꿀 때 옮기는 선이 한눈에 보인다. 펜은 다섯 자루.
WIRE = {
    'vcc': (200, 30, 30, 255),    # 빨강 — +5V
    'gnd': (30, 60, 200, 255),    # 파랑 — 0V(GND)
    'sig': (25, 25, 25, 255),     # 검정 — 출력·LED 쪽 신호(입력 점퍼는 INPUT 보라)
    'mid': (20, 130, 60, 255),    # 초록 — 칩과 칩 사이 중간 노드
}
KIND_KR = {'vcc': '+5V', 'gnd': '0V', 'sig': '신호', 'mid': '중간'}

# 앞 단계에서 그대로 두는 배선·부품 — 넷의 색이 아니라 표시라 `WIRE` 에 넣지 않는다.
KEEP = (165, 165, 165, 255)

# 걷기 보드에서 뽑는 배선 — footer 걷기 표와 같은 빨강, `WIRE` 밖(2026-09-18 실험03, 표에만 있어 놓쳤다).
REMOVE = (160, 30, 30, 255)

# 계측기 리드 — 배선이 아니라 집게로 문다. 회색 점선, 순서표도 '계측' 표에 따로.
PROBE = (105, 105, 110, 255)

# 따라 그리기 층 쪽에서 이번 층 신호선(sig·mid)에 선마다 주는 색 — 같은 색 점끼리 이으면 된다(2026-10-07
# 팀원 피드백 "선이 겹쳐 어디랑 이어지는지 모르겠다"). 빨강·파랑·보라·회색·검정은 넷 뜻이 있어 피하고,
# 이웃 순번끼리 색상이 크게 갈리게 줄 세웠다. 열 개를 넘는 층은 생성기(`trace_guide`)가 쪼개라고 멈춘다.
LAYER_PALETTE = (
    (230, 120, 0, 255),    # 주황
    (0, 150, 150, 255),    # 청록
    (200, 30, 150, 255),   # 자홍
    (120, 140, 0, 255),    # 올리브
    (40, 150, 220, 255),   # 하늘
    (140, 80, 30, 255),    # 갈색
    (240, 110, 170, 255),  # 분홍
    (30, 160, 60, 255),    # 초록
    (200, 160, 0, 255),    # 금색
    (150, 200, 40, 255),   # 연두
)


def _hex_color(c):
    """RGBA → '#rrggbb' — 사이드카·도장에 싣는 팔레트 색."""
    return '#{:02x}{:02x}{:02x}'.format(*c[:3])

# 입력 신호 이름 배지 — 다른 어느 색과도 안 겹치는 보라 바탕에 흰 화살촉·글자(2026-09-29 실험04,
# 흰 배지가 번호 원 사이에 묻혔다). 화살촉은 글리프가 아니라 다각형 — 기호 글리프는 □ 가 된다.
INPUT = (110, 40, 160, 255)
INPUT_TRI = 4.5   # 화살촉 폭. 좌 바깥 여백(v1 보드 테두리 149 ~ GND 레일 174 = 25px, v2 144 ~ 176 = 32px)에
                  # `D0` 배지가 들어가는 상한이다 — 글자 15 + 화살촉 4.5 + 틈 1 + 좌우 여백 1·1 = 22.5

# 단계 하나가 꽂는 새 신호선의 상한 — 확인이 실패하면 용의자가 그 셋이다(2026-09-20).
# 전원·레일 브리지·잭·LED 사슬 부품·칩 꽂기는 기반이라 세지 않는다.
STAGE_WIRE_BUDGET = 3

# 전원 잭 세 개의 중심 x (템플릿 상단). y 는 원 아래끝 근처.
JACKS = {'red': 439, 'yellow': 603, 'gray': 766}
JACK_BOTTOM = 160

JACK_KR = {'red': '빨강', 'yellow': '노랑', 'gray': '회색'}


def _boxes_touch(a, b):
    """두 상자 (x0, y0, x1, y1) 가 겹치는가. 걷기 번호 원 자리 잡기에 쓴다."""
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


# ---------------------------------------------------------------------------
# 판형 버전 — 버전마다 바뀌는 값을 `BoardSpec` 하나에 묶는다. 렌더러는 `self.spec` 만 읽고 분기하지 않는다.
# v1(실험01~04)의 숫자는 위 모듈 상수다(손그림 검토·시험이 읽는다). v2 는 `geometry.json` 에서만 읽는다 —
# 베껴 적으면 한쪽만 바뀐다. 설계: docs/plans/2026-10-02-브레드보드-v2-구조-설계.md

BOARD_VERSIONS = ('v1', 'v2')
# 실물 보드가 v2 다 — v1 주차는 `배치.py` 에 `BOARD = 'v1'` 을 적는다.
DEFAULT_BOARD = 'v2'

V2_GEOMETRY = os.path.join(REPO_ROOT, '.claude', 'assets', 'breadboard_v2', 'geometry.json')

# geometry.json 잭 이름 -> 렌더러 잭 키. 키는 v1 그대로 — `('jack', 'red')` 가 도장·손그림 문법에 들어 있다.
_V2_JACK_KEYS = {'+5V': 'red', 'yellow': 'yellow', '0V': 'gray'}

# v1 열 표 — `Breadboard.jpg` 실측(2026-09-07).
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
            # 가운데 레일은 두 블록이 같은 x 로 부른다 — 넷 단위가 ('rail', x) 라 한 넷이다
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
        # 입력선은 가운데 레일에서 왼쪽으로 뻗는다 — 배지는 반대쪽, 가운데 VCC 와 우 a 열 사이
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
