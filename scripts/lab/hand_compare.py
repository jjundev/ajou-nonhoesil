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

import os
import tempfile
from dataclasses import dataclass

from .hand_grid import load_renderer
from .hand_transcript import Diagram

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


# 손그림 검토가 정답으로 삼는 회로들. `main()` 의 dispatch 와 같은 이름을 쓴다
CIRCUITS = ('e1_and', 'e1_or', 'e1_nand', 'e1_nor', 'e1_comb',
            'e1_comb_s1', 'e1_comb_s2', 'e1_comb_s3')


class CompareError(ValueError):
    """참조를 꺼내거나 대조할 수 없다."""


def reference_diagram(circuit_id):
    """렌더러 빌더를 돌려 그 그림의 결선을 `Diagram` 으로 꺼낸다.

    빌더가 PNG 를 쓰긴 하지만 우리가 필요한 건 `wiring()` 이다. 임시 폴더에
    쓰고 버린다 — `export()` 가 `verify()` 를 부르므로 `overlaps` 도 이때 찬다.
    """
    if circuit_id not in CIRCUITS:
        raise CompareError(
            f"모르는 회로 ID: {circuit_id!r}. "
            f"쓸 수 있는 것: {', '.join(CIRCUITS)}")
    mod = load_renderer()
    builder = getattr(mod, f"build_{circuit_id}", None)
    if builder is None:
        raise CompareError(f"빌더가 없다: build_{circuit_id}")
    with tempfile.TemporaryDirectory() as tmp:
        bb = builder(os.path.join(tmp, f"{circuit_id}.png"))
    if bb is None:
        raise CompareError(
            f"build_{circuit_id} 가 렌더러를 돌려주지 않는다 — "
            "빌더 끝에 `return bb` 가 있어야 한다")
    return _from_wiring(bb.wiring(), circuit_id)


def _from_wiring(w, circuit_id):
    """`wiring()` 출력 -> `Diagram`. 손그림 쪽과 같은 모양으로 맞춘다."""
    bridges = []
    wires = []
    for x in w['wires']:
        if x.get('desc') == '레일 브리지' and x['frm'][0] == 'hole' and x['to'][0] == 'hole':
            bridges.append((x['kind'], x['frm'][1], x['to'][1]))
        else:
            wires.append(dict(x))
    if not bridges:
        bridges = [(kind, a, b) for kind, a, b in w['bridges']
                   if a is not None and b is not None]
    by_hole = {c['res_top']: c['tag'] for c in w['chains']}
    for r in w['resistors']:
        r['tag'] = by_hole.get(r['top'], r.get('label', ''))
    return Diagram(
        chips=[dict(c) for c in w['chips']],
        wires=wires,
        leds=[dict(l) for l in w['leds']],
        resistors=[dict(r) for r in w['resistors']],
        chains=[dict(c) for c in w['chains']],
        unused_inputs=[dict(u) for u in w['unused_inputs']],
        unused_outputs=[dict(u) for u in w['unused_outputs']],
        bridges=bridges,
        overlaps=list(w['overlaps']),
        circuit=circuit_id)



def _addr(hole):
    """홀 -> 사람이 읽는 주소. 판정문에 그대로 들어간다."""
    block, col, row = hole
    prefix = '좌' if block == 'left' else '우'
    names = {'gnd': 'GND레일', 'vcc': 'VCC레일',
             'mid_gnd': '중앙GND레일', 'mid_vcc': '중앙VCC레일'}
    if col in RAIL_COLS:
        return f'{prefix} {names[col]}{row}행'
    return f'{prefix} {col}{row}'


def check_holes(ref, hand):
    """H1 끝점이 실제 홀인가 · H2 한 홀에 리드 하나인가. (`ref` 는 쓰지 않는다)

    렌더러 `verify()` 의 R1·R2 를 손그림 쪽으로 옮긴 것이다. 그림대로 꽂을 수
    없는 결선은 무엇을 뜻하든 틀린 것이라 서명 비교보다 먼저 본다.

    규칙 함수는 전부 `(ref, hand)` 를 받는다 — `_RULES` 가 한 줄로 도는
    대신 규칙마다 분기를 두면 규칙이 늘 때마다 그 분기가 커진다.
    """
    mod = load_renderer()
    out, leads = [], {}

    def put(hole, what):
        block, col, row = hole
        if not 1 <= row <= mod.ROW_MAX:
            out.append(HandFinding(
                'H1', '치명', _addr(hole),
                f'{row}행은 판에 없다 (1~{mod.ROW_MAX}행)'))
            return
        if col in RAIL_COLS and row in mod.RAIL_GAP_ROWS:
            out.append(HandFinding(
                'H1', '치명', _addr(hole),
                f'레일 {row}행에는 홀이 없다 — 5홀씩 묶여 빈 행이다. '
                f'{what} 를 이웃 행으로 옮긴다'))
            return
        key = (block, col, row)
        if key in leads:
            out.append(HandFinding(
                'H2', '치명', _addr(hole),
                f'한 홀에 둘: {leads[key]} + {what}. '
                '같은 행 a~e 는 한 노드라 옆 홀로 옮기면 된다'))
        else:
            leads[key] = what

    for key, ch in zip(chip_keys(hand), hand.chips):
        for pin, hole in ch['pins'].items():
            put(hole, f'{key} pin {pin}')
    for w in hand.wires:
        for ep in (w['frm'], w['to']):
            if ep[0] == 'hole' and ep[1] is not None:
                put(ep[1], f"{w.get('kind', '')} 배선".strip())
    for l in hand.leds:
        put(l['anode'], f"{l['tag']} LED 애노드")
        put(l['cathode'], f"{l['tag']} LED 캐소드")
    for r in hand.resistors:
        put(r['top'], f"{r.get('tag', '')} 저항 윗다리".strip())
        put(r['bottom'], f"{r.get('tag', '')} 저항 아랫다리".strip())
    for kind, a, b in hand.bridges:
        put(a, f'{kind} 레일 브리지')
        put(b, f'{kind} 레일 브리지')
    return out


# 규칙을 여기 순서대로 돈다. 새 규칙은 이 목록에 올린다 — 함수만 만들고
# 목록에 안 올리면 검사가 조용히 빠진다. 2026-09-08 회차에서 LED 사슬 검사를
# 통째로 건너뛴 것이 바로 그 실패였다
_RULES = [check_holes]


def compare(ref, hand):
    """참조와 손그림을 견준다. 심한 것부터 정렬해서 준다."""
    out = []
    for rule in _RULES:
        out.extend(rule(ref, hand))
    order = {g: i for i, g in enumerate(GRADES)}
    return sorted(out, key=lambda f: (order.get(f.grade, 9), f.rule))

