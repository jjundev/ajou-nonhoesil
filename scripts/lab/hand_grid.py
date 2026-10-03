"""손그림 PDF 의 판형 좌표를 렌더러 좌표표에 맞춘다.

**사람이 좌표를 뜨지 않는다.** 배포본 판형은 정본 `Breadboard.jpg` 와 같은
그림인데 가로가 중앙 기준 5% 넓다 — `breadboard-diagram/SKILL.md` §2 가
"갈아끼우면 결선이 옆 홀에 그려지는데, 그림 자체는 멀쩡해 보여서 눈으로는 안
잡힌다"고 적어 둔 그 차이다. 눈대중 상수를 새로 만들면 같은 사고가 반복된다.

대신 이렇게 한다.

1. 손그림 PDF 의 각 쪽에는 판형 래스터가 **이미지로** 박혀 있고, 놓인 자리도
   PDF 안에 있다. 잉크가 없는 깨끗한 판형을 그대로 꺼낸다.
2. 그 래스터에서 홀 열·행을 검출한다.
3. 검출된 열(v1 28개·v2 26개)·행 63개를 그 판형 렌더러 좌표표에 순서대로 짝지어 축마다
   1차식을 맞춘다. 균일 가로 확대는 1차식이 정확히 흡수한다. 판형은 승인 결선의 것을
   받는다(`expected_board()`) — 검출에서 추측하지 않는다.
4. 잔차가 3px 를 넘으면 중단한다. 판형이 바뀐 것이다.

쪽 크기로 막지 않는 이유: 학생 PDF 는 필기 앱 내보내기라 1210x834pt 이고
배포본은 A4 594x841pt 다. 쪽 크기를 보면 정상 제출물을 거절한다. 기하를 본다.
"""

import hashlib
import importlib.util
import io
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERER = (REPO_ROOT / ".claude/skills/breadboard-diagram/scripts"
            / "render_breadboard.py")

# 판형 한 장에 있는 홀 열과 행. 렌더러 좌표표가 정하는 값이라 여기서 세지
# 않고 맞춰만 본다 — 검출이 이 수와 다르면 판형이 다른 것이다. v2 는 가운데
# 레일이 2열 하나라 26열이다
EXPECTED_COLS = {'v1': 28, 'v2': 26}
EXPECTED_ROWS = 63

# 잔차 한계. 렌더러 `hole_at()` 의 홀 허용치가 5px 이므로 그보다 넉넉히 안쪽
MAX_RESIDUAL = 3.0

_renderer = None


class GridError(ValueError):
    """판형을 못 읽었거나 좌표가 안 맞는다."""


def load_renderer():
    """렌더러 모듈. 스킬 폴더 안에 있어 import 경로에 없다."""
    global _renderer
    if _renderer is None:
        spec = importlib.util.spec_from_file_location(
            "render_breadboard", str(RENDERER))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _renderer = mod
    return _renderer


@dataclass
class BoardImage:
    md5: str
    width: int
    height: int
    rect: tuple      # 쪽 안에서 놓인 자리 (x0, y0, x1, y1) — 포인트 단위
    data: bytes      # 원본 래스터 바이트


@dataclass
class Calibration:
    ax: float
    bx: float
    ay: float
    by: float
    res_x: float
    res_y: float
    rect: tuple
    board_size: tuple
    dpi: int
    version: str = 'v1'   # 이 보정이 맞춘 판형

    def to_px(self, x, y):
        """렌더러 좌표 -> 그 쪽을 dpi 로 그렸을 때의 픽셀.

        렌더러 좌표 -> 판형 래스터 픽셀 -> 쪽 포인트 -> 렌더 픽셀 순으로 간다.
        """
        w, h = self.board_size
        x0, y0, x1, y1 = self.rect
        ix = self.ax * x + self.bx
        iy = self.ay * y + self.by
        pt_x = x0 + ix / w * (x1 - x0)
        pt_y = y0 + iy / h * (y1 - y0)
        s = self.dpi / 72.0
        return (pt_x * s, pt_y * s)


def board_image(pdf_path, page_index=0):
    """그 쪽에 깔린 판형 래스터와 놓인 자리.

    가장 넓게 깔린 이미지를 판형으로 본다. 학생이 사진을 덧붙였더라도 판형이
    쪽 대부분을 차지하기 때문이다.
    Microsoft: Print To PDF 처럼 세로로 쪼개져 박힌 판형은 위에서 아래로 이어붙인다.
    """
    import fitz
    from PIL import Image

    doc = fitz.open(str(pdf_path))
    try:
        if not 0 <= page_index < len(doc):
            raise GridError(
                f"{Path(pdf_path).name} 에 {page_index + 1}쪽이 없다 "
                f"(전체 {len(doc)}쪽)")
        page = doc[page_index]
        tiles = []
        for img in page.get_images(full=True):
            xref = img[0]
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            r = max(rects, key=lambda rr: rr.width * rr.height)
            tiles.append((r, xref))
        if not tiles:
            raise GridError(
                f"{Path(pdf_path).name} {page_index + 1}쪽에 판형 이미지가 없다. "
                "배포본 판형 위에 그린 PDF 만 검토한다")

        # 페이지 너비의 상당 부분을 차지하는 판형 후보 타일들을 먼저 거른다.
        # 학생이 덧붙인 사진·스탬프(작은 너비)가 타일 판정(all)을 깨뜨리지 않게 한다.
        min_board_w = min(400.0, page.rect.width * 0.6)
        cand_tiles = [t for t in tiles if t[0].width >= min_board_w]
        if not cand_tiles:
            cand_tiles = tiles

        cand_tiles.sort(key=lambda t: t[0].y0)
        is_tiled = len(cand_tiles) > 1 and all(
            abs(cand_tiles[i][0].x0 - cand_tiles[0][0].x0) < 5 and
            abs(cand_tiles[i][0].x1 - cand_tiles[0][0].x1) < 5
            for i in range(len(cand_tiles))
        )
        if is_tiled:
            extracted = [doc.extract_image(xref) for _, xref in cand_tiles]
            total_w = max(info["width"] for info in extracted)
            total_h = sum(info["height"] for info in extracted)
            stitched = Image.new("RGB", (total_w, total_h))
            cur_y = 0
            for info in extracted:
                part = Image.open(io.BytesIO(info["image"]))
                stitched.paste(part, (0, cur_y))
                cur_y += info["height"]
            buf = io.BytesIO()
            stitched.save(buf, format="PNG")
            data = buf.getvalue()
            min_x0 = min(t[0].x0 for t in cand_tiles)
            min_y0 = min(t[0].y0 for t in cand_tiles)
            max_x1 = max(t[0].x1 for t in cand_tiles)
            max_y1 = max(t[0].y1 for t in cand_tiles)
            rect = (min_x0, min_y0, max_x1, max_y1)
            return BoardImage(
                md5=hashlib.md5(data).hexdigest(),
                width=total_w,
                height=total_h,
                rect=rect,
                data=data,
            )
        else:
            best = max(cand_tiles, key=lambda t: t[0].width * t[0].height)
            rect, xref = best
            info = doc.extract_image(xref)
            return BoardImage(
                md5=hashlib.md5(info["image"]).hexdigest(),
                width=info["width"],
                height=info["height"],
                rect=(rect.x0, rect.y0, rect.x1, rect.y1),
                data=info["image"],
            )
    finally:
        doc.close()


def _runs(profile, threshold):
    """문턱을 넘는 구간들의 (시작, 끝) 목록."""
    out, i, n = [], 0, len(profile)
    while i < n:
        if profile[i] >= threshold:
            j = i
            while j < n and profile[j] >= threshold:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _merge_to_count(runs, expected):
    """이웃한 구간을 붙여 개수가 `expected` 가 되는 중심 목록.

    홀은 **작은 사각 테두리**로 그려져 있어 구간이 홀마다 둘씩(왼쪽 변,
    오른쪽 변) 나온다. 붙이는 간격을 0 부터 키우면서 개수가 맞는 지점을
    찾는다 — 결과가 결정적이고, 못 맞추면 소리를 낸다.
    """
    if not runs:
        raise GridError("홀을 하나도 못 찾았다")
    span = runs[-1][1] - runs[0][0]
    for gap in range(0, max(2, int(span / expected)) + 2):
        merged, cur = [], list(runs[0])
        for a, b in runs[1:]:
            if a - cur[1] <= gap:
                cur[1] = b
            else:
                merged.append(tuple(cur))
                cur = [a, b]
        merged.append(tuple(cur))
        if len(merged) == expected:
            return [(a + b) / 2.0 for a, b in merged]
    raise GridError(
        f"홀 {expected}개로 정리되지 않는다 (구간 {len(runs)}개). "
        "판형이 바뀌었거나 해상도가 모자란다")


def detect_grid(data, version='v1'):
    """판형 래스터에서 홀 열 중심 x 들과 행 중심 y 들.
    `version` 판형의 열 수로 모은다 — 다른 판형이면 개수가 안 맞거나 맞아도 잔차가 크다.

    잉크가 없는 원본 래스터를 본다 — 학생 필기는 PDF 의 다른 층에 있다.
    """
    from PIL import Image

    im = Image.open(io.BytesIO(data)).convert("L")
    w, h = im.size
    px = im.load()
    # 위쪽 전원 잭 영역/상단 경계선과 아래 여백을 뺀 몸통만 본다
    y0, y1 = int(h * 0.19), int(h * 0.965)
    x0, x1 = int(w * 0.02), int(w * 0.98)

    span = x1 - x0
    row_prof = [sum(1 for x in range(x0, x1) if px[x, y] < 140)
                for y in range(y0, y1)]
    # 인쇄된 판형 테두리·구분선을 뺀다. 실측(2026-09-09): 홀 행은 폭의
    # 0.29~0.33 까지만 어둡고 테두리는 0.70 이다. 0.45 는 그 사이다.
    # **열 쪽은 이 방법을 못 쓴다** — 홀 열은 모든 행에 홀이 있어 세로로
    # 0.95~1.0 까지 차서 인쇄된 레일선과 안 갈린다. 그래서 열은 폭으로 거른다
    # (아래 `col_runs` 의 `r[1] - r[0] >= 4`).
    row_prof = [v if v <= 0.45 * span else 0 for v in row_prof]
    rows = _merge_to_count(_runs(row_prof, max(row_prof) * 0.35),
                           EXPECTED_ROWS)

    # 열 프로파일: 3px 간격으로 훑되, 인쇄된 얇은 레일선(폭 2~3px)은 폭으로 걸러낸다
    col_prof = [0] * w
    for y in range(y0, y1, 3):
        for x in range(w):
            if px[x, y] < 140:
                col_prof[x] += 1

    col_runs = [r for r in _runs(col_prof, max(col_prof) * 0.12) if r[1] - r[0] >= 4]
    cols = _merge_to_count(col_runs, EXPECTED_COLS[version])

    return cols, [y + y0 for y in rows]


def _fit(src, dst):
    """dst = a*src + b 최소제곱. (a, b, 최대 잔차) 를 준다."""
    n = len(src)
    ms, md = sum(src) / n, sum(dst) / n
    num = sum((s - ms) * (d - md) for s, d in zip(src, dst))
    den = sum((s - ms) ** 2 for s in src)
    if den == 0:
        raise GridError("맞출 좌표가 한 점뿐이다")
    a = num / den
    b = md - a * ms
    res = max(abs(a * s + b - d) for s, d in zip(src, dst))
    return a, b, res


def _fit_version(board, version, dpi):
    """`version` 판형의 렌더러 좌표표로 맞춘 보정. 검출이 그 판형 열 수로 안 모이면 `GridError`."""
    mod = load_renderer()
    spec = mod.board_spec(version)
    cols, rows = detect_grid(board.data, version)
    ref_cols = sorted(_reference_cols(mod, version))
    ref_rows = [spec.row0 + (r - 1) * spec.row_pitch for r in range(1, mod.ROW_MAX + 1)]
    ax, bx, res_x = _fit(ref_cols, cols)
    ay, by, res_y = _fit(ref_rows, rows)
    return Calibration(ax, bx, ay, by, res_x, res_y, board.rect,
                       (board.width, board.height), dpi, version)


def _fits(cal):
    return cal.res_x <= MAX_RESIDUAL and cal.res_y <= MAX_RESIDUAL


def _try_fit(board, version, dpi):
    """맞으면 보정, 검출이 안 되거나 잔차가 크면 None."""
    try:
        cal = _fit_version(board, version, dpi)
    except GridError:
        return None
    return cal if _fits(cal) else None


def calibrate(board, version='v1', dpi=300):
    """검출한 격자를 `version` 판형의 렌더러 좌표표에 맞춘다.

    `version` 은 **승인 결선의 판형**이다(`expected_board()`). 그 판형으로 안 맞으면 다른
    판형으로도 맞춰 보되 **진단만 한다** — 맞으면 "판형 버전 불일치" 로 멈추고, 그 판형으로
    계속 가지 않는다. 학생이 다른 배포본 위에 그렸으면 다시 그려야 한다. 검출은 열 수를
    억지로 맞추므로(`_merge_to_count`) 열 수만으로는 판형을 못 가른다.
    """
    mod = load_renderer()
    cal = _try_fit(board, version, dpi)
    if cal is not None:
        return cal
    for other in mod.BOARD_VERSIONS:
        if other != version and _try_fit(board, other, dpi) is not None:
            raise GridError(
                f"판형 버전 불일치 — 승인 결선은 {version} 판형인데 제출 PDF 는 {other} 판형 "
                f"위에 그렸다. {version} 배포본 위에 다시 그려야 한다")
    cal = _fit_version(board, version, dpi)   # 검출 실패면 그 GridError 가 그대로 난다
    raise GridError(
        f"판형이 렌더러 좌표표와 맞지 않는다 "
        f"(가로 잔차 {cal.res_x:.1f}px, 세로 {cal.res_y:.1f}px, 한계 {MAX_RESIDUAL}). "
        "다른 판형 위에 그렸거나 판형이 바뀌었다")


def _reference_cols(mod, version='v1'):
    """렌더러가 아는 홀 열 x 들 — `version` 판형. 칩 몸통 경계는 홀이 아니다.

    숫자를 베껴 적지 않는다 — 렌더러 `column_table()` 이 유일한 권위다. 두 블록이 같은 x 로
    부르는 v2 가운데 레일은 한 번만 나와 26 이 된다.
    """
    return list(mod.column_table(version))


# 오버레이 색. 격자선은 **읽는 보조선**이지 판정 근거가 아니다 — 손그림 잉크
# (빨강·파랑·검정·초록)와 겹치지 않는 자홍/하늘로 골라 눈이 헷갈리지 않게 한다
GRID_ROW = (255, 0, 255, 70)
GRID_COL = (0, 160, 255, 60)
GRID_TEXT_ROW = (200, 0, 200, 255)
GRID_TEXT_COL = (0, 90, 200, 255)


def render_page(pdf_path, page_index=0, dpi=300):
    """그 쪽을 dpi 로 그린 이미지."""
    import fitz
    from PIL import Image

    doc = fitz.open(str(pdf_path))
    try:
        if not 0 <= page_index < len(doc):
            raise GridError(
                f"{Path(pdf_path).name} 에 {page_index + 1}쪽이 없다 "
                f"(전체 {len(doc)}쪽)")
        pix = doc[page_index].get_pixmap(dpi=dpi)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def _col_names(mod, version='v1'):
    """(블록, 열) -> 렌더러 x. 오버레이 라벨과 크롭이 함께 쓴다. 두 블록이 같이 쓰는 열(v2
    가운데 레일)은 `left` 로 한 번만 나온다."""
    return {name: x for x, name in mod.column_table(version).items()}


_SHORT = {'gnd': 'G-', 'vcc': 'V+', 'mid_gnd': 'g-', 'mid_vcc': 'v+'}


def overlay_grid(page_im, cal, out_path, max_row=35):
    """행 번호·열 이름·레일 빈 행을 반투명으로 덮은 그림.

    Claude 가 끝점을 읽는 **보조선**이다. 사람이 눈금을 세지 않게 하려고
    있는 것이지, 이 그림으로 판정하지 않는다 — 판정은 전사 파일로 한다.
    """
    from PIL import Image, ImageDraw, ImageFont

    mod = load_renderer()
    spec = mod.board_spec(cal.version)
    shared = mod.shared_columns(cal.version)
    im = page_im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
    except OSError:
        font = ImageFont.load_default()

    names = _col_names(mod, cal.version)
    xs = [cal.to_px(x, spec.row0)[0] for x in names.values()]
    x_lo, x_hi = min(xs), max(xs)

    for r in range(1, min(max_row, mod.ROW_MAX) + 1):
        y = cal.to_px(0, spec.row0 + (r - 1) * spec.row_pitch)[1]
        d.line([(x_lo - 60, y), (x_hi + 20, y)], fill=GRID_ROW, width=1)
        label = f'{r} gap' if r in mod.RAIL_GAP_ROWS else str(r)
        d.text((x_lo - 58, y - 10), label, fill=GRID_TEXT_ROW, font=font)

    y_top = cal.to_px(0, spec.row0)[1]
    y_bot = cal.to_px(0, spec.row0 + (min(max_row, mod.ROW_MAX) - 1)
                      * spec.row_pitch)[1]
    for (block, key), x in names.items():
        px = cal.to_px(x, spec.row0)[0]
        d.line([(px, y_top - 30), (px, y_bot)], fill=GRID_COL, width=1)
        tag = _SHORT.get(key, key)
        # 두 블록이 나눠 쓰는 열(v2 가운데 레일)은 좌·우가 없다 — 렌더러 주소도 접두어가 없다
        prefix = '' if x in shared else ('좌' if block == 'left' else '우')
        d.text((px - 9, y_top - 52), f'{prefix}{tag}',
               fill=GRID_TEXT_COL, font=font)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    Image.alpha_composite(im, ov).convert("RGB").save(out_path)
    return out_path


def crop_rows(page_im, cal, row_from, row_to, out_path, scale=3, block=None):
    """행 범위를 잘라 확대한다. 치명 결함의 증거로 쓴다."""
    from PIL import Image

    if row_to <= row_from:
        raise GridError(f"행 범위가 거꾸로다: {row_from} -> {row_to}")
    mod = load_renderer()
    spec = mod.board_spec(cal.version)
    names = _col_names(mod, cal.version)
    if block:
        # 두 블록이 나눠 쓰는 열(v2 가운데 레일)은 소속이 left 라도 우 블록 크롭에 넣는다 —
        # 우 LED 사슬의 GND 가 거기 꽂힌다
        shared = mod.shared_columns(cal.version)
        names = {k: v for k, v in names.items() if k[0] == block or v in shared}
    xs = [cal.to_px(x, spec.row0)[0] for x in names.values()]
    y0 = cal.to_px(0, spec.row0 + (row_from - 1) * spec.row_pitch)[1]
    y1 = cal.to_px(0, spec.row0 + (row_to - 1) * spec.row_pitch)[1]
    box = (max(0, int(min(xs) - 80)), max(0, int(y0 - 20)),
           min(page_im.width, int(max(xs) + 40)),
           min(page_im.height, int(y1 + 20)))
    c = page_im.crop(box)
    c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    c.save(out_path)
    return out_path


def expected_board(experiment):
    """그 주차 승인 결선의 판형 — `배치.py` 의 `BOARD`(없으면 v1).

    격자 보정은 전사보다 먼저라 회로 ID 를 모른다. 한 주차의 회로는 판형이 같으므로 주차
    결선 파일에서 읽는다 — 사이드카의 `board` 도 같은 값에서 나온다.
    """
    mod = load_renderer()
    return mod.board_version(mod.load_board(experiment))
