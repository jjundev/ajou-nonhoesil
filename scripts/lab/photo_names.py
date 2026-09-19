"""실험 사진 파일명 규칙. 체크리스트 인쇄본과 사진 시트가 같은 규칙을 읽는다.

- 진리표 행 사진: `<항목> <입력비트>.jpg` (예 `1-2 000.jpg`, `3-1 11.jpg`).
  항목 토큰은 명세 항목 제목의 `실험 N)` 번호이고, 비트열은 그 표의 입력 열 순서다.
- 스텝표·파형 사진: `<항목> <표ID> <설명>.jpg` (예 `1-1 T1 xy.jpg`). 시트에
  들어가지 않는다 — 결과보고서가 따로 싣는다.

앞에 `실험03 ` 같은 접두어를 붙이면 어느 규칙에도 맞지 않는다(실험02 가 그랬다).

PIL 을 import 하지 않는다 — `render.py` 가 이 모듈을 읽는다.
"""
from __future__ import annotations

import re

FILE = re.compile(r"^(?P<item>[\d]+(?:-[\d]+)?)\s+(?P<bits>[01]+)\.(?:jpe?g|png)$", re.I)
SIDE = re.compile(r"^(?P<item>\d+(?:-\d+)?)\s+(?P<table>T\d+)(?:\s.*)?\.(?:jpe?g|png)$", re.I)
ITEM_TOKEN = re.compile(r"실험\s*(?P<tok>\d+(?:-\d+)?)\)")


def item_token(title: str) -> str | None:
    """`실험 1-2) 전가산기` → `1-2`. 번호가 없는 제목(FPGA 프로젝트)은 `None`."""
    m = ITEM_TOKEN.search(title or "")
    return m.group("tok") if m else None


def photo_name(token: str, bits: str) -> str:
    return f"{token} {bits}.jpg"
