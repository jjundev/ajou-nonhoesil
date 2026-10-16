from pathlib import Path
from copy import deepcopy
import pytest
from tests.test_review_pack_explanation_content import setup, FRAGMENT
from scripts.lab.review_pack.explanation_render import write_explanations
from scripts.lab.review_pack.html2md import Parser
ASSETS=Path('.claude/skills/logic-lab-review-pack/assets')

def test_shared_note_shell_and_complete_content(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    paths=write_explanations(m,data,root,folder,ASSETS)
    html=paths['explanation_html'].read_text();md=paths['explanation_md'].read_text()
    assert 'data-screens="article.topic"' in html
    assert 'data-range="logic-lab-04-problem-explanation"' in html
    assert 'class="topic"' in html and 'data-explanation="solve"' in html
    assert '<details' not in html and 'pack-nav' not in html
    assert '문제 1 · 문항 제목' in html
    assert 'S=0이면 I0' in md and 'q-mux-001' in md
    template=ASSETS.joinpath('note-template.html').read_text()
    assert html.partition('<style>')[2].partition('</style>')[0]==template.partition('<style>')[2].partition('</style>')[0]

def test_original_prefilled_table_preserved(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    original='<table><tr><th>D7</th><th>D0</th></tr><tr><td>0</td><td>1</td></tr></table>'
    data['problems'][0]['html']['original']=original
    paths=write_explanations(m,data,root,folder,ASSETS)
    assert original in paths['explanation_html'].read_text()

def test_md_keeps_math_figures_anchors_and_sources(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    m['problems'][0]['sources']=m['topics'][0]['sources']
    path=root/m['problems'][0]['explanation_fragment']
    path.write_text(FRAGMENT.replace('Y=I0예요.','$Y=I_0$예요.'))
    paths=write_explanations(m,data,root,folder,ASSETS)
    md=paths['explanation_md'].read_text()
    assert '$Y=I_0$' in md and '<a id="q-mux-001"></a>' in md
    assert '출처:' in md and '출처:' not in paths['explanation_html'].read_text()

@pytest.mark.parametrize('state,label',[('disputed','답안 충돌'),('unresolved','정답 미확정')])
def test_answer_status_warning_is_not_lost(tmp_path,state,label):
    m,root,data=setup(tmp_path);m['problems'][0]['answer_status']=state
    (root/m['problems'][0]['explanation_fragment']).write_text(FRAGMENT.replace('선택선은 데이터가 아니에요.',label+' 조건을 확인해요.'))
    before=deepcopy(m);folder=tmp_path/'stage';folder.mkdir()
    paths=write_explanations(m,data,root,folder,ASSETS)
    assert label in paths['explanation_html'].read_text() and label in paths['explanation_md'].read_text()
    assert m==before

def test_future_workbook_build_includes_explanations(tmp_path):
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    m,root,data=setup(tmp_path)
    paths=assemble(m,root,tmp_path/'stage',ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    for label in ('실험설명','기출문제','기출풀이','문제설명'):
        for ext in ('html','md'):assert (tmp_path/'stage'/('.pack' if ext=='md' else '')/f'실험04_{label}.{ext}').is_file()


@pytest.mark.parametrize('equation', [
    '<p>S = x′y + xy′,  C = xy  (1)</p>',
    '<p>$$Y=\\overline{S}I_0+SI_1$$</p>',
    '<p>$R_{p(on)} = \\dfrac{V_{DD}-V_{OHmin}}{|I_{OHmax}|}$</p>',
])
def test_standalone_equations_are_cards_in_problem_and_solution(tmp_path, equation):
    m, root, data = setup(tmp_path)
    folder = tmp_path / 'stage'; folder.mkdir()
    data['problems'][0]['html']['original'] = '<p>식을 보고 회로를 그려요.</p>' + equation
    fragment = root / m['problems'][0]['explanation_fragment']
    fragment.write_text(FRAGMENT.replace('<p>Y=I0예요.</p>', equation))
    paths = write_explanations(m, data, root, folder, ASSETS)
    parser = Parser(); parser.feed(paths['explanation_html'].read_text())
    cards = [n for n in parser.root.walk() if 'equation-card' in n.attrs.get('class', '').split()]
    assert len(cards) == 2
    assert all(n.attrs.get('aria-label') == '수식' for n in cards)
    assert equation in paths['explanation_html'].read_text()
    assert '식을 보고 회로를 그려요.' in paths['explanation_md'].read_text()


def test_equation_cards_keep_prose_and_do_not_nest(tmp_path):
    m, root, data = setup(tmp_path)
    folder = tmp_path / 'stage'; folder.mkdir()
    prose = '<p>S=0이면 I0를 선택해요.</p>'
    card = '<div class="equation-card" role="group" aria-label="수식"><p>Y=I0</p></div>'
    data['problems'][0]['html']['original'] = prose + card
    paths = write_explanations(m, data, root, folder, ASSETS)
    html = paths['explanation_html'].read_text()
    assert prose in html
    assert html.count('class="equation-card"') == 1


def test_tables_are_cards_in_problem_and_solution_without_changing_cells(tmp_path):
    m, root, data = setup(tmp_path)
    folder = tmp_path / 'stage'; folder.mkdir()
    table = '<table><tr><th>D</th><th>A2</th></tr><tr><td>0000 0001</td><td>0</td></tr><tr><td>0000 0010</td><td></td></tr></table>'
    data['problems'][0]['html']['original'] = '<p>표를 완성하세요.</p>' + table + '<p>첫 행은 주어졌어요.</p>'
    fragment = root / m['problems'][0]['explanation_fragment']
    fragment.write_text(FRAGMENT.replace('<p>Y=I0예요.</p>', '<div class="table-wrap">'+table+'</div>'))
    paths = write_explanations(m, data, root, folder, ASSETS)
    html = paths['explanation_html'].read_text()
    parser = Parser(); parser.feed(html)
    cards = [n for n in parser.root.walk() if 'table-card' in n.attrs.get('class', '').split()]
    assert len(cards) == 2
    assert all(n.attrs.get('aria-label') == '표' for n in cards)
    assert html.count(table) == 2
    assert '<p>첫 행은 주어졌어요.</p>' in html
    assert '0000 0010' in paths['explanation_md'].read_text()


def test_authored_table_card_is_not_nested(tmp_path):
    m, root, data = setup(tmp_path)
    folder = tmp_path / 'stage'; folder.mkdir()
    card = '<div class="table-card" role="group" aria-label="표"><table><tr><td></td></tr></table></div>'
    data['problems'][0]['html']['original'] = card
    paths = write_explanations(m, data, root, folder, ASSETS)
    html = paths['explanation_html'].read_text()
    assert html.count('class="table-card"') == 1
    assert card in html


def test_v2_full_build_and_markdown_include_recall(tmp_path):
    from tests._explanation_recall_fixture import setup_v2
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    from scripts.lab.review_pack.checks import check_pack
    m, run, data = setup_v2(tmp_path)
    stage = tmp_path/'stage'
    paths = assemble(m, run, stage, ASSETS)
    outputs, count = convert_pack(paths['note_html'], paths['review_html'], manifest=m)
    for label in ('실험설명','기출문제','기출풀이','문제설명'):
        for ext in ('html','md'):
            assert (stage/('.pack' if ext=='md' else '')/f'실험04_{label}.{ext}').is_file()
    assert paths['explanation_md'] in outputs
    assert '선택선이라는 단서' in paths['explanation_md'].read_text(encoding='utf-8')
    assert '핵심 개념:' in paths['explanation_md'].read_text(encoding='utf-8')
    assert 'data-summary="recall"' in paths['explanation_html'].read_text(encoding='utf-8')
    assert check_pack(stage) == []


@pytest.mark.parametrize('state,label',[('disputed','답안 충돌'),('unresolved','정답 미확정')])
def test_v2_answer_warning_and_manifest_preserved(tmp_path,state,label):
    from tests._explanation_recall_fixture import setup_v2,FRAGMENT_V2
    m,run,data=setup_v2(tmp_path)
    m['problems'][0]['answer_status']=state
    (run/m['problems'][0]['explanation_fragment']).write_text(
        FRAGMENT_V2.replace('선택선은 데이터가 아니에요.',label+' 조건을 확인해요.'),encoding='utf-8')
    before=deepcopy(m)
    folder=tmp_path/'stage'; folder.mkdir()
    paths=write_explanations(m,data,run,folder,ASSETS)
    assert label in paths['explanation_html'].read_text(encoding='utf-8')
    assert label in paths['explanation_md'].read_text(encoding='utf-8')
    assert m==before



def test_recall_equation_and_table_survive_render_and_md(tmp_path):
    from tests._explanation_recall_fixture import setup_v2,FRAGMENT_V2,RECALL
    m,run,data=setup_v2(tmp_path)
    extra='<p>$$Y=\\overline{S}I_0+SI_1$$</p><table><tr><th>S</th><th>선택</th></tr><tr><td>0</td><td>I0</td></tr></table>'
    fragment=FRAGMENT_V2.replace(RECALL,RECALL.replace('</div>',extra+'</div>'))
    (run/m['problems'][0]['explanation_fragment']).write_text(fragment,encoding='utf-8')
    folder=tmp_path/'stage'; folder.mkdir()
    paths=write_explanations(m,data,run,folder,ASSETS)
    parser=Parser(); parser.feed(paths['explanation_html'].read_text(encoding='utf-8'))
    recall=next(n for n in parser.root.walk() if n.attrs.get('data-explanation')=='recall')
    classes=[n.attrs.get('class','').split() for n in recall.walk()]
    assert any('equation-card' in c for c in classes)
    assert any('table-card' in c for c in classes)
    md=paths['explanation_md'].read_text(encoding='utf-8')
    assert '\\overline{S}' in md and 'I0' in md and '선택' in md



def test_real_source05_v2_full_build(tmp_path):
    import json,shutil
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    from scripts.lab.review_pack.checks import check_pack
    from scripts.lab.review_pack.manifest import validate_manifest
    # Stored author tree omits imported evidence; materialize the exact published
    # snapshot in an isolated run and keep its original checksum guard enabled.
    source=Path('docs/learning-pack-source/실험05')
    run=tmp_path/'run';shutil.copytree(source,run)
    shutil.copytree(Path('복습노트/실험05/.pack/evidence'),run/'evidence')
    shutil.copy2(Path('복습노트/실험05/.pack/원문과_저작안내.md'),run/'원문과_저작안내.md')
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    assert validate_manifest(manifest)==[]
    assert set(manifest['explanation_checks'].values())=={'not_run'}
    paths=assemble(manifest,run,tmp_path/'stage',ASSETS)
    convert_pack(paths['note_html'],paths['review_html'],manifest=manifest)
    for label in ('실험설명','기출문제','기출풀이','문제설명'):
        for ext in ('html','md'):
            assert (tmp_path/'stage'/('.pack' if ext=='md' else '')/f'실험05_{label}.{ext}').is_file()
    parser=Parser();parser.feed(paths['explanation_html'].read_text(encoding='utf-8'))
    assert sum(n.attrs.get('data-explanation')=='recall' for n in parser.root.walk())==19
    assert check_pack(tmp_path/'stage')==[]

def test_recall_exported_to_md(tmp_path):
    m,root,data=setup(tmp_path);folder=tmp_path/'stage';folder.mkdir()
    paths=write_explanations(m,data,root,folder,ASSETS)
    html=paths['explanation_html'].read_text();md=paths['explanation_md'].read_text()
    assert html.index('data-explanation="recall"')<html.index('data-explanation="understand"')
    assert '이 문제를 보면 떠올려요' in md and '선택선 값 = 고를 입력 번호' in md and '떠올릴 것:' in md
