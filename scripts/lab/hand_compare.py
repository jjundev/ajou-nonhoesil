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

**사각지대: 레일 넷을 접으면서 참조에 없는 여분 부품 다리가 레일에 얹히는 것은
못 본다.** 접기 전에는 그 넷에 앉은 모든 핀이 "더 있다"로 시끄럽게 잡았지만,
같은 성질이 L1 저항 오배치처럼 단일 배선 오류를 허위 치명 3건으로 번지게 했다.
완화안(비핀 부착물도 남기기)은 실물 소음을 되살려 쓰지 않는다. 찬 홀에 꽂는
경우는 H2 가 여전히 잡으므로 완전한 무방비는 아니다. 이 사각지대를 닫으려면
"참조에 없는 부품"을 보는 새 규칙이 필요하다 — 서명 비교로는 안 된다.
"""

import os
import tempfile
from collections import Counter
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
    rule: str      # 'H1' ~ 'H15'
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
    """(칩 이름, 핀 번호) -> 그 핀 넷의 부착물. 자기 자신은 뺀다.

    **레일이 든 넷은 극성 토큰으로 접는다.** 입력은 GND 레일 홀에서 b열로
    들어오도록 그려져(`_input_jumper`) 입력 핀이 GND 넷 위에 앉는다 — 실험01
    NAND 참조에서 그 넷 부착물이 21개고 입력 핀 서명이 20개다. 접지 않으면
    레일 어디가 흔들려도 입력 핀 전부가 H6 을 낸다. 미사용 입력 한 가닥만
    빼도 H6 이 3건 헛났다.

    그 핀의 전기적 사실은 '어느 극성에 물렸는가' 가 전부이고, 같은 레일에
    누가 더 붙어 있는지는 그 핀과 무관하다. 레일끼리의 관계는 H3·H4·H8 이
    따로 본다. 레일이 없는 넷(칩 사이 연결·LED 사슬)은 그대로 열거한다 —
    거기가 신호선이라 낱낱이 봐야 한다.
    """
    nets = build_nets(diagram)
    att = attachments(diagram, nets)
    out = {}
    for key, ch in zip(chip_keys(diagram), diagram.chips):
        for pin, hole in ch['pins'].items():
            rep = nets[node_of(hole)]
            seen = att.get(rep, set()) - {('PIN', key, pin)}
            rails = {a for a in seen if a[0] == 'RAIL'}
            out[(key, pin)] = frozenset(rails) if rails else frozenset(seen)
    return out


# 손그림 검토가 정답으로 삼는 회로들. `main()` 의 dispatch 와 같은 이름을 쓴다.
# 실험02·03 은 2026-09-14 에 넣었다 — 그 전에는 `reference_diagram('e3_hs')` 가
# "모르는 회로 ID" 로 멈춰 두 주차 손그림을 검토할 수 없었다. 같은 날 조교 공지
# `_350547_1` 로 실험02 AC 특성·실험03 반가산기·반감산기를 하지 않게 되어 그 단계
# 그림 ID 가 빠졌다 — 완성본 `e2_tpd`·`e3_ha`·`e3_hs` 는 렌더러 회귀 사례로 남는다.
# 실험02·03 의 11개 모두 자기 대조에서 H12(서명 없음) 하나만 난다 — 참조 그림에는
# 서명이 없다.
CIRCUITS = ('e1_and', 'e1_or', 'e1_nand', 'e1_nor', 'e1_comb',
            'e1_or_s1', 'e1_nand_s1', 'e1_nand_s2', 'e1_nor_s1', 'e1_nor_s2',
            'e1_comb_s1', 'e1_comb_s2', 'e1_comb_s3',
            'e2_inv', 'e2_schmitt', 'e2_schmitt_s1', 'e2_tpd',
            'e3_ha', 'e3_fa', 'e3_fa_s1', 'e3_fa_s2',
            'e3_hs', 'e3_fs', 'e3_fs_s1')


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
    board = load_renderer().load_board(int(circuit_id.split("_", 1)[0][1:]))
    builder = getattr(board, f"build_{circuit_id}", None)
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
    """`wiring()` 출력 -> `Diagram`. 손그림 쪽과 같은 모양으로 맞춘다.

    브리지는 `wires` 에서 빼고 `bridges` 로만 보낸다 — 양쪽에 두면
    `check_holes` 가 같은 홀을 두 번 세어 H2 가 헛난다. 거르는 기준은
    **끝점 홀 쌍**이다. 배선 설명 문구로 맞추면 문구가 바뀔 때 조용히 깨지고,
    그때 폴백이 1행짜리 브리지를 내어 H1 이 회로마다 4건 헛난다.
    """
    bridges = [(kind, a, b) for kind, a, b in w['bridges']
               if a is not None and b is not None]
    bridge_ends = {frozenset((a, b)) for _kind, a, b in bridges}
    wires = [dict(x) for x in w['wires']
             if not (x['frm'][0] == 'hole' and x['to'][0] == 'hole'
                     and frozenset((x['frm'][1], x['to'][1])) in bridge_ends)]
    by_hole = {c['res_top']: c['tag'] for c in w['chains']}
    resistors = []
    for r in w['resistors']:
        new_r = dict(r)
        new_r['tag'] = by_hole.get(new_r['top'], new_r.get('label', ''))
        resistors.append(new_r)
    # 참조가 보드 안에 찍은 신호 이름 = 입력 이름 + LED 꼬리표 + 계측 지점 이름 (H15).
    # 계측 이름은 입력도 LED 도 없는 주차(실험02 `VIN`·`VOUT`·`CH1`)의 것이다.
    # **입력과 계측만 이름으로 중복을 지운다** — 입력은 점퍼마다가 아니라 이름마다
    # 배지가 하나다(e3 는 입력마다 좌·우 블록 점퍼가 둘). LED 꼬리표는 지우지
    # 않는다: 실험3 반감산기는 입력 B 와 출력 B 가 같은 글자라 둘 다 이름이다
    # (2026-09-14 — 전체를 `dict.fromkeys` 로 지우던 때는 `A B D` 로 줄어 출력 B 를
    # 빠뜨린 손그림이 통과했다).
    names = (list(dict.fromkeys(i['name'] for i in w['inputs']))
             + [c['tag'] for c in w['chains']]
             + list(dict.fromkeys(p['name'] for p in w.get('probes', []))))
    labels = [{'name': n, 'at': None} for n in names]
    return Diagram(
        chips=[dict(c) for c in w['chips']],
        wires=wires,
        leds=[dict(l) for l in w['leds']],
        resistors=resistors,
        chains=[dict(c) for c in w['chains']],
        unused_inputs=[dict(u) for u in w['unused_inputs']],
        unused_outputs=[dict(u) for u in w['unused_outputs']],
        bridges=bridges,
        overlaps=list(w['overlaps']),
        labels=labels,
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


def check_power(ref, hand):
    """H3 전원·접지 · H4 미사용 입력 접지 · H5 미사용 출력 개방.

    칩마다 이 넷을 세는 것이 손그림 검토의 뼈대다 — 회로가 무엇이든 항상
    같고, 빠지면 회로가 아예 안 돈다. 2026-09-08 손그림 3쪽에서 뒷단 칩
    오른쪽 다섯 가닥이 통째로 없었던 것을 잡는 자리다.
    """
    out = []
    hsig = signatures(hand)
    hkeys = set(chip_keys(hand))

    for key in chip_keys(ref):
        if key not in hkeys:
            out.append(HandFinding(
                'H3', '치명', key, '참조에 있는 칩이 손그림에 없다'))
            continue
        for pin, want, avoid in ((14, 'VCC', 'GND'), (7, 'GND', 'VCC')):
            sig = hsig.get((key, pin), frozenset())
            if ('RAIL', want) not in sig:
                out.append(HandFinding(
                    'H3', '치명', f'{key} pin {pin}',
                    f'{want} 레일에 닿지 않는다. '
                    f'{"전원이 안 들어가 칩이 동작하지 않는다" if pin == 14 else "접지가 없어 칩이 동작하지 않는다"}'))
            if ('RAIL', avoid) in sig:
                out.append(HandFinding(
                    'H3', '치명', f'{key} pin {pin}',
                    f'{avoid} 레일에도 닿아 있다 — 전원 단락이다'))

    for u in ref.unused_inputs:
        key, pin = u['chip'], u['pin']
        if key not in hkeys:
            continue
        if u.get('rail') is None:
            continue        # 개방(접지 생략) — 참조가 아무것도 요구하지 않는다
        want = 'VCC' if u.get('rail') == 'vcc' else 'GND'
        if ('RAIL', want) not in hsig.get((key, pin), frozenset()):
            out.append(HandFinding(
                'H4', '기능', f'{key} pin {pin}',
                f'미사용 입력인데 {want} 에 묶이지 않았다. '
                'CMOS 입력은 뜨면 안 된다'))

    for u in ref.unused_outputs:
        key, pin = u['chip'], u['pin']
        if key not in hkeys:
            continue
        sig = hsig.get((key, pin), frozenset())
        if sig:
            what = ', '.join(sorted(_describe(s) for s in sig))
            out.append(HandFinding(
                'H5', '치명', f'{key} pin {pin}',
                f'미사용 출력은 개방(NC)이어야 하는데 {what} 에 닿아 있다. '
                'GND 로 내리거나 출력끼리 묶으면 칩이 상한다'))
    return out



def _describe(item):
    """부착물 하나를 사람 말로."""
    if item[0] == 'PIN':
        return f'{item[1]} pin {item[2]}'
    if item[0] == 'LED':
        return f"{item[1]} LED {'애노드' if item[2] == 'A' else '캐소드'}"
    if item[0] == 'RES':
        return f"{item[1]} 저항 {'윗' if item[2] == 'T' else '아랫'}다리"
    if item[0] == 'RAIL':
        return f'{item[1]} 레일'
    if item[0] == 'JACK':
        return f'{item[1]} 전원잭'
    return str(item)


def check_signals(ref, hand):
    """H6 핀 서명 차이.

    전원(H3)·미사용(H4·H5)이 이미 본 것은 뺀다 — 한 결함을 두 번 보고하지
    않는다. 남는 것이 신호선이다: 입력, 단 간 연결, LED 도달.
    """
    out = []
    rsig, hsig = signatures(ref), signatures(hand)
    hkeys = set(chip_keys(hand))
    skip = {(u['chip'], u['pin']) for u in ref.unused_inputs}
    skip |= {(u['chip'], u['pin']) for u in ref.unused_outputs}

    for (key, pin), want in sorted(rsig.items()):
        if key not in hkeys or pin in (7, 14) or (key, pin) in skip:
            continue
        got = hsig.get((key, pin), frozenset())
        missing = want - got
        extra = got - want
        if not missing and not extra:
            continue
        parts = []
        if missing:
            parts.append('없다: ' + ', '.join(sorted(_describe(m) for m in missing)))
        if extra:
            parts.append('더 있다: ' + ', '.join(sorted(_describe(e) for e in extra)))
        note = _reference_hidden(ref, key, pin)
        out.append(HandFinding(
            'H6', '치명', f'{key} pin {pin}',
            ' · '.join(parts) + note))
    return out


def _reference_hidden(ref, key, pin):
    """참조 그림에서 그 핀으로 가는 선이 다른 선에 깔려 있으면 알린다.

    2026-09-08 5쪽에서 빠진 `A -> 74HC32 pin 1` 이 그런 선이었다. 원도가
    숨겨 놓은 것을 따라 그린 사람 탓으로 돌리면 다음에도 같은 자리가 빠진다.
    """
    needle = f'pin {pin}'
    base_key = key.split('#')[0]
    for w in ref.overlaps:
        if (key in w or base_key in w) and needle in w:
            return ' (참조 그림에서 다른 선에 깔려 잘 안 보이는 자리다)'
    return ''


def check_led_chains(ref, hand):
    """H7 LED 사슬이 이어져 있는가.

    신호 -> LED 애노드 -> 캐소드 -> 저항 윗다리 -> 아랫다리 -> GND 로 다섯
    자리가 사슬로 이어져야 한다. 어느 한 마디만 어긋나도 LED 는 안 켜지는데
    **칩 배선만 보면 멀쩡해 보인다.** 2026-09-08 1차 검토가 이 검사를 건너뛰어
    3·4쪽의 죽은 L1 을 통과시켰다.

    신호가 애노드에 도달하는지는 H6 이 이미 본다(핀 서명에 LED 애노드가
    들어간다). 여기는 캐소드부터 GND 까지를 본다.
    """
    out = []
    nets = build_nets(hand)
    att = attachments(hand, nets)
    by_tag = {c['tag']: c for c in hand.chains}

    for rc in ref.chains:
        tag = rc['tag']
        hcn = by_tag.get(tag)
        if hcn is None:
            out.append(HandFinding(
                'H7', '치명', tag,
                '참조에 있는 LED 사슬이 손그림에 없다 '
                '(LED 와 330Ω 을 같은 꼬리표로 적었는지 본다)'))
            continue
        k_net = nets.get(node_of(hcn['cathode']))
        t_net = nets.get(node_of(hcn['res_top']))
        if k_net != t_net:
            out.append(HandFinding(
                'H7', '치명', f"{tag} ({_addr(hcn['cathode'])})",
                f"LED 캐소드({_addr(hcn['cathode'])})와 "
                f"저항 윗다리({_addr(hcn['res_top'])})가 다른 줄이다. "
                'LED 가 안 켜지고 전류는 저항으로만 빠진다'))
        b_net = nets.get(node_of(hcn['res_bottom']))
        if ('RAIL', 'GND') not in att.get(b_net, set()):
            touched = ', '.join(sorted(_describe(a) for a in att.get(b_net, set())))
            out.append(HandFinding(
                'H7', '치명', f"{tag} ({_addr(hcn['res_bottom'])})",
                f"저항 아랫다리가 GND 레일에 닿지 않는다"
                + (f' — 대신 {touched} 에 닿아 있다' if touched else '')))
    return out


def check_rails(ref, hand):
    """H8 레일 연속성.

    레일쌍 넷은 서로 **별개 스트립**이다. +5V 를 한 레일에 넣고 칩 14번 핀을
    다른 레일에 물리면 그림은 완벽해 보이는데 전원이 안 간다. 렌더러도 같은
    이유로 `verify()` 에 연결성 검사를 넣었다 — 눈으로는 절대 안 잡힌다.
    """
    out = []
    nets = build_nets(hand)
    att = attachments(hand, nets)

    for pol, colset in (('VCC', VCC_COLS), ('GND', GND_COLS)):
        used = {}
        for node in nets:
            if node[0] == 'R' and node[2] in colset:
                rep = nets[node]
                if any(a[0] in ('PIN', 'JACK', 'RES', 'LED')
                       for a in att.get(rep, set())):
                    used.setdefault(rep, []).append(node)
        if len(used) > 1:
            groups = ' / '.join(
                '+'.join(sorted(f'{n[1]} {n[2]}' for n in g))
                for g in used.values())
            out.append(HandFinding(
                'H8', '치명', f'{pol} 레일',
                f'{pol} 레일이 끊겨 있다 — 브리지가 없다: {groups}. '
                '레일쌍은 별개 스트립이라 이어주지 않으면 전원이 안 간다'))
    return out


# 회로 ID -> 제목에 들어가야 할 말. 제목만 보고 다른 회로를 그렸다고
# 판정하지 않는다 — 제목이 틀렸는지 그림이 틀렸는지는 서명이 가른다.
# 실험02·03 은 결선도 제목(`set_header`)의 회로 이름에서 뽑았다.
CIRCUIT_WORDS = {
    'e1_and': ('AND',), 'e1_or': ('OR',),
    'e1_nand': ('NAND',), 'e1_nor': ('NOR',),
    'e1_comb': ('복합', 'COMB'),
    'e1_comb_s1': ('복합', 'COMB'), 'e1_comb_s2': ('복합', 'COMB'),
    'e1_comb_s3': ('복합', 'COMB'),
    'e2_inv': ('INVERTER', '인버터'),
    'e2_schmitt': ('SCHMITT', '슈미트'), 'e2_schmitt_s1': ('SCHMITT', '슈미트'),
    'e2_tpd': ('T_PD', 'TPD', 'AC 특성'),
    'e3_ha': ('반가산기', 'HALF ADDER'),
    'e3_fa': ('전가산기', 'FULL ADDER'), 'e3_fa_s1': ('전가산기', 'FULL ADDER'),
    'e3_fa_s2': ('전가산기', 'FULL ADDER'),
    'e3_hs': ('반감산기', 'HALF SUBTRACTOR'),
    'e3_fs': ('전감산기', 'FULL SUBTRACTOR'), 'e3_fs_s1': ('전감산기', 'FULL SUBTRACTOR'),
}


def _unshifted_elements(ref, hand, delta):
    """참조 좌표에 그대로 남은 손그림 요소 — (설명, 홀) 목록.

    LED·저항 다리는 꼬리표로 짝을 맞춘다. 배선은 꼬리표가 없어 끝점 홀 쌍으로
    맞추는데, 전체가 delta 만큼 밀린 그림에서는 레일 선이 우연히 참조의 다른
    선과 같은 자리에 올 수 있다(GND10→d10 이 밀려 GND11→d11 이 된다). 그래서
    **delta 만큼 되돌린 쌍이 참조에 있으면 '따라온 것'으로 보고 뺀다.** 잭
    끝점 배선은 칩 행에 앉을 수 없어 건너뛴다.
    """
    out = []
    ref_led = {(l['tag'], side): l[key] for l in ref.leds
               for side, key in (('A', 'anode'), ('K', 'cathode'))}
    for l in hand.leds:
        for side, key in (('A', 'anode'), ('K', 'cathode')):
            if ref_led.get((l['tag'], side)) == l[key]:
                out.append((_describe(('LED', l['tag'], side)), l[key]))

    ref_res = {(r.get('tag', ''), side): r[key] for r in ref.resistors
               for side, key in (('T', 'top'), ('B', 'bottom'))}
    for r in hand.resistors:
        for side, key in (('T', 'top'), ('B', 'bottom')):
            if ref_res.get((r.get('tag', ''), side)) == r[key]:
                out.append((_describe(('RES', r.get('tag', ''), side)), r[key]))

    ref_wires = {frozenset((w['frm'][1], w['to'][1])) for w in ref.wires
                 if w['frm'][0] == 'hole' and w['to'][0] == 'hole'}

    ref_rail_wires = set()
    for w in ref.wires:
        if w['frm'][0] == 'hole' and w['to'][0] == 'hole':
            a, b = w['frm'][1], w['to'][1]
            if b[1] in RAIL_COLS:
                ref_rail_wires.add((a, (b[0], b[1])))
            if a[1] in RAIL_COLS:
                ref_rail_wires.add((b, (a[0], a[1])))

    def back(hole):
        return (hole[0], hole[1], hole[2] - delta)

    for w in hand.wires:
        if w['frm'][0] != 'hole' or w['to'][0] != 'hole':
            continue
        a, b = w['frm'][1], w['to'][1]
        if frozenset((a, b)) not in ref_wires:
            continue
        if delta and frozenset((back(a), back(b))) in ref_wires:
            continue
        if delta and b[1] in RAIL_COLS and (back(a), (b[0], b[1])) in ref_rail_wires:
            continue
        if delta and a[1] in RAIL_COLS and (back(b), (a[0], a[1])) in ref_rail_wires:
            continue
        desc = f"{w.get('kind', '')} 배선 끝점".strip()
        out.append((desc, a))
        out.append((desc, b))
    return out


def check_chip_follow(ref, hand):
    """H14 칩 자리 변경을 안 따라간 요소.

    2026-09-09 시험 PDF 에서 74HC00 이 한 행 위(17행)에 있고 아래 배선은 전부
    따라갔는데 L1 저항만 참조 자리(d15→d17)에 남아 저항 아랫다리가 pin 1 행에
    앉았다. H7 이 증상("GND 에 안 닿는다")을, H10 이 행 차이를 냈지만 둘을 잇는
    줄이 없어 판정문만 읽으면 저항 한 줄 고치라는 뜻으로 읽혔다.

    거리 기준을 쓰지 않는다. **참조 좌표 그대로인 요소가 앉은 노드에서 이 칩의
    핀이 참조와 달라졌는가** 만 본다. 행 이동이면 참조에서 핀이 없던 노드에
    핀이 생기고(∅ → pin n), 뒤집힘이면 같은 노드의 핀 번호가 바뀐다(1 ↔ 14).
    충돌이 없으면 회로는 멀쩡하고 H10 표기만 남는다. 증상 줄(H3·H6·H7)은
    그대로 두고 이 줄을 더한다 — 같은 층위의 메아리가 아니라 원인 줄이다.
    """
    out = []
    rchips = dict(zip(chip_keys(ref), ref.chips))
    hchips = dict(zip(chip_keys(hand), hand.chips))
    for key, rch in rchips.items():
        hch = hchips.get(key)
        if hch is None:
            continue
        delta = hch['pin1_row'] - rch['pin1_row']
        hcol, rcol = hch.get('pin1_col', 'e'), rch.get('pin1_col', 'e')
        if delta == 0 and hcol == rcol:
            continue
        rpins = {node_of(h): p for p, h in rch['pins'].items()}
        hpins = {node_of(h): p for p, h in hch['pins'].items()}
        stuck = []
        for desc, hole in _unshifted_elements(ref, hand, delta):
            node = node_of(hole)
            r_pin, h_pin = rpins.get(node), hpins.get(node)
            if r_pin == h_pin:
                continue
            where = (f'pin {h_pin} 행' if h_pin is not None
                     else f'참조에서는 pin {r_pin} 행, 지금은 칩 밖')
            stuck.append(f'{desc} {_addr(hole)} ({where})')
        if not stuck:
            continue
        how = []
        if delta:
            how.append(f'참조보다 {delta:+d}행 옮겨졌')
        if hcol != rcol:
            how.append(f'pin 1 이 {hcol} 열로 뒤집혔')
        out.append(HandFinding(
            'H14', '치명', key,
            '고 '.join(how) + '는데 다음 요소가 참조 좌표에 남아 그 핀 행에 '
            '앉았다: ' + ', '.join(stuck)))
    return out


def check_placement(ref, hand):
    """H9 브리지 행 차이 · H10 칩 자리 차이(행·방향). 둘 다 표기다.

    칩이 밀리거나 뒤집혀도 배선이 함께 옮겨져 있으면 그림은 유효하다. 그래도
    알리는 이유는 체크리스트의 좌표 표기와 어긋나기 때문이다 — 같이 제출한다면
    맞춰 두는 편이 낫다. 옮겨진 자리를 배선이 **안** 따라간 것은 H14 가 본다.
    """
    out = []
    rmap, hmap = {}, {}
    for key, ch in zip(chip_keys(ref), ref.chips):
        rmap[key] = (ch['pin1_row'], ch.get('pin1_col', 'e'))
    for key, ch in zip(chip_keys(hand), hand.chips):
        hmap[key] = (ch['pin1_row'], ch.get('pin1_col', 'e'))
    for key, (rrow, rcol) in rmap.items():
        got = hmap.get(key)
        if got is None:
            continue
        hrow, hcol = got
        if hrow != rrow:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 pin 1 이 {rrow}행인데 손그림은 {hrow}행이다 '
                f'({hrow - rrow:+d}행). 배선이 함께 옮겨져 있으면 회로는 맞다'))
        if hcol != rcol:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 pin 1 이 {rcol} 열인데 손그림은 {hcol} 열이다 — '
                '칩이 뒤집혀 있다. 배선이 함께 뒤집혀 있으면 회로는 맞다'))

    # 메시지가 행만 말하므로 **행만 비교한다.** 종류까지 넣어 비교하면 전사가
    # `kind` 를 빠뜨렸을 때 '[29,30]인데 [29,30]이다' 라는 자기모순이 나온다
    rb = sorted({a[2] for _k, a, _b in ref.bridges})
    hb = sorted({a[2] for _k, a, _b in hand.bridges})
    if rb and hb and rb != hb:
        # 경고는 방향을 본다. round2 는 28·29행(참조보다 위)인데 '30행 아래'
        # 경고를 받았다 — 맞지 않는 조언이다
        below = max(hb) > max(rb)
        tail = ('레일이 가운데서 끊긴 실물 보드라면 참조보다 아래 놓인 브리지는 '
                '전원을 못 올린다' if below
                else '도면상 같은 노드라 회로에는 영향이 없다')
        out.append(HandFinding(
            'H9', '표기', '레일 브리지',
            f'참조는 {rb}행인데 손그림은 {hb}행이다. {tail}'))
    return out


def check_paperwork(ref, hand):
    """H11 제목 · H12 자필 기재 · H13 전사 보류."""
    out = []
    words = CIRCUIT_WORDS.get(hand.circuit or ref.circuit, ())
    title = (hand.title or '').upper()
    if words and title and not any(w.upper() in title for w in words):
        out.append(HandFinding(
            'H11', '표기', '제목',
            f'제목 {hand.title!r} 에 {" 또는 ".join(words)} 가 없다. '
            '회로와 제목 중 어느 쪽이 틀렸는지 함께 본다'))
    if not hand.signed:
        out.append(HandFinding(
            'H12', '표기', '자필 기재',
            '학번·이름·날짜가 없다. 참조 도면이 제출 조건으로 요구한다'))
    for hole in sorted(hand.uncertain):
        out.append(HandFinding(
            'H13', '보류', _addr(hole),
            '전사가 확신하지 못한 끝점이다. 그 자리를 확대해 다시 읽는다'))
    return out


def check_labels(ref, hand):
    """H15 입력·출력 신호 이름 표기. 참조가 보드 안에 찍은 이름이 손그림에 있는가.

    2026-09 실험01 예보 조교 감점(-1): "결선도에 입력 A·B·C 위치 표기가 없어
    확인하기 어렵다." 회로는 돌지만 채점에서 실제로 깎이므로 표기가 아니라 기능
    등급으로 제출을 막는다.

    **이름을 개수까지 센다. 어느 홀 옆에 적었는지는 보지 않는다** — 이 검사기는
    행이 밀려도 넷이 같으면 통과시키는 설계라 좌표 판정은 그 원칙과 부딪힌다.
    자리는 전사 규칙이 지킨다(보드 밖 여백의 글자는 전사하지 않는다). 개수를 세는
    이유는 실험3 반감산기다 — 입력 `B` 와 출력 `B` 가 같은 글자라 집합으로 보면
    출력 `B` 를 빠뜨린 그림이 통과한다. 대소문자는 가리지 않고, 손그림에만 있는
    이름은 알리지 않는다.
    """
    have = Counter(lb['name'].upper() for lb in hand.labels)
    want = Counter(lb['name'].upper() for lb in ref.labels)
    shown = {}
    for lb in ref.labels:
        shown.setdefault(lb['name'].upper(), lb['name'])
    out = []
    for key, n in want.items():
        short = n - have[key]
        if short <= 0:
            continue
        name = shown[key]
        if n == 1:
            msg = (f"신호 이름 {name!r} 이 그림 위에 없다. 입력은 점퍼 끝 옆, "
                   "출력은 LED 옆, 계측 지점 이름은 그 스트립 끝에 적는다")
        else:
            msg = (f"신호 이름 {name!r} 이 참조보다 {short}개 적다(참조 {n} · 그림 "
                   f"{have[key]}). 같은 글자가 입력과 출력에 따로 있다 — 입력은 점퍼 "
                   "끝 옆, 출력은 LED 옆에 각각 적는다")
        out.append(HandFinding('H15', '기능', name, msg))
    return out


# 규칙을 여기 순서대로 돈다. 새 규칙은 이 목록에 올린다 — 함수만 만들고
# 목록에 안 올리면 검사가 조용히 빠진다. 2026-09-08 회차에서 LED 사슬 검사를
# 통째로 건너뛴 것이 바로 그 실패였다
_RULES = [check_holes, check_power, check_signals, check_led_chains,
          check_rails, check_chip_follow, check_placement, check_paperwork,
          check_labels]


def compare(ref, hand):
    """참조와 손그림을 견준다. 심한 것부터 정렬해서 준다."""
    out = []
    for rule in _RULES:
        out.extend(rule(ref, hand))
    order = {g: i for i, g in enumerate(GRADES)}
    return sorted(out, key=lambda f: (order.get(f.grade, 9), f.rule))


BLOCKING = ('치명', '기능')


def verdict(findings):
    """치명·기능이 없으면 제출 가능. 표기는 막지 않고 별도 줄로 알린다."""
    return '수정 필요' if any(f.grade in BLOCKING for f in findings) else '제출 가능'


def judgment_markdown(pages, round_no):
    """쪽별 판정 문서. `pages` 는 (쪽 번호, 회로 ID, 결함들, 손그림) 목록."""
    every = [f for _p, _c, fs, _h in pages for f in fs]
    lines = [f'# 손그림 결선도 검토 round{round_no}', '',
             f'**총평: {verdict(every)}**', '']

    counts = {g: sum(1 for f in every if f.grade == g) for g in GRADES}
    lines += ['| 등급 | 건수 |', '|---|---|']
    lines += [f'| {g} | {counts[g]} |' for g in GRADES]
    lines.append('')

    for page, circuit, findings, hand in pages:
        lines.append(f'## {page}쪽 · {circuit} · {hand.title or "제목 없음"}')
        lines.append('')
        lines.append(f'판정: **{verdict(findings)}**')
        lines.append('')
        if not findings:
            lines += ['참조와 다른 곳이 없다.', '']
            continue
        lines += ['| 등급 | 규칙 | 자리 | 내용 |', '|---|---|---|---|']
        for f in findings:
            msg = f.message.replace('|', r'\|')
            lines.append(f'| {f.grade} | {f.rule} | {f.where} | {msg} |')
        lines.append('')
    return '\n'.join(lines)

