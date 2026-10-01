from pathlib import Path
import pytest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import validate_manifest

RUN = Path('tests/fixtures/review_pack')
ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')

def build(tmp_path, m):
    paths = assemble(m, RUN, tmp_path/'stage', ASSETS)
    convert_pack(paths['note_html'], paths['review_html'], manifest=m)
    return paths

def test_note_metadata_only_in_md(tmp_path):
    m = fixture(); m['note_presentation_version'] = 2
    paths = build(tmp_path, m)
    h = paths['note_html'].read_text(encoding='utf-8')
    d = paths['note_html'].with_suffix('.md').read_text(encoding='utf-8')
    assert 'class="sources"' not in h
    assert '출처와 문항목록.md에서' not in h
    assert '이 개념으로 풀 문제' not in h
    assert '출처:' in d and '#q-mux-001' in d
    assert check_pack(tmp_path/'stage') == []
    paths['note_html'].with_suffix('.md').write_text(
        d.replace('이 개념으로 풀 문제', '누락'), encoding='utf-8')
    assert any('metadata' in e for e in check_pack(tmp_path/'stage'))

def test_no_metadata_for_empty_topic():
    from scripts.lab.review_pack.note_metadata import topic_metadata
    m = fixture(); m['topics'][0]['sources'] = []; m['problems'] = []
    assert topic_metadata(m) == {'t-mux': ''}

def test_held_problem_is_not_linked():
    from scripts.lab.review_pack.note_metadata import topic_metadata
    m = fixture(); m['problems'][0]['status'] = 'held'
    assert '#q-mux-001' not in topic_metadata(m)['t-mux']

def test_legacy_output_remains_valid(tmp_path):
    paths = build(tmp_path, fixture())
    assert 'class="sources"' in paths['note_html'].read_text(encoding='utf-8')
    assert check_pack(tmp_path/'stage') == []

@pytest.mark.parametrize('value', [True, 1, 3, '2', None])
def test_invalid_presentation_version(value):
    m = fixture(); m['note_presentation_version'] = value
    assert validate_manifest(m)

def test_metadata_is_checked_per_topic(tmp_path):
    m = fixture(); m['note_presentation_version'] = 2
    m['topics'].append(dict(m['topics'][0], id='t-second'))
    paths = build(tmp_path, m)
    md = paths['note_html'].with_suffix('.md')
    text = md.read_text(encoding='utf-8')
    start = text.index('<a id="t-second">')
    md.write_text(text[:start] + text[start:].replace('출처:', '누락:'), encoding='utf-8')
    assert any('t-second' in e for e in check_pack(tmp_path/'stage'))

def test_injected_hidden_metadata_rejected(tmp_path):
    from scripts.lab.review_pack.note_metadata import check_note_metadata
    m = fixture(); m['note_presentation_version'] = 2
    paths = build(tmp_path, m)
    h = paths['note_html'].read_text(encoding='utf-8').replace('</main>', '<p hidden>출처: 원본</p></main>')
    d = paths['note_html'].with_suffix('.md').read_text(encoding='utf-8')
    assert check_note_metadata(m, h, d)
