import json
from scripts.lab.review_pack.question_bank_cli import main

def test_check_reports_draft_not_verified(tmp_path,capsys):
    source='tests/fixtures/review_pack/question_bank/minimal.json'
    assert main(['check','--root',str(tmp_path),'--bank',source])==0
    output=json.loads(capsys.readouterr().out)
    assert output['mechanical_check']=='pass'
    assert output['audit_status']=='draft'
    assert output['recorded_source_visual']=='not_run'

def test_invalid_json_has_nonzero_status(tmp_path,capsys):
    path=tmp_path/'bad.json'; path.write_text('{',encoding='utf-8')
    assert main(['check','--root',str(tmp_path),'--bank',str(path)])==1
    assert 'FAIL' in capsys.readouterr().err

def test_inventory_missing_is_failure(tmp_path,capsys):
    assert main(['inventory','--root',str(tmp_path),'--experiment','4'])==1
    assert 'FAIL' in capsys.readouterr().err
