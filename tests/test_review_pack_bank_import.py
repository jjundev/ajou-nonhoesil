import hashlib,json,unicodedata
from unittest.mock import patch
import pytest
from scripts.lab.review_pack.bank_import import import_bank
from scripts.lab.review_pack.__main__ import main
from tests._bank_import_fixture import create_bank,add_asset,save_bank,mark_partial

def test_snapshot_assets_and_inputs_unchanged(tmp_path):
    path,bank=create_bank(tmp_path);asset=add_asset(path,bank,'img-answer','answer','present',b'answer evidence')
    save_bank(path,bank);raw=path.read_bytes();run=tmp_path/'tmp/authoring'
    assert import_bank(tmp_path,path,run)==run
    assert (run/'evidence/question-bank.json').read_bytes()==raw
    assert (run/'evidence/assets/img-answer.png').read_bytes()==b'answer evidence'
    assert path.read_bytes()==raw and (tmp_path/'quiz.txt').read_bytes()==b'original quiz evidence'
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    assert m['bank_import']['sha256']==hashlib.sha256(raw).hexdigest()
    assert m['checks']['browser']=='not_run'

def test_bad_asset_creates_no_run(tmp_path):
    path,bank=create_bank(tmp_path);a=add_asset(path,bank,'broken','mixed','unknown',b'original');save_bank(path,bank)
    (path.parent/a['path']).write_bytes(b'changed')
    with pytest.raises(ValueError):import_bank(tmp_path,path,tmp_path/'run')
    assert not (tmp_path/'run').exists()

def test_existing_run_preserved(tmp_path):
    path,_=create_bank(tmp_path);run=tmp_path/'run';run.mkdir();(run/'memo').write_text('keep')
    with pytest.raises(ValueError):import_bank(tmp_path,path,run)
    assert (run/'memo').read_text()=='keep'

def test_draft_refused(tmp_path):
    path,bank=create_bank(tmp_path);bank['audit']['status']='draft';save_bank(path,bank)
    with pytest.raises(ValueError):import_bank(tmp_path,path,tmp_path/'run')
    assert not (tmp_path/'run').exists()

def test_finished_holds_import(tmp_path):
    path,bank=create_bank(tmp_path);mark_partial(bank);save_bank(path,bank)
    import_bank(tmp_path,path,tmp_path/'run')
    m=json.loads((tmp_path/'run/manifest.json').read_text(encoding='utf-8'))
    assert m['problems'][0]['status']=='held' and 'blurred' in m['problems'][0]['reason']

def test_nfd_filename(tmp_path):
    path,_=create_bank(tmp_path,relative=unicodedata.normalize('NFD','문제은행/실험04/은행 (1).json'))
    run=tmp_path/'run';import_bank(tmp_path,path,run)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    assert m['bank_import']['source_path']==path.relative_to(tmp_path).as_posix()

@pytest.mark.parametrize('overlap',['bank','parent','child'])
def test_overlapping_run_refused(tmp_path,overlap):
    path,_=create_bank(tmp_path)
    run={'bank':path.parent,'parent':path.parent.parent,'child':path.parent/'new'}[overlap]
    with pytest.raises(ValueError):import_bank(tmp_path,path,run)

def test_outside_input_refused(tmp_path):
    path,_=create_bank(tmp_path);trusted=tmp_path/'project';trusted.mkdir()
    with pytest.raises(ValueError):import_bank(trusted,path,trusted/'run')

def test_symlink_refused(tmp_path):
    path,_=create_bank(tmp_path);link=tmp_path/'linked'
    try:link.symlink_to(path.parent,target_is_directory=True)
    except OSError:pytest.skip('symlink unavailable')
    with pytest.raises(ValueError):import_bank(tmp_path,link/path.name,tmp_path/'run')

def test_io_failure_not_success_or_overwrite(tmp_path):
    path,bank=create_bank(tmp_path);add_asset(path,bank,'asset','mixed','unknown',b'image');save_bank(path,bank)
    with patch('scripts.lab.review_pack.bank_import.shutil.copy2',side_effect=OSError('test IO failure')):
        with pytest.raises(OSError):import_bank(tmp_path,path,tmp_path/'run')
    assert not (tmp_path/'run').exists() and path.exists()

def test_cli_import(tmp_path,capsys):
    path,_=create_bank(tmp_path)
    assert main(['import-bank','--root',str(tmp_path),'--bank',str(path),'--run',str(tmp_path/'run')])==0
    assert (tmp_path/'run/authoring-index.json').is_file()

def test_unsupported_version(tmp_path):
    path,bank=create_bank(tmp_path);bank['schema_version']=2;save_bank(path,bank)
    with pytest.raises(ValueError):import_bank(tmp_path,path,tmp_path/'run')
    assert not (tmp_path/'run').exists()
