import json
from pathlib import Path
import pytest
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack

@pytest.mark.parametrize('viewport',[{'width':1280,'height':900},{'width':375,'height':812}])
def test_real_workbook_decode_ready_and_no_overflow(tmp_path,viewport):
    pw = pytest.importorskip('playwright.sync_api')
    run = Path('docs/learning-pack-source/실험04')
    m = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    paths = assemble(m,run,tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    expected = [p['id'] for p in m['problems'] if p['status']=='included']
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport=viewport)
            errors = []; page.on('pageerror',lambda e:errors.append(str(e)))
            for key in ('question_html','review_html'):
                page.goto(paths[key].resolve().as_uri())
                page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
                assert page.locator('html').get_attribute('data-ready') == 'true'
                assert page.locator('body').get_attribute('data-overflow') == ''
                assert page.locator('.page--problem').evaluate_all('(nodes)=>nodes.map(n=>n.id)') == expected
                assert page.locator('.katex-error').count() == 0
                assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
                assert_workbook_bounds_and_links(page)
                if key == 'question_html':
                    assert page.locator('#q-mux4 tbody tr td:last-child').all_text_contents() == ['','','','']
                assert_offline_reload(page)
            assert errors == []

def assert_workbook_bounds_and_links(page):
    assert page.locator('.sol-step img').evaluate_all('''imgs => imgs.every(img => {
      const p=img.closest('.sol-step-body').getBoundingClientRect(),r=img.getBoundingClientRect();
      return r.left>=p.left-1 && r.right<=p.right+1;
    })''')
    assert page.locator('.sol-answer').evaluate_all('''nodes => nodes.every(node => {
      const p=node.closest('.work').getBoundingClientRect(),r=node.getBoundingClientRect();
      return r.bottom<=p.bottom+1;
    })''')
    assert page.locator('table').evaluate_all('''tables => tables.every(table => {
      const p=table.parentElement.getBoundingClientRect(),r=table.getBoundingClientRect();
      return r.left>=p.left-1 && r.right<=p.right+1;
    })''')
    assert page.locator('a.hint-strip').evaluate_all('''links => links.every(a =>
      document.getElementById(decodeURIComponent(a.hash.slice(1))))''')

def assert_offline_reload(page):
    page.context.set_offline(True)
    try:
        page.reload()
        page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
        assert page.locator('html').get_attribute('data-ready') == 'true'
        assert page.locator('.katex-error').count() == 0
        assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete && i.naturalWidth>0)')
    finally:
        page.context.set_offline(False)


def test_published_pack_table_borders_and_no_empty_condition_label(published_workbook_preview):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport={'width':1280,'height':900})
            for key in ('question', 'review'):
                page.goto(published_workbook_preview('실험05', key).as_uri())
                page.wait_for_function('document.documentElement.dataset.ready',timeout=60000)
                assert page.locator('body').get_attribute('data-overflow') == ''
                assert page.locator('#book table').first.evaluate('t=>getComputedStyle(t.querySelector("td")).borderTopWidth') != '0px'
                # q-excess3-why 는 조건이 비어 있다: 라벨도 없고, 구할 것은 남는다
                labels = page.locator('#q-excess3-why .block-label').all_text_contents()
                assert '조건' not in labels and '구할 것' in labels
                labels = page.locator('#q-dec3x8 .block-label').all_text_contents()
                assert '조건' in labels
                assert '원문 대조' not in page.locator('body').inner_text()

def _synthetic_pack(tmp_path, problems, mode):
    """합성 문항으로 문제지·해설지를 렌더해 로컬 자원과 함께 tmp 에 둔다."""
    import shutil
    from scripts.lab.review_pack.workbook_render import render_workbook_html
    assets = Path('.claude/skills/logic-lab-review-pack/assets')
    shutil.copytree(assets/'vendor', tmp_path/'.vendor', dirs_exist_ok=True)
    pack = tmp_path/'pack'; pack.mkdir(exist_ok=True)
    entries = []
    for i, p in enumerate(problems, 1):
        e = dict(id=p['id'], kind='기출', number=str(i), title=p['id'], section='실험 9 · 테스트', book_page=None,
                 difficulty=None, sol=None, original_lang='ko', depends_on=[], figures=[],
                 html={k: p.get(k, '') for k in ('original', 'conditions', 'ask')}, hints=[])
        if mode == 'answers': e['solution'] = dict(steps=[dict(label='식', html='<p>풀이</p>')], answer='<p>답</p>')
        entries.append(e)
    data = dict(meta=dict(mode=mode, title='합성', chapter=0, total=len(entries)), problems=entries)
    out = pack/f'{mode}.html'
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

def test_work_table_moves_to_the_work_area(tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    path = _synthetic_pack(tmp_path, SYNTH, 'problems')
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

def test_answer_sheet_keeps_the_blank_table_in_the_panel(tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    path = _synthetic_pack(tmp_path, SYNTH[:4], 'answers')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            page.goto(path.resolve().as_uri())
            page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
            assert page.locator('.work-block').count() == 0          # 풀이 단계가 들어갈 높이를 지킨다
            assert page.locator('#q-only-table .panel table').count() == 1
            assert page.locator('body').get_attribute('data-overflow') == ''

@pytest.mark.parametrize('exp,ids', [
    ('실험01', ['q-tt3-4row', 'q-tt3-8row', 'q-xor2-tt']),
    ('실험03', ['q-ha-table', 'q-fa-table', 'q-fs-table']),
    ('실험04', ['q-demux4', 'q-mux2-graded', 'q-mux4']),
    ('실험05', ['q-1of4-excess3', 'q-74hc148-table', 'q-dec3x8', 'q-excess3-enc-6row', 'q-excess3-enc-exam', 'q-prio-exam', 'q-prio-onehot']),
])
def test_published_packs_keep_fill_in_tables_out_of_the_question_panel(exp, ids, published_workbook_preview):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            for key in ('question', 'review'):
                question = key == 'question'
                page.goto(published_workbook_preview(exp, key).as_uri())
                page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
                assert page.locator('body').get_attribute('data-overflow') == ''
                for qid in ids:
                    in_panel = page.locator(f'#{qid} .panel table td:empty').count()
                    in_work = page.locator(f'#{qid} .page-center > .work-block td:empty').count()
                    # 문제지: 빈 칸 표는 풀이 칸에 있고 패널에는 없다. 해설지: 풀이 높이를 지키려고 패널에 둔다
                    assert (in_panel == 0 and in_work > 0) if question else (in_panel > 0 and in_work == 0)
                    assert '구할 것' in page.locator(f'#{qid} .panel .block-label').all_text_contents()
                if question:
                    assert page.locator('#q-mux4 .work-block tbody tr td:last-child').all_text_contents() == ['', '', '', ''] if exp == '실험04' else True
