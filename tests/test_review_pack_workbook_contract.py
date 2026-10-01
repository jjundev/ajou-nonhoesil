# tests/test_review_pack_workbook_contract.py
from pathlib import Path
import hashlib
import json
import pytest
from tests._workbook_fixture import create_workbook_run
from tests.test_review_pack_manifest import fixture
from scripts.lab.review_pack.manifest import output_names, validate_manifest

def test_v2_names_and_legacy():
    assert set(output_names(4)) == {'note_html','note_md','review_html','review_md'}
    names = output_names(4, review_presentation_version=2)
    assert names['question_html'] == '실험04_기출문제.html'
    assert names['review_html'] == '실험04_기출풀이.html'
    assert validate_manifest(fixture()) == []

@pytest.mark.parametrize('version', [True, '2', 1, 3])
def test_reject_invalid_version(tmp_path, version):
    m, run = create_workbook_run(tmp_path)
    m['review_presentation_version'] = version
    assert validate_manifest(m)

def test_modern_requires_workbook_path(tmp_path):
    m, run = create_workbook_run(tmp_path)
    del m['problems'][0]['workbook_fragment']
    assert validate_manifest(m)
    m['problems'][0]['workbook_fragment'] = '../escape.json'
    assert validate_manifest(m)

def test_snapshot_matches_provenance():
    root = Path('.claude/skills/logic-lab-review-pack/assets/workbook')
    provenance = json.loads((root/'provenance.json').read_text(encoding='utf-8'))
    for name, digest in provenance['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest
