import copy
import json
import pytest
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_figures import check_redrawn_figures
from tests._workbook_fixture import create_workbook_run, add_redrawn_figure

def test_problem_projection_excludes_answers_and_notes(tmp_path):
    m, run = create_workbook_run(tmp_path)
    before = copy.deepcopy(m)
    content = load_workbook_content(m, run)
    problem = build_workbook_data(m, content, 'problems')
    answer = build_workbook_data(m, content, 'answers')
    assert m == before
    assert 'solution' not in problem['problems'][0]
    assert 'notes' not in problem['problems'][0]
    assert '정답 전용 문구' not in json.dumps(problem, ensure_ascii=False)
    assert '해설 전용 대조 기록' not in json.dumps(problem, ensure_ascii=False)
    assert problem['problems'][0]['html'] == answer['problems'][0]['html']
    assert answer['problems'][0]['solution']['answer'] == '<p>Y=I0</p>'

@pytest.mark.parametrize('html', ['<script>1</script>', '<img onerror="alert(1)" src="x">',
    '<a href="javascript:alert(1)">x</a>', '<svg><script>1</script></svg>',
    '<div style="background:url(evidence/assets/answer.png)">x</div>'])
def test_active_or_hidden_resource_refused(tmp_path, html):
    m, run = create_workbook_run(tmp_path)
    path = run/m['problems'][0]['workbook_fragment']
    obj = json.loads(path.read_text(encoding='utf-8'))
    obj['original'] = html
    path.write_text(json.dumps(obj), encoding='utf-8')
    with pytest.raises(ValueError): load_workbook_content(m, run)

def test_duplicate_json_keys_fail(tmp_path):
    m, run = create_workbook_run(tmp_path)
    (run/m['problems'][0]['workbook_fragment']).write_text('{"original":"x","original":"y"}', encoding='utf-8')
    with pytest.raises(ValueError): load_workbook_content(m, run)

def test_solution_figure_cannot_be_used_as_problem(tmp_path):
    m, run = create_workbook_run(tmp_path)
    add_redrawn_figure(m, run, role='solution', exposure='present')
    path = run/m['problems'][0]['workbook_fragment']
    obj = json.loads(path.read_text(encoding='utf-8')); obj['problem_figures'] = ['f1']
    path.write_text(json.dumps(obj), encoding='utf-8')
    with pytest.raises(ValueError): load_workbook_content(m, run)

