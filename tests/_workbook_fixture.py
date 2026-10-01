# tests/_workbook_fixture.py
import json
import shutil
from pathlib import Path
from tests.test_review_pack_manifest import fixture

def create_workbook_run(tmp_path):
    run = tmp_path/'run'
    shutil.copytree(Path('tests/fixtures/review_pack'), run)
    m = fixture()
    m['review_presentation_version'] = 2
    m['figure_manifest'] = 'figures/redraw-manifest.json'
    m['checks'] = dict.fromkeys(('source_visual', 'content', 'independent', 'browser'), 'not_run')
    p = m['problems'][0]
    p['workbook_fragment'] = f'workbook/{p["id"]}.json'
    p['title'] = '문항 제목'
    authored = dict(original='<p>문제를 풀어 보시오.</p>', conditions='<p>S=0</p>',
        ask='<p>Y를 구하시오.</p>', problem_figures=[], hints=[dict(label='경로', html='<p>선택 경로를 보세요.</p>')],
        solution=dict(steps=[dict(label='선택', html='<p>정답 전용 문구</p>')], answer='<p>Y=I0</p>'),
        notes=['해설 전용 대조 기록'])
    (run/'workbook').mkdir()
    (run/p['workbook_fragment']).write_text(json.dumps(authored, ensure_ascii=False), encoding='utf-8')
    (run/'figures').mkdir(exist_ok=True)
    (run/m['figure_manifest']).write_text('{"schema_version":1,"figures":[]}', encoding='utf-8')
    (run/'manifest.json').write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
    return m, run
