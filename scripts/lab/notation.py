"""표기 규칙 (R3 정규화 · R5 보수 · R6 active-low).

**적용 범위가 이 모듈의 핵심이다.** `to_overbar_html` 은 부울식에만 쓴다.
표 헤더·신호명·**셀 값**에는 쓰지 않는다 — 실험6 의 `Q(t-1)'` 은 상태 토큰이지
부울식이 아니라서, 오버바로 승격하면 진리표가 망가진다.
"""

import re

DONT_CARE = "X"
_DC_TOKENS = ("x", "X", "-", "–", "—")

# `(A·B)'` 또는 `A'` 또는 `Q(t-1)'` — 괄호로 스코프가 명시된 것만 잡는다 (R5).
_PRIMED = re.compile(r"(\([^()]*\)|[A-Za-z][A-Za-z0-9_]*(?:\([^()]*\))?)'")


def normalize_cell(value, dont_care_column=False) -> str:
    """R3 정규화. don't-care 변형과 공백만 손댄다.

    **`H/L` ↔ `0/1` 변환은 절대 하지 않는다.** encoding 은 표의 속성이다.
    """
    s = " ".join(str(value).split())
    if s in _DC_TOKENS:
        return DONT_CARE
    if s == "" and dont_care_column:
        return DONT_CARE
    return s


def normalize_row(row, dont_care_columns=()) -> list:
    return [normalize_cell(v, i in dont_care_columns) for i, v in enumerate(row)]


def to_overbar_html(expr: str) -> str:
    """부울식의 `'` 를 오버바로 승격한다 (R5). **부울식에만 쓸 것.**"""
    def repl(m):
        inner = m.group(1)
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1]
        return f'<span class="ov">{inner}</span>'
    return _PRIMED.sub(repl, expr)


def active_low(name: str, first_use: bool, experiment: int) -> str:
    """R6. 맨 이름 + 첫 등장에만 `(Active Low)`. 실험9 만 교안 표기를 따른다."""
    if experiment == 9:
        return name
    return f"{name} (Active Low)" if first_use else name
