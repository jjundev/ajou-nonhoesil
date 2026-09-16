"""예상 결과 그림의 판정·이름·자리 — Chrome 을 부르지 않는 순수 함수.

`draw-expected-figure` 스킬이 쓴다. 그림 자체는 여기 없다 — 주차마다
`<실험NN>/output/<실험NN>_예상결과.html` 에 산다. 캡처와 숫자 검사는
`figure_export` 가 맡는다.

판정은 명세 표의 `kind` 로만 한다. `truth-table`·`stepped` 는 셀 표가 곧 예상
결과라 그림이 같은 행을 두 번 보여 줄 뿐이고, `capture` 만 셀 표 없이 산문을
갖는다(`docs/schema/lab-spec-v2.md` 표 속성 절).
"""

import re
from pathlib import Path

from . import notion

CAPTURE = "capture"
# 그림 자리를 넣는 대절. `.claude/보고서양식.md` `교집합` 프리셋의 이름이다 —
# 양식이 바뀌어 이 절이 없으면 `insert_placeholder` 가 멈춘다(조용히 넘기지 않는다).
PROCESS_SECTION = "실험 과정 및 예상 결과"
EMPTY_BLOCK = "<empty-block/>"
# 결선도 단계 그림(`…_1단계_칩교체.png`)은 완성본이 아니다.
_STAGE = re.compile(r"_\d+단계_")
# 명세에서 표 블록의 끝 — 다음 항목(`# `) 또는 다음 표(`## `).
_SPEC_HEAD = re.compile(r"^#{1,2} ", re.M)


def capture_tables(spec) -> list:
    """범위 안 항목의 `capture` 표를 `(항목, 표)` 로, 명세 순서대로."""
    out = []
    for item in spec.items:
        for table_id in item.tables:
            table = spec.table(table_id)
            if table is not None and table.kind == CAPTURE:
                out.append((item, table))
    return out


def gate_message(spec) -> str:
    """그림을 만들지 않을 때 남기는 한 줄. 말없이 끝나면 실패와 판정이 구분되지 않는다."""
    kinds = []
    for item in spec.items:
        for table_id in item.tables:
            table = spec.table(table_id)
            if table is not None:
                kinds.append(f"{table.id}: {table.kind}")
    return (", ".join(kinds) + " — capture 표가 없어 예상 결과 그림을 만들지 않는다. "
            "표가 곧 예상 결과다")


def sub_id(item) -> str:
    """`E2.P1-1` → `1-1`. 파일 이름의 소실험 자리다."""
    if ".P" not in item.id:
        raise ValueError(f"항목 id 에 .P 가 없다: {item.id}")
    return item.id.split(".P", 1)[1]


def figure_png_name(exp_dir, item) -> str:
    """결선도 완성본 이름의 `결선도` 를 `예상결과` 로 바꾼다. 없으면 소실험 번호로만 짓는다.

    접두어가 `실험NN_<소실험>_결선도_` 까지라 `1` 이 `10` 을 삼키지 않는다.
    """
    exp_dir = Path(exp_dir)
    prefix = f"{exp_dir.name}_{sub_id(item)}_"
    finals = sorted(p.name for p in (exp_dir / "결선도").glob(f"{prefix}결선도_*.png")
                    if not _STAGE.search(p.name))
    if len(finals) > 1:
        raise ValueError(f"{prefix} 의 결선도 완성본이 둘 이상이다: {finals}")
    if not finals:
        return f"{prefix}예상결과.png"
    return finals[0].replace(f"{prefix}결선도_", f"{prefix}예상결과_", 1)


def spec_figure_path(png_name) -> str:
    """명세(`체크리스트/명세.md`) 위치 기준으로 `output/` 의 그림을 가리킨다."""
    return f"../output/{png_name}"


def set_spec_figure(spec_text, table_id, rel_path) -> str:
    """그 표 블록의 `- figure:` 를 바꾸거나 `- kind: capture` 다음 줄에 넣는다."""
    head = re.search(rf"^## {re.escape(table_id)} ·.*$", spec_text, re.M)
    if head is None:
        raise ValueError(f"명세에 {table_id} 표가 없다")
    nxt = _SPEC_HEAD.search(spec_text, head.end())
    end = nxt.start() if nxt else len(spec_text)
    block = spec_text[head.end():end]
    line = f"- figure: {rel_path}"
    if re.search(r"^- figure:.*$", block, re.M):
        block = re.sub(r"^- figure:.*$", line, block, count=1, flags=re.M)
    else:
        kind = re.search(rf"^- kind: {CAPTURE}[ \t]*$", block, re.M)
        if kind is None:
            raise ValueError(f"{table_id} 는 capture 표가 아니다 — figure 는 capture 표만 갖는다")
        block = block[:kind.end()] + "\n" + line + block[kind.end():]
    return spec_text[:head.end()] + block + spec_text[end:]


def is_uploaded(output_dir, source_name) -> bool:
    """그 md 를 source 로 한 예비보고서 업로드 기록이 있는가.

    올린 페이지에 해당하는 md 를 고치면 노션 페이지와 갈라진다 — 노션은 덮어쓰지
    않으므로(`sync-report-to-notion` 절대 규칙 1) 그 차이를 되돌릴 길이 없다.
    """
    return any(r.get("kind") == "예비보고서" and r.get("source") == source_name
               for r in notion.load_records(output_dir))


def placeholder_alt(item_title) -> str:
    return f"{item_title} 예상 결과"


def insert_placeholder(md_text, item_title, png_name, caption) -> str:
    """`# 실험 과정 및 예상 결과` 의 `## <item_title>` 소절 끝에 그림 줄과 캡션을 넣는다.

    자리는 소절의 마지막 내용 줄 뒤, 여백 블록(`<empty-block/>`) 앞이다. 캡션은
    번호 없는 한 줄이다 — 보고서 문단은 줄로 쪼개지 않고(③ §절대 규칙 18),
    결선도 그림도 번호를 달지 않는다. 같은 alt 가 이미 있으면 그대로 돌려준다.
    """
    if "\n" in caption:
        raise ValueError("캡션은 한 줄이어야 한다")
    alt = placeholder_alt(item_title)
    if f"![{alt}](" in md_text:
        return md_text
    lines = md_text.split("\n")
    try:
        sec = lines.index(f"# {PROCESS_SECTION}")
    except ValueError:
        raise ValueError(f"예비보고서에 `# {PROCESS_SECTION}` 절이 없다") from None
    sec_end = next((i for i in range(sec + 1, len(lines)) if lines[i].startswith("# ")),
                   len(lines))
    try:
        sub = lines.index(f"## {item_title}", sec + 1, sec_end)
    except ValueError:
        raise ValueError(f"`# {PROCESS_SECTION}` 안에 `## {item_title}` 소절이 없다") from None
    sub_end = next((i for i in range(sub + 1, sec_end) if lines[i].startswith("## ")),
                   sec_end)
    last = sub
    for i in range(sub + 1, sub_end):
        s = lines[i].strip()
        if s and s != EMPTY_BLOCK:
            last = i
    new = ["", f"![{alt}]({png_name})", "", caption]
    return "\n".join(lines[:last + 1] + new + lines[last + 1:])
