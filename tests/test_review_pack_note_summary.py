"""Note summaries are rules / why / traps parts, not one paragraph."""
import shutil
from pathlib import Path
import pytest
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.manifest import validate_manifest
from scripts.lab.review_pack.note_metadata import summary_structure_errors

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

def test_build_enforces_only_when_opted_in(tmp_path):
    run = tmp_path / 'run'; shutil.copytree(RUN, run)
    (run / 'sections/t-mux.html').write_text(sum_('<p>외울 규칙은 S=0이면 I0예요.</p>'), encoding='utf-8')
    m = fixture(); m['note_presentation_version'] = 2
    assemble(m, run, tmp_path / 'old', ASSETS)
    m['note_summary_version'] = 2
    with pytest.raises(ValueError, match='t-mux'):
        assemble(m, run, tmp_path / 'new', ASSETS)
    (run / 'sections/t-mux.html').write_text(sum_(RULES + WHY), encoding='utf-8')
    note = assemble(m, run, tmp_path / 'ok', ASSETS)['note_html'].read_text(encoding='utf-8')
    assert 'class="sum-rules"' in note

@pytest.mark.parametrize('value', [True, 1, 3, '2'])
def test_invalid_summary_version(value):
    m = fixture(); m['note_presentation_version'] = 2; m['note_summary_version'] = value
    assert validate_manifest(m)

def test_summary_version_needs_presentation_v2():
    m = fixture(); m['note_summary_version'] = 2
    assert validate_manifest(m)
