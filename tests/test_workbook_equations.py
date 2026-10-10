"""쉼표로 이어진 논리식이 식마다 한 줄로 나뉘는지 본다.

템플릿의 breakEquations 는 순수 JS 함수라 합성 해설지를 연 쪽에서 직접 불러 잰다.
실제 식은 복습노트/실험05/실험05_기출풀이.md 의 기출4·7·12 에서 가져왔다.

단언은 splitEquationList 를 한 곳씩 망가뜨려도(깊이 계산·머리 간격 제거·prefix·왼쪽 변 조건·
말미 깊이 검사·말미 쉼표) 실패하도록 행 전체를 잰다.
"""
import re
from pathlib import Path

import pytest

from scripts.lab.review_pack.workbook_render import apply_local_patches
from tests.test_review_pack_workbook_browser import _synthetic_pack

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')

OUTPUT = r"O_0=\overline{I_1}\,\overline{I_0},\ O_1=\overline{I_1}I_0,\ O_2=I_1\overline{I_0},\ O_3=I_1I_0"   # 기출4
BITS = r"\mathrm{Bit3}=SW5,\ \mathrm{Bit2}=SW1+SW2+SW3+SW4,\ \mathrm{Bit1}=SW0+SW3+SW4,\ \mathrm{Bit0}=SW0+SW2+SW4"  # 기출7
DEMUX = r"Y_0=\overline{S_1}\,\overline{S_0}D,\ Y_1=\overline{S_1}S_0D,\ Y_2=S_1\overline{S_0}D,\ Y_3=S_1S_0D"  # 기출12
LONG = r'\overline{x_1}\,\overline{x_2}\,\overline{x_3}\,\overline{x_4}\,\overline{x_5}'   # 40자를 넘기려는 우변
ROW_SEP = ' \\\\ '


def test_patch_applies_to_both_templates():
    for name in ('problem.html', 'answer.html'):
        text = (ASSETS/'workbook'/name).read_text(encoding='utf-8').replace('\r\n', '\n')
        assert 'splitEquationList' in apply_local_patches(text, name)


@pytest.fixture(scope='module')
def chrome():
    """모듈 하나에 playwright 를 한 번만 띄운다(sync API 는 한 스레드에서 중첩해 시작할 수 없다)."""
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            yield browser


@pytest.fixture(scope='module')
def breaker(chrome, tmp_path_factory):
    path = _synthetic_pack(tmp_path_factory.mktemp('equations'),
                           [dict(id='q-eq', original='<p>식</p>', ask='<p>구하세요.</p>')], 'answers')
    page = chrome.new_page(viewport={'width': 1280, 'height': 900})
    page.goto(path.resolve().as_uri())
    page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
    yield lambda html: page.evaluate('h => breakEquations(h)', html)
    page.close()


def rows_of(out):
    """`$$\\begin{aligned}행 \\\\ 행\\end{aligned}$$` 한 덩어리를 행 목록으로 돌려준다(앞뒤 공백 제거)."""
    m = re.fullmatch(r'\$\$\\begin\{aligned\}(.*)\\end\{aligned\}\$\$', out, re.S)
    assert m, out
    return [r.strip() for r in m.group(1).split(ROW_SEP)]


@pytest.mark.parametrize('tex,labels', [
    (OUTPUT, ['O_0', 'O_1', 'O_2', 'O_3']),
    (BITS, [r'\mathrm{Bit3}', r'\mathrm{Bit2}', r'\mathrm{Bit1}', r'\mathrm{Bit0}']),
    (DEMUX, ['Y_0', 'Y_1', 'Y_2', 'Y_3']),
])
def test_comma_list_becomes_one_aligned_row_per_equation(breaker, tex, labels):
    out = breaker(f'$${tex}$$')
    assert out.count(r'\begin{aligned}') == 1
    rows = rows_of(out)
    assert [r.split(' &amp;= ')[0] for r in rows] == labels
    # 모든 행이 라벨로 시작한다 — 앞 조각의 `,\ ` 꼬리나 이어 붙인 간격이 행 머리에 남지 않는다
    assert all(r.startswith(f'{label} &amp;= ') for r, label in zip(rows, labels)), rows
    assert r',\ ' not in out


@pytest.mark.parametrize('sep', [r',\ ', r',\quad ', r',\qquad ', r',\, ', r',\; ', ', ', ',  \\ \\quad '])
def test_piece_head_spacing_is_removed(breaker, sep):
    out = breaker('$$' + sep.join([f'Y_{i}=\\overline{{S_{i}}}D' for i in range(4)]) + '$$')
    rows = rows_of(out)
    assert [r.startswith(f'Y_{i} &amp;= ') for i, r in enumerate(rows)] == [True] * 4, rows
    assert rows == [f'Y_{i} &amp;= \\overline{{S_{i}}}D' for i in range(4)]


@pytest.mark.parametrize('tex', [
    r'f(a,b)=' + LONG,
    r'f(a=1,b=0)=' + LONG,      # 소괄호 안에 =
    r'g[a=1,b=0]=' + LONG,      # 대괄호 안에 =
    r'[0=a,1=b)=' + LONG,       # 반열린 구간 꼴
])
def test_commas_inside_brackets_are_not_list_separators(breaker, tex):
    out = breaker(f'$${tex}$$')
    # 괄호 안 쉼표는 최상위가 아니다 → 식 목록 분할이 일어나지 않아 `b` 가 새 행의 왼쪽 변이 되지 않는다
    assert not any(r.startswith(('b &amp;=', '1 &amp;=')) for r in rows_of(out)), out
    assert out.count(',') == tex.count(',')                 # 쉼표를 지우지도 않는다
    assert re.search(r'[a1],[b1]', out)                      # 쉼표가 앞 행 안에 그대로 있다


def test_list_inside_left_right_is_not_split(breaker):
    # \left\{ 은 중괄호 깊이가 아니라 \left…\right 깊이로만 잡힌다
    out = breaker(r'$$\left\{a=1,b=0\right\}=' + LONG + '$$')
    assert rows_of(out) == [r'\left\{a=1,b=0\right\} &amp;= ' + LONG]
    # 쉼표 앞 조각 `x=\left\{a` 와 뒤 조각 `b=1\right\}+…` 가 둘 다 관계식처럼 보이는 꼴: \left…\right 깊이를 안 세면 갈라진다
    out = breaker(r'$$x=\left\{a,b=1\right\}+' + LONG + '$$')
    assert rows_of(out) == [r'x &amp;= \left\{a,b=1\right\}+' + LONG]
    # \left( … \right) 도 한 식이다
    out = breaker(r'$$\left(a=1,b=0\right)=' + LONG + '$$')
    assert rows_of(out) == [r'\left(a=1,b=0\right) &amp;= ' + LONG]


def test_list_with_a_relationless_piece_is_kept_whole(breaker):
    # 둘째 조각 `\text{단 } y_1+y_2+y_3+y_4` 에는 관계 기호가 없다 → 쉼표 분할 없이 기존 동작
    out = breaker(r'$$x_1=a+b+c+d+e+f+g+h,\ \text{단 } y_1+y_2+y_3+y_4$$')
    assert rows_of(out) == [r'x_1 &amp;= a+b+c+d+e+f+g+h,\ \text{단 } y_1+y_2+y_3+y_4']


def test_comma_inside_text_is_not_a_list_separator(breaker):
    # \text{…} 안 쉼표는 중괄호 안이라 최상위가 아니다: 조각은 둘뿐이고 \text{단,} 는 둘째 행 왼쪽 변에 통째로 남는다
    out = breaker(r'$$x_1=a+b+c+d+e+f+g+h,\ \text{단,}\ y=z+z+z+z$$')
    assert rows_of(out) == [r'x_1 &amp;= a+b+c+d+e+f+g+h', r'\text{단,}\ y &amp;= z+z+z+z']


def test_relationless_left_side_piece_keeps_old_behaviour(breaker):
    # 둘째 조각 `=K+…` 은 왼쪽 변이 없다 → 쉼표 분할 안 함. 옛 동작은 `=` 마다 자르되 쉼표(`h,\ `)를 지우지 않는다
    out = breaker(r'$$A=B+C+D+E+F+G+H+I+J+K+L+M+N+O+P+Q+R+S+T+U+V+W+X+Y+Z+a+b+h,\ =K+L$$')
    assert rows_of(out) == ['A &amp;= B+C+D+E+F+G+H+I+J+K+L+M+N+O+P+Q+R+S+T+U+V+W+X+Y+Z+a+b+h,\\', '&amp;= K+L']


def test_trailing_comma_is_ignored(breaker):
    out = breaker(r'$$' + OUTPUT.replace(r',\ O_3=I_1I_0', '') + ',$$')   # O_0..O_2 뒤에 쉼표
    rows = rows_of(out)
    assert [r.split(' &amp;= ')[0] for r in rows] == ['O_0', 'O_1', 'O_2']
    assert not rows[-1].endswith(','), rows
    assert not any(r.startswith(r'\ ') for r in rows)
    # 네 식 전부 + 말미 쉼표
    out = breaker(r'$$' + OUTPUT + ',$$')
    assert [r.split(' &amp;= ')[0] for r in rows_of(out)] == ['O_0', 'O_1', 'O_2', 'O_3']


def test_single_equation_with_trailing_comma_keeps_old_behaviour(breaker):
    # 조각이 하나뿐이면 목록이 아니다: 옛 동작대로 쉼표가 우변 끝에 남는다
    out = breaker(r'$$x=1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1,$$')
    assert rows_of(out) == [r'x &amp;= 1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1+1,']


def test_unbalanced_delimiters_keep_old_behaviour(breaker):
    # `\left(` … `\right.` 는 깊이 계산상 끝에 1 이 남는다 → 안전하게 분할하지 않는다
    out = breaker(r'$$a=b+c+d+e+f+g+h+i+j+k+l+m+n+o,\ c=\left(d+e\right.$$')
    assert r',\ c' in out                        # 옛 동작: 쉼표와 꼬리표가 앞 행 끝에 남는다
    assert not any(r.startswith('c &amp;=') for r in rows_of(out))


def test_prefix_goes_on_the_first_row_only(breaker):
    out = breaker(r'$$x=1$$ → $$' + OUTPUT + '$$')
    assert out.count(r'\Rightarrow') == 1
    assert r'\begin{aligned}\Rightarrow\ O_0 &amp;= ' in out
    tail = out.split(r'\begin{aligned}', 1)[1]
    rows = tail.removesuffix(r'\end{aligned}$$').split(ROW_SEP)
    assert [r.startswith(r'\Rightarrow\ O_0 &amp;= ') for r in rows] == [True, False, False, False]
    assert all(r.startswith(f'O_{i} &amp;= ') for i, r in enumerate(rows) if i)


def test_piece_tail_is_left_alone(breaker):
    # 꼬리의 `\\ ` 는 간격 명령이 아니라 줄바꿈이다: `\` 와 공백을 먹으면 안 된다
    out = breaker(r'$$A=B+C+D+E+F+G+H+I+J+K+L+M+N+O+P+Q+R\\ ,D=E$$')
    assert rows_of(out) == [r'A &amp;= B+C+D+E+F+G+H+I+J+K+L+M+N+O+P+Q+R\\', r'D &amp;= E']


def test_short_list_stays_inline(breaker):
    src = r'$O_0=a,\ O_1=b$'
    assert breaker(src) == src


def test_single_chain_keeps_old_rows(breaker):
    out = breaker(r'$$A=B+C+D+E+F+G+H+I+J+K=L+M+N+O+P+Q+R+S+T+U$$')
    rows = rows_of(out)
    assert len(rows) == 2
    assert rows[1].startswith('&amp;= ')


# ---------- 게시본 ----------

def _top_level_commas(tex):
    """중괄호·소괄호·대괄호 깊이 0 에서 쉼표가 몇 개인지 센다. 백슬래시 뒤 한 글자(`\\,` 같은 간격 명령)는 건너뛴다."""
    depth = commas = 0
    it = iter(tex)
    for ch in it:
        if ch == '\\':
            next(it, None)
        elif ch in '{([':
            depth += 1
        elif ch in '})]':
            depth -= 1
        elif ch == ',' and depth == 0:
            commas += 1
    return commas


def test_published_experiment05_has_no_top_level_commas_in_display_math(chrome):
    """게시본 실험05 해설지의 디스플레이 식에 식 목록 쉼표가 남지 않고, 기출4 의 `O_0 &= ` 행이 있다."""
    html = Path('복습노트/실험05/실험05_기출풀이.html')
    page = chrome.new_page(viewport={'width': 1280, 'height': 900})
    try:
        page.goto(html.resolve().as_uri())
        page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
        texs = page.locator('.katex-display annotation[encoding="application/x-tex"]').evaluate_all(
            'n => n.map(x => x.textContent)')
    finally:
        page.close()
    assert texs, '디스플레이 식이 하나도 없다 — KaTeX 가 안 돌았다'
    with_commas = [t for t in texs if _top_level_commas(t)]
    assert with_commas == [], with_commas[:3]
    assert any(re.search(r'O_0\s*&=', t) for t in texs), '기출4 의 O_0 행이 aligned 로 나뉘지 않았다'
