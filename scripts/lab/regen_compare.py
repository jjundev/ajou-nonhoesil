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
        head = re.sub(r"\(.*?\)", "", head)
        for p in re.findall(r"(?<![A-Za-z])\d+", head):
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


from . import config, validate                      # noqa: E402
from .spec_parser import parse_spec                 # noqa: E402
from .specdiff import compare_specs, uncovered_tables   # noqa: E402

_SENT_SPLIT = re.compile(r"(?<=[.。다\)])\s|\|")


def _sentences(path, min_len):
    t = re.sub(r"\s+", " ", Path(path).read_text(encoding="utf-8"))
    return {p.strip() for p in _SENT_SPLIT.split(t) if len(p.strip()) >= min_len}


def shared_sentences(regen_paths, corpus_paths, min_len=25) -> list:
    """재생성물과 코퍼스가 공유하는 문장. 격리의 실증이다 — 답을 못 봤으면
    칩 이름·프론트매터 조각 말고는 겹칠 수 없다."""
    r, c = set(), set()
    for p in regen_paths:
        r |= _sentences(p, min_len)
    for p in corpus_paths:
        c |= _sentences(p, min_len)
    return sorted(r & c, key=len, reverse=True)


_CELL = re.compile(r"행\d+ \S+: 원본 '([^']*)' / 재생성 '([^']*)'")
_ENC_PAIRS = {("0", "L"), ("1", "H"), ("L", "0"), ("H", "1")}


def classify_spec_diffs(diffs) -> dict:
    """`compare_specs` 의 줄을 다섯 갈래로 나눈다. 갈래마다 뜻이 다르다 —
    `id_shift` 는 표가 하나 늘거나 줄어 번호가 밀린 것, `encoding` 은 `0/1`↔`H/L`
    치환으로 설명되는 셀, `cell` 은 진짜 값 차이, `title` 은 이름만 다른 것."""
    out = {"id_shift": [], "encoding": [], "title": [], "cell": [], "other": []}
    for d in diffs:
        if d.startswith("[표 ID"):
            out["id_shift"].append(d)
        elif " encoding: " in d:
            out["encoding"].append(d)
        elif " title: " in d:
            out["title"].append(d)
        else:
            m = _CELL.search(d)
            if m and (m.group(1), m.group(2)) in _ENC_PAIRS:
                out["encoding"].append(d)
            elif m:
                out["cell"].append(d)
            else:
                out["other"].append(d)
    return out


def judgment_markdown(experiment: int, regen_dir, corpus_dirs=()) -> str:
    """판정 초안. 자동으로 셀 수 있는 것만 센다 — 제목 갈림의 옳고 그름과
    산문은 사람이 본다."""
    root = Path(config.experiment_dir(experiment))
    regen_dir = Path(regen_dir)
    o_spec, r_spec = root / "체크리스트/명세.md", regen_dir / "체크리스트/명세.md"
    o_net, r_net = root / "결선도/netlist.md", regen_dir / "결선도/netlist.md"

    diffs = classify_spec_diffs(compare_specs(o_spec, r_spec))
    total = sum(len(v) for v in diffs.values())
    unc = uncovered_tables(r_spec)
    findings = validate.check_netlist(r_net, parse_spec(r_spec))
    by_level = {lvl: [f for f in findings if f.level == lvl] for lvl in ("error", "warn", "info")}
    pins = compare_netlist_pins(o_net, r_net)
    corpus = [o_spec, o_net]
    for d in corpus_dirs:
        corpus += sorted(Path(d).glob("*.md"))
    shared = shared_sentences([r_spec, r_net], corpus)

    L = [f"# 실험{experiment} 격리 재생성 판정 초안", "",
         "이 회차는 세션 메모리 주입 아래서 돌았다.", "",
         f"## 1. compare_specs 차이 {total}건"]
    for k, label in (("id_shift", "ID 밀림"), ("encoding", "인코딩 치환"), ("title", "제목"),
                     ("cell", "**셀 실차이**"), ("other", "기타")):
        L.append(f"- {label}: {len(diffs[k])}건")
        L += [f"    - {x}" for x in diffs[k][:20]]
    L += ["", f"대조 밖 표 {len(unc)}건"] + [f"- {x}" for x in unc]
    L += ["", f"## 2. check_netlist error {len(by_level['error'])}건 · warn {len(by_level['warn'])}건 · info {len(by_level['info'])}건 (회로 메타 `diagram` 등은 안 센다)"]
    L += [f"- {f}" for lvl in ("error", "warn", "info") for f in by_level[lvl]]
    L += ["", f"## 3. 핀 간선 차이 {len(pins)}건"] + [f"- {x}" for x in pins]
    L += ["", f"## 4. 문장 교집합 {len(shared)}건 (25자 이상)"] + [f"- {s[:120]}" for s in shared[:15]]
    L += ["", "## 5. 사람이 볼 것",
          "- 제목 차이는 가리키는 대상이 바뀌었는지부터 본다 (런북 V1 절의 title 기준).",
          "- 머리말 표(토큰 규약)와 산문은 도구가 안 본다. 원본과 나란히 읽는다.",
          "- 에이전트 보고 3항(첫 실행 error/warn/info)으로 **규칙이 막았나 / 검사가 잡았나**를 가른다.",
          "",
          "> 구조 검증이 통과했다는 것은 파서가 읽을 수 있다는 뜻이고, 내용이 맞다는 뜻이 아니다.", ""]
    return "\n".join(L)
