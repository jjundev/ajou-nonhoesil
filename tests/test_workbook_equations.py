"""쉼표로 이어진 논리식이 식마다 한 줄로 나뉘는지 본다.

템플릿의 breakEquations 는 순수 JS 함수라 합성 해설지를 연 쪽에서 직접 불러 잰다.
실제 식은 복습노트/실험05/실험05_기출풀이.md 의 기출4·7·12 에서 가져왔다.
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


def test_patch_applies_to_both_templates():
    for name in ('problem.html', 'answer.html'):
        text = (ASSETS/'workbook'/name).read_text(encoding='utf-8').replace('\r\n', '\n')
        assert 'splitEquationList' in apply_local_patches(text, name)


@pytest.fixture(scope='module')
def breaker(tmp_path_factory):
    pw = pytest.importorskip('playwright.sync_api')
    path = _synthetic_pack(tmp_path_factory.mktemp('equations'),
                           [dict(id='q-eq', original='<p>식</p>', ask='<p>구하세요.</p>')], 'answers')
    with pw.sync_playwright() as driver:
        with driver.chromium.launch(channel='chrome') as browser:
            page = browser.new_page(viewport={'width': 1280, 'height': 900})
            page.goto(path.resolve().as_uri())
            page.wait_for_function('document.documentElement.dataset.ready', timeout=60000)
            yield lambda html: page.evaluate('h => breakEquations(h)', html)


@pytest.mark.parametrize('tex,labels', [
    (OUTPUT, ['O_0', 'O_1', 'O_2', 'O_3']),
    (BITS, [r'\mathrm{Bit3}', r'\mathrm{Bit2}', r'\mathrm{Bit1}', r'\mathrm{Bit0}']),
    (DEMUX, ['Y_0', 'Y_1', 'Y_2', 'Y_3']),
])
def test_comma_list_becomes_one_aligned_row_per_equation(breaker, tex, labels):
    out = breaker(f'$${tex}$$')
    assert out.count(r'\begin{aligned}') == 1
    assert re.findall(r'(\\mathrm\{Bit\d\}|[OY]_\d) &amp;= ', out) == labels
    assert out.count(r' \\ ') == 3
    assert r',\ ' not in out


def test_function_arguments_are_not_split(breaker):
    out = breaker(r'$$f(a,b)=\overline{x_1}\,\overline{x_2}\,\overline{x_3}\,\overline{x_4}\,\overline{x_5}$$')
    assert 'f(a,b) &amp;=' in out
    assert ' \\\\ ' not in out


def test_list_with_a_relationless_piece_is_kept_whole(breaker):
    # 둘째 조각 `\text{단 } y_1+y_2+y_3+y_4` 에는 관계 기호가 없다 → 쉼표 분할 없이 기존 동작
    out = breaker(r'$$x_1=a+b+c+d+e+f+g+h,\ \text{단 } y_1+y_2+y_3+y_4$$')
    assert out.count(r'\begin{aligned}') <= 1
    assert r'a+b+c+d+e+f+g+h,\ \text{단 } y_1+y_2+y_3+y_4' in out   # 한 행 안에 그대로
    assert ' \\\\ ' not in out


def test_comma_inside_text_is_not_a_list_separator(breaker):
    # \text{…} 안의 쉼표는 중괄호 안이라 최상위가 아니다
    out = breaker(r'$$x_1=a+b+c+d+e+f+g+h,\ \text{단,}\ y=z+z+z+z$$')
    assert out.count(r'\begin{aligned}') <= 1
    assert r'\text{단,}' in out


def test_short_list_stays_inline(breaker):
    src = r'$O_0=a,\ O_1=b$'
    assert breaker(src) == src


def test_single_chain_keeps_old_rows(breaker):
    out = breaker(r'$$A=B+C+D+E+F+G+H+I+J+K=L+M+N+O+P+Q+R+S+T+U$$')
    rows = [r.strip() for r in out.removeprefix(r'$$\begin{aligned}').removesuffix(r'\end{aligned}$$').split(' \\\\ ')]
    assert len(rows) == 2
    assert rows[1].startswith('&amp;= ')
