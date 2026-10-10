"""Regression gates for a narrowly scoped introduction refresh."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

SCRIPT = Path('docs/learning-pack-source/refresh_motivation.py')
PACKS = Path('복습노트')
TITLE = '왜 이 회로를 쓰는지 먼저 알아봐요'


def module():
    spec = importlib.util.spec_from_file_location('motivation_refresh', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


@pytest.fixture
def source(tmp_path):
    pack = tmp_path/'source'
    shutil.copytree(PACKS/'실험03', pack)
    fragment = tmp_path/'intro.html'
    fragment.write_text('<div class="layer eli5"><span class="layer-title">이해를 위한 예시</span>'
                        '<p>새로운 동기 설명이에요.</p></div>'
                        '<div class="sum" hidden><p>계산이 필요한 이유예요.</p></div>')
    return pack, fragment


@pytest.mark.parametrize('number', range(1, 6))
def test_stage_preserves_everything_except_intro(tmp_path, number):
    pack = PACKS/f'실험{number:02d}'
    fragment = tmp_path/'intro.html'
    fragment.write_text('<p>새로운 동기 설명이에요.</p><div class="sum" hidden><p>계산해요.</p></div>')
    before = snapshot(pack)
    stage = module().prepare_stage(pack, fragment, tmp_path/'stage')
    after = snapshot(stage)
    note = f'실험{number:02d}_실험설명.html'
    allowed = {note, note.replace('.html', '.md'), '자료/manifest.json'}
    owned = set(json.loads(before['자료/manifest.json'])['generated_files'])
    assert after.keys() == owned
    assert all(before[k] == after[k] for k in owned-allowed)
    old, new = before[note].decode(), after[note].decode()
    old_articles = re.findall(r'<article\b[^>]*id="(?!t-start")([^"]+)".*?</article>', old, re.S)
    assert old_articles == re.findall(r'<article\b[^>]*id="(?!t-start")([^"]+)".*?</article>', new, re.S)
    for article in re.findall(r'<article\b[^>]*id="(?!t-start")[^"]+".*?</article>', old, re.S):
        assert article in new
    assert re.findall(r'const KEY\s*=.*?;', old) == re.findall(r'const KEY\s*=.*?;', new)
    old_md = before[note.replace('.html', '.md')].decode()
    new_md = after[note.replace('.html', '.md')].decode()
    next_anchor = re.search(r'<a id="(?!learning|t-start)[^"]+"></a>', old_md).group()
    assert old_md[old_md.index(next_anchor):] == new_md[new_md.index(next_anchor):]


def test_source_pack_is_untouched(source, tmp_path):
    pack, fragment = source
    before = snapshot(pack)
    module().prepare_stage(pack, fragment, tmp_path/'stage')
    assert snapshot(pack) == before


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'existing', 'wrong_first'])
def test_unsupported_intro_aborts(source, tmp_path, case):
    pack, fragment = source
    note = pack/'실험03_실험설명.html'
    text = note.read_text()
    stage = tmp_path/'stage'
    if case == 'missing':
        note.write_text(text.replace('id="t-start"', 'id="gone"'))
    elif case == 'duplicate':
        note.write_text(text.replace('</main>', '<article id="t-start"><h3>둘</h3></article></main>'))
    elif case == 'existing':
        stage.mkdir(); (stage/'keep').write_text('user')
    else:
        path = pack/'자료/manifest.json'
        m = json.loads(path.read_text()); m['topics'][0]['id'] = 'other'; path.write_text(json.dumps(m))
    before = snapshot(pack)
    with pytest.raises(ValueError):
        module().prepare_stage(pack, fragment, stage)
    assert snapshot(pack) == before
    if case == 'existing':
        assert (stage/'keep').read_text() == 'user'
    else:
        assert not stage.exists()


def test_html_md_title_and_id_agree(source, tmp_path):
    pack, fragment = source
    stage = module().prepare_stage(pack, fragment, tmp_path/'stage')
    h = (stage/'실험03_실험설명.html').read_text()
    d = (stage/'실험03_실험설명.md').read_text()
    m = json.loads((stage/'자료/manifest.json').read_text())
    assert TITLE in h and TITLE in d and m['topics'][0]['title'] == TITLE
    assert '새로운 동기 설명이에요.' in h and '새로운 동기 설명이에요.' in d
    assert h.count('id="t-start"') == d.count('id="t-start"') == 1
    assert all(v == 'not_run' for v in m['checks'].values())
    assert set(m['generated_files']) == set(snapshot(stage))


def test_authoring_sources_keep_new_intro(tmp_path):
    src = Path('docs/learning-pack-source')
    copy = tmp_path/'실험04'
    shutil.copytree(src/'실험04', copy)
    subprocess.run([sys.executable, str(copy/'refresh_note.py')], check=True)
    assert (copy/'sections/t-start.html').read_bytes() == (src/'실험04/sections/t-start.html').read_bytes()
    assert json.loads((copy/'manifest.json').read_text())['topics'][0]['title'] == TITLE
    code = ('import sections; from pathlib import Path; '
            'assert sections.S["t-start"].strip() == Path("sections/t-start.html").read_text().strip(); '
            f'assert sections.TOPICS[0][1] == {TITLE!r}')
    subprocess.run([sys.executable, '-c', code], cwd=src/'실험05', check=True)


def test_stage_created_during_preflight_is_preserved(source, tmp_path, monkeypatch):
    pack, fragment = source
    mod = module()
    stage = tmp_path/'stage'
    original = mod._snapshot
    def snapshot_with_race(folder):
        data = original(folder)
        if not stage.exists():
            stage.mkdir(); (stage/'keep').write_text('concurrent user file')
        return data
    monkeypatch.setattr(mod, '_snapshot', snapshot_with_race)
    with pytest.raises((ValueError, FileExistsError)):
        mod.prepare_stage(pack, fragment, stage)
    assert (stage/'keep').read_text() == 'concurrent user file'


def test_refresh_does_not_claim_user_files(source, tmp_path):
    pack, fragment = source
    memo = pack/'사용자메모.md'
    memo.write_text('사용자가 별도로 저장한 파일')
    stage = module().prepare_stage(pack, fragment, tmp_path/'stage')
    owned = json.loads((stage/'자료/manifest.json').read_text())['generated_files']
    assert '사용자메모.md' not in owned
    assert not (stage/'사용자메모.md').exists()
    assert memo.read_text() == '사용자가 별도로 저장한 파일'
    for pdf in pack.glob('*.pdf'):
        assert pdf.name not in owned and not (stage/pdf.name).exists()
