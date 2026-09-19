"""강의노트 회로도 크롭 — 체크리스트 회로 페이지 첫머리에 싣는 PNG 를 만든다.

교안 회로도는 래스터 이미지 위에 IC 이름·신호 이름이 **텍스트로** 겹쳐 있다(실험3
p5·p7). 임베드 이미지를 그대로 뽑으면 `74HC86`·`A`·`Ci` 가 빠지므로 쪽을 300dpi 로
렌더하면서 영역을 잘라 낸다. 기본 영역은 여러 쪽에 반복되는 로고를 뺀 가장 큰 이미지의
자리에 4pt 여백을 둔 것이다 — 여백을 더 주면 이미지 바로 아래 캡션 '회로 구성'(p5·p7
top 507pt)이 반쯤 걸린다. 그림 자리가 다르면 `--box` 로 준다.

PNG 는 고치는 명세 옆, 곧 `<실험NN>/체크리스트/` 에 둔다. `결선도/` 는 `배치.py`
출력만 담는다(`tests/test_breadboard_boards.py` 의 `CommittedPngs`). 기존 명세가
있으면 `--spec` 으로 스크래치패드 사본을 준다 — PNG 도 사본 옆에 떨어지고
`<실험NN>/` 은 건드리지 않는다(draft-lab-spec 절대 규칙 13).

pymupdf(`fitz`)는 함수 안에서만 부른다 — `render`·`validate` 가 이 모듈을 안 부르지만,
fitz 없는 기계에서 `scripts.lab` 을 import 하다 죽는 일을 만들지 않는다.
"""

import argparse
import re
from collections import Counter
from pathlib import Path

from . import config
from .figure import sub_id
from .spec_parser import parse_spec

DPI = 300
MARGIN_PT = 4


def schematic_name(exp_dir, item) -> str:
    """`실험03` + `E3.P1-2` → `실험03_1-2_회로도.png`."""
    return f"{Path(exp_dir).name}_{sub_id(item)}_회로도.png"


def page_count(manual) -> int:
    import fitz
    with fitz.open(str(manual)) as doc:
        return len(doc)


def default_box(manual, page: int) -> tuple:
    """그 쪽에서 로고를 뺀 가장 큰 이미지 자리 + 여백 (pt, 쪽 왼쪽 위 기준).

    로고 = 문서 쪽의 절반 이상에 같은 xref 로 나오는 이미지.
    """
    import fitz
    with fitz.open(str(manual)) as doc:
        counts = Counter()
        for p in doc:
            for xref in {info[0] for info in p.get_images(full=True)}:
                counts[xref] += 1
        pg = doc[page - 1]
        rects = [r for xref in {info[0] for info in pg.get_images(full=True)}
                 if counts[xref] * 2 < len(doc)
                 for r in pg.get_image_rects(xref)]
        if not rects:
            raise ValueError(f"{manual} p{page} 에 회로도로 볼 이미지가 없다 — "
                             "--box x0,y0,x1,y1 (pt) 로 영역을 준다")
        r = max(rects, key=lambda r: r.width * r.height)
        box = fitz.Rect(r.x0 - MARGIN_PT, r.y0 - MARGIN_PT,
                        r.x1 + MARGIN_PT, r.y1 + MARGIN_PT) & pg.rect
        return (box.x0, box.y0, box.x1, box.y1)


def crop(manual, page: int, box: tuple, out) -> None:
    import fitz
    with fitz.open(str(manual)) as doc:
        pix = doc[page - 1].get_pixmap(dpi=DPI, clip=fitz.Rect(*box))
        pix.save(str(out))


_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def set_spec_schematic(spec_text: str, item_id: str, rel_paths: list) -> str:
    """프론트매터의 그 항목에 `    schematic: [...]` 를 넣거나 바꾼다.

    자리는 `pages:` 다음 줄, 없으면 항목 블록의 끝이다. 항목은 `  - id:`(2칸),
    필드는 4칸 들여쓰기라고 본다 — `draft-lab-spec` 이 쓰는 형태다.
    """
    front = _FRONT.match(spec_text)
    if front is None:
        raise ValueError("명세에 프론트매터가 없다")
    lines = front.group(1).split("\n")
    start = next((i for i, l in enumerate(lines)
                  if re.fullmatch(rf"  - id: {re.escape(item_id)}\s*", l)), None)
    if start is None:
        raise ValueError(f"명세 프론트매터에 항목 {item_id} 가 없다")
    end = next((i for i in range(start + 1, len(lines))
                if not lines[i].startswith("    ")), len(lines))
    new = f"    schematic: [{', '.join(rel_paths)}]"
    block = lines[start:end]
    at = next((i for i, l in enumerate(block) if l.startswith("    schematic:")), None)
    if at is not None:
        block[at] = new
    else:
        pages = next((i for i, l in enumerate(block) if l.startswith("    pages:")), None)
        block.insert(len(block) if pages is None else pages + 1, new)
    lines[start:end] = block
    return f"---\n{chr(10).join(lines)}\n---\n" + spec_text[front.end():]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="강의노트 회로도를 300dpi 로 크롭해 체크리스트/ 에 두고 명세 schematic 에 적는다")
    ap.add_argument("experiment", type=int)
    ap.add_argument("item", help="명세 항목 id (예: E3.P1-2)")
    ap.add_argument("--page", type=int, help="교안 쪽. 없으면 항목 pages 의 첫 쪽")
    ap.add_argument("--box", help="x0,y0,x1,y1 (pt, 쪽 왼쪽 위 기준). 없으면 default_box")
    ap.add_argument("--spec", type=Path,
                    help="고칠 명세 경로. PNG 도 그 옆에 둔다. 없으면 <실험NN>/체크리스트/명세.md "
                         "— 기존 명세가 있을 때(draft-lab-spec 절대 규칙 13) 스크래치패드 사본을 준다")
    a = ap.parse_args(argv)

    root = config.find_project_root(Path("."))
    exp_dir = root / config.experiment_dir(a.experiment)   # PNG 이름(`실험NN_`)은 늘 여기서 온다
    spec_path = a.spec or exp_dir / "체크리스트/명세.md"
    spec = parse_spec(spec_path)
    item = next((i for i in spec.items if i.id == a.item), None)
    if item is None:
        ap.error(f"명세에 항목 {a.item} 가 없다: {[i.id for i in spec.items]}")
    page = a.page or (item.pages[0] if item.pages else None)
    if page is None:
        ap.error(f"항목 {item.id} 에 pages 가 없다 — --page 로 쪽을 준다")
    manual = root / spec.source_manual
    n_pages = page_count(manual)
    if not 1 <= page <= n_pages:
        ap.error(f"교안 쪽 {page} 가 범위 밖이다 — {spec.source_manual} 은 1~{n_pages} 쪽이다")
    if a.box:
        try:
            box = tuple(float(v) for v in a.box.split(","))
        except ValueError:
            ap.error(f"--box 는 x0,y0,x1,y1 네 수다 — 받은 값: {a.box}")
        if len(box) != 4:
            ap.error("--box 는 x0,y0,x1,y1 네 수다")
    else:
        box = default_box(manual, page)
    name = schematic_name(exp_dir, item)
    out = spec_path.parent / name
    crop(manual, page, box, out)
    spec_path.write_text(
        set_spec_schematic(spec_path.read_text(encoding="utf-8"), item.id, [name]),
        encoding="utf-8")
    print(f"{out} ← {spec.source_manual} p{page} box={tuple(round(v, 1) for v in box)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
