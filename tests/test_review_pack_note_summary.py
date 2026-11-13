"""Note summaries are rules / why / traps parts, not one paragraph."""
import json
import shutil
from pathlib import Path
import pytest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.manifest import validate_manifest
from scripts.lab.review_pack.note_metadata import summary_structure_errors
from scripts.lab.review_pack.note_summary import SUMMARY_FILE, check_topic_ids, load_note_summaries, lost_tokens, render_summary, replace_summary

RUN = Path('tests/fixtures/review_pack')
ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
RULES = '<p class="sum-label">외울 규칙</p><ul class="sum-rules"><li><b>S=0</b> → I0</li></ul>'
WHY = '<p class="sum-label">이유</p><p class="sum-why">선택선이 입력 번호예요.</p>'
TRAPS = '<p class="sum-label sum-label-warn">헷갈리지 마요</p><ul class="sum-traps"><li>S는 출력이 아니에요.</li></ul>'

def sum_(inner):
    return '<p>본문</p><div class="sum" hidden>' + inner + '</div>'

@pytest.mark.parametrize('inner', [RULES, RULES + WHY, RULES + TRAPS, RULES + WHY + TRAPS])
def test_valid_parts(inner):
    assert summary_structure_errors('t', sum_(inner)) == []

@pytest.mark.parametrize('inner,why', [
    ('<p>외울 규칙은 S=0이면 I0예요.</p>', 'old paragraph'),
    (WHY, 'no rules'),
    (WHY + RULES, 'rules not first'),
    (RULES + TRAPS + WHY, 'out of order'),
    (RULES + WHY + WHY, 'repeated'),
    ('<p class="sum-label">외울 규칙</p><ul class="sum-rules"></ul>', 'empty list'),
    ('<p class="sum-label">외울 규칙</p><p class="sum-rules">S=0 → I0</p>', 'rules not a list'),
    ('<p class="sum-label">요점</p><ul class="sum-rules"><li>x</li></ul>', 'unknown label'),
    (RULES + '<p class="sum-label">헷갈리지 마요</p><ul class="sum-traps"><li>x</li></ul>', 'traps label not warn'),
    (RULES + '덧붙인 글', 'loose text'),
])
def test_rejected(inner, why):
    assert summary_structure_errors('t', sum_(inner)), why

def test_two_sums_rejected():
    assert summary_structure_errors('t', sum_(RULES) + '<div class="sum" hidden>' + RULES + '</div>')

def _opt_in_run(tmp_path, inner='<p>외울 규칙은 S=0이면 I0예요.</p>'):
    run = tmp_path / 'run'; shutil.copytree(RUN, run)
    (run / 'sections/t-mux.html').write_text(sum_(inner), encoding='utf-8')
    m = fixture(); m['note_presentation_version'] = 2; m['note_summary_version'] = 2
    return run, m

def write_summaries(run, topics):
    (run / SUMMARY_FILE).write_text(json.dumps({'schema_version': 1, 'topics': topics}, ensure_ascii=False), encoding='utf-8')

def build_stage(run, m, stage):
    return assemble(m, run, stage, ASSETS)

def test_build_enforces_only_when_opted_in(tmp_path):
    run, m = _opt_in_run(tmp_path)
    del m['note_summary_version']
    build_stage(run, m, tmp_path / 'old')
    m['note_summary_version'] = 2
    with pytest.raises(ValueError, match='t-mux'):
        build_stage(run, m, tmp_path / 'new')
    (run / 'sections/t-mux.html').write_text(sum_(RULES + WHY), encoding='utf-8')
    note = build_stage(run, m, tmp_path / 'ok')['note_html'].read_text(encoding='utf-8')
    assert 'class="sum-rules"' in note

def test_build_applies_run_summaries(tmp_path):
    run, m = _opt_in_run(tmp_path)
    write_summaries(run, {t['id']: {'rules': [['A', 'B']]} for t in m['topics']})
    paths = build_stage(run, m, tmp_path / 'stage')
    html = paths['note_html'].read_text(encoding='utf-8')
    assert html.count('<p class="sum-label">외울 규칙</p>') == len(m['topics'])
    assert (tmp_path / 'stage/.pack/sections/note-summaries.json').read_bytes() == (run / SUMMARY_FILE).read_bytes()

def test_build_rejects_summary_topic_mismatch(tmp_path):
    run, m = _opt_in_run(tmp_path)
    write_summaries(run, {t['id']: {'rules': [['A', 'B']]} for t in m['topics'][1:]})
    with pytest.raises(ValueError, match=m['topics'][0]['id'] + ': missing summary'):
        build_stage(run, m, tmp_path / 'stage')

@pytest.mark.parametrize('value', [True, 1, 3, '2'])
def test_invalid_summary_version(value):
    m = fixture(); m['note_presentation_version'] = 2; m['note_summary_version'] = value
    assert validate_manifest(m)

def test_summary_version_needs_presentation_v2():
    m = fixture(); m['note_summary_version'] = 2
    assert validate_manifest(m)

def test_render_summary_passes_structure_check():
    html = render_summary(dict(rules=[['S=1', 'Q=1']], why='되먹임 때문이에요.', traps=['00은 금지예요.']))
    assert summary_structure_errors('t-x', html) == []
    assert '<li><b>S=1</b> → Q=1</li>' in html

def test_render_summary_omits_empty_parts():
    html = render_summary(dict(rules=[['A', 'B']]))
    assert '이유' not in html and '헷갈리지 마요' not in html
    assert summary_structure_errors('t-x', html) == []

def test_render_summary_keeps_inline_markup():
    html = render_summary(dict(rules=[['Q<sub>n</sub>', '유지']]))
    assert '<b>Q<sub>n</sub></b>' in html and summary_structure_errors('t-x', html) == []

def test_replace_summary_requires_exactly_one():
    with pytest.raises(ValueError, match='t-x'):
        replace_summary('t-x', '<p>본문</p>', dict(rules=[['A', 'B']]))
    two = '<div class="sum" hidden>a</div><div class="sum" hidden>b</div>'
    with pytest.raises(ValueError, match='t-x'):
        replace_summary('t-x', two, dict(rules=[['A', 'B']]))

def test_replace_summary_keeps_body_bytes():
    out = replace_summary('t-x', '<p>본문</p><div class="sum" hidden><p>옛 요약</p></div>', dict(rules=[['A', 'B']]))
    assert out.startswith('<p>본문</p><div class="sum" hidden><p class="sum-label">외울 규칙</p>')

def test_lost_tokens_names_missing_facts():
    old = '<div class="sum" hidden><p>74HC76은 J=K=1에서 토글해요.</p></div>'
    assert lost_tokens(old, render_summary(dict(rules=[['J=K=1', '토글']]))) == ['74HC76']
    assert lost_tokens(old, render_summary(dict(rules=[['74HC76 J=K=1', '토글']]))) == []

def test_load_note_summaries_rejects_bad_shape(tmp_path):
    (tmp_path / 'sections').mkdir()
    p = tmp_path / SUMMARY_FILE
    assert load_note_summaries(tmp_path) is None
    p.write_text(json.dumps({'schema_version': 1, 'topics': {'t-a': {'rules': []}}}), encoding='utf-8')
    with pytest.raises(ValueError, match='t-a'):
        load_note_summaries(tmp_path)
    p.write_text(json.dumps({'schema_version': 1, 'topics': {'t-a': {'rules': [['A', 'B']], 'note': 'x'}}}), encoding='utf-8')
    with pytest.raises(ValueError, match='t-a'):
        load_note_summaries(tmp_path)

def test_check_topic_ids_names_the_id():
    with pytest.raises(ValueError, match='t-b: missing summary'):
        check_topic_ids({'t-a': {}}, ['t-a', 't-b'])
    with pytest.raises(ValueError, match='t-z: unknown topic'):
        check_topic_ids({'t-a': {}, 't-z': {}}, ['t-a'])

def test_lost_tokens_does_not_glue_adjacent_items():
    old = '<div class="sum" hidden>NAND·NOR는 반대예요.</div>'
    assert lost_tokens(old, render_summary(dict(rules=[['OR', '1'], ['NAND·NOR', '반대']]))) == []

@pytest.mark.parametrize('old,new,lost', [
    ('74HC74는 ↑에서 저장해요.', '74HC74는 엣지에서 저장해요.', ['↑']),
    ('LED마다 330Ω 저항이에요.', 'LED마다 330 저항이에요.', ['330Ω']),
    ('Q(t−1)은 직전 값이에요.', 'Q(t+1)은 직전 값이에요.', ['−']),
    ('E=1·SR≠11 조건이에요.', 'E=1·SR=11 조건이에요.', ['≠']),
    ('최대 2ⁿ개예요.', '최대 2개예요.', ['2ⁿ']),
    ('입력 X(don’t-care)예요.', '입력 X(don-care)예요.', ['don’t']),
])
def test_lost_tokens_sees_symbols(old, new, lost):
    wrap = lambda t: '<div class="sum" hidden>' + t + '</div>'
    assert lost_tokens(wrap(old), wrap(new)) == lost

def test_check_pack_flags_summary_drift(tmp_path):
    from scripts.lab.review_pack.checks import check_pack
    from scripts.lab.review_pack.navigation_upgrade import ROOT
    (tmp_path / '.vendor').symlink_to((ROOT / '복습노트/.vendor').resolve(), target_is_directory=True)
    pack = tmp_path / '실험01'; shutil.copytree(ROOT / '복습노트/실험01', pack)
    assert check_pack(pack) == []
    page = pack / '실험01_실험설명.html'
    text = page.read_text(encoding='utf-8')
    page.write_text(text.replace('<li><b>NOT</b> → 0과 1을 뒤집어요</li>', '<li><b>NOT</b> → 손으로 고친 문장</li>', 1), encoding='utf-8')
    assert any('t-gates: summary differs from sections/note-summaries.json' in e for e in check_pack(pack))
