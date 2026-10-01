import copy
from pathlib import Path
from scripts.lab.review_pack.workbook_content import load_workbook_content, build_workbook_data
from scripts.lab.review_pack.workbook_render import render_workbook_html, read_workbook_payload
from scripts.lab.review_pack.workbook_md import write_workbook_md, check_workbook_md
from tests._workbook_fixture import create_workbook_run

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')

def test_md_retains_table_math_and_all_solution_steps(tmp_path):
    m, run = create_workbook_run(tmp_path)
    data = build_workbook_data(m, load_workbook_content(m,run), 'answers')
    p = data['problems'][0]
    p['solution']['steps'].append(dict(label='검산',html='<p>$$Y=I_0$$</p><table><tr><th>S</th><th>Y</th></tr><tr><td>0</td><td>I0</td></tr></table>'))
    path = write_workbook_md(data,m,tmp_path/'실험04_기출풀이.md')
    (tmp_path/'실험04_실험설명.md').write_text('<a id="t-mux"></a>',encoding='utf-8')
    (tmp_path/'실험04_기출문제.md').write_text('# 문제',encoding='utf-8')
    text = path.read_text(encoding='utf-8')
    assert '$$Y=I_0$$' in text and '| 0 | I0 |' in text
    assert '정답 전용 문구' in text
    assert f'<a id="{p["id"]}"></a>' in text
    assert check_workbook_md(data,m,path) == []
    path.write_text(text.replace('정답 전용 문구',''),encoding='utf-8')
    assert check_workbook_md(data,m,path)
