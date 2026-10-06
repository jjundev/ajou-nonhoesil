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

import glob
from pathlib import Path
from scripts.lab.review_pack.work_table import FIELDS

SOURCES = sorted(glob.glob('docs/learning-pack-source/*/workbook/*.json'))
EXPECTED = {
    '실험04': {'q-demux4', 'q-mux2-graded', 'q-mux4'},
    '실험05': {'q-1of4-excess3', 'q-74hc148-table', 'q-dec3x8', 'q-excess3-enc-6row',
               'q-excess3-enc-exam', 'q-prio-exam', 'q-prio-onehot'},
}

# 발행된 팩에서 표지가 달린 문항. 실험01·03 은 작성 JSON 이 저장소에 없어 발행 payload 로만 확인한다.
PUBLISHED = {**EXPECTED,
    '실험01': {'q-tt3-4row', 'q-tt3-8row', 'q-xor2-tt'},
    '실험03': {'q-ha-table', 'q-fa-table', 'q-fs-table'},
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
        assert marked == PUBLISHED.get(path.parent.name, set()), f'{path}: 표지 달린 문항이 기대와 다르다'

def test_docs_state_the_work_table_rule():
    skill = Path('.claude/skills/logic-lab-review-pack/SKILL.md').read_text(encoding='utf-8')
    ref = Path('.claude/skills/logic-lab-review-pack/references/workbook.md').read_text(encoding='utf-8')
    assert 'work-table' in ref and 'work_table' in ref and 'TEMPLATE_PATCHES' in ref
    assert 'work-table' in skill and 'TEMPLATE_PATCHES' in skill
    assert '두 건' not in skill and '2건' not in ref        # 패치 개수 문구가 낡지 않게

@pytest.mark.parametrize('cell', ['<td>&nbsp;</td>', '<td colspan="2"></td>', '<td><br></td>', '<td> <br/> </td>'])
def test_other_empty_cell_forms_are_fill_in_cells(cell):
    html = BLANK.replace('<td></td>', cell)
    assert 'work-table' in mark_work_tables(html)
    with pytest.raises(ValueError): check_work_tables(html, 'q')

def test_nested_div_in_table_wrap_is_rejected():
    with pytest.raises(ValueError, match='q-x'):
        check_work_tables('<div class="table-wrap"><div>t</div><table><tr><td></td></tr></table></div>', 'q-x')
