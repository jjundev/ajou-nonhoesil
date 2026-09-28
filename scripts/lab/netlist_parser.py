"""`netlist.md` → `LabNetlist`. 필드 계약은 `docs/schema/lab-netlist-v2.md` 가 정본이다.

`spec_parser` 와 같은 분업을 지킨다 — 이 파서는 **표현할 수 없는 것에만** 예외를
던지고(알 수 없는 kind, 회로인데 id 가 없음), 의미 결함(없는 항목을 가리킴, 그림
파일 부재)은 `validate.check_netlist_circuits` 가 findings 로 보고한다.

`kind` 가 **인쇄 라우터**다. 목적지를 산문의 모양으로 짐작하던 시절에는 핀아웃
출처(참고문헌)가 배선 단계 7~11번으로 찍히고, 참조 핀아웃 표는 표 줄이라는
이유로 통째로 사라지고, 미확정 절은 제목만 남아 문장이 끊겼다. 목적지를
데이터로 적으면 그 세 결함이 구조적으로 불가능해진다.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import md

KINDS = ("common", "lookup", "sources", "open-issues", "circuit", "layout", "must-read")

# `must-read` 는 공통면 맨 위 경고 상자다(2026-09-28). 공통 규칙·미확정 표는 인쇄하지 않고
# 이 절만 싣는다 — 학생이 실제로 읽는 유일한 규칙 자리라 길어지면 다시 안 읽힌다.
MUST_READ_MAX = 5

_H1 = re.compile(r"^#[ \t]+(?!#)(.+?)[ \t]*$", re.M)
_ATTR = re.compile(r"^-[ \t]+([a-z_]+)[ \t]*:[ \t]*(.*)$")

# `- U1 = 74HC08 (quad ...)` 또는 ``## U1 = `7490` (decade counter)``.
# 백틱으로 감싼 이름은 닫는 백틱까지 통째로 잡는다 — 실험10 의
# `` `741 OP amp` `` 처럼 낱말이 여럿인 칩이 실재한다. 첫 공백에서 끊으면
# `741` 이 되어 칩 교체 배너가 엉뚱한 이름을 말한다.
IC_DECL = re.compile(r"(U\d+)[ \t]*=[ \t]*(`[^`\n]+`|[^\s(,`\n]+)")

_BACKFILL = (
    "`# ` 절마다 `- kind:` 를 적고, 회로 절에는 `- id:`·`- item:`·`- tables:` 를 "
    "채운다. 계약은 docs/schema/lab-netlist-v2.md 다"
)

# 회로 절 안 `## 단계` 표의 열. 렌더러가 **열 이름**으로 읽는다 — 순서가 아니라
# 이름이 계약이라 저작자가 열을 바꾸면 여기서 거절한다
STAGE_COLUMNS = ("단계", "그림", "이 단계에서", "확인")
_STAGE_HEAD = re.compile(r"^##[ \t]+단계[ \t]*$")

# 단계 `확인` 칸이 가리키는 관측 노드. 2026-09-20 단계 세분화: 단계 하나는 관측 노드
# 하나를 세우고, 그 이름은 같은 회로 `## 노드` 표에 있어야 한다(`validate` 가 잰다).
# 백틱이 이름의 경계다 — `A⊕B` 는 `(A⊕B)·Ci` 의 부분 문자열이라 공백으로는 못 가른다.
# 닫는 백틱을 선택으로 둔 이유: 셀이 백틱으로 끝나면 `_split_subtable` 이 그것을 뗀다.
_STAGE_NODE = re.compile(r"^노드\s+`([^`]+)(?:`|$)")

# `단계` 셀의 문법 판정은 여기 한 곳이다. 검증기는 이 정규식을 되풀이하지 않고
# `stage_no`·`walk`·`walk_of`만 읽는다. 앞자리 0은 정수 비교에서 같은 번호다.
_STAGE_NUMBER = re.compile(r"^[0-9]+$")
_STAGE_WALK = re.compile(r"^([0-9]+)걷기$")

_HOLE_PATTERN = r"(?:좌|우)\s*[a-j]\s*[1-9][0-9]*"
_HOLE = re.compile(_HOLE_PATTERN)
_WALK_ADDRESS = re.compile(rf"({_HOLE_PATTERN})\s*→\s*({_HOLE_PATTERN})")


def _normalise_hole(token: str) -> str:
    match = re.fullmatch(r"(좌|우)\s*([a-j])\s*([1-9][0-9]*)", token)
    assert match is not None
    return f"{match.group(1)} {match.group(2)}{match.group(3)}"


def _walk_addresses(text: str) -> list[str]:
    return [f"{_normalise_hole(start)} → {_normalise_hole(end)}"
            for start, end in _WALK_ADDRESS.findall(text)]


def _holes(text: str) -> list[str]:
    return [_normalise_hole(match.group(0)) for match in _HOLE.finditer(text)]


# 회로 절 안 `## 노드` 표의 열. 프로브로 찍을 핀과 그 기대값 식 — 2026-09-20 회고:
# 다 꽂고 켰을 때 틀리면 용의자가 선 전부였다. 노드 하나를 찍을 때마다 절반으로 준다
NODE_COLUMNS = ("노드", "식", "핀")
_NODE_HEAD = re.compile(r"^##[ \t]+노드[ \t]*$")


class NetlistError(ValueError):
    """결선도를 구조적으로 읽을 수 없을 때."""


@dataclass
class NetlistSection:
    kind: str
    title: str
    body: str                 # 속성 리스트를 걷어낸 나머지
    line: int
    id: Optional[str] = None
    item: Optional[str] = None
    tables: list = field(default_factory=list)
    diagram: Optional[str] = None
    continues: Optional[str] = None    # 앞 회로를 뜯지 않고 이어 붙인다
    rebuild: bool = False              # 앞 회로의 신호선을 전부 뽑고 새로 짓는다
    refs: list = field(default_factory=list)   # 이 회로 페이지에 실을 참조표
    stages: list = field(default_factory=list)   # `## 단계` 표. 관측 노드 하나 = 단계 하나
    nodes: list = field(default_factory=list)    # `## 노드` 표. 행 = {"name", "expr", "pin"}

    @property
    def ics(self) -> list:
        """이 절이 선언한 칩 이름. 등장 순서를 지키고 중복을 지운다.

        `- ics:` 필드를 따로 두지 않는다 — 배선 본문의 `U<n> = <칩>` 선언이 이미
        정답이고, 필드를 늘리면 둘이 표류한다. 인쇄본의 칩 교체 배너가 이것을
        쓴다 (netlist M10: 칩이 종류당 하나라 회로를 순차로 배선해야 한다).
        """
        out = []
        for _, chip in IC_DECL.findall(self.body):
            chip = chip.strip("`")
            if chip not in out:
                out.append(chip)
        return out


@dataclass
class LabNetlist:
    experiment: int
    spec: str
    sections: list
    path: Path
    text: str

    @property
    def circuits(self) -> list:
        return [s for s in self.sections if s.kind == "circuit"]

    def of_kind(self, kind: str) -> list:
        return [s for s in self.sections if s.kind == kind]


def _split_subtable(body, head_re, columns, keys, label, path, line):
    """회로 본문에서 `## <label>` 헤딩과 그 표를 떼어 `(행 dict 목록, 나머지 본문)` 으로.

    떼어내는 이유: 남겨 두면 `render._circuit_body` 가 "칩이 아닌 헤딩 아래의
    표" 규칙으로 참조표로 인쇄한다 — 블록과 표가 두 번 찍힌다.
    `## 단계` 와 `## 노드` 가 같은 규칙이라 한 함수다.
    """
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if not head_re.match(ln.rstrip()):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        table, nxt = md.parse_table_at(lines, j) if j < len(lines) else (None, j)
        if table is None:
            raise NetlistError(
                f"{path}:{line + i} 근처 `## {label}` 아래에 표가 없다. "
                f"`| {' | '.join(columns)} |` 표를 헤딩 바로 아래 둔다")
        if tuple(h.strip() for h in table.header) != columns:
            raise NetlistError(
                f"{path}:{line + i} 근처 `## {label}` 표의 열이 {table.header} 다. "
                f"{list(columns)} 이어야 한다 — 렌더러가 열 이름으로 읽는다")
        # 짧은 행은 `md._cells` 가 채우지 않는다. 그대로 `dict(zip(...))` 하면 키가
        # 빠진 dict 이 나와, 읽는 쪽(`validate._check_nodes`, `nodes.compute`)이
        # `KeyError` 로 죽는다 — 검증기는 예외로 중단하지 않는 것이 계약이다.
        # 구조 결함은 파서 몫이므로 여기서 거절한다.
        for k, row in enumerate(table.rows, start=1):
            if len(row) != len(columns):
                raise NetlistError(
                    f"{path}:{line + i} 근처 `## {label}` 표의 행 {k} 의 셀이 "
                    f"{len(row)}개다. {len(columns)}개({', '.join(columns)})여야 한다")
        rows = [dict(zip(keys, (c.strip().strip("`") for c in row)))
                for row in table.rows]
        if not rows:
            raise NetlistError(f"{path}:{line + i} 근처 `## {label}` 표에 행이 없다")
        return rows, "\n".join(lines[:i] + lines[nxt:])
    return [], body


def _split_stages(body, path, line):
    """`## 단계` 표. 실험01 실험실 기록(2026-09-11): 복합회로를 전부 꽂고 불이 안
    들어오자 어디가 틀렸는지 알 수 없었다. 단계마다 LED 로 확인하는 자리가 데이터여야
    체크리스트에 확인 칸이 생긴다.

    2026-09-20 단계 세분화: `확인` 칸이 `노드 `<이름>`` 로 시작하면 그 이름을 `node`
    키로 낸다. 열을 늘리지 않은 이유는 실험01·02 승인본의 단계 표 7개가 헤더 불일치로
    통째로 거절당하기 때문이다 — 옛 표는 `node` 가 `None` 이고 검증기가 warn 만 한다.

    일반 단계 번호도 `stage_no` 정수로 낸다. 검증기가 원문 문자열을 다시 정규식으로
    재지 않아야 `03걷기`와 `03`을 같은 번호로 비교할 수 있고, `2 걷기`·`걷기2`가
    일반 단계인 척 노드 검사 뒤로 숨지 않는다.

    2026-09-20 걷기 보드: `단계` 칸이 `<k>걷기` 면 걷기 행이다 — 선을 뽑기만 하는
    장이라 관측 노드도 새 신호선도 없다. `k` 는 **바로 다음 행**의 단계 번호이고,
    그 대조는 검증기가 한다. 판정은 여기 한 곳이다 — 검증기·렌더러·체크리스트가
    각자 문자열을 다시 재면 같은 개념에 기계가 셋이 된다.
    """
    rows, rest = _split_subtable(body, _STAGE_HEAD, STAGE_COLUMNS,
                                 ("n", "diagram", "todo", "check"), "단계", path, line)
    for row in rows:
        m = _STAGE_NODE.match(row["check"])
        row["node"] = m.group(1) if m else None
        number = _STAGE_NUMBER.match(row["n"])
        walk = _STAGE_WALK.match(row["n"])
        row["stage_no"] = int(number.group(0)) if number and not walk else None
        row["walk"] = walk is not None
        row["walk_of"] = int(walk.group(1)) if walk else None
        row["walk_addresses"] = _walk_addresses(row["todo"]) if row["walk"] else []
        row["check_holes"] = _holes(row["check"]) if row["walk"] else []
    return rows, rest


def _split_nodes(body, path, line):
    """`## 노드` 표. 단계 끝에서 LED 만 보면 중간단은 관측점이 없다 — 프로브로 찍을
    핀과 그 기대값 식을 데이터로 둬야 실패한 행에서 고장 노드를 좁힐 수 있다."""
    return _split_subtable(body, _NODE_HEAD, NODE_COLUMNS,
                           ("name", "expr", "pin"), "노드", path, line)


def _leading_attrs(block: str):
    """절 첫머리의 **연속된** `- key: value` 줄만 속성으로 읽는다. (dict, 나머지 본문).

    `spec_parser._attrs` 는 블록 전체를 훑고 표 줄에서 멈춘다. 여기서는 더
    좁힌다 — 회로 절의 본문은 `- U1 = 74HC08` 불릿과 `- 미사용 입력핀: pin 9 →
    GND` 처럼 콜론이 든 한글 불릿으로 이어지고, 그 뒤에 표가 없어 멈출 곳이
    없다. 지금은 키 패턴(`[a-z_]+`)이 한글 불릿을 걸러주지만 그건 우연이다.
    첫 비-속성 줄에서 멈추면 키 패턴이 넓어져도 안전하다.
    """
    attrs, lines, i = {}, block.split("\n"), 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines):
        m = _ATTR.match(lines[i])
        if not m:
            break
        attrs[m.group(1)] = m.group(2).strip()
        i += 1
    return attrs, "\n".join(lines[i:])


def _check_must_read(title, body, line, path) -> None:
    """불릿(들여쓴 이어지는 줄 포함)과 표만, 최상위 불릿은 `MUST_READ_MAX` 개까지."""
    bullets = 0
    for raw in body.split("\n"):
        if not raw.strip() or raw[0] in " \t" or raw.lstrip().startswith("|"):
            continue
        if raw.startswith("- "):
            bullets += 1
            continue
        raise NetlistError(
            f"{path}:{line} 절 {title!r}(must-read) 에 불릿·표가 아닌 줄이 있습니다: "
            f"{raw.strip()[:40]!r}. 이유·출처는 `kind: common` 절에 둔다 — 인쇄되지 않는다")
    if bullets > MUST_READ_MAX:
        raise NetlistError(
            f"{path}:{line} 절 {title!r}(must-read) 의 불릿이 {bullets}개입니다. "
            f"최대 {MUST_READ_MAX}개 — 실험실에서 손으로 할 일만 남긴다")
    if bullets == 0 and "|" not in body:
        raise NetlistError(f"{path}:{line} 절 {title!r}(must-read) 이 비어 있습니다")


def _parse_section(title, block, line, path) -> NetlistSection:
    attrs, body = _leading_attrs(block)
    kind = attrs.get("kind")
    if kind not in KINDS:
        raise NetlistError(
            f"{path}:{line} 절 {title!r} 의 kind 가 {kind!r} 입니다. "
            f"허용: {', '.join(KINDS)}. kind 가 인쇄 목적지를 정한다 — {_BACKFILL}"
        )
    if kind == "must-read":
        _check_must_read(title, body, line, path)
    if kind != "circuit":
        return NetlistSection(kind=kind, title=title, body=body, line=line)
    for required in ("id", "item", "tables"):
        if not attrs.get(required):
            raise NetlistError(
                f"{path}:{line} 회로 절 {title!r} 에 {required} 가 없습니다. {_BACKFILL}"
            )
    tables = md.parse_value(attrs["tables"])
    if not isinstance(tables, list):
        tables = [tables]
    refs = md.parse_value(attrs["refs"]) if attrs.get("refs") else []
    if not isinstance(refs, list):
        refs = [refs]
    rebuild = attrs.get("rebuild", "false").strip().lower()
    if rebuild not in ("true", "false"):
        # `yes`·`1` 을 조용히 참으로 읽으면 오타 하나로 배너가 뒤집힌다
        raise NetlistError(
            f"{path}:{line} 회로 절 {title!r} 의 rebuild 가 {attrs['rebuild']!r} 입니다. "
            "true 또는 false 만 쓴다")
    stages, body = _split_stages(body, path, line)
    nodes, body = _split_nodes(body, path, line)
    return NetlistSection(
        kind=kind, title=title, body=body, line=line,
        id=attrs["id"], item=attrs["item"], tables=[str(t) for t in tables],
        diagram=attrs.get("diagram") or None,
        continues=attrs.get("continues") or None,
        rebuild=rebuild == "true",
        refs=[str(r) for r in refs],
        stages=stages,
        nodes=nodes,
    )


def parse_netlist(path) -> LabNetlist:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    front, body = md.split_frontmatter(text)
    if front.get("schema") != "lab-netlist/v2":
        raise NetlistError(
            f"{path}: schema 가 lab-netlist/v2 가 아닙니다 ({front.get('schema')!r}). "
            "v1 은 `week:` 를 요구했다 — 일정은 이제 config.EXPERIMENT_DATES 한 곳에만 산다"
        )
    for required in ("experiment", "spec"):
        if front.get(required) is None:
            raise NetlistError(f"{path}: 프론트매터에 {required} 가 없습니다")

    heads = list(_H1.finditer(body))
    if not heads:
        raise NetlistError(f"{path}: `# ` 절이 하나도 없습니다. {_BACKFILL}")

    # `split_frontmatter` 가 떼어낸 프론트매터만큼 줄 번호가 밀린다. 안 더하면
    # 오류가 가리키는 줄이 프론트매터 한복판이라 백필하려는 사람이 엉뚱한 곳을
    # 연다 — 이 모듈이 존재하는 이유가 실행 가능한 오류 메시지다.
    offset = text[: len(text) - len(body)].count("\n")

    sections = []
    for n, m in enumerate(heads):
        end = heads[n + 1].start() if n + 1 < len(heads) else len(body)
        line = offset + body[: m.start()].count("\n") + 1
        sections.append(_parse_section(m.group(1), body[m.end():end], line, path))

    must = [s for s in sections if s.kind == "must-read"]
    if len(must) > 1:
        raise NetlistError(
            f"{path}:{must[1].line} must-read 절이 {len(must)}개입니다. 하나로 합친다 — "
            f"상한 {MUST_READ_MAX} 은 공통면 전체의 줄 수다")

    seen = set()
    for c in [s for s in sections if s.kind == "circuit"]:
        if c.id in seen:
            raise NetlistError(
                f"{path}: 회로 ID {c.id} 가 두 번 정의됐다. ID 는 문서 전체에서 "
                "유일해야 한다 — 인쇄 순서이자 오류 메시지의 지시 대상이다"
            )
        seen.add(c.id)
    if not seen:
        raise NetlistError(
            f"{path}: `kind: circuit` 절이 하나도 없습니다. 인쇄본은 회로마다 "
            f"한 쪽을 낸다. {_BACKFILL}"
        )

    return LabNetlist(experiment=front["experiment"],
                      spec=front["spec"], sections=sections, path=path, text=text)
