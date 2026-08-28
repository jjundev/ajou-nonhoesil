"""표기 규칙 (R3 정규화 · R5 보수 · R6 active-low).

**적용 범위가 이 모듈의 핵심이다.** `to_overbar_html` 은 부울식에만 쓴다.
표 헤더·신호명·**셀 값**에는 쓰지 않는다 — 실험6 의 `Q(t-1)'` 은 상태 토큰이지
부울식이 아니라서, 오버바로 승격하면 진리표가 망가진다.

그 경계를 문서로만 지키지 않는다. `normalize_cell` 이 돌려주는 값은 `CellValue`
(str 하위 타입) 이고, `to_overbar_html` 은 그걸 받으면 거절한다. 셀 값과 부울식은
문법적으로 구별되지 않으므로(`Q(t-1)'` 과 `(A·B)'` 은 같은 모양이다), 타입만이
호출부의 실수를 잡아낼 수 있다.
"""

import re

DONT_CARE = "X"
_DC_TOKENS = ("x", "X", "-", "–", "—")
_IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


class CellValue(str):
    """표 셀에서 온 값. 부울식이 아니다 — 오버바 승격 대상이 아니다."""

    __slots__ = ()


def normalize_cell(value, dont_care_column=False) -> CellValue:
    """R3 정규화. don't-care 변형과 공백만 손댄다.

    **`H/L` ↔ `0/1` 변환은 절대 하지 않는다.** encoding 은 표의 속성이다.
    """
    s = " ".join(str(value).split())
    if s in _DC_TOKENS:
        return CellValue(DONT_CARE)
    if s == "" and dont_care_column:
        return CellValue(DONT_CARE)
    return CellValue(s)


def normalize_row(row, dont_care_columns=()) -> list:
    return [normalize_cell(v, i in dont_care_columns) for i, v in enumerate(row)]


def _match_paren(text: str, start: int) -> int:
    """`text[start]` 의 `(` 에 대응하는 `)` 위치. 없으면 -1."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _primes(text: str, i: int) -> int:
    n = 0
    while i + n < len(text) and text[i + n] == "'":
        n += 1
    return n


def _wrap(piece: str, count: int) -> str:
    for _ in range(count):
        piece = f'<span class="ov">{piece}</span>'
    return piece


def to_overbar_html(expr) -> str:
    """부울식의 `'` 를 오버바로 승격한다 (R5). **부울식에만 쓸 것.**

    괄호 스코프를 지키고 **중첩을 지원한다** — `(A'·B)'` 는 `A` 위의 바와
    `A'·B` 전체 위의 바가 겹쳐 나온다. 이 형태가 2주차 명세 T5 의 실제 식이다.

    입력은 대수 표기(문자·숫자·`·`·`+`·`⊕`·`'`·괄호)로 가정한다.
    HTML 이스케이프는 하지 않는다 — 호출부가 알고리즘 텍스트만 넘겨야 한다.
    """
    if isinstance(expr, CellValue):
        raise TypeError(
            "셀 값에는 오버바를 승격하지 않는다. 실험6 의 `Q(t-1)'` 같은 상태 "
            "토큰은 부울식이 아니다 — 승격하면 진리표가 망가진다."
        )
    out, i, n = [], 0, len(expr)
    while i < n:
        ch = expr[i]
        if ch == "(":
            close = _match_paren(expr, i)
            if close < 0:                       # 괄호가 안 맞으면 글자 그대로
                out.append(ch)
                i += 1
                continue
            inner = to_overbar_html(expr[i + 1:close])
            count = _primes(expr, close + 1)
            out.append(_wrap(inner, count) if count else f"({inner})")
            i = close + 1 + count
        elif ch.isalpha():
            m = _IDENT.match(expr, i)
            end = m.end()
            if end < n and expr[end] == "(":    # `Q(t-1)` 같은 이름
                close = _match_paren(expr, end)
                if close >= 0:
                    end = close + 1
            count = _primes(expr, end)
            out.append(_wrap(expr[i:end], count))
            i = end + count
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def active_low(name: str, first_use: bool, experiment: int) -> str:
    """R6. 맨 이름 + 첫 등장에만 `(Active Low)`. 실험9 만 교안 표기를 따른다."""
    if experiment == 9:
        return name
    return f"{name} (Active Low)" if first_use else name
