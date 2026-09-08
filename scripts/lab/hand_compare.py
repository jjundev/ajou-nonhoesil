"""손그림 결선도를 참조와 대조한다.

**홀 좌표가 아니라 넷으로 본다.** 칩이 참조보다 한 행 위에 놓여도 주변 배선이
같이 옮겨져 있으면 그림은 유효하다 — 2026-09-08 손그림 세 쪽이 전부 그랬다.
좌표를 직접 비교하면 멀쩡한 그림을 오답으로 찍는다. `regen_compare` 가 결선도
명세를 간선 집합으로 보는 것과 같은 이유다.

모델:

- **노드** — 단자대 스트립 `('T', 블록, 행, 반쪽)` 과 전원 레일
  `('R', 블록, 열)`. 레일은 행을 무시한다(한 도체다). 잭은 `('J', 색)`.
- **간선** — 배선(점퍼)만. LED·저항·칩 핀은 노드를 잇지 **않는다**. 부품이지
  단락이 아니다. 이걸 섞으면 LED 양끝이 한 넷이 되어 사슬 검사가 통째로 무의미해진다.
- **부착물** — 그 노드에 붙은 것. 핀·LED 다리·저항 다리·잭, 그리고 레일 극성.
- **핀 서명** — 그 핀이 속한 넷의 부착물 집합. 비교 단위다.

레일은 **극성으로만** 서명에 넣는다. 좌 GND 로 내렸든 중앙 GND 로 내렸든 같은
뜻이고, 브리지가 있으면 한 넷이다. 브리지 유무는 H8 이 따로 본다 — 한 결함을
두 번 보고하지 않기 위해서다.
"""

from dataclasses import dataclass

RAIL_COLS = frozenset({'gnd', 'vcc', 'mid_gnd', 'mid_vcc'})
VCC_COLS = frozenset({'vcc', 'mid_vcc'})
GND_COLS = frozenset({'gnd', 'mid_gnd'})
LEFT_HALF = frozenset('abcde')

GRADES = ('치명', '기능', '표기', '보류')


@dataclass
class HandFinding:
    rule: str      # 'H1' ~ 'H13'
    grade: str     # 치명 | 기능 | 표기 | 보류
    where: str
    message: str

    def __str__(self):
        return f"[{self.grade}] {self.rule} {self.where} — {self.message}"


def node_of(hole):
    """홀 -> 노드. 같은 행 a~e 는 한 노드, f~j 는 다른 한 노드."""
    block, col, row = hole
    if col in RAIL_COLS:
        return ('R', block, col)
    return ('T', block, row, 'L' if col in LEFT_HALF else 'R')


def _endpoint_node(ep):
    kind, val = ep
    return ('J', val) if kind == 'jack' else node_of(val)


class _UF(dict):
    def find(self, k):
        self.setdefault(k, k)
        while self[k] != k:
            self[k] = self[self[k]]
            k = self[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self[rb] = ra


def build_nets(diagram):
    """노드 -> 대표 노드. 배선만 잇는다."""
    uf = _UF()
    for hole in _all_holes(diagram):
        uf.find(node_of(hole))
    for w in diagram.wires:
        uf.union(_endpoint_node(w['frm']), _endpoint_node(w['to']))
    for _kind, a, b in diagram.bridges:
        uf.union(node_of(a), node_of(b))
    return {k: uf.find(k) for k in list(uf)}


def _all_holes(diagram):
    for ch in diagram.chips:
        yield from ch['pins'].values()
    for w in diagram.wires:
        for ep in (w['frm'], w['to']):
            if ep[0] == 'hole' and ep[1] is not None:
                yield ep[1]
    for l in diagram.leds:
        yield l['anode']
        yield l['cathode']
    for r in diagram.resistors:
        yield r['top']
        yield r['bottom']
    for _k, a, b in diagram.bridges:
        yield a
        yield b


def chip_keys(diagram):
    """칩 순서 -> 이름. 종류로 맺고 같은 종류가 둘이면 둘째부터 '#2'."""
    seen, out = {}, []
    for ch in diagram.chips:
        label = ch['label']
        seen[label] = seen.get(label, 0) + 1
        out.append(label if seen[label] == 1 else f"{label}#{seen[label]}")
    return out


def chip_key(diagram, index):
    """지정한 인덱스의 칩 이름."""
    return chip_keys(diagram)[index]


def attachments(diagram, nets=None):
    """대표 노드 -> 그 넷에 붙은 것들."""
    nets = nets if nets is not None else build_nets(diagram)
    out = {}

    def add(node, item):
        out.setdefault(nets.get(node, node), set()).add(item)

    for key, ch in zip(chip_keys(diagram), diagram.chips):
        for pin, hole in ch['pins'].items():
            add(node_of(hole), ('PIN', key, pin))
    for l in diagram.leds:
        add(node_of(l['anode']), ('LED', l['tag'], 'A'))
        add(node_of(l['cathode']), ('LED', l['tag'], 'K'))
    for r in diagram.resistors:
        add(node_of(r['top']), ('RES', r.get('tag', ''), 'T'))
        add(node_of(r['bottom']), ('RES', r.get('tag', ''), 'B'))
    for w in diagram.wires:
        for ep in (w['frm'], w['to']):
            if ep[0] == 'jack':
                add(('J', ep[1]), ('JACK', ep[1]))
    # 레일 극성. 레일 이름이 아니라 극성만 — 좌·중앙 어느 쪽인지는 저작자
    # 선택이고 브리지가 있으면 같은 넷이다
    for node in list(nets):
        if node[0] == 'R':
            pol = 'VCC' if node[2] in VCC_COLS else 'GND'
            add(node, ('RAIL', pol))
    return out


def signatures(diagram):
    """(칩 이름, 핀 번호) -> 그 핀 넷의 부착물. 자기 자신은 뺀다."""
    nets = build_nets(diagram)
    att = attachments(diagram, nets)
    out = {}
    for key, ch in zip(chip_keys(diagram), diagram.chips):
        for pin, hole in ch['pins'].items():
            rep = nets[node_of(hole)]
            out[(key, pin)] = frozenset(att.get(rep, set()) - {('PIN', key, pin)})
    return out
