"""실험사진을 항목별로 한 장에 합성한다 (export-photo-sheet 스킬의 엔진).

`<실험NN>/실험사진/<항목> <입력비트>.jpg` (예: `1-1 000.jpg`, `3-1 11.jpg`) 를
항목마다 2열 격자로 묶어 `<실험NN>/실험사진/시트/` 에 JPEG 한 장씩 낸다.
타일마다 입력 조합과 LED 상태를 캡션으로 굽는다 — 캡션이 사진에 붙어 있으면
노션에 손으로 끼울 때 사진과 캡션이 어긋날 수 없다.

캡션의 LED 상태는 **`기록.md` 확인 칸**에서 온다:
  - `✓`   → 그 행의 예상값
  - 값    → 그 관찰값 (불일치 행)
  - 공란  → 거부한다. 시험하지 않은 행의 사진이 있다는 것은 파일명이나 기록 중
            하나가 틀렸다는 뜻이므로 조용히 만들지 않는다.

값을 켜짐·꺼짐으로 옮길 때는 LED 극성을 본다. 결선도 완성본 사이드카에 `0 이면 켜짐`
으로 적힌 출력(Active Low — 실험05 의 74HC42)은 `0` 이 켜짐이다. 극성은
`photo_label.led_order` 와 같은 곳에서 읽는다 — 두 곳이 따로 정하면 사진 이름과 캡션이
서로 반대로 갈린다(2026-10-09 실험05 1-2 시트 캡션이 전부 뒤집혀 나왔다).

노션 무료 플랜의 업로드 상한(5 MB)을 넘지 않도록 저장 후 크기를 검사한다.

사용:
    python -m scripts.lab.contact_sheet <실험번호> --check          # 파일명·기록 대조만. 문제 있으면 종료 코드 1
    python -m scripts.lab.contact_sheet <실험번호> --dry-run        # 캡션만 출력
    python -m scripts.lab.contact_sheet <실험번호>                  # 합성
    python -m scripts.lab.contact_sheet <실험번호> --only 2-1       # 한 항목만 다시
    python -m scripts.lab.contact_sheet <실험번호> --tile-width 800 # 타일 폭(기본 1000)
    python -m scripts.lab.contact_sheet <실험번호> --per-sheet 4    # 항목당 4장씩 여러 시트(_1, _2 …)
    python -m scripts.lab.contact_sheet <실험번호> --photo-dir DIR  # 사진 폴더 대체(시험용)
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import config, md
from .photo_names import FILE as _FILE, SIDE as _SIDE, item_token

DEFAULT_TILE_W = 1000    # 타일 폭(px). 타일 높이는 그 항목 사진의 비율에서 정한다
CAPTION_H = 72          # 한 줄 캡션 띠 높이. 줄이 늘면 _caption_height 가 키운다
CAPTION_PAD = 20        # 캡션 좌우 여백
GAP = 0                  # 타일 사이 여백. 2026-09-18 실험03 시트에서 사용자가 없앴다
MAX_BYTES = 5 * 1024 * 1024
COLS = 2

_PHOTO_EXT = {".jpg", ".jpeg", ".png"}
_ITEM_HEADING = re.compile(r"^##\s+(?P<id>E\d+\.P[\w-]+)\s+·\s+(?P<title>.+)$")

_FONT_CANDIDATES = (
    r"C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
)


class ContactSheetError(RuntimeError):
    pass


@dataclass
class ItemRecord:
    id: str
    title: str
    token: str          # `1-1`, `3` — 제목의 `실험 N)` 에서 뽑은 것
    inputs: list        # ['A', 'B', 'C']
    outputs: list       # ['L1', 'L2']
    rows: dict          # bits -> (expected list, check cell)


@dataclass
class Plan:
    """항목 하나의 합성 계획. `problems` 가 비어 있어야 만든다."""
    token: str
    record: ItemRecord | None
    out: Path
    photos: list = field(default_factory=list)      # [(bits, Path)]
    captions: list = field(default_factory=list)    # photos 와 같은 순서
    problems: list = field(default_factory=list)    # 문자열


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise ContactSheetError(
        "한글 글꼴을 찾지 못했다. 후보: " + ", ".join(_FONT_CANDIDATES))


def _slug(title: str) -> str:
    """`실험 1-1) 3-input AND gate` → `3입력_AND`. 손그림 파일명 규칙과 맞춘다."""
    name = title.split(")", 1)[1] if ")" in title else title
    name = re.sub(r"(\d)-input", r"\1입력", name)
    name = re.sub(r"\bgate\b", "", name, flags=re.I)
    name = re.sub(r"([가-힣])\s+([가-힣])", r"\1\2", name)   # 복합 논리회로 → 복합논리회로
    name = re.sub(r"[()]", "", name)   # 괄호가 남으면 md 그림 링크 `](…)` 가 거기서 끊긴다(실험05 1-2 제목)
    return re.sub(r"\s+", "_", name.strip())


def load_records(record_path: Path) -> list[ItemRecord]:
    """기록.md 에서 항목별 표(입력 열·출력 열·확인 칸)를 읽는다."""
    text = record_path.read_text(encoding="utf-8")
    _, body = md.split_frontmatter(text)
    lines = body.split("\n")
    heads = [(i, m) for i, ln in enumerate(lines) if (m := _ITEM_HEADING.match(ln))]
    tables = md.parse_tables(body)
    out = []
    for n, (i, m) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        tbl = next((t for t in tables if i < t.line - 1 < end), None)
        if tbl is None:
            continue
        header = [h.strip() for h in tbl.header]
        if header[-1] != "확인":
            continue
        inputs = [h for h in header[:-1] if not h.endswith("예상")]
        outputs = [h[:-2] for h in header[:-1] if h.endswith("예상")]
        rows = {}
        for r in tbl.rows:
            cells = [c.strip() for c in r]
            bits = "".join(cells[: len(inputs)])
            rows[bits] = (cells[len(inputs): len(inputs) + len(outputs)], cells[-1])
        out.append(ItemRecord(
            id=m.group("id"), title=m.group("title").strip(),
            token=item_token(m.group("title")) or "", inputs=inputs, outputs=outputs, rows=rows))
    return out


def _match_item(token: str, records: list[ItemRecord]) -> ItemRecord | None:
    for r in records:
        if r.token == token:
            return r
    head = token.split("-")[0]
    hits = [r for r in records if r.token == head]
    return hits[0] if len(hits) == 1 else None


def _caption(rec: ItemRecord, bits: str, active_low: frozenset = frozenset()) -> str:
    if len(bits) != len(rec.inputs):
        raise ContactSheetError(
            f"입력이 {len(rec.inputs)}개인데 파일명 비트가 `{bits}` 다")
    if bits not in rec.rows:
        raise ContactSheetError(f"기록.md 에 `{bits}` 행이 없다")
    expected, check = rec.rows[bits]
    if not check:
        raise ContactSheetError(
            f"`{bits}` 확인 칸이 비어 있다(시험하지 않은 행) — "
            "파일명이나 기록.md 중 하나가 틀렸다. 캡션을 지어내지 않는다")
    if check == "✓":
        states = expected
    else:
        vals = re.findall(r"[01]", check)
        if len(vals) != len(rec.outputs):
            raise ContactSheetError(
                f"`{bits}` 확인 칸 `{check}` 에서 출력 {len(rec.outputs)}개를 읽지 못했다")
        states = vals
    ins = " ".join(f"{n}={b}" for n, b in zip(rec.inputs, bits))
    on = {n: ("0" if n in active_low else "1") for n in rec.outputs}
    outs = " · ".join(f"{n} {'켜짐' if s == on[n] else '꺼짐'}" for n, s in zip(rec.outputs, states))
    return f"{ins}  →  {outs}"


def _active_low(experiment: int, token: str) -> frozenset:
    """그 항목에서 `0` 이 켜짐인 출력 이름들. 사이드카가 없으면 전부 Active High 로 본다."""
    from .photo_label import LabelError, led_order
    try:
        return frozenset(l.signal for l in led_order(experiment, token) if l.active_low)
    except LabelError:
        return frozenset()


def plan(experiment: int, photo_dir: Path | None = None,
         only: str | None = None) -> tuple[list[Plan], list[str], list[str]]:
    """합성 계획을 세운다. 파일을 만들지 않는다.

    반환: (항목별 Plan 목록, 어느 항목에도 속하지 않는 문제 목록 — 규칙 밖 파일명 등,
          건너뛴 스텝표·파형 사진 파일명 목록 — 문제로 세지 않는다)
    """
    exp_dir = Path(config.experiment_dir(experiment))
    photo_dir = photo_dir or exp_dir / "실험사진"
    record = exp_dir / "체크리스트" / "기록.md"
    if not record.exists():
        raise ContactSheetError(f"{record} 가 없다")
    if not photo_dir.is_dir():
        raise ContactSheetError(f"{photo_dir} 가 없다")
    records = load_records(record)

    loose: list[str] = []
    skipped: list[str] = []
    groups: dict[str, list[tuple[str, Path]]] = {}
    for p in sorted(photo_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in _PHOTO_EXT:
            continue
        m = _FILE.match(p.name)
        if not m:
            if _SIDE.match(p.name):
                skipped.append(p.name)
                continue         # 스텝표·파형 사진 — 시트 대상이 아니다(결과보고서가 따로 싣는다)
            loose.append(f"파일명이 `<항목> <입력비트>.jpg` 규칙 밖: {p.name}")
            continue
        groups.setdefault(m.group("item"), []).append((m.group("bits"), p))
    if not groups and not loose:
        raise ContactSheetError(
            f"{photo_dir} 에 시트로 묶을 사진(`<항목> <입력비트>.jpg`)이 없다")

    plans = []
    for token, photos in groups.items():
        if only and token != only:
            continue
        rec = _match_item(token, records)
        photos.sort(key=lambda t: t[0])
        out = photo_dir / "시트" / (
            f"{exp_dir.name}_{rec.token}_사진_{_slug(rec.title)}.jpg" if rec else f"{exp_dir.name}_{token}_사진.jpg")
        pl = Plan(token=token, record=rec, out=out, photos=photos)
        if rec is None:
            pl.problems.append(f"항목 토큰 `{token}` 에 맞는 기록.md 항목이 없다")
        else:
            low = _active_low(experiment, rec.token)
            seen = set()
            for bits, p in photos:
                if bits in seen:
                    pl.problems.append(f"{p.name}: `{bits}` 조합 사진이 둘 이상이다")
                seen.add(bits)
                try:
                    pl.captions.append(_caption(rec, bits, low))
                except ContactSheetError as e:
                    pl.problems.append(f"{p.name}: {e}")
                    pl.captions.append(None)
        plans.append(pl)
    if only and not plans:
        raise ContactSheetError(f"`--only {only}` 에 해당하는 사진이 없다")
    return plans, loose, skipped


def _wrap(caption: str, font, tile_w: int) -> list[str]:
    """타일 폭에 안 들어가면 ` · ` 자리에서 줄을 바꾼다 — 출력이 열 개인 표(실험05 1-2)는
    한 줄 캡션이 타일 폭의 두 배라 뒤가 잘렸다(2026-10-09)."""
    width = tile_w - 2 * CAPTION_PAD
    lines: list[str] = []
    for piece in caption.split(" · "):
        if lines and font.getlength(lines[-1] + " · " + piece) <= width:
            lines[-1] += " · " + piece
        else:
            lines.append(piece)
    return lines


def _caption_height(lines: int, font) -> int:
    return CAPTION_H + (lines - 1) * round(font.size * 1.35)


def _tile(path: Path, caption: str, font, tile_w: int, tile_h: int, cap_h: int) -> Image.Image:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((tile_w, tile_h))
    tile = Image.new("RGB", (tile_w, tile_h + cap_h), "white")
    tile.paste(im, ((tile_w - im.width) // 2, cap_h + (tile_h - im.height) // 2))
    d = ImageDraw.Draw(tile)
    d.rectangle((0, 0, tile_w, cap_h), fill=(30, 30, 30))
    for k, line in enumerate(_wrap(caption, font, tile_w)):
        tw = d.textlength(line, font=font)
        d.text(((tile_w - tw) / 2, 14 + k * round(font.size * 1.35)), line, fill="white", font=font)
    return tile


def _save_under_limit(sheet: Image.Image, out: Path) -> int:
    for q in (85, 80, 72, 65, 55):
        sheet.save(out, "JPEG", quality=q, optimize=True)
        size = out.stat().st_size
        if size <= MAX_BYTES:
            return size
    raise ContactSheetError(f"{out.name}: 품질을 낮춰도 5 MB 를 넘는다 ({size} B)")


def _tile_height(photos: list, tile_w: int) -> int:
    """그 항목 사진들의 세로/가로 비율 최대값으로 타일 높이를 정한다 — 정사각 사진에
    4:3 타일을 주면 위아래에 흰 띠가 남는다(2026-09-18 실험03에서 사용자가 지적)."""
    ratio = 0.0
    for _, p in photos:
        with Image.open(p) as im:
            w, h = ImageOps.exif_transpose(im).size
        ratio = max(ratio, h / w)
    return round(tile_w * ratio)


def _sheet_outputs(pl: Plan, per_sheet: int | None) -> list[tuple[Path, list, list]]:
    """Plan 하나를 시트 단위로 쪼갠다. `per_sheet` 가 없으면 한 장, 있으면 그 수만큼
    묶어 `_1`, `_2` … 접미어를 붙인다."""
    n = len(pl.photos)
    if not per_sheet or per_sheet >= n:
        return [(pl.out, pl.photos, pl.captions)]
    chunks = []
    for i in range(0, n, per_sheet):
        k = i // per_sheet + 1
        out = pl.out.with_name(f"{pl.out.stem}_{k}{pl.out.suffix}")
        chunks.append((out, pl.photos[i:i + per_sheet], pl.captions[i:i + per_sheet]))
    return chunks


def build(plans: list[Plan], tile_w: int = DEFAULT_TILE_W,
          per_sheet: int | None = None) -> list[tuple[Path, int]]:
    """문제 없는 Plan 만 합성한다. 문제 있는 Plan 이 하나라도 있으면 아무것도 만들지 않는다.

    `per_sheet` 를 주면 항목 하나를 그 수만큼씩 여러 장으로 나눈다(예: 8장을 4장씩 두 장)."""
    bad = [p for p in plans if p.problems]
    if bad:
        raise ContactSheetError(
            "대조에 실패한 항목이 있어 합성하지 않는다: " + ", ".join(p.token for p in bad))
    font = _font(round(tile_w * 0.03))
    results = []
    for pl in plans:
        pl.out.parent.mkdir(exist_ok=True)
        tile_h = _tile_height(pl.photos, tile_w)
        cap_h = _caption_height(max(len(_wrap(c, font, tile_w)) for c in pl.captions), font)
        th = tile_h + cap_h
        for out, photos, captions in _sheet_outputs(pl, per_sheet):
            rows = -(-len(photos) // COLS)
            sheet = Image.new("RGB", (COLS * tile_w + (COLS + 1) * GAP, rows * th + (rows + 1) * GAP), "white")
            for k, ((_, p), cap) in enumerate(zip(photos, captions)):
                x = GAP + (k % COLS) * (tile_w + GAP)
                y = GAP + (k // COLS) * (th + GAP)
                sheet.paste(_tile(p, cap, font, tile_w, tile_h, cap_h), (x, y))
            results.append((out, _save_under_limit(sheet, out)))
    return results


def _print_check(plans: list[Plan], loose: list[str], skipped: list[str]) -> int:
    n_bad = len(loose) + sum(len(p.problems) for p in plans)
    print("| 항목 | 사진 수 | 문제 |")
    print("|---|---|---|")
    for pl in plans:
        print(f"| {pl.token} | {len(pl.photos)} | {'; '.join(pl.problems) or '없음'} |")
    for msg in loose:
        print(f"| – | – | {msg} |")
    if skipped:      # 알림일 뿐 문제가 아니다 — n_bad 에 세지 않는다
        print(f"\n건너뜀 (스텝표·파형 사진 — 시트 대상 아님): {len(skipped)}장 — {', '.join(skipped)}")
    print(f"\n대조 결과: 문제 {n_bad}건")
    return 1 if n_bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("experiment", type=int)
    ap.add_argument("--check", action="store_true", help="파일명·기록 대조만 하고 표로 보고한다")
    ap.add_argument("--dry-run", action="store_true", help="캡션만 출력하고 파일을 만들지 않는다")
    ap.add_argument("--only", metavar="항목", help="이 항목 토큰(예: 2-1)만 다룬다")
    ap.add_argument("--tile-width", type=int, default=DEFAULT_TILE_W, metavar="PX")
    ap.add_argument("--per-sheet", type=int, metavar="N",
                    help="항목 하나를 사진 N장씩 여러 장으로 나눈다(파일명에 _1, _2 … 가 붙는다)")
    ap.add_argument("--photo-dir", type=Path, help="사진 폴더를 대체한다(시험용)")
    a = ap.parse_args(argv)
    try:
        plans, loose, skipped = plan(a.experiment, a.photo_dir, a.only)
        if a.check:
            return _print_check(plans, loose, skipped)
        if loose:
            for msg in loose:
                print("오류:", msg, file=sys.stderr)
            return 1
        for pl in plans:
            print(pl.out)
            for (bits, p), cap in zip(pl.photos, pl.captions):
                print(f"    {p.name:14s} {cap or '(캡션 없음)'}")
            for msg in pl.problems:
                print("    오류:", msg)
        if a.dry_run:
            return 1 if any(p.problems for p in plans) else 0
        for out, size in build(plans, a.tile_width, a.per_sheet):
            print(f"저장 {out}  {size // 1024} KB")
    except ContactSheetError as e:
        print("오류:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
