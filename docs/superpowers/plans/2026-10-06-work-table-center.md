# 빈 진리표를 중앙 풀이 공간으로 옮기기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 문제지·해설지에서 학생이 채울 빈 표(진리표 등)를 좌측 회색 패널이 아니라 가운데 점격자 풀이 칸 맨 위에 보이게 하고, 같은 실수가 다시 생기지 않게 막는다.

**Architecture:** 작성 HTML의 표 래퍼에 `work-table` 표지를 단다. 표지는 `work_table.py` 한 곳에서 (a) 빈 `<td>`가 있는 표에 자동으로 달고 (b) 빌드·재렌더 때 표지와 빈 칸이 어긋나면 오류를 낸다. 템플릿(해시 고정)은 `workbook_render`의 덧씌우기 패치로만 바꿔, 표지 달린 표를 `.page-center`의 `.work` 앞으로 옮기고 쪽 맞춤이 넘침을 검사하게 한다. 이미 발행된 팩은 `rerender`가 payload를 표지 달아 다시 만든다.

**Tech Stack:** Python 3 표준 라이브러리, pytest, Playwright(Chrome), 해시 고정 HTML 템플릿(`problem.html`, `answer.html`) + `workbook_render.LOCAL_PATCHES`.

**Spec:** 이 문서 맨 아래 「설계 요약」(2026-10-06 grill-yourself 결과. Needs-you #7~#9는 추천값으로 확정).

## 실행 후 변경 (2026-10-06, 구현 완료·main 병합)

아래 본문은 실행 전 계획이다. 실행하면서 다음이 달라졌다. 본문과 충돌하면 이 목록이 맞다.

1. **해설지는 표를 패널에 둔다(#8 번복).** 해설지에도 옮기면 실험04 `q-mux2-graded`의 7단계 풀이가 3번째 단으로 밀려 넘쳤다(풀이 높이 약 138px 감소). 사용자가 "해설지는 패널에 둔다"를 골랐다. 그래서 `TEMPLATE_PATCHES`는 `problem.html` 하나뿐이고 `ANSWER_CENTER` 앵커는 없다. 해설지 쪽 테스트는 `.work-block`이 없고 표가 패널에 있고 `data-overflow=''`임을 확인한다. CSS(`.work-block` 규칙)는 두 템플릿 공통이지만 해설지에서는 쓰이지 않는다.
2. **대상이 실험01·03까지 넓어졌다.** 실험01(`q-tt3-4row`, `q-tt3-8row`, `q-xor2-tt`)과 실험03(`q-ha-table`, `q-fa-table`, `q-fs-table`)에도 채울 표가 있었다. 두 실험은 작성 JSON이 저장소에 없어 발행 payload를 `rerender`로만 갱신했다. 발행본 기준 대상은 5개 팩 16문항이다. 테스트의 `PUBLISHED`가 이 집합을 고정한다(작성 JSON 기준 `EXPECTED`는 실험04·05의 10문항).
3. **빈 칸 판정을 넓혔다.** `EMPTY_CELL_RE`는 `<td\b[^>]*>(?:\s|&nbsp;|<br\s*/?>)*</td>`다. 속성이 붙은 `<td>`, `&nbsp;`, `<br>`만 든 칸도 채울 표로 본다. `table-wrap` 안에 다른 `<div>`가 있으면 `check_work_tables`가 거부한다.
4. **이미지가 든 블록은 지우지 않는다.** `MOVE_TABLES`는 표를 옮긴 뒤 블록에 글자가 없고 `img, table, .katex`도 없을 때만 블록을 지운다.
5. 발행본 5개 팩(실험01~05)을 모두 `rerender`하고 PDF 10개를 다시 만들었다. 합성 브라우저 테스트는 문제지(`problems`)만 대상으로 하고, 해설지는 별도 테스트로 패널 유지를 확인한다.
6. 병합 후 알려진 한계: `?`·`___` 같은 자리표시자로 쓴 빈 칸은 판정하지 못한다. 새 실험 팩의 표지 문항은 `PUBLISHED`에 직접 적어야 한다.

## Global Constraints

- 템플릿 원본 `.claude/skills/logic-lab-review-pack/assets/workbook/problem.html`, `answer.html`과 `provenance.json` 해시는 바꾸지 않는다. 변경은 렌더 때 덧씌우기로만 한다.
- 패치 앵커가 템플릿에서 정확히 1번 나오지 않으면 렌더가 `ValueError`로 실패해야 한다(조용히 넘기지 않는다).
- 문제은행·원문 자산·`evidence/`는 수정하지 않는다.
- 문제지 payload/DOM에 `solution`, `notes`, 증거가 없다는 기존 계약을 유지한다.
- 작성 HTML에는 `style`(img의 `max-width:100%;height:auto` 제외)·`on*`·`<a href>`(문제 쪽)를 쓰지 않는다. `class="table-wrap work-table"`는 허용된다.
- 표를 옮긴 자리에 라벨을 새로 붙이지 않는다(#7). 해설지는 패널에 둔다(#8, 실행 중 번복: 위 「실행 후 변경」 1). 빈 칸이 없는 표(배선표 등)는 패널에 둔다(#9).
- 표가 칸에 안 들어가면 글자를 줄이지 않고 `data-overflow`로 발행을 막는다.
- 문서·주석·커밋 메시지는 한국어, 기존 코드의 한 줄 압축 스타일을 따른다.

## Review Focus

1. **빈 머리칸(`<th></th>`)은 채울 표가 아니다** — `['D0D1D2D3','','Excess-3']`처럼 머리가 빈 표(`q-1of4-excess3`)는 `<td>`가 비어 있을 때만 표지가 붙어야 한다. (Task 1 테스트)
2. **표만 있던 블록은 빈 라벨을 남기지 않는다** — `q-mux4`는 「조건」이 표뿐이다. 옮긴 뒤 「조건」 라벨만 남으면 안 된다. (Task 3 브라우저 테스트)
3. **넓은·긴 표가 중앙에서 잘리지 않는다** — 11열(`q-excess3-enc-exam`), 9열 8행(`q-dec3x8`), 회로도+표(`q-74hc148-table`). 안 들어가면 `data-overflow`로 드러나야 한다. (Task 3 합성 테스트, Task 4 실제 팩 테스트)
4. **표가 둘이거나 표지 없는 표가 섞인 문항** — 둘 다 옮기되 순서를 지키고, 표지 없는 표는 패널에 남는다. (Task 3 브라우저 테스트)
5. **재실행해도 결과가 같다** — `rerender`·`mark_work_tables`를 두 번 돌려도 파일이 더 바뀌지 않는다. (Task 1, Task 4)

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/lab/review_pack/work_table.py` (신규) | 표지 규칙의 단일 출처: `mark_work_tables`, `check_work_tables`, `mark_payload`, `migrate_workbook_json`, CLI |
| `scripts/lab/review_pack/workbook_content.py` (수정) | 빌드 때 `check_work_tables` 호출 |
| `scripts/lab/review_pack/workbook_rerender.py` (수정) | 재렌더 때 `mark_payload` 호출 |
| `scripts/lab/review_pack/workbook_render.py` (수정) | 템플릿별 패치(`TEMPLATE_PATCHES`)와 CSS 추가 |
| `docs/learning-pack-source/실험04/refresh_workbook.py`, `실험05/build_run.py` (수정) | 생성기가 JSON을 쓸 때 표지를 달기 |
| `docs/learning-pack-source/실험04/workbook/*.json`, `실험05/workbook/*.json` (수정) | 대상 10문항에 표지 |
| `복습노트/실험04`, `실험05`의 기출문제·기출풀이 HTML/MD/PDF (재생성) | 발행본 |
| `tests/test_review_pack_work_table.py` (신규) | 규칙·말뭉치 테스트 |
| `tests/test_review_pack_workbook_render.py`, `tests/test_review_pack_workbook_browser.py` (수정) | 패치·브라우저 테스트 |
| `.claude/skills/logic-lab-review-pack/SKILL.md`, `references/workbook.md` (수정) | 작성 규칙·패치 개수 문서 |

대상 10문항 — 실험04: `q-demux4`, `q-mux2-graded`, `q-mux4` / 실험05: `q-1of4-excess3`, `q-74hc148-table`, `q-dec3x8`, `q-excess3-enc-6row`, `q-excess3-enc-exam`, `q-prio-exam`, `q-prio-onehot`.

작업 시작 전 브랜치를 만든다: `git switch -c feat/work-table-center`

---

### Task 1: 표지 규칙 모듈 `work_table.py`

**Files:**
- Create: `scripts/lab/review_pack/work_table.py`
- Test: `tests/test_review_pack_work_table.py`

**Interfaces:**
- Consumes: 없음(표준 라이브러리만).
- Produces:
  - `FIELDS = ('original','conditions','ask')`
  - `mark_work_tables(html: str) -> str` — 빈 `<td>`가 있는 `table-wrap` div에 `work-table` 클래스를 단다. 멱등.
  - `check_work_tables(html: str, question_id: str) -> None` — 어긋나면 `ValueError`.
  - `mark_payload(data: dict) -> int` — payload(`data['problems'][i]['html'][field]`)를 표지 달고 검사, 바뀐 필드 수를 돌려준다.
  - `migrate_workbook_json(path) -> bool` — 문항 JSON 한 개를 제자리 수정, 바뀌었으면 True.
  - CLI: `python -m scripts.lab.review_pack.work_table <JSON 파일 또는 폴더>...`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/test_review_pack_work_table.py
import json
import pytest
from scripts.lab.review_pack.work_table import (
    mark_work_tables, check_work_tables, mark_payload, migrate_workbook_json)

BLANK = '<div class="table-wrap"><table><thead><tr><th>A</th><th>Y</th></tr></thead><tbody><tr><td>0</td><td></td></tr></tbody></table></div>'
FULL = BLANK.replace('<td></td>', '<td>1</td>')
MARKED = BLANK.replace('"table-wrap"', '"table-wrap work-table"')

def test_mark_adds_class_only_to_tables_with_an_empty_cell():
    assert mark_work_tables(BLANK) == MARKED
    assert mark_work_tables(FULL) == FULL

def test_mark_is_idempotent_and_keeps_surrounding_text():
    text = '<p>앞</p>' + BLANK + '<p>뒤</p>'
    once = mark_work_tables(text)
    assert once == '<p>앞</p>' + MARKED + '<p>뒤</p>'
    assert mark_work_tables(once) == once

def test_empty_header_cell_is_not_a_fill_in_table():
    head_blank = '<div class="table-wrap"><table><thead><tr><th>D</th><th></th></tr></thead><tbody><tr><td>0</td><td>1</td></tr></tbody></table></div>'
    assert mark_work_tables(head_blank) == head_blank
    check_work_tables(head_blank, 'q')

def test_check_rejects_blank_table_left_unmarked():
    with pytest.raises(ValueError, match='q-x'): check_work_tables(BLANK, 'q-x')

def test_check_rejects_marked_table_without_empty_cell():
    with pytest.raises(ValueError, match='q-x'): check_work_tables(FULL.replace('"table-wrap"', '"table-wrap work-table"'), 'q-x')

def test_check_rejects_table_outside_wrapper():
    with pytest.raises(ValueError, match='q-x'): check_work_tables('<table><tr><td></td></tr></table>', 'q-x')

def test_check_accepts_text_marked_and_complete_tables():
    check_work_tables('<p>표 없음</p>', 'q')
    check_work_tables(MARKED + FULL, 'q')

def test_two_tables_are_judged_one_by_one():
    both = mark_work_tables(BLANK + FULL + BLANK)
    assert both.count('work-table') == 2
    check_work_tables(both, 'q')

def test_mark_payload_marks_every_field_and_reports_changes():
    data = {'problems': [{'id': 'q', 'html': {'original': '<p>x</p>' + BLANK, 'conditions': FULL, 'ask': '<p>y</p>'}}]}
    assert mark_payload(data) == 1
    assert 'work-table' in data['problems'][0]['html']['original']
    assert mark_payload(data) == 0          # 두 번째는 바뀌는 것이 없다

def test_migrate_keeps_trailing_newline_and_other_fields(tmp_path):
    obj = {'original': BLANK, 'conditions': '', 'ask': '<p>a</p>', 'hints': [], 'notes': []}
    for newline in ('', '\n'):
        path = tmp_path / f'q{len(newline)}.json'
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + newline, encoding='utf-8')
        assert migrate_workbook_json(path) is True
        text = path.read_text(encoding='utf-8')
        assert text.endswith('\n') == bool(newline)
        assert json.loads(text)['original'] == MARKED and json.loads(text)['notes'] == []
        assert migrate_workbook_json(path) is False
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.lab.review_pack.work_table`

- [ ] **Step 3: 최소 구현을 쓴다**

```python
# scripts/lab/review_pack/work_table.py
"""학생이 채울 표(빈 <td> 가 있는 표)는 좌측 패널이 아니라 풀이 칸에 둔다. 그 표지(work-table)의 단일 출처."""
from pathlib import Path
import json
import re
import sys

FIELDS = ('original', 'conditions', 'ask')
MARK = 'work-table'
WRAP_RE = re.compile(r'<div class="(table-wrap(?: work-table)?)">(.*?)</div>', re.S)
EMPTY_CELL_RE = re.compile(r'<td>\s*</td>')     # 머리칸(<th>)이 비어 있는 것은 채울 표가 아니다

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
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py -v`
Expected: 10 passed

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/review_pack/work_table.py tests/test_review_pack_work_table.py
git commit -m "feat(review-pack): 채울 표 표지(work-table) 규칙 모듈을 추가한다"
```

---

### Task 2: 빌드 검사·생성기·원본 JSON에 표지 적용 (재발방지 ①②③)

**Files:**
- Modify: `scripts/lab/review_pack/workbook_content.py:84-85`
- Modify: `docs/learning-pack-source/실험04/refresh_workbook.py`(`obj=dict(` 직전)
- Modify: `docs/learning-pack-source/실험05/build_run.py:111-112`
- Modify (스크립트로): `docs/learning-pack-source/실험04/workbook/*.json`, `실험05/workbook/*.json`
- Test: `tests/test_review_pack_work_table.py`(말뭉치 테스트 추가)

**Interfaces:**
- Consumes: `check_work_tables(html, question_id)`, `mark_work_tables(html)`, `migrate_workbook_json(path)`, `FIELDS` (Task 1).
- Produces: 작성 JSON이 표지 규칙을 지킨다. 어긴 JSON은 `load_workbook_content`가 `ValueError`로 거부한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `tests/test_review_pack_work_table.py` 끝에 추가

```python
import glob
from pathlib import Path
from scripts.lab.review_pack.work_table import FIELDS

SOURCES = sorted(glob.glob('docs/learning-pack-source/*/workbook/*.json'))
EXPECTED = {
    '실험04': {'q-demux4', 'q-mux2-graded', 'q-mux4'},
    '실험05': {'q-1of4-excess3', 'q-74hc148-table', 'q-dec3x8', 'q-excess3-enc-6row',
               'q-excess3-enc-exam', 'q-prio-exam', 'q-prio-onehot'},
}

def _fragments():
    for f in SOURCES:
        obj = json.loads(Path(f).read_text(encoding='utf-8'))
        if isinstance(obj, dict) and all(k in obj for k in FIELDS):
            yield Path(f).parts[-3], Path(f).stem, obj

def test_every_authored_fragment_obeys_the_work_table_rule():
    seen = list(_fragments())
    assert seen, '작성 JSON 을 못 찾았다'
    for exp, qid, obj in seen:
        for key in FIELDS: check_work_tables(obj[key], f'{exp}/{qid}')

def test_exactly_the_expected_questions_carry_a_work_table():
    found = {}
    for exp, qid, obj in _fragments():
        if any('work-table' in obj[k] for k in FIELDS): found.setdefault(exp, set()).add(qid)
    assert found == EXPECTED

def test_content_loader_rejects_a_blank_table_left_in_the_panel(tmp_path):
    from scripts.lab.review_pack.workbook_content import load_workbook_content
    from tests._workbook_fixture import create_workbook_run
    m, run = create_workbook_run(tmp_path)
    path = run / m['problems'][0]['workbook_fragment']
    obj = json.loads(path.read_text(encoding='utf-8'))
    obj['conditions'] = BLANK
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='work-table'): load_workbook_content(m, run)
    obj['conditions'] = MARKED
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
    load_workbook_content(m, run)             # 표지가 있으면 통과
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py -v`
Expected: 새 테스트 3개 FAIL (`found == EXPECTED` 불일치 — 아직 표지가 없음, 로더가 거부하지 않음)

- [ ] **Step 3: 로더에 검사를 넣는다** — `workbook_content.py`

파일 위쪽 import 묶음에 추가:

```python
from .work_table import check_work_tables
```

`for field in ('original','conditions','ask'):` 루프(84행 부근)를 이렇게 바꾼다:

```python
        for field in ('original','conditions','ask'):
            check_authored_html(obj[field],run,p['id'],figures,problem=True)
            check_work_tables(obj[field],p['id'])
```

- [ ] **Step 4: 생성기를 고친다 (다음 재생성에서도 표지가 유지되게)**

`docs/learning-pack-source/실험04/refresh_workbook.py`: 파일 위쪽 `from scripts.lab.review_pack.html2md import ...` 줄 아래에 추가하고,

```python
from scripts.lab.review_pack.work_table import mark_work_tables
```

`obj=dict(original=original,conditions=conditions,...` 줄 바로 위에 추가한다:

```python
        original,conditions=mark_work_tables(original),mark_work_tables(conditions)   # 채울 표는 풀이 칸으로
```

`docs/learning-pack-source/실험05/build_run.py` 11행의 `sys.path.insert(0, str(Path(__file__).parent))` 아래에 `sys.path.insert(0, str(Path(__file__).resolve().parents[3]))`가 없으면 추가하고(이미 저장소 루트가 path에 있으면 생략), import를 더한다:

```python
from scripts.lab.review_pack.work_table import mark_work_tables, FIELDS
```

`for pid, obj in PR.P.items():` 루프를 이렇게 바꾼다:

```python
for pid, obj in PR.P.items():
    obj = {**obj, **{k: mark_work_tables(obj[k]) for k in FIELDS}}     # 채울 표는 풀이 칸으로
    (RUN / 'workbook' / f'{pid}.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
```

Run: `python -c "import ast,sys; [ast.parse(open(f,encoding='utf-8').read()) for f in ('docs/learning-pack-source/실험04/refresh_workbook.py','docs/learning-pack-source/실험05/build_run.py')]; print('ok')"`
Expected: `ok` (문법만 확인. 두 생성기는 manifest·checks를 초기화하므로 지금 다시 돌리지 않는다.)

- [ ] **Step 5: 이미 만든 원본 JSON에 표지를 단다**

Run: `python -m scripts.lab.review_pack.work_table docs/learning-pack-source/실험04/workbook docs/learning-pack-source/실험05/workbook`
Expected: 출력 `표지 추가:` 줄이 정확히 10개(대상 10문항). 다르면 멈추고 어떤 문항이 빠지거나 더 붙었는지 표와 대조한다.

- [ ] **Step 6: 통과를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py tests/test_review_pack_workbook_content.py tests/test_review_pack_workbook_contract.py -v`
Expected: 전부 PASS

Run: `git diff --stat docs/learning-pack-source`
Expected: JSON 10개 변경, 각 1~2줄(클래스 문자열만).

- [ ] **Step 7: 커밋**

```bash
git add scripts/lab/review_pack/workbook_content.py docs/learning-pack-source tests/test_review_pack_work_table.py
git commit -m "feat(review-pack): 빈 칸 표에 표지가 없으면 빌드가 거부하고 원본 10문항에 표지를 단다"
```

---

### Task 3: 템플릿 덧씌우기 패치 — 표를 풀이 칸으로 옮기고 넘침을 검사

**Files:**
- Modify: `scripts/lab/review_pack/workbook_render.py:17-38`
- Test: `tests/test_review_pack_workbook_render.py`(문자열 테스트), `tests/test_review_pack_workbook_browser.py`(합성 브라우저 테스트)

**Interfaces:**
- Consumes: 템플릿 앵커. `problem.html`에는 `  center.append(el('div', 'work'));`, `answer.html`에는 `  center.append(solutionArea(p));` 가 각각 정확히 1번 있다. 두 템플릿 모두 `  fitStripFormulas(page);\n  const ok = fits();` 가 1번 있다.
- Produces: `TEMPLATE_PATCHES: dict[str, list[tuple[str,str]]]`, `apply_local_patches(text, name)`(시그니처 그대로, 공통 패치 + 템플릿별 패치 적용). 렌더된 HTML에서 `.work-table` 표는 `.page-center > .work-block` 안에 있다.

- [ ] **Step 1: 실패하는 문자열 테스트를 쓴다** — `tests/test_review_pack_workbook_render.py` 끝에 추가

```python
def test_work_table_patch_is_in_both_templates(tmp_path):
    m, run = create_workbook_run(tmp_path)
    content = load_workbook_content(m, run)
    for mode in ('problems', 'answers'):
        text = render_workbook_html(build_workbook_data(m, content, mode), ASSETS)
        assert "panel.querySelectorAll('.work-table')" in text
        assert "el('div', 'work-block')" in text
        assert '#book .work-block td' in text
        assert '.page-center > .work-block ~ .work { min-height: 25mm; }' in text
        assert "center.querySelector('.work-block')" in text          # 쪽 맞춤이 넘침을 본다
        assert '#book .original td { height: 7mm; }' in text           # 기존 패치는 그대로

def test_work_table_patch_anchor_loss_is_rejected_per_template():
    import pytest
    from scripts.lab.review_pack.workbook_render import apply_local_patches, TEMPLATE_PATCHES
    for name, anchor in (('problem.html', "center.append(el('div', 'work'));"), ('answer.html', 'center.append(solutionArea(p));')):
        text = (ASSETS/'workbook'/name).read_bytes().decode('utf-8').replace('\r\n', '\n')
        apply_local_patches(text, name)                                # 원본은 통과
        with pytest.raises(ValueError): apply_local_patches(text.replace(anchor, '// gone'), name)
        with pytest.raises(ValueError): apply_local_patches(text + '\n' + anchor, name)   # 두 번 나와도 거부
    assert set(TEMPLATE_PATCHES) == {'problem.html', 'answer.html'}
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_review_pack_workbook_render.py -k work_table -v`
Expected: FAIL — `ImportError: TEMPLATE_PATCHES`

- [ ] **Step 3: 패치를 구현한다** — `workbook_render.py`

`TABLE_CSS` 문자열 끝(`#book .original td { height: 7mm; }` 줄 다음, 닫는 `'''` 앞)에 규칙을 더한다:

```python
#book .original td { height: 7mm; }
/* 채울 표(work-table)는 풀이 칸 맨 위(.work-block)로 옮겨진다. 풀이 공간은 최소 25mm를 남긴다 */
#book .work-block { flex: none; }
#book .work-block .table-wrap { margin: 0; }
#book .work-block table { table-layout: fixed; margin: 0; }
#book .work-block td { height: 7mm; }
.page-center > .work-block ~ .work { min-height: 25mm; }

```

`LOCAL_PATCHES=[...]` 줄 아래부터 `apply_local_patches`까지를 이렇게 바꾼다:

```python
MOVE_TABLES=("  const moved = [...panel.querySelectorAll('.work-table')];   // 학생이 채울 표는 좌측 패널이 아니라 풀이 칸 맨 위로\n"
             "  if (moved.length) {\n"
             "    const wb = el('div', 'work-block');\n"
             "    for (const t of moved) {\n"
             "      const owner = t.closest('.block');\n"
             "      wb.append(t);\n"
             "      if (!owner.querySelector('.prose').textContent.trim()) owner.remove();   // 표만 있던 블록은 빈 라벨째 지운다\n"
             "    }\n"
             "    center.append(wb);\n"
             "  }\n")
FIT_OLD="  fitStripFormulas(page);\n  const ok = fits();"
FIT_NEW=("  fitStripFormulas(page);\n"
         "  const center = page.querySelector('.page-center');   // 풀이 칸으로 옮긴 표가 칸에 안 들어가면 넘침으로 알린다\n"
         "  const ok = fits() && (!center.querySelector('.work-block') || (center.scrollHeight <= center.clientHeight + 1 && center.scrollWidth <= center.clientWidth + 1));")
PROBLEM_CENTER="  center.append(el('div', 'work'));"
ANSWER_CENTER="  center.append(solutionArea(p));"
# 템플릿마다 줄이 달라 앵커도 다르다. 스냅샷이 바뀌어 anchor 가 사라지거나 둘이 되면 실패한다.
TEMPLATE_PATCHES={
    'problem.html':[(PROBLEM_CENTER,MOVE_TABLES+PROBLEM_CENTER),(FIT_OLD,FIT_NEW)],
    'answer.html':[(ANSWER_CENTER,MOVE_TABLES+ANSWER_CENTER),(FIT_OLD,FIT_NEW)],
}

def apply_local_patches(text, name):
    for old,new in LOCAL_PATCHES+TEMPLATE_PATCHES.get(name,[]):
        if text.count(old)!=1: raise ValueError('Local patch anchor not unique in '+name+': '+old[:30])
        text=text.replace(old,new)
    return text
```

- [ ] **Step 4: 문자열 테스트 통과를 확인한다**

Run: `python -m pytest tests/test_review_pack_workbook_render.py -v`
Expected: 전부 PASS(기존 `test_local_patches_add_table_borders...`, `test_local_patch_anchor_loss_is_rejected` 포함)

- [ ] **Step 5: 실패하는 합성 브라우저 테스트를 쓴다** — `tests/test_review_pack_workbook_browser.py` 끝에 추가

```python
def _synthetic_pack(tmp_path, problems, mode):
    """합성 문항으로 문제지·해설지를 렌더해 로컬 자원과 함께 tmp 에 둔다."""
    import shutil
    from scripts.lab.review_pack.workbook_render import render_workbook_html
    assets = Path('.claude/skills/logic-lab-review-pack/assets')
    shutil.copytree(assets/'vendor', tmp_path/'assets'/'vendor', dirs_exist_ok=True)
    entries = []
    for i, p in enumerate(problems, 1):
        e = dict(id=p['id'], kind='기출', number=str(i), title=p['id'], section='실험 9 · 테스트', book_page=None,
                 difficulty=None, sol=None, original_lang='ko', depends_on=[], figures=[],
                 html={k: p.get(k, '') for k in ('original', 'conditions', 'ask')}, hints=[])
        if mode == 'answers': e['solution'] = dict(steps=[dict(label='식', html='<p>풀이</p>')], answer='<p>답</p>')
        entries.append(e)
    data = dict(meta=dict(mode=mode, title='합성', chapter=0, total=len(entries)), problems=entries)
    out = tmp_path/f'{mode}.html'
    out.write_text(render_workbook_html(data, assets), encoding='utf-8')
    return out

def _table(cols, rows, blank=True, marked=True):
    head = ''.join(f'<th>H{c}</th>' for c in range(cols))
    row = '<tr>' + ('<td></td>' if blank else '<td>1</td>') * cols + '</tr>'
    cls = 'table-wrap work-table' if marked else 'table-wrap'
    return f'<div class="{cls}"><table><thead><tr>{head}</tr></thead><tbody>{row * rows}</tbody></table></div>'

SYNTH = [
    dict(id='q-only-table', original='<p>표를 완성하시오.</p>', conditions=_table(8, 4), ask='<p>채우세요.</p>'),
    dict(id='q-two-tables', original='<p>두 표.</p>' + _table(4, 2), conditions='<p>보조</p>' + _table(4, 2, blank=False, marked=False) + _table(3, 2), ask='<p>채우세요.</p>'),
    dict(id='q-wide', original='<p>넓은 표</p>' + _table(11, 8), ask='<p>채우세요.</p>'),
    dict(id='q-plain', original='<p>표 없음</p>', conditions='<p>조건</p>', ask='<p>구하세요.</p>'),
    dict(id='q-too-big', original='<p>안 들어가는 표</p>' + _table(6, 40), ask='<p>채우세요.</p>'),
]

@pytest.mark.parametrize('mode', ['problems', 'answers'])
def test_work_table_moves_to_the_work_area(tmp_path, mode):
    pw = pytest.importorskip('playwright.sync_api')
    path = _synthetic_pack(tmp_path, SYNTH, mode)
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            page.goto(path.resolve().as_uri())
            page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
            count = lambda sel: page.locator(sel).count()
            # 표만 있던 「조건」 블록은 라벨까지 사라지고, 구할 것은 남는다
            assert '조건' not in page.locator('#q-only-table .panel .block-label').all_text_contents()
            assert '구할 것' in page.locator('#q-only-table .panel .block-label').all_text_contents()
            assert count('#q-only-table .panel table') == 0 and count('#q-only-table .page-center > .work-block table') == 1
            # 표 둘: 둘 다 옮기고 순서를 지키며, 표지 없는 표(내용이 찬 표)는 패널에 남는다
            assert count('#q-two-tables .page-center > .work-block table') == 2
            assert page.locator('#q-two-tables .work-block table th').evaluate_all('t=>t.length') == 4 + 3
            assert count('#q-two-tables .panel table') == 1 and count('#q-two-tables .panel td:empty') == 0
            # 표가 없는 문항은 그대로
            assert count('#q-plain .work-block') == 0
            # 넓은 표는 중앙 폭 안에 들어온다
            assert page.locator('#q-wide .work-block').evaluate('w=>w.scrollWidth<=w.clientWidth+1')
            # 표는 풀이 칸 위, 풀이 공간은 25mm 이상 남는다
            assert page.locator('#q-wide .page-center').evaluate("c=>c.children[0].classList.contains('work-block')")
            assert page.locator('#q-wide .work').evaluate('w=>w.getBoundingClientRect().height') >= 25 * 96 / 25.4 - 1
            # 안 들어가는 표는 조용히 잘리지 않고 넘침으로 드러난다
            assert page.locator('body').get_attribute('data-overflow') == 'q-too-big'
```

- [ ] **Step 6: 브라우저 테스트를 돌린다**

Run: `python -m pytest tests/test_review_pack_workbook_browser.py -k work_table_moves -v`
Expected: PASS(2개). 실패하면 어느 단언인지 보고 패치 JS/CSS를 고친다. 해설지(`answers`)에서 `q-wide` 등이 `data-overflow`에 올라 단언이 깨지면, 그 문항의 해설 단계가 너무 길어서인지(합성 데이터 문제) 패치 문제인지 가려 보고 사용자에게 알린다. 임의로 단언을 느슨하게 하지 않는다.

- [ ] **Step 7: 전체 workbook 테스트와 커밋**

Run: `python -m pytest tests -q -k "workbook or work_table"`
Expected: 전부 PASS

```bash
git add scripts/lab/review_pack/workbook_render.py tests/test_review_pack_workbook_render.py tests/test_review_pack_workbook_browser.py
git commit -m "feat(review-pack): 채울 표를 풀이 칸 맨 위로 옮기는 템플릿 패치와 넘침 검사를 추가한다"
```

---

### Task 4: 발행된 팩 다시 만들기와 실제 팩 회귀 테스트 (재발방지 ④)

**Files:**
- Modify: `scripts/lab/review_pack/workbook_rerender.py`
- Modify: `tests/test_review_pack_workbook_browser.py`, `tests/test_review_pack_work_table.py`
- Regenerate: `복습노트/실험04/`, `복습노트/실험05/`의 `*_기출문제.html/.md/.pdf`, `*_기출풀이.html/.md/.pdf`

**Interfaces:**
- Consumes: `mark_payload(data) -> int` (Task 1), 패치된 렌더러 (Task 3).
- Produces: `rerender_workbook(folder)`가 payload에 표지를 달고 검사한 뒤 다시 렌더한다. 발행된 두 팩의 문제지·해설지가 새 배치가 된다.

- [ ] **Step 1: 실패하는 실제 팩 테스트를 쓴다** — `tests/test_review_pack_work_table.py` 끝에 추가

```python
def test_published_payloads_obey_the_rule_and_match_the_source():
    from scripts.lab.review_pack.workbook_render import read_workbook_payload
    packs = sorted(Path('복습노트').glob('실험*/실험*_기출문제.html')) + sorted(Path('복습노트').glob('실험*/실험*_기출풀이.html'))
    assert packs
    for path in packs:
        data = read_workbook_payload(path)
        marked = set()
        for p in data['problems']:
            for key in FIELDS:
                check_work_tables(p['html'][key], p['id'])
                if 'work-table' in p['html'][key]: marked.add(p['id'])
        exp = path.parent.name
        assert marked == EXPECTED.get(exp, set()), f'{path}: 표지 달린 문항이 기대와 다르다'
```

`tests/test_review_pack_workbook_browser.py` 끝에 추가:

```python
@pytest.mark.parametrize('exp,ids', [
    ('실험04', ['q-demux4', 'q-mux2-graded', 'q-mux4']),
    ('실험05', ['q-1of4-excess3', 'q-74hc148-table', 'q-dec3x8', 'q-excess3-enc-6row', 'q-excess3-enc-exam', 'q-prio-exam', 'q-prio-onehot']),
])
def test_published_packs_keep_fill_in_tables_out_of_the_panel(exp, ids):
    pw = pytest.importorskip('playwright.sync_api')
    pack = Path('복습노트')/exp
    if not (pack/f'{exp}_기출문제.html').exists(): pytest.skip(exp+' 없음')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            for name in (f'{exp}_기출문제.html', f'{exp}_기출풀이.html'):
                page.goto((pack/name).resolve().as_uri())
                page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
                assert page.locator('body').get_attribute('data-overflow') == ''
                # 어느 문항이든 패널 안에 빈 칸이 있는 표가 남아 있으면 안 된다
                assert page.locator('.page--problem .panel td:empty').count() == 0
                for qid in ids:
                    assert page.locator(f'#{qid} .panel table td:empty').count() == 0
                    assert page.locator(f'#{qid} .page-center > .work-block td:empty').count() > 0
                    labels = page.locator(f'#{qid} .panel .block-label').all_text_contents()
                    assert '구할 것' in labels
                if name.endswith('기출문제.html'):
                    assert page.locator('#q-mux4 .work-block tbody tr td:last-child').all_text_contents() == ['', '', '', '']
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py::test_published_payloads_obey_the_rule_and_match_the_source tests/test_review_pack_workbook_browser.py -k published -v`
Expected: FAIL — 발행본 payload에 아직 표지가 없다.

- [ ] **Step 3: `rerender`가 표지를 달게 한다** — `workbook_rerender.py`

import 묶음에 추가:

```python
from .work_table import mark_payload
```

`for p in data['problems']:` 루프 앞(`data=read_workbook_payload(path)` 다음 줄)에 추가:

```python
        mark_payload(data)          # 채울 표는 풀이 칸으로. 이미 달려 있으면 아무것도 하지 않는다
```

- [ ] **Step 4: 발행된 두 팩을 다시 만든다**

```bash
python -m scripts.lab.review_pack rerender --folder 복습노트/실험04
python -m scripts.lab.review_pack rerender --folder 복습노트/실험05
```

Expected: 각각 오류 없이 종료(오류 목록이 비어 있음). 오류가 나오면 그대로 읽고 원인을 고친 뒤 다시 돌린다.

- [ ] **Step 5: 변경 범위를 확인한다**

Run: `git status --short 복습노트`
Expected: 변경 파일이 `실험04`, `실험05`의 `*_기출문제.html/.md`, `*_기출풀이.html/.md` 뿐. 다른 파일(실험설명, assets, 다른 실험)이 바뀌었으면 멈추고 원인을 찾는다.

Run: `git diff --stat 복습노트 | tail -3` 후 한 파일의 `git diff`를 훑어, 바뀐 것이 `work-table` 클래스와 패치된 템플릿 JS/CSS뿐인지 본다.

- [ ] **Step 6: 멱등성을 확인한다**

```bash
git add 복습노트
python -m scripts.lab.review_pack rerender --folder 복습노트/실험04
python -m scripts.lab.review_pack rerender --folder 복습노트/실험05
git diff --stat 복습노트
```

Expected: 마지막 `git diff --stat`이 아무것도 출력하지 않는다(스테이지된 결과와 같음 = 두 번째 실행이 아무것도 바꾸지 않음).

- [ ] **Step 7: 테스트 통과를 확인한다**

Run: `python -m pytest tests -q -k "work_table or workbook"`
Expected: 전부 PASS

- [ ] **Step 8: 눈으로 확인한다**

Run: `python -m scripts.lab.workbook_pdf 실험04` 그리고 `python -m scripts.lab.workbook_pdf 실험05`
Expected: 각각 문제지·해설지 PDF가 A4 가로, 쪽 수·넘침 검사 통과. 실패하면 성공이라 하지 않고 출력을 그대로 보고한다.

PDF에서 `q-dec3x8`(실험05), `q-mux4`(실험04), `q-excess3-enc-exam`(실험05, 표가 가장 넓다)의 쪽을 이미지로 렌더해(예: `pdftoppm -r 80 -f N -l N`) 표가 가운데 위, 점격자가 그 아래, 힌트 띠가 오른쪽이고 아무것도 잘리지 않았는지 직접 본다.

- [ ] **Step 9: 커밋**

```bash
git add scripts/lab/review_pack/workbook_rerender.py tests 복습노트
git commit -m "docs(복습노트): 실험04·05 문제지·해설지에서 채울 표를 풀이 칸으로 옮긴다"
```

---

### Task 5: 작성 규칙 문서화와 기록 (재발방지 ⑤)

**Files:**
- Modify: `.claude/skills/logic-lab-review-pack/references/workbook.md:3,21`
- Modify: `.claude/skills/logic-lab-review-pack/SKILL.md:73`
- Test: `tests/test_review_pack_work_table.py`(문서가 규칙을 말하는지)

**Interfaces:**
- Consumes: `LOCAL_PATCHES`(공통 2건) + `TEMPLATE_PATCHES`(템플릿별 2건씩).
- Produces: 다음 실험 팩을 만드는 사람이 표지 규칙·패치 개수·재생성 방법을 문서에서 찾을 수 있다.

- [ ] **Step 1: 실패하는 테스트를 쓴다** — `tests/test_review_pack_work_table.py` 끝에 추가

```python
def test_docs_state_the_work_table_rule():
    skill = Path('.claude/skills/logic-lab-review-pack/SKILL.md').read_text(encoding='utf-8')
    ref = Path('.claude/skills/logic-lab-review-pack/references/workbook.md').read_text(encoding='utf-8')
    assert 'work-table' in ref and 'work_table' in ref and 'TEMPLATE_PATCHES' in ref
    assert 'work-table' in skill
    assert '두 건' not in skill and '2건' not in ref        # 패치 개수 문구가 낡지 않게
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py::test_docs_state_the_work_table_rule -v`
Expected: FAIL

- [ ] **Step 3: 문서를 고친다**

`references/workbook.md` 3행의 `workbook_render.LOCAL_PATCHES(표 테두리 CSS·빈 조건 블록 생략 2건)만 바꾼다.`를 다음으로 바꾼다:

```
workbook_render.LOCAL_PATCHES(표 테두리 CSS·빈 조건 블록 생략, 모든 템플릿 공통 2건)와 TEMPLATE_PATCHES(채울 표를 풀이 칸으로 옮기기·넘침 검사, 템플릿마다 2건)만 바꾼다.
```

21행(`원문 조건·표·문장은 텍스트로 보존한다...`) 아래에 문단을 추가한다:

```
학생이 채울 표(빈 `<td>`가 있는 표)는 `<div class="table-wrap work-table">`로 쓴다. 이 표는 좌측 패널이 아니라 가운데 풀이 칸 맨 위에 나온다. 표지는 손으로 달지 말고 `mark_work_tables`(scripts/lab/review_pack/work_table.py)로 단다. 생성기가 JSON을 쓸 때 부르고, 이미 쓴 JSON은 `python -m scripts.lab.review_pack.work_table <폴더>`로 단다. 빈 칸이 있는데 표지가 없거나, 표지가 있는데 빈 칸이 없으면 build가 거부한다. 해설 단계의 완성된 표(`solution`)에는 표지를 달지 않는다. 배선표처럼 빈 칸이 없는 표는 패널에 남는다. 이미 발행된 팩은 `rerender`가 표지를 달아 다시 만든다.
```

`SKILL.md` 73행의 `workbook_render.LOCAL_PATCHES 두 건(표 테두리 CSS, 빈 조건 블록 생략)만 덧씌운다.`를 다음으로 바꾼다:

```
workbook_render의 LOCAL_PATCHES(표 테두리 CSS, 빈 조건 블록 생략)와 TEMPLATE_PATCHES(채울 표를 work-table 표지로 풀이 칸 맨 위에 옮김)만 덧씌운다.
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m pytest tests/test_review_pack_work_table.py -v`
Expected: 전부 PASS

- [ ] **Step 5: 전체 테스트와 커밋**

Run: `python -m pytest tests -q`
Expected: 전부 PASS. 기존 실패가 있으면 이 작업 이전(`git stash` 없이 `git log`의 main 기준)에도 있었는지 구분해 보고한다.

```bash
git add .claude/skills/logic-lab-review-pack tests/test_review_pack_work_table.py
git commit -m "docs(review-pack): 채울 표 표지 규칙과 템플릿별 패치를 문서에 적는다"
```

- [ ] **Step 6: 메모리에 한 줄 남긴다**

`C:\Users\Hyunjun\.claude\projects\C--Users-Hyunjun-Desktop------26-2----\memory\`에 `workbook-work-table.md`(type: project)를 쓰고 `MEMORY.md`에 포인터 한 줄을 더한다. 본문: 채울 표는 `work-table` 표지로 중앙 풀이 칸에 가며, 규칙의 단일 출처는 `work_table.py`, 새 실험 팩은 생성기에서 `mark_work_tables`를 부르고 `rerender`로 기존 팩을 갱신한다. **Why:** 좌측 패널에 빈 표가 있으면 태블릿에서 쓸 자리가 없다. **How to apply:** 새 실험 문제지를 만들 때 빈 표가 패널에 남지 않는지 build 오류와 `test_review_pack_work_table.py`로 확인한다.

---

## 재발방지 대책 요약

| # | 방지 장치 | 막는 실수 | 어디서 걸리나 |
|---|---|---|---|
| 1 | `check_work_tables`가 build·rerender 때 빈 칸↔표지 불일치를 거부 | 새 문항을 쓰면서 표지를 빼먹음 | `load_workbook_content`, `mark_payload` |
| 2 | 생성기(`refresh_workbook.py`, `build_run.py`)가 JSON을 쓸 때 표지를 자동으로 달기 | 재생성하면 표지가 사라짐 | 생성기 |
| 3 | 말뭉치 테스트: 모든 원본 JSON·발행 payload가 규칙을 지키고 표지 문항 집합이 기대와 같음 | 표지가 슬그머니 빠지거나 엉뚱한 문항에 붙음 | `test_review_pack_work_table.py` |
| 4 | 실제 팩 브라우저 테스트: 패널에 빈 칸 표 0개, 중앙에 있음, `data-overflow=''` | 템플릿 갱신·패치 변경으로 배치가 깨짐 | `test_review_pack_workbook_browser.py` |
| 5 | 패치 앵커가 템플릿별로 정확히 1번 나오지 않으면 렌더 실패 | 템플릿 스냅샷을 갱신했더니 패치가 조용히 빠짐 | `apply_local_patches`, 앵커 테스트 |
| 6 | 넘침 검사(`center.scrollHeight`)를 쪽 맞춤에 포함 | 표가 커서 풀이 칸이 잘리는데 발행됨 | 템플릿 `fitProblemPage` 패치 |
| 7 | 문서(SKILL.md, workbook.md)와 메모리에 규칙·단일 출처 기록 | 다음 실험에서 규칙을 모름 | Task 5 |

## 설계 요약 (Spec)

- 대상: 학생이 채울 빈 칸(`<td></td>`)이 있는 표. 위치(`original`/`conditions`/`ask`)와 무관. 머리칸(`<th>`)이 빈 표, 빈 칸 없는 표(배선표 등)는 패널에 남는다(#9).
- 배치: 문제지의 가운데 칸 = 회로도 띠 → 채울 표 → 점격자 풀이 칸(최소 25mm). 라벨 없음(#7). 해설지는 표를 패널에 둔다(#8 번복).
- 표지: `class="table-wrap work-table"`. JSON 스키마(`AUTHOR_KEYS`)·MD 변환은 바뀌지 않는다.
- 실패 방식: 표가 안 들어가면 `data-overflow`에 올라 발행이 막힌다. 글자를 줄이지 않는다.
- 범위: 발행된 실험01·03·04·05 팩의 16문항(작성 JSON이 있는 실험04·05는 10문항). 실험02는 해당 문항이 없다. 문제은행·템플릿 원본·해시는 건드리지 않는다.
