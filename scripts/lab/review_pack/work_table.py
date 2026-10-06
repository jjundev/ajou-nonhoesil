"""학생이 채울 표(빈 <td> 가 있는 표)는 좌측 패널이 아니라 풀이 칸에 둔다. 그 표지(work-table)의 단일 출처."""
from pathlib import Path
import json
import re
import sys

FIELDS = ('original', 'conditions', 'ask')
MARK = 'work-table'
WRAP_RE = re.compile(r'<div class="(table-wrap(?: work-table)?)">(.*?)</div>', re.S)
EMPTY_CELL_RE = re.compile(r'<td\b[^>]*>(?:\s|&nbsp;|<br\s*/?>)*</td>')     # 머리칸(<th>)이 비어 있는 것은 채울 표가 아니다

def mark_work_tables(html):
    def fix(m):
        if EMPTY_CELL_RE.search(m.group(2)) and MARK not in m.group(1).split():
            return f'<div class="table-wrap {MARK}">{m.group(2)}</div>'
        return m.group(0)
    return WRAP_RE.sub(fix, html)

def check_work_tables(html, question_id):
    wraps = WRAP_RE.findall(html)
    if html.count('<table') != len(wraps):
        raise ValueError(question_id + ': 표는 <div class="table-wrap"> 안에 둬야 한다')
    for cls, body in wraps:
        if '<div' in body: raise ValueError(question_id + ': table-wrap 안에 다른 div 를 두지 않는다')
        empty, marked = bool(EMPTY_CELL_RE.search(body)), MARK in cls.split()
        if empty and not marked:
            raise ValueError(question_id + ': 빈 칸이 있는 표에 work-table 표지가 없다(좌측 패널에 남는다)')
        if marked and not empty:
            raise ValueError(question_id + ': work-table 표지가 붙은 표에 빈 칸이 없다')

def mark_payload(data):
    changed = 0
    for p in data['problems']:
        for key in FIELDS:
            before = p['html'][key]
            after = mark_work_tables(before)
            check_work_tables(after, p['id'])
            if after != before:
                p['html'][key] = after; changed += 1
    return changed

def migrate_workbook_json(path):
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    obj = json.loads(text)
    if not isinstance(obj, dict) or not all(k in obj for k in FIELDS): return False
    changed = False
    for key in FIELDS:
        after = mark_work_tables(obj[key])
        check_work_tables(after, path.stem)
        changed |= after != obj[key]; obj[key] = after
    if changed:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + ('\n' if text.endswith('\n') else ''), encoding='utf-8')
    return changed

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        target = Path(arg)
        for f in sorted(target.glob('*.json')) if target.is_dir() else [target]:
            if migrate_workbook_json(f): print('표지 추가:', f)
