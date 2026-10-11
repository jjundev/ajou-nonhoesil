"""보드 LED 순서와 단계별 급전 지도 — 체크리스트 단계 LED 점등 표의 재료.

`board_leds` 는 결선도 사이드카 `leds`(v2 만, 블록 좌→우·행 위→아래)를 ①②… 번호와 함께 읽는다.
`feeds_by_stage` 는 netlist `## 단계` 표의 `U<n> pin <p>→LED <tag> 급전` 표기를 단계마다 누적해
"이 단계 뒤 어느 LED 가 어느 노드를 보나" 를 낸다. 급전 핀을 `## 노드` 표의 `핀` 열에서 찾아 노드를
정하므로 임시 급전(실험05 C2 2단계, LED A2 가 D0' 를 본다)도 풀린다. 걷기 행은 그 행에 적힌 LED
급전을 지운다 (docs/plans/2026-10-11-체크리스트-LED-점등열-설계.md).

이 모듈은 `render`·`validate` 를 import 하지 않는다 — 둘 다 이것을 쓴다(순환 방지).
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

FEED = re.compile(r"(U\d+)\s*pin\s*(\d+)\s*→\s*LED\s*([A-Za-z0-9']+)\s*급전")
RELEASE = re.compile(r"→\s*LED\s*([A-Za-z0-9']+)")


@dataclass(frozen=True)
class Led:
    tag: str            # 보드에 찍힌 LED 이름
    at: str             # 신호 홀 주소 (예 '우 a6')
    active_low: bool    # 출력 0 이면 켜짐 (Negative Logic)
    index: int          # 1 부터, 보드 순서


def board_leds(png) -> list:
    """PNG 옆 사이드카의 `leds`. 파일이나 키가 없으면 [] — v1·재생성 전 JSON 은 옛 경로로 간다."""
    side = Path(png).with_suffix(".json")
    if not side.exists():
        return []
    data = json.loads(side.read_text(encoding="utf-8"))
    return [Led(tag=d["tag"], at=d["at"], active_low=bool(d["active_low"]), index=i)
            for i, d in enumerate(data.get("leds", []), start=1)]


def _plain(text) -> str:
    return (text or "").replace("*", "").replace("`", "")


def _pin_nodes(section) -> dict:
    """'U4 pin 3' → 노드 이름. 핀 칸의 공백을 한 칸으로 맞춘다."""
    return {" ".join(n["pin"].split()): n["name"] for n in section.nodes if n.get("pin")}


def _resolve(section, chip, pin, tag):
    """급전 하나 → 노드 이름. 핀이 `## 노드` 표에 없고 태그가 노드 이름이면 태그, 둘 다 아니면 None."""
    node = _pin_nodes(section).get(f"{chip} pin {pin}")
    if node is not None:
        return node
    if any(n["name"] == tag for n in section.nodes):
        return tag
    return None


def feeds_by_stage(section, start=None) -> list:
    """`section.stages` 와 같은 길이. 원소마다 그 단계 **뒤** 누적 {LED 태그: 노드 이름}.

    `start` 는 앞 회로에서 이어받는 지도다(`continues`). 못 푼 급전은 지도에 넣지 않는다 —
    `unresolved_feeds` 가 원문을 낸다.
    """
    current = dict(start or {})
    out = []
    for stage in section.stages:
        text = _plain(stage.get("todo"))
        if stage.get("walk"):
            for tag in RELEASE.findall(text):
                current.pop(tag, None)
        else:
            for chip, pin, tag in FEED.findall(text):
                node = _resolve(section, chip, pin, tag)
                if node is not None:
                    current[tag] = node
        out.append(dict(current))
    return out


def unresolved_feeds(section) -> list:
    """노드로 못 푼 급전 표기의 원문 — 검증 warn 용."""
    out = []
    for stage in section.stages:
        if stage.get("walk"):
            continue
        for m in FEED.finditer(_plain(stage.get("todo"))):
            if _resolve(section, *m.groups()) is None:
                out.append(m.group(0))
    return out


def watched(leds, feed, section) -> list:
    """보드 LED 중 지도에 있고 그 노드가 이 회로 `## 노드` 표에 있는 것 — 보드 순서.

    `continues` 회로는 앞 회로 지도를 이어받는데, 그 노드는 이 회로 표·기록표로 계산할 수 없다.
    """
    names = {n["name"] for n in section.nodes}
    return [led for led in leds if feed.get(led.tag) in names]


def lit(bit, active_low) -> bool:
    """논리값 → LED 가 켜지나. Negative Logic 이면 0 에서 켜진다."""
    return bit == 0 if active_low else bit == 1


def circled(n) -> str:
    """1→'①' … 20→'⑳'."""
    if not 1 <= n <= 20:
        raise ValueError(f"원문자 번호는 1~20 이다: {n}")
    return chr(0x2460 + n - 1)
