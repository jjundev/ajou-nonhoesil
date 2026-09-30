import json
import pytest
from scripts.lab.review_pack.bank_import import import_bank
from scripts.lab.review_pack.bank_asset_checks import check_bank_problem_assets
from tests._bank_import_fixture import create_bank,add_asset,save_bank

def asset_pack(tmp_path,exposure='present'):
    path,bank=create_bank(tmp_path)
    role='problem' if exposure=='none' else 'mixed'
    add_asset(path,bank,'scan',role,exposure,b'original image '+exposure.encode())
    bank['occurrences'][0]['blocks'].append(dict(id='b-scan',type='figure',text='scan',tex=None,cells=None,asset_id='scan'))
    save_bank(path,bank);run=tmp_path/'run';import_bank(tmp_path,path,run)
    (run/'figures/renamed.png').write_bytes((run/'evidence/assets/scan.png').read_bytes())
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'));m['problems'][0]['status']='included'
    write_card(run,'<div class="problem"><img src="figures/renamed.png"></div>')
    return run,m

def write_card(run,body):
    (run/'실험04_기출풀이.html').write_text('<main><article class="card" id="q1">'+body+'</article></main>',encoding='utf-8')

@pytest.mark.parametrize('exposure',['present','unknown'])
def test_renaming_does_not_hide_exposure(tmp_path,exposure):
    run,m=asset_pack(tmp_path,exposure)
    assert check_bank_problem_assets(run,m)

def test_safe_image_allowed(tmp_path):
    run,m=asset_pack(tmp_path,'none')
    assert check_bank_problem_assets(run,m)==[]

def test_allowed_in_solution(tmp_path):
    run,m=asset_pack(tmp_path)
    write_card(run,'<div class="problem"><p>문제</p></div><details class="solution"><summary>풀이</summary><img src="figures/renamed.png"></details>')
    assert check_bank_problem_assets(run,m)==[]

def test_allowed_in_original(tmp_path):
    run,m=asset_pack(tmp_path)
    write_card(run,'<div class="problem"><p>문제</p></div><details class="original"><summary>원문</summary><img src="figures/renamed.png"></details>')
    assert check_bank_problem_assets(run,m)==[]

@pytest.mark.parametrize('body',[
    '<div class="problem"><p>문제</p></div><img src="figures/renamed.png">',
    '<div class="problem"><svg><image href="figures/renamed.png"/></svg></div>',
    '<div class="problem" style="background:url(figures/renamed.png)"><p>문제</p></div>',
    '<div class="problem"><object data="figures/renamed.png"></object></div>',
    '<div class="problem"><embed src="figures/renamed.png"></div>',
    '<img src="figures/renamed.png">',
    '<div class="problem">one</div><div class="problem">two</div>',
    '<div class="problem"><details class="original"><img src="figures/renamed.png"></details></div>',
    '<div class="problem"><p>문제</p></div><details class="hint"><img src="figures/renamed.png"></details>',
])
def test_alternative_placements_do_not_bypass(tmp_path,body):
    run,m=asset_pack(tmp_path)
    write_card(run,body)
    assert check_bank_problem_assets(run,m)

def test_encoded_filename(tmp_path):
    run,m=asset_pack(tmp_path);(run/'figures/한 글 (1).png').write_bytes((run/'figures/renamed.png').read_bytes())
    write_card(run,'<div class="problem"><img src="figures/%ED%95%9C%20%EA%B8%80%20%281%29.png"></div>')
    assert check_bank_problem_assets(run,m)

def test_same_hash_safe_and_exposed_is_conservative(tmp_path):
    path,bank=create_bank(tmp_path)
    for ident,role,exposure in [('safe','problem','none'),('unsafe','mixed','present')]:
        add_asset(path,bank,ident,role,exposure,b'same image')
        bank['occurrences'][0]['blocks'].append(dict(id='b-'+ident,type='figure',text=ident,tex=None,cells=None,asset_id=ident))
    save_bank(path,bank);run=tmp_path/'run';import_bank(tmp_path,path,run)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'));m['problems'][0]['status']='included'
    write_card(run,'<div class="problem"><img src="evidence/assets/safe.png"></div>')
    assert check_bank_problem_assets(run,m)

@pytest.mark.parametrize('url',['https://example.com/a.png','data:image/png;base64,AA==','../outside.png'])
def test_nonlocal_question_assets_refused(tmp_path,url):
    run,m=asset_pack(tmp_path)
    write_card(run,f'<div class="problem"><img src="{url}"></div>')
    assert check_bank_problem_assets(run,m)

def test_new_teaching_image_allowed(tmp_path):
    run,m=asset_pack(tmp_path);(run/'figures/new.svg').write_text('<svg/>')
    write_card(run,'<div class="problem"><img src="figures/new.svg"></div>')
    assert check_bank_problem_assets(run,m)==[]

@pytest.mark.parametrize('body',[
    '<div class="problem"><img src="figures/safe.png" srcset="figures/renamed.png 1x"></div>',
    '<div class="problem"><picture><source srcset="figures/renamed.png 2x"><img src="figures/safe.png"></picture></div>',
    '<div class="problem"><p>문제</p></div><style>.problem{background-image:url(figures/renamed.png)}</style>',
    '<div class="problem"><p>문제</p></div><details class="original"><summary><img src="figures/renamed.png"></summary></details>',
    '<div class="problem"><p>문제</p></div><details class="original" open><summary>원문</summary><img src="figures/renamed.png"></details>',
    '<div class="problem"><p>문제</p></div><details class="solution" open><summary>풀이</summary><img src="figures/renamed.png"></details>',
])
def test_review_exposure_reproductions(tmp_path,body):
    run,m=asset_pack(tmp_path)
    (run/'figures/safe.png').write_bytes(b'new teaching image')
    write_card(run,body)
    assert check_bank_problem_assets(run,m)

def test_style_outside_card_is_not_a_bypass(tmp_path):
    run,m=asset_pack(tmp_path)
    write_card(run,'<div class="problem"><p>문제</p></div>')
    p=run/'실험04_기출풀이.html'
    p.write_text(p.read_text(encoding='utf-8')+'<style>.problem{background:url(figures/renamed.png)}</style>',encoding='utf-8')
    assert check_bank_problem_assets(run,m)
