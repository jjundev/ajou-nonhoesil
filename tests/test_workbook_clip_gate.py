"""맞춤이 끝난 뒤에도 남은 잘림·넘침을 data-overflow 로 알리는 훑기를 본다.

기존 맞춤의 사각지대: fitDisplayMath 는 70% 까지만 줄이고 그 뒤로는 `.katex-display` 의
overflow-x 가 잘라도 눈에 띄지 않았고, fitSolution 은 마지막 풀이 단계만 쟀으며,
표는 칸을 넘어도 맞춤이 보지 않았다.

주의: 템플릿의 renderMath 는 KaTeX 가 안 불러와졌으면 조용히 돌아온다(그러면 훑기가 항상 거짓을
돌려줘 테스트가 의미를 잃는다). 그래서 KaTeX 가 `.pack/assets/vendor` 에서 실제로 불러와졌는지를
모든 쪽 열기에서 먼저 확인한다. `_synthetic_pack` 은 vendor 를 `assets/vendor` 에 둬 로드되지 않는다.
"""
import shutil
from pathlib import Path

import pytest

from scripts.lab.review_pack.manifest import DATA
from scripts.lab.review_pack.workbook_render import read_workbook_payload, render_workbook_html

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
NOTES = Path('복습노트')
PACKS = ['실험01', '실험02', '실험03', '실험04', '실험05']


def terms(n):
    return '+'.join(f'a_{{{i}}}' for i in range(n))


def write_pack(tmp, problems, mode):
    """합성 문항으로 문제지·해설지를 렌더한다. KaTeX 가 로드되도록 vendor 를 `<.pack>/assets/vendor` 에 둔다."""
    shutil.copytree(ASSETS/'vendor', tmp/DATA/'assets'/'vendor', dirs_exist_ok=True)
    entries = []
    for i, p in enumerate(problems, 1):
        e = dict(id=p['id'], kind='기출', number=str(i), title=p['id'], section='실험 9 · 테스트', book_page=None,
                 difficulty=None, sol=None, original_lang='ko', depends_on=[], figures=[],
                 html={k: p.get(k, '') for k in ('original', 'conditions', 'ask')}, hints=[])
        if mode == 'answers':
            e['solution'] = dict(steps=[dict(label='식', html=h) for h in p.get('steps', ['<p>풀이</p>'])], answer=p.get('answer', '<p>답</p>'))
        entries.append(e)
    data = dict(meta=dict(mode=mode, title='합성', chapter=0, total=len(entries)), problems=entries)
    out = tmp/f'{mode}.html'
    out.write_text(render_workbook_html(data, ASSETS), encoding='utf-8')
    return out


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as chrome:
            yield chrome


def open_page(browser, path, display=True):
    """HTML 을 열어 맞춤이 끝나길 기다린다. KaTeX 가 실제로 돌았는지도 확인한다(display: 식이 있어야 한다)."""
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(Path(path).resolve().as_uri())
    page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
    assert page.locator('html').get_attribute('data-ready') == 'true'
    assert errors == []
    assert page.evaluate('typeof renderMathInElement') == 'function', 'KaTeX 가 로드되지 않았다 — 훑기가 무의미하다'
    assert page.locator('.katex-error').count() == 0
    if display:
        assert page.locator('.katex-display').count() > 0, '수식이 렌더되지 않았다'
    return page


def overflow_of(page):
    return page.locator('body').get_attribute('data-overflow')


# ---------- 식 ----------

def test_unfittable_display_formula_is_reported(browser, tmp_path):
    steps = ['<p>$$' + terms(90) + '$$</p>']
    path = write_pack(tmp_path, [dict(id='q-wide-formula', original='<p>식</p>', ask='<p>구하세요.</p>', steps=steps)], 'answers')
    page = open_page(browser, path)
    assert overflow_of(page).split(',') == ['q-wide-formula']
    # 쪽에도 빨간 표시가 남는다(기존 넘침 표시와 같은 방식)
    assert page.locator('#q-wide-formula').get_attribute('data-overflow') is not None


def test_formula_that_fits_after_shrinking_is_not_reported(browser, tmp_path):
    # 70% 로 줄이면 들어오는 식(대조군): 훑기가 늘 참을 돌려주지 않는다는 증거.
    steps = ['<p>$$' + terms(24) + '$$</p>']
    path = write_pack(tmp_path, [dict(id='q-fits', original='<p>식</p>', ask='<p>구하세요.</p>', steps=steps)], 'answers')
    page = open_page(browser, path)
    scale = page.evaluate("document.querySelector('#q-fits .sol-step-body .katex-display').firstElementChild.style.transform")
    assert scale.startswith('scale('), f'대조군이 줄지 않았다: {scale!r}'
    assert overflow_of(page) == ''


def test_formula_just_past_the_shrink_limit_is_reported(browser, tmp_path):
    # 70% 로 줄여도 몇 px 넘치는 경계: 앞 테스트(24항, 들어옴)와 뒤 테스트(90항) 사이를 좁혀서 잡는다.
    steps = ['<p>$$' + terms(32) + '$$</p>']
    path = write_pack(tmp_path, [dict(id='q-edge', original='<p>식</p>', ask='<p>구하세요.</p>', steps=steps)], 'answers')
    page = open_page(browser, path)
    assert page.evaluate("document.querySelector('#q-edge .katex-display').firstElementChild.style.transform") == 'scale(0.7)'
    assert overflow_of(page).split(',') == ['q-edge']


def test_panel_display_formula_is_checked_too(browser, tmp_path):
    # 문제 칸(왼쪽 패널)의 식도 같은 잘림을 낸다.
    path = write_pack(tmp_path, [dict(id='q-panel', original='<p>$$' + terms(90) + '$$</p>', ask='<p>구하세요.</p>')], 'problems')
    page = open_page(browser, path)
    assert overflow_of(page).split(',') == ['q-panel']


def test_inline_formula_without_break_points_is_reported(browser, tmp_path):
    # 줄바꿈 지점이 없는 인라인 식($…$)은 맞춤이 줄이지 않고, 풀이 흐름 overflow:hidden 이 잘라 낸다.
    for n in (22, 26, 36):
        steps = ['<p>값은 $\\overline{' + terms(n) + '}$ 이다.</p>']
        path = write_pack(tmp_path, [dict(id=f'q-inline{n}', original='<p>식</p>', ask='<p>구하세요.</p>', steps=steps)], 'answers')
        page = open_page(browser, path, display=False)
        assert page.locator('.katex-display').count() == 0       # 인라인이다
        assert overflow_of(page).split(',') == [f'q-inline{n}'], n
        page.close()


def test_long_inline_mathrm_is_reported(browser, tmp_path):
    steps = ['<p>$\\mathrm{' + 'ABCDEFGHIJ' * 16 + '}$</p>']      # 160자, 줄바꿈 지점 없음
    path = write_pack(tmp_path, [dict(id='q-mathrm', original='<p>식</p>', ask='<p>구하세요.</p>', steps=steps)], 'answers')
    page = open_page(browser, path, display=False)
    assert page.locator('.katex-display').count() == 0
    assert overflow_of(page).split(',') == ['q-mathrm']


def test_inline_formula_in_panel_and_answer_is_reported(browser, tmp_path):
    wide = '$\\overline{' + terms(40) + '}$'
    path = write_pack(tmp_path, [dict(id='q-panel-inline', original=f'<p>{wide}</p>', ask='<p>구하세요.</p>')], 'problems')
    assert overflow_of(open_page(browser, path, display=False)).split(',') == ['q-panel-inline']
    path = write_pack(tmp_path, [dict(id='q-answer-inline', original='<p>식</p>', ask='<p>구하세요.</p>', answer=f'<p>{wide}</p>')], 'answers')
    assert overflow_of(open_page(browser, path, display=False)).split(',') == ['q-answer-inline']


def test_short_inline_formulas_are_not_reported(browser, tmp_path):
    # 대조군: 짧은 인라인 식과 호스트 안에서 줄이 바뀌는 글
    steps = ['<p>$x_1+x_2$ 이고 $\\overline{' + terms(4) + '}$ 이다. ' + '글 ' * 60 + '</p>']
    path = write_pack(tmp_path, [dict(id='q-ok', original='<p>$a+b$</p>', ask='<p>$y$</p>', steps=steps)], 'answers')
    assert overflow_of(open_page(browser, path, display=False)) == ''


# ---------- 쪽 순회 범위: 문항이 여럿인 팩 ----------

def three(bad):
    wide = ['<p>$$' + terms(90) + '$$</p>']
    ok = ['<p>$$x+y$$</p>']
    return [dict(id=f'q{i}', original='<p>식</p>', ask='<p>구하세요.</p>', steps=wide if i in bad else ok) for i in (1, 2, 3)]


@pytest.mark.parametrize('bad,expected', [({1}, 'q1'), ({2}, 'q2'), ({3}, 'q3'), ({1, 3}, 'q1,q3'), ({1, 2, 3}, 'q1,q2,q3')])
def test_only_the_clipped_pages_are_reported_in_a_multi_problem_pack(browser, tmp_path, bad, expected):
    page = open_page(browser, write_pack(tmp_path, three(bad), 'answers'))
    assert overflow_of(page) == expected
    for i in (1, 2, 3):                     # 쪽 표시도 걸린 쪽에만
        assert (page.locator(f'#q{i}').get_attribute('data-overflow') is not None) == (i in bad)


def test_page_already_overflowing_is_listed_once(browser, tmp_path):
    # 풀이가 칸에 안 들어가(fitSolution 이 이미 넘침으로 올림) 훑기에도 걸리는 쪽: id 는 한 번만
    tall = ['<p>$$' + terms(90) + '$$</p>'] + ['<p>' + '긴 풀이 문장입니다. ' * 12 + '</p>'] * 60
    probs = [dict(id='q-dup', original='<p>식</p>', ask='<p>구하세요.</p>', steps=tall),
             dict(id='q-clean', original='<p>식</p>', ask='<p>구하세요.</p>'),
             dict(id='q-scan-only', original='<p>식</p>', ask='<p>구하세요.</p>', steps=['<p>$$' + terms(90) + '$$</p>'])]
    page = open_page(browser, write_pack(tmp_path, probs, 'answers'))
    assert overflow_of(page) == 'q-dup,q-scan-only'
    # q-dup 은 맞춤 쪽에서 이미 넘침이고(마지막 단계가 칸 밖) 훑기 조건도 참이다
    assert page.evaluate("(() => { const f = document.querySelector('#q-dup .sol-flow').getBoundingClientRect();"
                         " const l = document.querySelector('#q-dup .sol-step:last-child').getBoundingClientRect();"
                         " return l.bottom > f.bottom + 1 || l.right > f.right + 1; })()")
    assert page.evaluate("hasClippedContent(document.getElementById('q-dup'))")


def test_bare_table_without_wrapper_is_checked(browser, tmp_path):
    # `.table-wrap` 없이 쓴 30열 표(풀이 단계). 옛 선택(.table-wrap)은 못 봤다.
    head = ''.join(f'<th>H{i}</th>' for i in range(30))
    row = ''.join('<td>1</td>' for _ in range(30))
    steps = [f'<table><thead><tr>{head}</tr></thead><tbody><tr>{row}</tr></tbody></table>']
    path = write_pack(tmp_path, [dict(id='q-bare', original='<p>표</p>', ask='<p>구하세요.</p>', steps=steps)], 'answers')
    page = open_page(browser, path, display=False)
    assert page.locator('#q-bare .table-wrap').count() == 0
    assert overflow_of(page).split(',') == ['q-bare']


# ---------- 합성 DOM 으로 훑기 함수만 ----------

@pytest.fixture(scope='module')
def scratch(browser, tmp_path_factory):
    """템플릿이 올라온 쪽. hasClippedContent 가 전역 함수로 있어야 한다."""
    path = write_pack(tmp_path_factory.mktemp('scratch'), [dict(id='q-s', original='<p>$$x=1$$</p>', ask='<p>y</p>')], 'answers')
    page = open_page(browser, path)
    assert page.evaluate("typeof hasClippedContent") == 'function'
    return page


FLOW = ('<section class="page page--problem" id="t" style="position:absolute;left:0;top:0;width:400px">'
        '<div class="sol-flow" style="flex:none;position:relative;height:100px;width:300px;overflow:hidden">'
        '<ol class="sol-steps">{steps}</ol></div></section>')


def clipped(page, html):
    return page.evaluate('''html => {
      document.querySelectorAll('#t').forEach(n => n.remove());
      document.body.insertAdjacentHTML('beforeend', html);
      const r = hasClippedContent(document.getElementById('t'));
      document.getElementById('t').remove();
      return r;
    }''', html)


def step(top, height, width=100):
    pos = f'position:absolute;left:0;top:{top}px;height:{height}px;width:{width}px;margin:0'
    return f'<li class="sol-step" style="{pos}"></li>'


def test_every_solution_step_is_checked(scratch):
    # 첫 단계만 flow 아래로 나가고 마지막 단계는 안에 있다: 마지막만 보던 기존 fits() 는 통과시켰다.
    out_first = FLOW.format(steps=step(0, 220) + step(0, 20) + step(30, 20))
    assert clipped(scratch, out_first) is True
    # 가운데 단계가 나간 경우
    assert clipped(scratch, FLOW.format(steps=step(0, 20) + step(0, 220) + step(30, 20))) is True
    # 셋 모두 안
    assert clipped(scratch, FLOW.format(steps=step(0, 20) + step(30, 20) + step(60, 30))) is False
    # 오른쪽으로 나간(넘친 단) 단계
    assert clipped(scratch, FLOW.format(steps=step(0, 20) + step(30, 20, width=450))) is True
    # flow 가 없는 쪽(문제지)은 거짓
    assert clipped(scratch, '<section class="page page--problem" id="t"><p>x</p></section>') is False


# 표: wrap 보다 넓다는 것만으로는 걸지 않는다. 실제로 잘리거나(clip 조상) 옆 단·flow 밖을 침범할 때만 참이다.
PAGE = '<section class="page page--problem" id="t" style="position:absolute;left:0;top:0;width:700px">{}</section>'
COLS = ('<div class="sol-flow{cls}" style="flex:none;position:relative;width:600px;height:200px;padding:0;overflow:{overflow};'
        'column-count:2;column-gap:30px;column-fill:auto">{}</div>')   # 단 폭 285, 다음 단 왼쪽은 315


def tbl(width):
    return f'<table style="width:{width}px;table-layout:fixed;border-collapse:collapse"><tr><td style="padding:0">1</td></tr></table>'


def wrap_in_column(table_width, first_column=True, overflow='hidden', bare=False):
    filler = '' if first_column else '<div style="height:200px"></div>'
    body = tbl(table_width) if bare else f'<div class="table-wrap" style="width:285px">{tbl(table_width)}</div>'
    return PAGE.format(COLS.format(filler + body, cls=' is-2col', overflow=overflow))


def test_table_spilling_into_the_column_gap_is_not_reported(scratch):
    # 실험05 q-sa-enc8x3 꼴: 첫 단 폭(285)을 11px 넘었지만 단 사이 여백(30px) 안에서 끝난다 → 보이고 겹치지 않는다
    assert clipped(scratch, wrap_in_column(296)) is False
    assert clipped(scratch, wrap_in_column(285)) is False


def test_bare_table_follows_the_same_rules(scratch):
    # `.table-wrap` 없는 table: 단 사이 여백은 통과, 다음 단 침범은 참(11px 오탐 판정은 그대로)
    assert clipped(scratch, wrap_in_column(296, bare=True)) is False
    assert clipped(scratch, wrap_in_column(330, bare=True)) is True
    assert clipped(scratch, wrap_in_column(300, first_column=False, bare=True)) is True
    assert clipped(scratch, PAGE.format(f'<div style="width:200px;overflow:hidden">{tbl(260)}</div>')) is True


def test_inline_formula_is_checked_against_its_text_box(scratch):
    def inline(host_cls, content_width, tag='div', extra=''):
        return PAGE.format(f'<{tag} class="{host_cls}" style="width:200px;{extra}"><span class="katex"><span class="katex-html">'
                           f'<span style="display:inline-block;width:{content_width}px;height:10px"></span></span></span></{tag}>')
    for host in ('prose sol-step-body', 'prose', 'hint-strip-item', 'sol-answer'):
        assert clipped(scratch, inline(host, 260)) is True, host
        assert clipped(scratch, inline(host, 180)) is False, host
    # 표 칸 안
    cell = PAGE.format('<table style="table-layout:fixed;width:100px"><tr><td style="padding:0">'
                       '<span class="katex"><span class="katex-html"><span style="display:inline-block;width:{}px;height:10px"></span></span></span>'
                       '</td></tr></table>')
    assert clipped(scratch, cell.format(160)) is True
    assert clipped(scratch, cell.format(90)) is False
    # display 식 안의 .katex 는 이미 display 검사가 맡는다, Hint 띠 식은 범위 밖(문서의 한계)
    strip = PAGE.format('<div class="hint-strip-item" style="width:100px"><span class="hint-strip-formula"><span class="katex">'
                        '<span class="katex-html"><span style="display:inline-block;width:300px;height:10px"></span></span></span></span></div>')
    assert clipped(scratch, strip) is False


def test_table_reaching_into_the_next_column_is_reported(scratch):
    assert clipped(scratch, wrap_in_column(330)) is True      # 다음 단 왼쪽(315)을 15px 넘는다
    assert clipped(scratch, wrap_in_column(318)) is True      # 3px 만 넘어도 옆 단 글자를 건드린다


def test_table_in_the_last_column_is_checked_against_the_flow_edge(scratch):
    assert clipped(scratch, wrap_in_column(285, first_column=False)) is False   # 315+285=600: flow 오른쪽에 딱 맞는다
    assert clipped(scratch, wrap_in_column(300, first_column=False)) is True    # 315+300=615 > flow 오른쪽 600
    assert clipped(scratch, wrap_in_column(330, first_column=False)) is True
    # flow 자신이 clip 하지 않아도(조상 검사에 안 걸려도) 마지막 단은 flow 오른쪽을 기준으로 잡는다
    assert clipped(scratch, wrap_in_column(285, first_column=False, overflow='visible')) is False
    assert clipped(scratch, wrap_in_column(300, first_column=False, overflow='visible')) is True


def test_table_cut_by_an_overflow_hidden_ancestor_is_reported(scratch):
    def hidden(width, style='overflow:hidden'):
        return PAGE.format(f'<div style="width:200px;{style}"><div class="table-wrap">{tbl(width)}</div></div>')
    assert clipped(scratch, hidden(260)) is True              # 조상 오른쪽(200)에서 잘린다
    assert clipped(scratch, hidden(260, 'overflow-x:clip')) is True
    assert clipped(scratch, hidden(190)) is False
    # wrap 자신이 스크롤 영역이면 인쇄에서는 잘린다
    own = PAGE.format(f'<div class="table-wrap" style="width:200px;overflow-x:auto">{tbl(260)}</div>')
    assert clipped(scratch, own) is True
    # 잘리지도 침범하지도 않는 넘침(조상 clip 이 멀다)은 옛 scrollWidth 판정과 달리 거짓이다
    free = PAGE.format(f'<div class="table-wrap" style="width:200px">{tbl(260)}</div>')
    assert clipped(scratch, free) is False


def test_table_past_a_single_column_flow_edge_is_reported(scratch):
    def single(width):
        flow = ('<div class="sol-flow" style="flex:none;position:relative;width:300px;height:200px;padding:0;overflow:visible">'
                f'<div class="table-wrap" style="width:300px">{tbl(width)}</div></div>')
        return PAGE.format(flow)
    assert clipped(scratch, single(360)) is True              # flow 오른쪽(300) 밖, 잘리지는 않지만 옆 칸을 침범
    assert clipped(scratch, single(301)) is False             # 1px 이내는 반올림 오차로 본다
    assert clipped(scratch, single(280)) is False


def test_display_formula_wider_than_its_box_is_reported(scratch):
    # 합성 DOM: katex-display 안쪽 내용이 박스를 넘고 transform 으로 줄어든 뒤에도 넘친다.
    # `.katex` 블록 자체의 rect 는 transform 으로 작아져 박스 안에 있으므로 내용 범위를 재야 한다.
    def display(content_width, scale):
        return ('<section class="page page--problem" id="t" style="position:absolute;left:0;top:0;width:400px">'
                '<div class="katex-display" style="width:200px"><span class="katex" style="display:block;white-space:nowrap;'
                f'transform-origin:left center;transform:scale({scale})"><span class="katex-html">'
                f'<span style="display:inline-block;width:{content_width}px;height:10px"></span></span></span></div></section>')
    assert clipped(scratch, display(600, 0.7)) is True       # 420px > 200px
    assert clipped(scratch, display(250, 0.7)) is False      # 175px <= 200px
    assert clipped(scratch, display(180, 1)) is False


# ---------- 게시본 ----------

@pytest.mark.parametrize('pack', PACKS)
def test_published_packs_report_no_clipped_content(browser, tmp_path, pack):
    """게시본 문제·해설 payload 를 지금 템플릿으로 다시 렌더해 훑기가 아무 쪽도 걸지 않는지 본다.

    걸리면 임계값을 풀지 말고 어느 쪽·어느 검사인지부터 본다(plan Task 2 Step 4).
    """
    folder = NOTES/pack
    names = [f'{pack}_기출문제.html', f'{pack}_기출풀이.html']
    if not all((folder/n).exists() for n in names):
        pytest.fail(f'{pack} 게시본이 없다')
    # 게시본이 쓰는 자료(vendor·그림)를 그대로 쓴다
    (tmp_path/DATA).symlink_to((folder/DATA).resolve(), target_is_directory=True)
    for name in names:
        data = read_workbook_payload(folder/name)
        out = tmp_path/name
        out.write_text(render_workbook_html(data, folder/DATA/'assets'), encoding='utf-8')
        page = open_page(browser, out, display='$$' in str(data))
        try:
            assert page.evaluate('typeof hasClippedContent') == 'function', f'{name}: 훑기가 템플릿에 없다'
            ids = [p['id'] for p in data['problems']]
            assert page.locator('.page--problem').evaluate_all('n => n.map(x => x.id)') == ids
            assert overflow_of(page) == '', f'{name}: data-overflow={overflow_of(page)!r}'
        finally:
            page.close()
