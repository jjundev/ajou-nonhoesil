"""이름 없는 실험 결과 사진에 `<항목> <입력비트>.jpg` 이름을 붙인다.

입력 스위치는 사진에서 읽지 않는다(얽힌 점퍼 — `write-result-report/필기전사.md`).
대신 사진에서 읽은 LED 켜짐 패턴을 명세 진리표의 출력 열과 맞대 입력 행을 거꾸로 찾는다.
그래서 이 경로로 붙인 라벨의 확인 칸은 늘 `✓` 다 — 근거가 출력 하나뿐이라는 것을
`기록.md` 메모에 남기는 것은 스킬(`label-lab-photos`)의 몫이다.

- LED 순서·극성은 결선도 완성본 사이드카 JSON(`실험NN_<항목>_결선도_<이름>.json`)의 LED 사슬
  desc 에서 읽는다. 판 위 행 오름차순, 같은 행이면 좌 블록 먼저다. desc 에 `0 이면 켜짐` 이
  있으면 Active Low 다.
- 진리표는 그 항목의 `truth-table` · `role: record` 표다.

    python3 -m scripts.lab.photo_label 5 1-2                      # LED 읽는 순서만 출력
    python3 -m scripts.lab.photo_label 5 1-2 --read 'a.jpg=1000000000' ...
    python3 -m scripts.lab.photo_label 5 1-2 --read ... --apply   # 실험사진/ 으로 복사

종료 코드: 0 = 문제 없음(·복사함), 1 = 문제 있음(복사 안 함), 2 = 입력 오류.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from scripts.lab import config
from scripts.lab.photo_names import item_token, photo_name
from scripts.lab.spec_parser import parse_spec, split_indices

ROOT = Path(__file__).resolve().parents[2]

_LED_POS = re.compile(r"LED\((?:\S+ )?(?P<blk>[좌우]) [a-j](?P<row>\d+)")
_TABLE_COL = re.compile(r"진리표 (?P<table>T\d+) 의 (?P<sig>\S+) 열")
_PREFIX = re.compile(r"^(?P<sig>[^:\s]+):")
_ACTIVE_LOW = '0 이면 켜짐'


class LabelError(ValueError):
    pass


@dataclass
class Led:
    signal: str
    table: str | None
    block: str
    row: int
    active_low: bool


@dataclass
class Row:
    source: str
    pattern: str
    observed: dict
    status: str              # unique | ambiguous | none | duplicate | assigned
    bits: str | None = None
    candidates: list = field(default_factory=list)
    check: str | None = None  # '✓' 또는 관찰값 `A3=0 A2=0 …`


@dataclass
class Result:
    experiment: int
    token: str
    table_id: str
    inputs: list
    outputs: list
    leds: list
    rows: list
    order_sensitive: bool
    problems: list


def _exp_dir(experiment: int, root: Path) -> Path:
    return root / config.experiment_dir(experiment)


def led_order(experiment: int, token: str, root: Path = ROOT) -> list[Led]:
    """완성본 사이드카의 LED 를 판 위 순서(행 오름차순, 좌→우)로."""
    d = _exp_dir(experiment, root) / '결선도'
    name = re.compile(rf"^실험\d+_{re.escape(token)}_결선도_.+\.json$")
    stage = re.compile(r"_\d+(?:단계|걷기)_")   # `_1단계_Y0`·`_3걷기_인버터프로브` — 완성본이 아니다
    found = sorted(p for p in d.glob('*.json')
                   if name.match(p.name) and not stage.search(p.name)) if d.is_dir() else []
    if len(found) != 1:
        raise LabelError(f'{d} 에서 {token} 완성본 사이드카를 하나로 못 찾음: {[p.name for p in found]}')
    leds = []
    for step in json.loads(found[0].read_text(encoding='utf-8'))['steps']:
        desc = step.get('desc', '')
        pos = _LED_POS.search(desc)
        if not pos:
            continue
        col = _TABLE_COL.search(desc)
        pre = _PREFIX.match(desc)
        signal = col.group('sig') if col else (pre.group('sig') if pre else None)
        if not signal:
            continue
        leds.append(Led(signal, col.group('table') if col else None, pos.group('blk'),
                        int(pos.group('row')), _ACTIVE_LOW in desc))
    if not leds:
        raise LabelError(f'{found[0].name} 에 LED 사슬이 없음')
    return sorted(leds, key=lambda l: (l.row, 0 if l.block == '좌' else 1))


def _item_table(experiment: int, token: str, root: Path, table_id: str | None):
    spec = parse_spec(_exp_dir(experiment, root) / '체크리스트' / '명세.md')
    items = [i for i in spec.items if item_token(i.title) == token]
    if not items:
        raise LabelError(f'명세에 `실험 {token})` 항목이 없음')
    by_id = {t.id: t for t in spec.tables}
    tables = [by_id[t] for t in items[0].tables
              if by_id[t].kind == 'truth-table' and by_id[t].role == 'record']
    if table_id:
        tables = [t for t in tables if t.id == table_id]
    if len(tables) != 1:
        raise LabelError(f'{token} 의 기록용 진리표가 하나가 아님: {[t.id for t in tables]} — --table 로 고른다')
    return tables[0]


def _values(pattern: str, leds: list[Led]) -> dict:
    """LED 켜짐 비트(1=켜짐) → 신호 논리값."""
    out = {}
    for bit, led in zip(pattern, leds):
        lit = bit == '1'
        out[led.signal] = '0' if lit == led.active_low else '1'
    return out


def _label(table, inputs, outputs, observed, leds_signals):
    """관찰값과 출력이 같은 행들의 입력 비트."""
    cands = []
    for row in table.rows:
        if all(row[i] == observed[table.header[i]] for i in outputs if table.header[i] in leds_signals):
            cands.append(''.join(row[i] for i in inputs))
    return cands


def _check(table, outputs, bits, inputs, observed):
    for row in table.rows:
        if ''.join(row[i] for i in inputs) == bits:
            expected = {table.header[i]: row[i] for i in outputs}
            same = all(expected[k] == v for k, v in observed.items() if k in expected)
            return '✓' if same else ' '.join(f'{k}={v}' for k, v in observed.items())
    return None


def _resolve_with(table, inputs, outputs, leds, reads, assign, sequence):
    signals = {l.signal for l in leds}
    input_rows = [''.join(r[i] for i in inputs) for r in table.rows]
    rows = []
    for n, (src, pattern) in enumerate(reads):
        obs = _values(pattern, leds)
        given = assign.get(src) or assign.get(Path(src).name)
        if sequence and given is None:
            given = input_rows[n] if n < len(input_rows) else None
        if given is not None:
            if given not in input_rows:
                rows.append(Row(src, pattern, obs, 'none'))
                continue
            rows.append(Row(src, pattern, obs, 'assigned', given, [given],
                            _check(table, outputs, given, inputs, obs)))
            continue
        cands = _label(table, inputs, outputs, obs, signals)
        status = 'unique' if len(cands) == 1 else ('none' if not cands else 'ambiguous')
        bits = cands[0] if status == 'unique' else None
        if bits is not None and not re.fullmatch(r'[01]+', bits):
            status, bits = 'ambiguous', None   # 입력에 X — 파일명 비트가 될 수 없다
        rows.append(Row(src, pattern, obs, status, bits, cands,
                        _check(table, outputs, bits, inputs, obs) if bits else None))
    seen = {}
    for r in rows:
        if r.bits:
            seen.setdefault(r.bits, []).append(r)
    for same in seen.values():
        if len(same) > 1:
            for r in same:
                r.status = 'duplicate'
    return rows


def resolve(experiment: int, token: str, reads, *, assign=None, sequence=False,
            order='sidecar', table_id=None, root: Path = ROOT) -> Result:
    """`reads` = [(사진 경로, LED 켜짐 비트 — `led_order` 순서)]."""
    assign = dict(assign or {})
    table = _item_table(experiment, token, root, table_id)
    inputs, outputs = split_indices(table)
    leds = [l for l in led_order(experiment, token, root) if l.table in (None, table.id)]
    out_names = [table.header[i] for i in outputs]
    missing = [l.signal for l in leds if l.signal not in out_names]
    if missing:
        raise LabelError(f'LED 신호 {missing} 가 {table.id} 출력 열 {out_names} 에 없음')
    for src, pattern in reads:
        if not re.fullmatch(r'[01]+', pattern) or len(pattern) != len(leds):
            raise LabelError(f'{src}: 패턴 `{pattern}` — LED {len(leds)}개의 0/1 이어야 함')
    col_leds = sorted(leds, key=lambda l: out_names.index(l.signal))
    use = col_leds if order == 'columns' else leds
    alt = leds if order == 'columns' else col_leds
    rows = _resolve_with(table, inputs, outputs, use, reads, assign, sequence)
    order_sensitive = False
    if [l.signal for l in use] != [l.signal for l in alt] and not sequence:
        other = _resolve_with(table, inputs, outputs, alt, reads, assign, sequence)
        order_sensitive = any(a.bits != b.bits for a, b in zip(rows, other))
    problems = [f'{r.source}: {r.status}' for r in rows if r.status not in ('unique', 'assigned')]
    return Result(experiment, token, table.id, [table.header[i] for i in inputs], out_names,
                  use, rows, order_sensitive, problems)


def apply(result: Result, dest: Path) -> list[Path]:
    """문제가 없을 때만 원본을 남기고 `dest/<항목> <비트>.jpg` 로 복사. 기존 파일은 덮지 않는다."""
    if result.problems:
        raise LabelError('문제가 있어 복사하지 않음: ' + '; '.join(result.problems))
    targets = [(Path(r.source), dest / photo_name(result.token, r.bits)) for r in result.rows]
    clash = [t.name for _, t in targets if t.exists()]
    if clash:
        raise LabelError(f'이미 있는 파일: {clash}')
    dest.mkdir(parents=True, exist_ok=True)
    for src, t in targets:
        shutil.copy2(src, t)
    return [t for _, t in targets]


def _print(result: Result) -> None:
    print(f'실험{result.experiment:02d} {result.token} · {result.table_id} · 입력 {" ".join(result.inputs)}')
    print('LED 읽는 순서(판 위 행 오름차순): ' + ', '.join(
        f'{l.signal}({l.block}{l.row}{" ·0에서 켜짐" if l.active_low else ""})' for l in result.leds))
    if not result.rows:
        return
    print()
    print('| 원본 | 패턴 | 출력값 | 상태 | 입력 | 파일명 | 확인 칸 |')
    print('|---|---|---|---|---|---|---|')
    for r in result.rows:
        vals = ' '.join(f'{k}={r.observed[k]}' for k in result.outputs if k in r.observed)
        extra = f' 후보 {r.candidates}' if r.status == 'ambiguous' else ''
        name = photo_name(result.token, r.bits) if r.bits else '—'
        print(f'| {Path(r.source).name} | {r.pattern} | {vals} | {r.status}{extra} | '
              f'{r.bits or "—"} | {name} | {r.check or "—"} |')
    if result.order_sensitive:
        print('\nORDER-SENSITIVE: 진리표 열 순서로 LED 를 읽으면 라벨이 달라진다 — 실물 LED 순서를 확인할 것.')
    covered = {r.bits for r in result.rows if r.bits}
    print(f'\n진리표 {result.table_id} 행 중 사진이 있는 행: {len(covered)}')
    if result.problems:
        print('문제 ' + str(len(result.problems)) + '건: ' + '; '.join(result.problems))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('experiment', type=int)
    ap.add_argument('token', help='항목 토큰 (명세 제목의 `실험 N)` 번호, 예 1-2)')
    ap.add_argument('--read', action='append', default=[], metavar='경로=패턴',
                    help='LED 켜짐 비트(1=켜짐), 위 `LED 읽는 순서` 대로')
    ap.add_argument('--assign', action='append', default=[], metavar='경로=입력비트',
                    help='사용자가 알려 준 입력 조합(역산 대신 쓴다)')
    ap.add_argument('--sequence', action='store_true', help='--read 순서 = 진리표 행 순서')
    ap.add_argument('--order', choices=('sidecar', 'columns'), default='sidecar')
    ap.add_argument('--table')
    ap.add_argument('--apply', action='store_true', help='<실험NN>/실험사진/ 으로 복사')
    a = ap.parse_args(argv)
    try:
        reads = [tuple(x.rsplit('=', 1)) for x in a.read]
        assign = dict(x.rsplit('=', 1) for x in a.assign)
        res = resolve(a.experiment, a.token, reads, assign=assign, sequence=a.sequence,
                      order=a.order, table_id=a.table)
    except (LabelError, ValueError) as e:
        print('오류:', e, file=sys.stderr)
        return 2
    _print(res)
    if a.apply:
        try:
            for p in apply(res, _exp_dir(a.experiment, ROOT) / '실험사진'):
                print('복사:', p.relative_to(ROOT))
        except LabelError as e:
            print('복사 안 함:', e, file=sys.stderr)
            return 1
    return 1 if res.problems else 0


if __name__ == '__main__':
    sys.exit(main())
