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

KINDS = ("common", "lookup", "sources", "open-issues", "circuit")

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
    refs: list = field(default_factory=list)   # 이 회로 페이지에 실을 참조표

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


def _parse_section(title, block, line, path) -> NetlistSection:
    attrs, body = _leading_attrs(block)
    kind = attrs.get("kind")
    if kind not in KINDS:
        raise NetlistError(
            f"{path}:{line} 절 {title!r} 의 kind 가 {kind!r} 입니다. "
            f"허용: {', '.join(KINDS)}. kind 가 인쇄 목적지를 정한다 — {_BACKFILL}"
        )
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
    return NetlistSection(
        kind=kind, title=title, body=body, line=line,
        id=attrs["id"], item=attrs["item"], tables=[str(t) for t in tables],
        diagram=attrs.get("diagram") or None,
        continues=attrs.get("continues") or None,
        refs=[str(r) for r in refs],
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
