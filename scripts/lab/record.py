"""`LabSpec` → `기록.md`. 사람이 채워도 되고 vision 이 채워도 된다.

확인 칸 규약:
    ✓        예상값과 일치
    <값>     불일치 — 실제로 관찰한 값을 적는다
    (공란)   아직 확인하지 않음
표 전체를 진행하지 않았으면 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.

kind 마다 칸의 뜻이 다르다:
    truth-table  입력은 주어지고, 출력에 `예상` 을 병기한 뒤 확인 칸을 붙인다
    stepped      스텝·조작은 주어지고, 명세에서 **비어 있는 열**이 채울 칸이다
    capture      셀 표가 아니라 스케치 격자 + 캡션 줄

`role: reference` 인 표는 건너뛴다. 교안에서 그대로 옮긴 참조표라 학생이
배선하지도 채우지도 않는다 (실험1 의 2입력 이론표 T6~T9). 확인 칸을 만들면
"2입력 AND 이론표를 실험실에서 채우시오" 라는 무의미한 빈 칸이 나온다.
"""

import unicodedata

from .spec_parser import split_columns

PROMPTS = ("막혔던 것", "예상과 달랐던 것", "뭘 바꿔서 해결했나", "새로 안 것")


def _width(text: str) -> int:
    """한글·한자는 2칸을 차지한다. 손으로 채울 표라 정렬이 실제로 중요하다."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, target: int) -> str:
    return text + " " * max(0, target - _width(text))


def _grid(header, rows) -> str:
    widths = [max([_width(header[i])] + [_width(r[i]) for r in rows])
              for i in range(len(header))]
    lines = ["| " + " | ".join(_pad(h, widths[i]) for i, h in enumerate(header)) + " |",
             "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    lines += ["| " + " | ".join(_pad(c, widths[i]) for i, c in enumerate(r)) + " |"
              for r in rows]
    return "\n".join(lines)


def _truth_table(table) -> str:
    inputs, outputs = split_columns(table)
    at = {c: i for i, c in enumerate(table.header)}
    header = list(inputs) + [f"{c}예상" for c in outputs] + ["확인"]
    rows = [[row[at[c]] for c in inputs] + [row[at[c]] for c in outputs] + [""]
            for row in table.rows]
    return _grid(header, rows)


def _stepped(table) -> str:
    """명세에서 비어 있는 열이 실험실에서 채울 칸이다. `예상` 을 붙이지 않는다."""
    return _grid(list(table.header) + ["확인"], [list(row) + [""] for row in table.rows])


def _capture(table) -> str:
    return (f"> 예상: {table.expected or '(명세에 expected 가 없다)'}\n\n"
            "```\n  스케치 — 파형을 여기에 그린다\n\n\n\n\n```\n\n"
            "- 캡션:\n- 사진 파일:")


_RENDER = {"truth-table": _truth_table, "stepped": _stepped, "capture": _capture}


def derive_record(spec) -> str:
    out = [
        "---", "schema: lab-record/v1", f"week: {spec.week}",
        f"experiment: {spec.experiment}", "spec: 명세.md",
        "filled_by: ~          # hand | vision | 미기입", "---", "",
        f"# {spec.week}주차 · 실험{spec.experiment} {spec.title} 기록", "",
        "확인 칸: `✓` 일치 / 값 = 불일치 시 실제 관찰값 / 공란 = 미확인.",
        "표를 통째로 진행하지 않았으면 그 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.", "",
    ]
    for item in spec.items:
        out += [f"## {item.id} · {item.title}",
                f"IC: {', '.join(item.ics)} · 판독: {', '.join(item.device)}", ""]
        for table_id in item.tables:
            table = spec.table(table_id)
            if table.role == "reference":
                continue          # 교안 참조표다. 실험실에서 채우지 않는다
            out += [f"### {table.id} · {table.title}", "",
                    _RENDER[table.kind](table), "", "- 메모:", ""]
    out += ["# 실험 종료 메모", ""] + [f"- {p}:" for p in PROMPTS] + [""]
    return "\n".join(out)
