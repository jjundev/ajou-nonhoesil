"""손그림 전사 파일을 읽어 `Diagram` 으로 만든다.

전사는 **사람(vision)이 적는다.** 선 끝점 추출을 자동화하지 않는 이유는 검정이
신호선·칩 글자·저항 지그재그를 전부 겸해서 색 분할이 되지 않기 때문이다.
대신 읽은 결과를 파일로 남긴다 — 재검토 때 무엇을 잘못 읽었는지 짚을 수 있다.

주소 문법은 렌더러 `addr()` 출력과 **같은 말**이다 ('좌 b10',
'좌 GND레일10행'). 양쪽을 같은 말로 맞춰야 비교가 된다. 렌더러가 '보드밖(입력)'
이나 '분기점' 을 낼 수도 있는데 그건 홀이 아니므로 전사에서는 거절한다.

JSON 을 쓴다. `requirements-dev.txt` 에 PyYAML 이 없고 `scripts/lab/` 은 표준
라이브러리만 쓴다는 정책이 그 파일에 적혀 있다.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .hand_grid import load_renderer

TERMINAL_COLS = tuple('abcdefghij')
RAIL_NAMES = {
    'GND레일': 'gnd', 'VCC레일': 'vcc',
    '중앙GND레일': 'mid_gnd', '중앙VCC레일': 'mid_vcc',
}
BLOCKS = {'좌': 'left', '우': 'right'}
# 가운데 레일을 두 블록이 나눠 쓰는 판형 — 렌더러 `shared_columns()` 가 비지 않는 판형과 같다
# (`test_hand_transcript` 가 맞댄다). 이 모듈은 표준 라이브러리만 써서 렌더러를 띄우지 않는다
SHARED_MID_BOARDS = frozenset({'v2'})
JACK_COLORS = {'빨강': 'red', '노랑': 'yellow', '회색': 'gray'}
ROW_MIN, ROW_MAX = 1, 63

_TERMINAL = re.compile(r'^(좌|우)\s+([a-j])(\d{1,2})$')
_RAIL = re.compile(r'^(?:(좌|우)\s+)?(중앙GND레일|중앙VCC레일|GND레일|VCC레일)(\d{1,2})행$')
_JACK = re.compile(r'^전원잭\((빨강|노랑|회색)\)$')

REQUIRED_KEYS = ('page', 'circuit', 'chips', 'wires')


class TranscriptError(ValueError):
    """전사 파일을 읽을 수 없다."""


@dataclass
class Diagram:
    """한 쪽의 결선. 손그림과 참조가 **같은 모양**으로 담긴다."""
    chips: list = field(default_factory=list)
    wires: list = field(default_factory=list)
    leds: list = field(default_factory=list)
    resistors: list = field(default_factory=list)
    chains: list = field(default_factory=list)
    unused_inputs: list = field(default_factory=list)
    unused_outputs: list = field(default_factory=list)
    bridges: list = field(default_factory=list)
    overlaps: list = field(default_factory=list)
    uncertain: set = field(default_factory=set)
    # 연결 대상을 판독할 수 있는 신호 이름. at 은 글자 위치가 아닌 대상 홀. H15 가 본다
    labels: list = field(default_factory=list)
    title: str = ""
    circuit: str = ""
    page: int = 0
    board: str = 'v1'       # 판형 — 참조는 빌더에서, 손그림은 승인 결선의 판형을 받는다


def chip_pins(block, pin1_row, pin1_col='e', n=14):
    """DIP-n 이 꽂히는 홀. pin 1~n/2 는 pin 1 열, n/2+1~n 은 건너편 열을 거꾸로 올라온다.

    `pin1_col='e'` 가 렌더러 `draw_chip()` 이 꽂는 자리와 같아야 한다 —
    `test_핀_배치가_렌더러와_같다`(14핀)·`test_16핀_핀_배치가_참조_빌더와_같다` 가 그것을
    묶어 둔다. `'f'` 는 노치가 아래를 보게 그린 칩이다. 채널을 걸치지 않는 열은 핀 모델이
    없어 거절한다. `n` 은 핀 수 — 호출자가 칩 모델 표(`dip_pins`)에서 얻어 넘긴다.
    """
    across = {'e': 'f', 'f': 'e'}
    if pin1_col not in across:
        raise ValueError(
            f"pin 1 열은 e 또는 f 다 — DIP 칩은 채널을 걸친다: {pin1_col!r}")
    pins = {}
    for i in range(n // 2):
        pins[i + 1] = (block, pin1_col, pin1_row + i)
        pins[n - i] = (block, across[pin1_col], pin1_row + i)
    return pins


def parse_address(text, board='v1'):
    """'좌 b10' -> ('hole', ('left', 'b', 10)). 홀이 아니면 거절한다.

    `board` 는 승인 결선의 판형이다. 가운데 레일을 두 블록이 나눠 쓰는 판형(v2)에서는
    `중앙GND레일9행`·`좌 중앙GND레일9행`·`우 중앙GND레일9행` 이 모두 한 레일
    `('left', 'mid_gnd', 9)` 다 — 렌더러가 소속을 `left` 로 정했다. v1 은 좌·우 중앙 레일이
    따로라 블록을 적어야 한다.
    """
    s = (text or "").strip()
    m = _JACK.match(s)
    if m:
        return ('jack', JACK_COLORS[m.group(1)])
    m = _TERMINAL.match(s)
    if m:
        row = int(m.group(3))
        _check_row(row, s)
        return ('hole', (BLOCKS[m.group(1)], m.group(2), row))
    m = _RAIL.match(s)
    if m:
        row = int(m.group(3))
        _check_row(row, s)
        side, col = m.group(1), RAIL_NAMES[m.group(2)]
        if col.startswith('mid_') and board in SHARED_MID_BOARDS:
            return ('hole', ('left', col, row))
        if side is None:
            raise TranscriptError(
                f"{s!r} — {board} 판형에서는 이 레일이 좌·우에 따로 있다. "
                f"'좌 {m.group(2)}{row}행' 처럼 블록을 적는다")
        return ('hole', (BLOCKS[side], col, row))
    raise TranscriptError(
        f"홀 주소로 읽을 수 없다: {s!r} — "
        "'좌 b10' · '좌 GND레일10행' · '전원잭(빨강)' 꼴로 적는다 "
        "(v2 가운데 레일은 '중앙GND레일10행')")


def _check_row(row, s):
    if not ROW_MIN <= row <= ROW_MAX:
        raise TranscriptError(f"{ROW_MIN}~{ROW_MAX}행 밖이다: {s!r}")


def parse_transcript(path, board='v1'):
    """전사 JSON -> `Diagram`. `board` 는 승인 결선의 판형(`hand_grid.expected_board()`)."""
    path = Path(path)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise TranscriptError(f"{path.name} 을 읽을 수 없다: {e}") from e

    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        raise TranscriptError(
            f"{path.name} 에 {', '.join(missing)} 이(가) 없다")

    chips = []
    for ch in obj['chips']:
        try:
            label = ch['label']
            pin1_row = ch['pin1_row']
        except KeyError as e:
            raise TranscriptError(f"칩 항목에 필수 키 {e} 가 없다: {ch}") from e
        block = BLOCKS.get(ch.get('block'), ch.get('block'))
        if block not in ('left', 'right'):
            raise TranscriptError(f"블록이 좌/우가 아니다: {ch.get('block')!r}")
        try:
            row = int(pin1_row)
        except (ValueError, TypeError) as e:
            raise TranscriptError(f"pin1_row 가 정수가 아니다: {pin1_row!r}") from e
        _check_row(row, f"{label} pin1_row={row}")
        # pin 1 열. 없으면 e — 기존 전사가 전부 그렇다. 뒤집어 그린 칩은 f 다.
        # 채널을 안 걸친 칩(a~d·g~j)은 핀 모델이 없어 전사가 못 담는다 —
        # 그 칩의 pin 1 홀을 `uncertain` 에 올리면 H13 보류로 사람에게 간다
        pin1_col = ch.get('pin1_col', 'e')
        if pin1_col not in ('e', 'f'):
            raise TranscriptError(
                f"{label} pin1_col={pin1_col!r} — pin 1 열은 e 또는 f 다. "
                "채널을 안 걸친 칩은 pin 1 홀을 uncertain 에 올린다")
        # 핀 수는 칩 모델 표에서 — 74HC42 는 16, 모르는 이름은 14(렌더러 그리기와 같다).
        # 14 를 박아 두면 16핀 칩의 pin 8~16 이 한 행씩 어긋나 H3·H6 가 헛난다(2026-10-07 실험05).
        n = load_renderer().dip_pins(label)
        last = row + n // 2 - 1
        _check_row(last, f"{label} pin {n // 2} 행={last}")
        chips.append({'label': label, 'block': block,
                      'pin1_row': row, 'pin1_col': pin1_col,
                      'pins': chip_pins(block, row, pin1_col, n)})

    wires = []
    for w in obj['wires']:
        try:
            w_from = w['from']
            w_to = w['to']
        except KeyError as e:
            raise TranscriptError(f"배선 항목에 필수 키 {e} 가 없다: {w}") from e
        wires.append({'kind': w.get('color', ''), 'desc': w.get('desc', ''),
                      'frm': parse_address(w_from, board), 'to': parse_address(w_to, board)})

    leds = []
    for l in obj.get('leds', []):
        try:
            tag = l['tag']
            anode = l['anode']
            cathode = l['cathode']
        except KeyError as e:
            raise TranscriptError(f"LED 항목에 필수 키 {e} 가 없다: {l}") from e
        leds.append({'tag': tag,
                     'anode': parse_address(anode, board)[1],
                     'cathode': parse_address(cathode, board)[1]})

    resistors = []
    for r in obj.get('resistors', []):
        try:
            top = r['top']
            bottom = r['bottom']
        except KeyError as e:
            raise TranscriptError(f"저항 항목에 필수 키 {e} 가 없다: {r}") from e
        resistors.append({'tag': r.get('tag', ''), 'label': r.get('label', '330Ω'),
                          'top': parse_address(top, board)[1],
                          'bottom': parse_address(bottom, board)[1]})

    by_tag = {l['tag']: l for l in leds}
    chains = []
    for r in resistors:
        led = by_tag.get(r['tag'])
        if led is None:
            raise TranscriptError(
                f"저항 꼬리표 {r['tag']!r} 에 맞는 LED 가 없다. "
                "LED 와 저항은 같은 꼬리표로 묶는다")
        chains.append({'tag': r['tag'], 'anode': led['anode'],
                       'cathode': led['cathode'],
                       'res_top': r['top'], 'res_bottom': r['bottom']})

    bridges = []
    for b in obj.get('bridges', []):
        try:
            b_from = b['from']
            b_to = b['to']
        except KeyError as e:
            raise TranscriptError(f"브리지 항목에 필수 키 {e} 가 없다: {b}") from e
        a = parse_address(b_from, board)[1]
        z = parse_address(b_to, board)[1]
        bridges.append((b.get('kind', ''), a, z))

    uncertain = {parse_address(u, board)[1] for u in obj.get('uncertain', [])}

    # 선택 키다 — 2026-09-12 이전 전사에는 없다. 없으면 빈 목록이고 H15 가 이름마다 잡는다
    labels = []
    for lb in obj.get('labels', []):
        try:
            name = lb['name']
        except KeyError as e:
            raise TranscriptError(f"이름표 항목에 필수 키 {e} 가 없다: {lb}") from e
        name = str(name).strip()
        if not name:
            raise TranscriptError(f"이름표 항목의 name 이 비어 있다: {lb}")
        at = parse_address(lb['at'], board)[1] if lb.get('at') else None
        labels.append({'name': name, 'at': at})

    return Diagram(chips=chips, wires=wires, leds=leds, resistors=resistors,
                   chains=chains, bridges=bridges, uncertain=uncertain,
                   labels=labels,
                   title=obj.get('title', ''), circuit=obj['circuit'],
                   page=int(obj['page']), board=board)
