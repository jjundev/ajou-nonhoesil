import pytest

from scripts.lab.review_pack.explanation_content import validate_fragment, load_explanations
from scripts.lab.review_pack.manifest import validate_manifest, output_names
from tests.test_review_pack_explanation_content import setup, FRAGMENT
from tests._explanation_recall_fixture import setup_v2, FRAGMENT_V2, RECALL, SUMMARY


def test_v1_and_inactive_manifest_remain_readable(tmp_path):
    m, root, data = setup(tmp_path)
    assert validate_manifest(m) == []
    assert len(load_explanations(m, data, root)) == 1
    del m['problem_explanation_version']
    del m['explanation_checks']
    assert validate_manifest(m) == []
    assert 'explanation_html' not in output_names(4)


def test_v2_contract_and_names(tmp_path):
    m, root, data = setup_v2(tmp_path)
    assert validate_manifest(m) == []
    assert len(load_explanations(m, data, root)) == 1
    assert output_names(4, review_presentation_version=2,
                        problem_explanation_version=2)['explanation_html'] == '실험04_문제설명.html'


@pytest.mark.parametrize('body', [
    '<h4>개념</h4>', '<div><h4>개념</h4></div>',
    '<span class="layer-title">개념</span>',
    '<h4>개념</h4><p hidden>숨긴 설명</p>',
    '<h4>개념</h4><div aria-hidden="true">숨긴 설명</div>',
    '<h4>개념</h4><p>&nbsp; </p>',
])
def test_recall_requires_visible_body(body):
    replacement = '<div class="layer formal" data-explanation="recall">' + body + '</div>'
    with pytest.raises(ValueError, match='recall'):
        validate_fragment(FRAGMENT_V2.replace(RECALL, replacement), 'q', 'verified', version=2)


@pytest.mark.parametrize('fragment', [
    FRAGMENT, FRAGMENT_V2 + RECALL,
    FRAGMENT_V2.replace(RECALL, '').replace(
        '<div class="layer formal" data-explanation="solve">',
        RECALL + '<div class="layer formal" data-explanation="solve">'),
    FRAGMENT_V2.replace(RECALL, '<div>' + RECALL + '</div>'),
    FRAGMENT_V2 + '<div data-explanation="foreign"><p>문장</p></div>',
])
def test_v2_section_coverage_order_and_direct_children(fragment):
    with pytest.raises(ValueError):
        validate_fragment(fragment, 'q', 'verified', version=2)


def test_v2_requires_concept_summary():
    with pytest.raises(ValueError, match='summary'):
        validate_fragment(FRAGMENT_V2.replace(SUMMARY, ''), 'q', 'verified', version=2)


@pytest.mark.parametrize('replacement', [
    '<p data-summary="recall"><strong class="layer-title">개념</strong></p>',
    '<div data-summary="recall"><h4>제목</h4></div>',
    SUMMARY + SUMMARY,
])
def test_v2_concept_summary_needs_one_body(replacement):
    with pytest.raises(ValueError, match='summary'):
        validate_fragment(FRAGMENT_V2.replace(SUMMARY, replacement), 'q', 'verified', version=2)


@pytest.mark.parametrize('version', [0, 3, True, '2'])
def test_unknown_versions_rejected(tmp_path, version):
    m, root, data = setup_v2(tmp_path)
    m['problem_explanation_version'] = version
    assert validate_manifest(m)


@pytest.mark.parametrize('wrapper', [
    '<div hidden>{}</div>', '<div aria-hidden="true">{}</div>',
    '<h4>{}</h4>', '<div class="layer-title">{}</div>',
    '<div><span hidden>{}</span></div>',
])
def test_summary_rejects_excluded_ancestor(wrapper):
    with pytest.raises(ValueError, match='summary needs recall body'):
        validate_fragment(FRAGMENT_V2.replace(SUMMARY, wrapper.format(SUMMARY)),
                          'q', 'verified', version=2)


def test_summary_accepts_visible_nested_wrapper_inside_outer_hidden_sum():
    validate_fragment(FRAGMENT_V2.replace(SUMMARY, '<div><span>' + SUMMARY + '</span></div>'),
                      'q', 'verified', version=2)


@pytest.mark.parametrize('wrapper', ['<div hidden>{}</div>', '<h4>{}</h4>'])
def test_v1_summary_ancestor_behavior_is_unchanged(wrapper):
    validate_fragment(FRAGMENT.replace('<p>S를 읽고 입력을 골라요.</p>',
                                      wrapper.format('<p>S를 읽고 입력을 골라요.</p>')),
                      'q', 'verified', version=1)
