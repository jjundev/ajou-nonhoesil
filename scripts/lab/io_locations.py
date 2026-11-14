"""표 옆 입력·LED 위치 안내. 위치는 결선도 JSON에서만 읽는다.

입력의 순위는 조작하는 레일 끝의 x·행으로 정하고, 표의 열 순서와 분리한다.
보드에서 쓰는 전체 점퍼를 남겨 부분 입력 표에서도 '위에서 몇째'가 바뀌지 않는다.
"""
import html
import json
from pathlib import Path

from .leds import circled

_ORDINALS = ('첫째', '둘째', '셋째', '넷째', '다섯째', '여섯째', '일곱째', '여덟째', '아홉째', '열째')


def _read(png):
    if png is None:
        return {}
    try:
        data = json.loads(Path(png).with_suffix('.json').read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _valid_input(row):
    return (isinstance(row, dict) and isinstance(row.get('name'), str)
            and isinstance(row.get('at'), str) and isinstance(row.get('rail'), str)
            and isinstance(row.get('x'), (int, float))
            and isinstance(row.get('row'), int) and 1 <= row['row'] <= 63)


def location_issues(png, inputs):
    """누락은 조용히 숨기지 않고 렌더러·검사기가 같은 기준으로 알린다."""
    data = _read(png)
    names = {r['name'] for r in _input_rows(data)}
    return [f'입력 위치 없음: {name} — 결선도 생성기의 입력 위치 JSON을 확인한다'
            for name in inputs if name not in names]


def _side(rail):
    if '중앙' in rail or '가운데' in rail:
        return '가운데'
    return '왼쪽' if rail.startswith('좌') else '오른쪽'


# 표 머리 이름 → 결선도 JSON 의 입력 이름. 실험07 스텝표가 `SERIAL DATA` 로 쓰는 입력을
# 결선도는 `D` 로 꽂는다. 위치도와 '입력 설정' 칸이 같은 표로 이름을 맞춘다.
ALIASES = {'SERIAL DATA': 'D'}


def location_name(name):
    return ALIASES.get(name, name)


def _input_rows(data):
    raw = data.get('inputs', [])
    return [r for r in raw if _valid_input(r)] if isinstance(raw, list) else []


def _groups(rows):
    """점퍼 열(x)마다 한 묶음, 묶음 안은 위→아래(행). 위치도와 입력 칸의 유일한 순서 출처."""
    groups = {}
    for row in rows:
        groups.setdefault(row['x'], []).append(row)
    out = []
    for _, group in sorted(groups.items()):
        group.sort(key=lambda r: (r['row'], r['name']))
        out.append((_side(group[0]['rail']), group))
    return out


def input_columns(png, names):
    """'입력 설정' 칸을 위치도 모양으로 쌓을 열 — [(묶음 이름, [표 이름…]), …].

    표 이름은 그대로 돌려주고 정렬만 결선도 JSON 으로 한다. 이 표에 없는 점퍼와 빈 묶음은
    뺀다. 위치를 못 찾는 입력이 하나라도 있으면 None — 일부만 옮겨 쌓으면 순서가 두 출처로
    갈리므로, 렌더러는 명세 순서의 한 줄 목록으로 돌아간다(위치도는 경고를 따로 띄운다).
    """
    if png is None or not names:
        return None
    by_location = {location_name(n): n for n in names}
    rows = _input_rows(_read(png))
    if set(by_location) - {r['name'] for r in rows}:
        return None
    columns = []
    for side, group in _groups(rows):
        picked = [by_location[r['name']] for r in group if r['name'] in by_location]
        if picked:
            columns.append((side, picked))
    return columns


def location_order(png, names):
    """입력 **열** 자리 순서 — `names` 의 색인을 위치도와 같은 묶음·위→아래로 늘어놓는다.

    진리표·단계 표의 열을 다시 세울 때 쓴다. 한 신호를 두 점퍼로 꽂은 보드는 처음 나온 자리를
    쓴다(열은 하나다). 위치를 못 찾거나 이름이 겹치면(입력·출력이 같은 글자인 표는 입력만
    넘기지만, 방어한다) 명세 순서 그대로 — `input_columns` 와 같은 물러섬이다.
    """
    names = list(names)
    identity = list(range(len(names)))
    columns = input_columns(png, names) if len(set(names)) == len(names) else None
    if columns is None:
        return identity
    order = []
    for _, picked in columns:
        for name in picked:
            k = names.index(name)
            if k not in order:
                order.append(k)
    return order if sorted(order) == identity else identity


def locations_html(png, inputs, *, feed=None):
    """위→아래 순서를 단순화한 위치도. feed=None은 완성본, dict는 단계 급전."""
    esc = html.escape
    data = _read(png)
    wanted = set(inputs)
    rows = _input_rows(data)
    out = ['<aside class="io-locations" aria-label="입력과 LED 위치">',
           '<p class="io-title"><b>입력·LED 위치</b></p>']
    missing = location_issues(png, inputs)
    if missing:
        names = ', '.join(name for name in inputs if name not in {r['name'] for r in rows})
        out.append('<p class="io-warning">입력 위치를 확인할 수 없어요. 결선도를 봐요.'
                   f' ({esc(names)})</p>')
    out.append('<section class="io-groups">')
    for side, group in _groups(rows):
        out.append(f'<section class="io-group"><b>{side} 입력 점퍼</b>'
                   '<span class="io-direction">위 ↓ 아래</span><ol>')
        for i, row in enumerate(group):
            ordinal = _ORDINALS[i] if i < len(_ORDINALS) else f'{i + 1}번째'
            muted = '' if row['name'] in wanted else ' io-muted'
            out.append(f'<li class="io-input{muted}" title="{esc(row["rail"])}">'
                       f'<span class="io-rank">{ordinal}</span>'
                       f'<span class="io-symbol">●</span><strong>{esc(row["name"])}</strong></li>')
        out.append('</ol></section>')
    led_groups = {}
    for index, led in enumerate(data.get('leds', []), 1):
        block = '왼쪽' if led['at'].startswith('좌') else '오른쪽'
        led_groups.setdefault(block, []).append((index, led))
    for block, group in led_groups.items():
        out.append(f'<section class="io-group io-led-group"><b>{block} LED</b>'
                   '<span class="io-direction">위 ↓ 아래</span><ol>')
        for index, led in group:
            tag = led['tag']
            muted = ' io-muted' if feed is not None and tag not in feed else ''
            note = (f'<small>지금은 {esc(feed[tag])} 확인</small>'
                    if feed is not None and tag in feed and feed[tag] != tag else '')
            out.append(f'<li class="io-led{muted}"><span class="io-symbol">○</span>'
                       f'<span>{circled(index)}</span><strong>{esc(tag)}</strong>{note}</li>')
        out.append('</ol></section>')
    out += ['</section>', '</aside>']
    return ''.join(out)
