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
    raw = data.get('inputs', [])
    rows = [r for r in raw if _valid_input(r)] if isinstance(raw, list) else []
    names = {r['name'] for r in rows}
    return [f'입력 위치 없음: {name} — 결선도 생성기의 입력 위치 JSON을 확인한다'
            for name in inputs if name not in names]


def _side(rail):
    if '중앙' in rail or '가운데' in rail:
        return '가운데'
    return '왼쪽' if rail.startswith('좌') else '오른쪽'


def locations_html(png, inputs, *, feed=None):
    """위→아래 순서를 단순화한 위치도. feed=None은 완성본, dict는 단계 급전."""
    esc = html.escape
    data = _read(png)
    wanted = set(inputs)
    raw = data.get('inputs', [])
    rows = [r for r in raw if _valid_input(r)] if isinstance(raw, list) else []
    out = ['<aside class="io-locations" aria-label="입력과 LED 위치">',
           '<p class="io-title"><b>입력·LED 위치</b> · 결선도와 같은 방향으로 봐요</p>']
    missing = location_issues(png, inputs)
    if missing:
        names = ', '.join(name for name in inputs if name not in {r['name'] for r in rows})
        out.append('<p class="io-warning">입력 위치를 확인할 수 없어요. 결선도를 봐요.'
                   f' ({esc(names)})</p>')
    out.append('<section class="io-groups">')
    groups = {}
    for row in rows:
        groups.setdefault(row['x'], []).append(row)
    for _, group in sorted(groups.items()):
        group.sort(key=lambda r: (r['row'], r['name']))
        side = _side(group[0]['rail'])
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
    led_hint = ' 흐린 LED는 이 표에서 보지 않아요.' if feed is not None else ''
    out += ['</section>', '<p class="io-foot">위아래 순서를 나타내요. 간격은 줄였어요.'
            f' 흐린 입력은 이 표에서 바꾸지 않아요.{led_hint}</p>', '</aside>']
    return ''.join(out)
