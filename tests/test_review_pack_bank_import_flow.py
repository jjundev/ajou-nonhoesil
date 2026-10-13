import json,shutil
from pathlib import Path
import pytest
from scripts.lab.review_pack.__main__ import main
from scripts.lab.review_pack.bank_import import import_bank
from scripts.lab.review_pack.manifest import load_manifest
from tests._bank_import_fixture import create_bank,add_asset,save_bank

def author_fixture(root,run):
    assets=Path('.claude/skills/logic-lab-review-pack/assets')
    target=root/'.claude/skills/logic-lab-review-pack/assets'
    target.parent.mkdir(parents=True);shutil.copytree(assets,target)
    p=run/'manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    m['topics']=[dict(id='t-example',title='개념 예',requires=[],sources=[],fragment='sections/t-example.html')]
    (run/'sections/t-example.html').write_text('<p>검증 fixture 개념입니다.</p>',encoding='utf-8')
    m['problems'][0].update(status='included',topics=['t-example'],reason='fixture authored',
        derived_answer='fixture answer',answer_status='unresolved',fragment='problems/q1.html')
    (run/'problems/q1.html').write_text('<div class="problem"><p>입력이 0일 때 출력은?</p></div>'
        '<a href="{{NOTE_HREF}}#t-example">개념</a>'
        '<details class="hint"><summary>힌트</summary>fixture hint</details>'
        '<details class="solution"><summary>풀이</summary>fixture answer</details>',encoding='utf-8')
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    return m

def prepared(tmp_path,*,asset=False):
    path,bank=create_bank(tmp_path)
    if asset:
        add_asset(path,bank,'asset','mixed','unknown',b'asset evidence');save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run);author_fixture(tmp_path,run)
    return path,run

def test_build_check_preserve_evidence(tmp_path):
    path,run=prepared(tmp_path);stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==0
    assert (stage/'.pack/evidence/question-bank.json').read_bytes()==path.read_bytes()
    assert (stage/'.pack/authoring-index.json').is_file()
    assert main(['check','--folder',str(stage)])==0
    m=load_manifest(stage/'.pack/manifest.json')
    assert {'.pack/evidence/question-bank.json','.pack/authoring-index.json','.pack/원문과_저작안내.md'}<=set(m['generated_files'])
    text=(stage/'실험04_기출풀이.html').read_text(encoding='utf-8')
    assert 'fixture answer' not in text.split('<div class="problem">')[0].split('<article class="card"')[1]
    assert '.pack/원문과_저작안내.md#q1' in text

def test_bank_changed_blocks_build_before_stage(tmp_path):
    path,run=prepared(tmp_path);path.write_bytes(path.read_bytes()+b'\n');stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==1
    assert not stage.exists()

@pytest.mark.parametrize('changed',['bank','source','asset'])
def test_change_blocks_publish_preserving_destination(tmp_path,changed,capsys):
    path,run=prepared(tmp_path,asset=True);stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==0
    m=load_manifest(stage/'.pack/manifest.json');m['checks'].update(source_visual='pass',content='self_review',browser='pass')
    (stage/'.pack/manifest.json').write_text(json.dumps(m),encoding='utf-8')
    dest=tmp_path/'복습노트/실험04';dest.mkdir(parents=True);(dest/'memo').write_text('keep')
    target={'bank':path,'source':tmp_path/'quiz.txt','asset':path.parent/'assets/asset.png'}[changed]
    target.write_bytes(target.read_bytes()+b'changed')
    capsys.readouterr()
    assert main(['publish','--root',str(tmp_path),'--stage',str(stage),'--experiment','4'])==1
    assert 'changed' in capsys.readouterr().out.lower()
    assert (dest/'memo').read_text()=='keep'

def test_not_reviewed_pack_not_published(tmp_path):
    path,run=prepared(tmp_path);stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==0
    assert main(['publish','--root',str(tmp_path),'--stage',str(stage),'--experiment','4'])==1
    assert not (tmp_path/'복습노트/실험04').exists()

def test_fixture_publish_retains_evidence_and_memo(tmp_path):
    path,run=prepared(tmp_path);stage=tmp_path/'stage'
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(stage)])==0
    m=load_manifest(stage/'.pack/manifest.json');m['checks'].update(source_visual='pass',content='self_review',browser='pass')
    (stage/'.pack/manifest.json').write_text(json.dumps(m),encoding='utf-8')
    dest=tmp_path/'복습노트/실험04';dest.mkdir(parents=True);(dest/'memo').write_text('keep')
    assert main(['publish','--root',str(tmp_path),'--stage',str(stage),'--experiment','4'])==0
    assert (dest/'memo').read_text()=='keep'
    assert (dest/'.pack/evidence/question-bank.json').read_bytes()==path.read_bytes()
    assert main(['check','--folder',str(dest)])==1                     # 루트에는 .html·.pdf 만 — 메모는 .pack/ 로
    (dest/'memo').rename(dest/'.pack/memo')
    assert main(['check','--folder',str(dest)])==0
    assert list(dest.parent.glob('실험04.backup-*'))

def test_duplicate_manifest_keys_rejected(tmp_path):
    path,run=prepared(tmp_path)
    p=run/'manifest.json';text=p.read_text(encoding='utf-8')
    p.write_text(text.replace('"bank_id":','"bank_id":"wrong","bank_id":',1),encoding='utf-8')
    with pytest.raises(ValueError,match='Duplicate JSON key'):
        load_manifest(p)

@pytest.mark.parametrize('body',[
    '<div class="problem"><img src="figures/safe.png" srcset="figures/renamed.png 1x"></div>',
    '<div class="problem"><p>문제</p></div><style>.problem{background-image:url(figures/renamed.png)}</style>',
    '<div class="problem"><p>문제</p></div><details class="original"><summary><img src="figures/renamed.png"></summary></details>',
    '<div class="problem"><p>문제</p></div><details class="original" open><summary>원문</summary><img src="figures/renamed.png"></details>',
])
def test_review_findings_fail_end_to_end_build(tmp_path,body):
    path,bank=create_bank(tmp_path)
    add_asset(path,bank,'exposed','mixed','present',b'answer image');save_bank(path,bank)
    run=tmp_path/'run';import_bank(tmp_path,path,run);author_fixture(tmp_path,run)
    (run/'figures/renamed.png').write_bytes(b'answer image')
    (run/'figures/safe.png').write_bytes(b'new teaching image')
    (run/'problems/q1.html').write_text(body+
        '<a href="{{NOTE_HREF}}#t-example">개념</a>'
        '<details class="hint"><summary>힌트</summary>hint</details>'
        '<details class="solution"><summary>풀이</summary>answer</details>',encoding='utf-8')
    assert main(['build','--root',str(tmp_path),'--run',str(run),'--stage',str(tmp_path/'stage')])==1
