"""격리 재생성물을 승인본과 대조한다.

`specdiff.compare_specs` 가 명세의 계약 필드를 보는 것과 짝을 이룬다 — 여기는
**결선도**와 **산문 재사용**을 본다. 결선도는 핀 번호를 줄 단위로 비교하지 않고
**간선 집합**으로 비교한다: `pin 3 → U1.pin4` 와 `pin 4 ← pin 3` 은 같은 선이고,
어느 칩 상자에 적었는가는 저작자 선택이다. 미사용 핀의 GND·개방 지정도 간선이라
누락이 그대로 드러난다.

칩은 U 번호가 아니라 **종류**(`74HC08`)로 맺는다. 원본이 `U3`, 재생성이 `U1` 로
불러도 같은 칩이다. 한 회로에 같은 종류가 둘이면 둘째부터 `#2` 를 붙인다.
"""

import re
from collections import Counter
from pathlib import Path

from .netlist_parser import parse_netlist
from .render import _circuit_body, _plain

_CHIP_HEAD = re.compile(r"U(\d+)\s*=\s*([A-Za-z0-9]+)")
_WIRE = re.compile(r"^pin\s*(\d+)\s*(←|→|<-|->)\s*(.+)$")
_UNUSED_HEAD = re.compile(r"미사용\s*(입력|출력)핀")
_OTHER_PIN = re.compile(r"U(\d+)[ .]*pin\s*(\d+)")
_SELF_PIN = re.compile(r"^pin\s*(\d+)$")
_INPUT = re.compile(r"입력\s*([A-Z]\w*)")
_LED = re.compile(r"LED_?([A-Z]\w*)|\bL(\d)\b")


def _clean(text: str) -> str:
    t = re.split(r"※", text)[0]
    t = re.sub(r"\(.*?\)", "", t)
    return re.sub(r"\s+", " ", t).strip(" ,·*`")


def _endpoint(text: str, umap: dict, self_key: str):
    t = _clean(text)
    m = _OTHER_PIN.search(t)
    if m:
        return ("PIN", umap.get(f"U{m.group(1)}", f"U{m.group(1)}"), int(m.group(2)))
    m = _SELF_PIN.match(t)
    if m:
        return ("PIN", self_key, int(m.group(1)))
    m = _INPUT.search(t)
    if m:
        return ("IN", m.group(1))
    m = _LED.search(t)
    if m:
        return ("LED", m.group(1) or f"L{m.group(2)}")
    if "VCC" in t or "+5V" in t:
        return ("VCC",)
    if "GND" in t:
        return ("GND",)
    if "개방" in t:
        return ("OPEN",)
    return ("TEXT", t)


def _chip_keys(nodes) -> dict:
    """`U<n>` → 칩키. 같은 종류가 둘이면 둘째부터 `#2`."""
    seen, umap = Counter(), {}
    for n in nodes:
        if n["type"] != "chip":
            continue
        m = _CHIP_HEAD.search(n["head"])
        if not m:
            continue
        kind = m.group(2)
        seen[kind] += 1
        umap[f"U{m.group(1)}"] = kind if seen[kind] == 1 else f"{kind}#{seen[kind]}"
    return umap


def _edges_of_chip(chip, umap) -> set:
    m = _CHIP_HEAD.search(chip["head"])
    if not m:
        return set()
    me = umap[f"U{m.group(1)}"]
    edges = set()

    def add(pin, target_text):
        edges.add(frozenset({("PIN", me, int(pin)), _endpoint(target_text, umap, me)}))

    for w in chip["wires"]:
        mw = _WIRE.match(_clean(w)) or _WIRE.match(w.strip())
        if mw:
            add(mw.group(1), mw.group(3))
    for u in chip["unused"]:
        # 불릿형은 `미사용 입력핀: pin 9, 10 → GND`, 헤딩형은 `_absorb_wiring` 이
        # 셀을 ` · ` 로 이은 `미사용 입력핀 11, 13 · GND · 플로팅 금지` 다. 핀은
        # 화살표나 `·` 앞 조각의 숫자 전부, 대상은 그 뒤에서 GND/VCC/개방을 찾는다.
        mu = _UNUSED_HEAD.search(u)
        if not mu:
            continue
        rest = u[mu.end():].replace("->", "→")
        head = re.split(r"→|·", rest, maxsplit=1)[0]
        tail = rest[len(head):]
        target = "GND" if "GND" in tail else "VCC" if "VCC" in tail else "개방" if "개방" in tail else tail
        for p in re.findall(r"\d+", head):
            add(p, target)
    for kind, table in chip["blocks"]:
        if kind != "table":
            continue
        for row in table.rows:
            cells = [_plain(c).strip() for c in row]
            if len(cells) < 2 or not cells[0]:
                continue
            pins = re.findall(r"\d+", re.sub(r"\(.*?\)", "", cells[0]))
            if not pins:
                continue
            for p in pins:
                add(p, cells[1])
    return edges


def pin_nets(netlist_path) -> dict:
    """항목 id → 간선 집합."""
    out = {}
    for sec in parse_netlist(Path(netlist_path)).circuits:
        nodes, _, _ = _circuit_body(sec)
        umap = _chip_keys(nodes)
        edges = out.setdefault(sec.item, set())
        for chip in (n for n in nodes if n["type"] == "chip"):
            edges |= _edges_of_chip(chip, umap)
    return out


def _fmt(edge) -> str:
    def one(e):
        if e[0] == "PIN":
            return f"{e[1]} pin {e[2]}"
        return e[0] if len(e) == 1 else f"{e[0]}:{e[1]}"
    a, b = sorted(edge, key=lambda e: (e[0] != "PIN", str(e)))
    return f"{one(a)} ↔ {one(b)}"


def compare_netlist_pins(original, regenerated) -> list:
    """차이 한 건에 한 줄. 같으면 빈 리스트."""
    a, b = pin_nets(original), pin_nets(regenerated)
    out = []
    for item in sorted(set(a) | set(b), key=str):
        if item not in b:
            out.append(f"{item}: 원본에만 있는 항목이다 (간선 {len(a[item])}개)")
            continue
        if item not in a:
            out.append(f"{item}: 재생성에만 있는 항목이다 (간선 {len(b[item])}개)")
            continue
        for e in sorted(a[item] - b[item], key=_fmt):
            out.append(f"{item}: 원본에만 — {_fmt(e)}")
        for e in sorted(b[item] - a[item], key=_fmt):
            out.append(f"{item}: 재생성에만 — {_fmt(e)}")
    return out
