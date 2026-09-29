from pathlib import Path
import pytest
from scripts.lab.review_pack.checks import boolean_equivalent,check_pack
from scripts.lab.review_pack.render import assemble
from scripts.lab.review_pack.html2md import convert_pack
from tests.test_review_pack_manifest import fixture

def make_pack(tmp_path):
    p=assemble(fixture(),Path('tests/fixtures/review_pack'),tmp_path/'stage',Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(p['note_html'],p['review_html'])
    return tmp_path/'stage'

def test_demorgan():
    assert boolean_equivalent("(A·B)'","A'+B'")
    assert not boolean_equivalent('A+B','A·B')
    with pytest.raises(ValueError):boolean_equivalent('!A',"A'")

def test_pack_ok(tmp_path):
    assert check_pack(make_pack(tmp_path))==[]

def test_missing_image(tmp_path):
    p=make_pack(tmp_path);f=p/'실험04_실험설명.html'
    f.write_text(f.read_text(encoding='utf-8').replace('</main>','<img src="missing.png"></main>'),encoding='utf-8')
    assert any('missing.png' in e for e in check_pack(p))

def test_duplicate_id(tmp_path):
    p=make_pack(tmp_path);f=p/'실험04_실험설명.html'
    f.write_text(f.read_text(encoding='utf-8').replace('</main>','<p id="t-mux">중복</p></main>'),encoding='utf-8')
    assert any('duplicate' in e for e in check_pack(p))

def test_external_resource(tmp_path):
    p=make_pack(tmp_path);f=p/'실험04_실험설명.html'
    f.write_text(f.read_text(encoding='utf-8').replace('</main>','<img src="https://example.com/x.png"></main>'),encoding='utf-8')
    assert any('remote' in e for e in check_pack(p))
