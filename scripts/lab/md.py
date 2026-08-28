"""마크다운 프론트매터·표 파싱 원시 함수. 표준 라이브러리만 쓴다.

PyYAML 이 이 환경에 없으므로 프론트매터는 이 프로젝트가 실제로 쓰는 부분집합만
직접 파싱한다:

    key: scalar
    key: {a: 1, b: "x"}      인라인 매핑
    key: [a, b]              인라인 시퀀스
    key:                     블록 시퀀스
      - scalar
      - {a: 1}
    key: |                   블록 스칼라 (여러 줄 산문)
      첫 줄
      둘째 줄
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MdTable:
    header: list
    rows: list
    line: int  # 구분선의 1-based 줄 번호


_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")   # `\|` 는 셀 구분자가 아니다


def split_top(s: str) -> list:
    """괄호·따옴표 안을 건드리지 않고 최상위 쉼표로만 자른다."""
    parts, buf, depth, quote = [], [], 0, ""
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def parse_value(s: str) -> Any:
    s = s.strip()
    if s in ("", "~", "null"):
        return None
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for part in split_top(s[1:-1]):
            k, _, v = part.partition(":")
            out[k.strip()] = parse_value(v)
        return out
    if s.startswith("[") and s.endswith("]"):
        return [parse_value(p) for p in split_top(s[1:-1])]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _mapping(lines, i, indent):
    """indent 수준의 매핑을 읽는다. (dict, 다음 인덱스) 반환."""
    out = {}
    while i < len(lines) and _indent(lines[i]) == indent:
        line = lines[i]
        key, sep, rest = line.strip().partition(":")
        if not sep:
            raise ValueError(f"'키: 값' 형태가 아닙니다: {line.strip()!r}")
        key, rest = key.strip(), rest.strip()

        if rest == "|":                       # 블록 스칼라
            i += 1
            chunk = []
            while i < len(lines) and _indent(lines[i]) > indent:
                chunk.append(lines[i].strip())
                i += 1
            out[key] = " ".join(chunk)
        elif rest:
            out[key] = parse_value(rest)
            i += 1
        else:                                  # 중첩 블록
            i += 1
            if i < len(lines) and _indent(lines[i]) > indent:
                out[key], i = _block(lines, i, _indent(lines[i]))
            else:
                out[key] = None
    return out, i


def _sequence(lines, i, indent):
    """indent 수준의 `- ` 시퀀스를 읽는다. (list, 다음 인덱스) 반환."""
    out = []
    while (i < len(lines) and _indent(lines[i]) == indent
           and lines[i].lstrip().startswith("- ")):
        rest = lines[i].lstrip()[2:]
        i += 1
        child = [rest]
        while i < len(lines) and _indent(lines[i]) > indent:
            child.append(lines[i][indent + 2:])
            i += 1
        if len(child) == 1:
            out.append(parse_value(child[0]))
        else:                                  # 시퀀스 안의 블록 매핑
            value, _ = _mapping(child, 0, 0)
            out.append(value)
    return out, i


def _block(lines, i, indent):
    if lines[i].lstrip().startswith("- "):
        return _sequence(lines, i, indent)
    return _mapping(lines, i, indent)


def parse_block(src: str) -> dict:
    """들여쓰기 기반 미니 YAML 블록을 dict 로 읽는다."""
    lines = [ln for ln in src.split("\n")
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return {}
    value, _ = _mapping(lines, 0, _indent(lines[0]))
    return value


def split_frontmatter(text: str):
    """`---` 로 감싼 프론트매터를 (dict, 본문) 으로 가른다."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        raise ValueError("프론트매터가 닫히지 않았습니다 (`---` 짝이 맞지 않음)")
    return parse_block(m.group(1)), text[m.end():]


def _cells(line: str) -> list:
    """셀로 자른다. `\\|` 는 구분자가 아니라 셀 안의 문자다.

    쪼개 버리면 `validate` 의 "셀에 escape 된 파이프" 검사가 영영 발화하지 못한다
    — 검사가 찾는 문자열이 파싱 단계에서 사라지기 때문이다.
    """
    return [c.strip() for c in _CELL_SPLIT.split(_ROW.match(line).group(1))]


def parse_tables(body: str) -> list:
    """본문에서 마크다운 표를 전부 찾는다.

    구분선은 **위치로만** 판정한다 — 헤더 바로 다음 줄이어야 한다. 내용으로
    판정하면 `| - | - |` 같은 don't-care 행이 구분선과 구별되지 않아 데이터가
    조용히 사라진다 (`-` 는 이 프로젝트의 don't-care 표기 중 하나다).
    """
    lines = body.split("\n")
    tables, i = [], 0
    while i < len(lines):
        if not (_ROW.match(lines[i]) and not _SEP.match(lines[i])
                and i + 1 < len(lines) and _SEP.match(lines[i + 1])):
            i += 1
            continue
        header = _cells(lines[i])
        sep_line = i + 2                      # 구분선의 1-based 줄 번호
        i += 2
        rows = []
        while i < len(lines) and _ROW.match(lines[i]):
            if i + 1 < len(lines) and _SEP.match(lines[i + 1]):
                break                         # 이 줄은 다음 표의 헤더다
            rows.append(_cells(lines[i]))
            i += 1
        tables.append(MdTable(header=header, rows=rows, line=sep_line))
    return tables
