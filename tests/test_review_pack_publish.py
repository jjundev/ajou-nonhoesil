from pathlib import Path
import json
import os
from unittest.mock import patch
import pytest
from scripts.lab.review_pack.publish import publish
from scripts.lab.review_pack.sources import file_sha256
from tests.test_review_pack_checks import make_pack

def ready(tmp_path):
    stage=make_pack(tmp_path);source=tmp_path/'강의노트/실험4.pdf'
    source.parent.mkdir();source.write_bytes(b'source')
    m=json.loads((stage/'.pack/manifest.json').read_text(encoding='utf-8'))
    m['sources'][0]['sha256']=file_sha256(source)
    m['checks'].update(content='self_review',browser='pass',source_visual='pass')
    m['generated_files']=[p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()]
    (stage/'.pack/manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
    dest=tmp_path/'복습노트/실험04';dest.mkdir(parents=True)
    (dest/'사용자메모.md').write_text('보존',encoding='utf-8')
    return stage,dest,source

def test_failed_pack_cannot_replace(tmp_path):
    dest=tmp_path/'복습노트/실험04';dest.mkdir(parents=True)
    (dest/'memo').write_text('keep')
    stage=tmp_path/'stage';stage.mkdir()
    with pytest.raises(ValueError):publish(stage,dest,tmp_path)
    assert (dest/'memo').read_text()=='keep'

def test_source_changed_refused(tmp_path):
    stage,dest,source=ready(tmp_path);source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='원문 변경'):publish(stage,dest,tmp_path)
    assert (dest/'사용자메모.md').exists()

def test_preserve_user_file_and_backup(tmp_path):
    stage,dest,_=ready(tmp_path)
    backup=publish(stage,dest,tmp_path)
    assert (backup/'사용자메모.md').exists()
    assert (dest/'사용자메모.md').read_text(encoding='utf-8')=='보존'
    assert (dest/'실험04_기출풀이.html').exists()
    assert not (dest/'.pack/assets/vendor').exists()
    assert (dest.parent/'.vendor/katex/katex.min.js').is_file()

def test_rename_failure_rolls_back(tmp_path):
    stage,dest,_=ready(tmp_path)
    original=os.replace;calls=[]
    def fail_second(a,b):
        calls.append((a,b))
        if len(calls)==2:raise OSError('test failure')
        return original(a,b)
    with patch('scripts.lab.review_pack.publish.os.replace',side_effect=fail_second):
        with pytest.raises(OSError):publish(stage,dest,tmp_path)
    assert (dest/'사용자메모.md').read_text(encoding='utf-8')=='보존'

def test_browser_unchecked_refused(tmp_path):
    stage,dest,_=ready(tmp_path);p=stage/'.pack/manifest.json'
    m=json.loads(p.read_text(encoding='utf-8'));m['checks']['browser']='not_run'
    p.write_text(json.dumps(m),encoding='utf-8')
    with pytest.raises(ValueError):publish(stage,dest,tmp_path)

def test_user_collision_not_overwritten(tmp_path):
    stage,dest,_=ready(tmp_path)
    (dest/'실험04_기출풀이.html').write_text('user authored')
    with pytest.raises(ValueError):publish(stage,dest,tmp_path)
    assert (dest/'실험04_기출풀이.html').read_text()=='user authored'


def ready_v2(tmp_path):
    from tests._explanation_recall_fixture import setup_v2
    from scripts.lab.review_pack.render import assemble
    from scripts.lab.review_pack.html2md import convert_pack
    m, run, data = setup_v2(tmp_path)
    for s in m['sources']:
        path = tmp_path/s['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture source')
        s['sha256'] = file_sha256(path)
    m['checks'].update(source_visual='pass',content='self_review',browser='pass')
    m['explanation_checks'].update(source_visual='pass',content='self_review',browser='pass')
    stage = tmp_path/'stage'
    paths = assemble(m,run,stage,Path('.claude/skills/logic-lab-review-pack/assets'))
    convert_pack(paths['note_html'],paths['review_html'],manifest=m)
    m['generated_files'] = sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
    (stage/'.pack/manifest.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
    dest = tmp_path/'복습노트/실험04'; dest.mkdir(parents=True)
    (dest/'사용자메모.md').write_text('보존',encoding='utf-8')
    return stage,dest

@pytest.mark.parametrize('suffix', ['html', 'HTML'])
def test_v2_user_explanation_collision_refused(tmp_path, suffix):
    stage,dest = ready_v2(tmp_path)
    path = dest/f'실험04_문제설명.{suffix}'
    path.write_bytes(b'user original')
    with pytest.raises(ValueError,match='User file collision'):
        publish(stage,dest,tmp_path)
    assert path.read_bytes() == b'user original'
    assert (dest/'사용자메모.md').read_text(encoding='utf-8') == '보존'

def test_v2_rename_failure_restores_original(tmp_path):
    stage,dest = ready_v2(tmp_path)
    original = os.replace; calls = []
    def fail_second(a,b):
        calls.append((a,b))
        if len(calls) == 2: raise OSError('test failure')
        return original(a,b)
    with patch('scripts.lab.review_pack.publish.os.replace',side_effect=fail_second):
        with pytest.raises(OSError): publish(stage,dest,tmp_path)
    assert (dest/'사용자메모.md').read_text(encoding='utf-8') == '보존'
    assert not (dest/'실험04_문제설명.html').exists()

def test_v2_user_file_survives_success(tmp_path):
    stage,dest = ready_v2(tmp_path)
    backup = publish(stage,dest,tmp_path)
    assert (backup/'사용자메모.md').read_text(encoding='utf-8') == '보존'
    assert (dest/'사용자메모.md').read_text(encoding='utf-8') == '보존'
    assert (dest/'실험04_문제설명.html').is_file()
