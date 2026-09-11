"""실험사진을 항목별로 한 장에 합성한다 (④ write-result-report §사진 배치).

`<실험NN>/실험사진/<항목> <입력비트>.jpg` (예: `1-1 000.jpg`, `3-1 11.jpg`) 를
항목마다 2열 격자로 묶어 `<실험NN>/실험사진/시트/` 에 JPEG 한 장씩 낸다.
타일마다 입력 조합과 LED 상태를 캡션으로 굽는다 — 캡션이 사진에 붙어 있으면
노션에 손으로 끼울 때 사진과 캡션이 어긋날 수 없다.

캡션의 LED 상태는 **`기록.md` 확인 칸**에서 온다:
  - `✓`   → 그 행의 예상값
  - 값    → 그 관찰값 (불일치 행)
  - 공란  → 거부한다. 시험하지 않은 행의 사진이 있다는 것은 파일명이나 기록 중
            하나가 틀렸다는 뜻이므로 조용히 만들지 않는다.

노션 무료 플랜의 업로드 상한(5 MB)을 넘지 않도록 저장 후 크기를 검사한다.

사용:
    python -m scripts.lab.contact_sheet <실험번호> [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import config, md

TILE_W = 1000            # 타일 폭(px). 세로 사진이면 1000×1333
TILE_H = 1333
CAPTION_H = 72
GAP = 24
MAX_BYTES = 5 * 1024 * 1024
COLS = 2

_FILE = re.compile(r"^(?P<item>[\d]+(?:-[\d]+)?)\s+(?P<bits>[01]+)\.(?:jpe?g|png)$", re.I)
_ITEM_HEADING = re.compile(r"^##\s+(?P<id>E\d+\.P[\w-]+)\s+·\s+(?P<title>.+)$")
_ITEM_TOKEN = re.compile(r"실험\s*(?P<tok>\d+(?:-\d+)?)\)")

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
        # 표 구분선 줄 번호(1-based)가 이 항목 구간에 드는 첫 표
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
        tok = _ITEM_TOKEN.search(m.group("title"))
        out.append(ItemRecord(
            id=m.group("id"), title=m.group("title").strip(),
            token=tok.group("tok") if tok else "", inputs=inputs, outputs=outputs, rows=rows))
    return out


def _match_item(token: str, records: list[ItemRecord]) -> ItemRecord:
    for r in records:
        if r.token == token:
            return r
    head = token.split("-")[0]
    hits = [r for r in records if r.token == head]
    if len(hits) == 1:
        return hits[0]
    raise ContactSheetError(f"사진 파일의 항목 토큰 `{token}` 에 맞는 기록.md 항목이 없다")


def _caption(rec: ItemRecord, bits: str) -> str:
    if len(bits) != len(rec.inputs):
        raise ContactSheetError(
            f"{rec.title}: 입력이 {len(rec.inputs)}개인데 파일명 비트가 `{bits}` 다")
    if bits not in rec.rows:
        raise ContactSheetError(f"{rec.title}: 기록.md 에 `{bits}` 행이 없다")
    expected, check = rec.rows[bits]
    if not check:
        raise ContactSheetError(
            f"{rec.title} `{bits}`: 확인 칸이 비어 있다(시험하지 않은 행) — "
            "사진 파일명이나 기록.md 중 하나가 틀렸다. 캡션을 지어내지 않는다")
    if check == "✓":
        states = expected
    else:
        # 불일치 행: 관찰값을 `L1=0 L2=1` 또는 `0 1` 형태로 적어 둔 것을 받는다
        vals = re.findall(r"[01]", check)
        if len(vals) != len(rec.outputs):
            raise ContactSheetError(
                f"{rec.title} `{bits}`: 확인 칸 `{check}` 에서 출력 {len(rec.outputs)}개를 "
                "읽지 못했다")
        states = vals
    ins = " ".join(f"{n}={b}" for n, b in zip(rec.inputs, bits))
    outs = " · ".join(f"{n} {'켜짐' if s == '1' else '꺼짐'}" for n, s in zip(rec.outputs, states))
    return f"{ins}  →  {outs}"


def _tile(path: Path, caption: str, font) -> Image.Image:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((TILE_W, TILE_H))
    tile = Image.new("RGB", (TILE_W, TILE_H + CAPTION_H), "white")
    tile.paste(im, ((TILE_W - im.width) // 2, CAPTION_H + (TILE_H - im.height) // 2))
    d = ImageDraw.Draw(tile)
    d.rectangle((0, 0, TILE_W, CAPTION_H), fill=(30, 30, 30))
    tw = d.textlength(caption, font=font)
    d.text(((TILE_W - tw) / 2, 14), caption, fill="white", font=font)
    return tile


def _save_under_limit(sheet: Image.Image, out: Path) -> int:
    for q in (85, 80, 72, 65, 55):
        sheet.save(out, "JPEG", quality=q, optimize=True)
        size = out.stat().st_size
        if size <= MAX_BYTES:
            return size
    raise ContactSheetError(f"{out.name}: 품질을 낮춰도 5 MB 를 넘는다 ({size} B)")


def build(experiment: int, dry_run: bool = False) -> list[tuple[Path, list[str]]]:
    exp_dir = Path(config.experiment_dir(experiment))
    photo_dir = exp_dir / "실험사진"
    record = exp_dir / "체크리스트" / "기록.md"
    if not record.exists():
        raise ContactSheetError(f"{record} 가 없다")
    records = load_records(record)

    groups: dict[str, list[tuple[str, Path]]] = {}
    for p in sorted(photo_dir.iterdir()):
        m = _FILE.match(p.name)
        if not m:
            continue
        groups.setdefault(m.group("item"), []).append((m.group("bits"), p))
    if not groups:
        raise ContactSheetError(f"{photo_dir} 에 `<항목> <비트>.jpg` 사진이 없다")

    font = None if dry_run else _font(30)
    out_dir = photo_dir / "시트"
    results = []
    for token, photos in groups.items():
        rec = _match_item(token, records)
        photos.sort(key=lambda t: t[0])
        captions = [_caption(rec, bits) for bits, _ in photos]
        out = out_dir / f"{exp_dir.name}_{rec.token}_사진_{_slug(rec.title)}.jpg"
        if not dry_run:
            out_dir.mkdir(exist_ok=True)
            rows = -(-len(photos) // COLS)
            tile_h = TILE_H + CAPTION_H
            sheet = Image.new("RGB", (COLS * TILE_W + (COLS + 1) * GAP,
                                      rows * tile_h + (rows + 1) * GAP), "white")
            for k, ((_, p), cap) in enumerate(zip(photos, captions)):
                x = GAP + (k % COLS) * (TILE_W + GAP)
                y = GAP + (k // COLS) * (tile_h + GAP)
                sheet.paste(_tile(p, cap, font), (x, y))
            _save_under_limit(sheet, out)
        results.append((out, captions))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("experiment", type=int)
    ap.add_argument("--dry-run", action="store_true", help="캡션만 출력하고 파일을 만들지 않는다")
    a = ap.parse_args(argv)
    try:
        for out, captions in build(a.experiment, a.dry_run):
            print(out)
            for c in captions:
                print("   ", c)
    except ContactSheetError as e:
        print("오류:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
