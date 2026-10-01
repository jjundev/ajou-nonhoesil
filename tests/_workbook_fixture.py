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

def add_redrawn_figure(m, run, *, role='problem', exposure='none'):
    import hashlib
    p = m['problems'][0]
    folder = 'questions' if role == 'problem' else 'solutions'
    svg = f'figures/{folder}/diagram.svg'
    png = f'figures/{folder}/diagram.png'
    (run/svg).parent.mkdir(parents=True, exist_ok=True)
    (run/svg).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><title>S入力</title><path d="M0 50 H200"/></svg>', encoding='utf-8')
    # 표준 라이브러리만으로 유효한 2×1 RGB PNG 테스트 파일 작성
    import struct, zlib
    def chunk(kind, body):
        return struct.pack('!I', len(body))+kind+body+struct.pack('!I', zlib.crc32(kind+body)&0xffffffff)
    raw = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B',2,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'+b'\xff'*6))+chunk(b'IEND',b'')
    (run/png).write_bytes(raw)
    row = dict(id='f1', question_id=p['id'], role=role, svg=svg, png=png,
        svg_sha256=hashlib.sha256((run/svg).read_bytes()).hexdigest(),
        png_sha256=hashlib.sha256(raw).hexdigest(), w_mm=100.0, h_mm=50.0,
        source_asset_ids=[], source_refs=p['sources'], derivation='입력 조건에서 직접 작성',
        answer_exposure=exposure, review_status='not_run', review_notes='검토 전')
    (run/m['figure_manifest']).write_text(json.dumps(dict(schema_version=1,figures=[row]),ensure_ascii=False),encoding='utf-8')
    return row
