"""Note reading v1: conclusion first, compare rows marked, no generic titles or filler."""
import re
import shutil
from pathlib import Path
import pytest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.manifest import validate_manifest
from scripts.lab.review_pack.note_reading import reading_structure_errors
from scripts.lab.review_pack.html2md import export_document

RUN = Path('tests/fixtures/review_pack')
ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
SUM = '<div class="sum" hidden><p class="sum-label">외울 규칙</p><ul class="sum-rules"><li><b>S=0</b> → I0</li></ul></div>'
GIST = '<p class="gist"><strong>S가 고른 입력이 출력돼요.</strong> S=0이면 I0이에요.</p>'


def layer(title, body, kind='eli5'):
    return f'<div class="layer {kind}"><span class="layer-title">{title}</span>{body}</div>'


def table(*marks):
    rows = ''.join(f'<tr data-row="{m}"><td>{i}</td></tr>' if m else f'<tr><td>{i}</td></tr>' for i, m in enumerate(marks))
    return f'<div class="table-wrap"><table><thead><tr><th>S</th></tr></thead><tbody>{rows}</tbody></table></div>'


GOOD = layer('S가 출력 입력을 골라요', GIST) + layer('S=0과 S=1을 비교해요', table('compare', None, 'compare', 'avoid'), 'formal') + SUM


def test_good_topic_passes():
    assert reading_structure_errors('t', GOOD) == []


@pytest.mark.parametrize('html,why', [
    (layer('S가 출력 입력을 골라요', '<p>S=0이면 I0이에요.</p>') + SUM, 'no gist'),
    (layer('S가 출력 입력을 골라요', '<p class="gist">S=0이면 I0이에요.</p>') + SUM, 'gist without strong'),
    (layer('S가 출력 입력을 골라요', '<p>앞 문단</p>' + GIST) + SUM, 'gist not first'),
    (layer('한눈에 보기', GIST) + SUM, 'generic title'),
    (layer('S가 출력 입력을 골라요', GIST) + layer('헷갈리기 쉬운 말', '<p>x</p>', 'warn') + SUM, 'generic warn title'),
    (layer('S가 출력 입력을 골라요', GIST + '<p>다섯 줄로 기억하면 충분해요.</p>') + SUM, 'filler'),
    (layer('S가 출력 입력을 골라요', GIST + '<p>아래 표는 외울 필요 없고 꺼내 쓰면 돼요.</p>') + SUM, 'filler'),
    (layer('S가 출력 입력을 골라요', GIST + table('compare', None)) + SUM, 'single compare row'),
    (layer('S가 출력 입력을 골라요', GIST + table('hl', 'hl')) + SUM, 'unknown mark'),
    ('<p>층 없음</p>' + SUM, 'no layer'),
])
def test_rejected(html, why):
    assert reading_structure_errors('t', html), why


def test_practice_title_is_allowed():
    assert reading_structure_errors('t', GOOD.replace(SUM, layer('한 단계만 풀어 봐요', '<p>?</p>', 'supp') + SUM)) == []


@pytest.mark.parametrize('extra,ok', [
    (dict(note_reading_version=1), True),
    (dict(note_reading_version=2), False),
    (dict(note_reading_version=True), False),
])
def test_manifest_version(extra, ok):
    m = fixture(); m.update(note_presentation_version=2, note_summary_version=2, **extra)
    assert (validate_manifest(m) == []) is ok


def test_manifest_needs_summary_v2():
    m = fixture(); m.update(note_presentation_version=2, note_reading_version=1)
    assert any('note_reading_version' in e for e in validate_manifest(m))


def _run(tmp_path, fragment):
    run = tmp_path / 'run'; shutil.copytree(RUN, run)
    (run / 'sections/t-mux.html').write_text(fragment, encoding='utf-8')
    m = fixture(); m.update(note_presentation_version=2, note_summary_version=2)
    return run, m


def test_build_enforces_only_when_opted_in(tmp_path):
    bad = layer('한눈에 보기', '<p>S=0이면 I0이에요.</p>') + SUM
    run, m = _run(tmp_path, bad)
    assemble(m, run, tmp_path / 'old', ASSETS)
    m['note_reading_version'] = 1
    with pytest.raises(ValueError, match='t-mux'):
        assemble(m, run, tmp_path / 'new', ASSETS)


def test_build_keeps_row_marks_and_md_bolds_compare_rows(tmp_path):
    run, m = _run(tmp_path, GOOD)
    m['note_reading_version'] = 1
    paths = assemble(m, run, tmp_path / 'stage', ASSETS)
    page = paths['note_html'].read_text(encoding='utf-8')
    page = page[page.index('<section id="learning">'):page.index('</main>')]
    assert page.count('data-row="compare"') == 2 and 'data-row="avoid"' in page
    assert '<p class="gist">' in page
    md, _ = export_document(paths['note_html'], export=False)
    assert '| **0** |' in md and '| **2** |' in md and '| 1 |' in md and '| 3 |' in md


def test_template_has_one_reading_block():
    text = (ASSETS / 'note-template.html').read_text(encoding='utf-8')
    assert text.count('/* note-reading:start */') == 1 and text.count('/* note-reading:end */') == 1
    block = re.search(r'/\* note-reading:start \*/(.*?)/\* note-reading:end \*/', text, re.S).group(1)
    for selector in ('.gist', 'tr[data-row="compare"]', 'tr[data-row="avoid"]'):
        assert selector in block
