from pathlib import Path
import copy
import json
import re
import shutil

import pytest

from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.table_layout_upgrade import upgrade_layout_html, upgrade_packs

PACKS = Path('복습노트')
ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
CARD = '<div class="table-wrap"><div class="table-card" role="group" aria-label="표"><table><thead><tr><th>S</th><th>Y</th></tr></thead><tbody><tr><td>0</td><td>I0</td></tr></tbody></table></div></div>'
LAYOUT = {'version': 1, 'tables': [{'key': 't-mux/0', 'expected_headers': ['S', 'Y'],
          'columns': [{'role': 'input', 'kind': 'signal', 'group': '입력'}, {'role': 'output', 'kind': 'signal', 'group': '출력'}],
          'boundaries': [{'left': 0, 'kind': 'major'}]}]}


def old_html(newline='\n'):
    return newline.join([
        '<html><style>',
        '    td:first-child, th:first-child { min-width: 6em; }',
        '',
        '    /* 위젯 */',
        '</style><body><main><section id="learning">',
        f'<article class="topic" id="t-mux"><h3>MUX</h3>{CARD}</article>',
        '<article class="topic" id="t-other"><h3>기타</h3><p>표 없음</p></article>',
        '</section></main></body></html>'])


def note_path(folder):
    return folder / f'{folder.name}_실험설명.html'


def snapshot(folder):
    return {p.relative_to(folder): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


def pack_with_layout(tmp_path, name='실험04'):
    target = tmp_path / name
    shutil.copytree(PACKS / name, target)
    text = note_path(target).read_text(encoding='utf-8')
    body = text[text.index('<section id="learning">'):text.index('</main>')]
    from scripts.lab.review_pack.html2md import Parser
    from scripts.lab.review_pack.table_layout import grid
    import re
    tables = []
    for match in re.finditer(r'<article class="topic" id="([^"]+)">(.*?)</article>', body, re.S):
        for ordinal, source in enumerate(re.findall(r'<table\b.*?</table>', match.group(2), re.S)):
            parser = Parser(); parser.feed(source)
            _, headers = grid(next(n for n in parser.root.walk() if n.tag == 'table'), 'x')
            tables.append({'key': f'{match.group(1)}/{ordinal}', 'expected_headers': headers,
                           'columns': [{'role': 'description', 'kind': 'text', 'group': '내용'} for _ in headers]})
    # 발행본 상태와 무관하게 템플릿 사본 동기화·문제설명 재렌더 경로를 타도록 사본을 낡게 만든다.
    stale = target / '.pack/assets/note-template.html'
    stale.write_bytes(stale.read_bytes() + b'<!-- stale -->')
    (target / '.pack/sections').mkdir(exist_ok=True)
    (target / '.pack/sections/table-layout.json').write_text(json.dumps({'version': 1, 'tables': tables}, ensure_ascii=False), encoding='utf-8')
    return target


def test_lays_out_tables_and_inserts_css():
    out = upgrade_layout_html(old_html(), LAYOUT)
    assert '<div class="table-card" role="group" aria-label="표"><table data-layout-table="t-mux/0"' in out
    assert out.count('/* explanation-table-layout:start */') == 1
    assert out.index('min-width: 6em') < out.index('/* explanation-table-layout:start */') < out.index('/* 위젯 */')


def test_crlf_page_keeps_crlf():
    out = upgrade_layout_html(old_html('\r\n'), LAYOUT)
    assert '\n' not in out.replace('\r\n', '')


def test_upgrade_is_idempotent():
    once = upgrade_layout_html(old_html(), LAYOUT)
    assert upgrade_layout_html(once, LAYOUT) == once


def test_existing_css_block_is_replaced_not_duplicated():
    stale = old_html().replace('    /* 위젯 */', '    /* explanation-table-layout:start */\n    .stale {}\n    /* explanation-table-layout:end */\n\n    /* 위젯 */')
    out = upgrade_layout_html(stale, LAYOUT)
    assert '.stale' not in out and out.count('/* explanation-table-layout:start */') == 1


@pytest.mark.parametrize('change', ['missing', 'unknown', 'header'])
def test_layout_drift_raises(change):
    layout = copy.deepcopy(LAYOUT)
    if change == 'missing':
        layout['tables'] = []
    if change == 'unknown':
        layout['tables'].append(dict(layout['tables'][0], key='t-gone/0'))
    if change == 'header':
        layout['tables'][0]['expected_headers'][0] = 'X'
    with pytest.raises(ValueError):
        upgrade_layout_html(old_html(), layout)


def test_missing_layout_file_aborts_batch_before_writes(tmp_path):
    good = pack_with_layout(tmp_path, '실험04')
    bad = tmp_path / '실험05'
    shutil.copytree(PACKS / '실험05', bad)
    (bad / '.pack/sections/table-layout.json').unlink(missing_ok=True)
    before = snapshot(good)
    with pytest.raises(ValueError, match='실험05'):
        upgrade_packs([good, bad], apply=True, backup_root=tmp_path / 'backup')
    assert snapshot(good) == before and not (tmp_path / 'backup').exists()


def test_apply_changes_only_note_and_template_copy(tmp_path):
    folder = pack_with_layout(tmp_path)
    before = snapshot(folder)
    upgrade_packs([folder], apply=True, backup_root=tmp_path / 'backup')
    after = snapshot(folder)
    changed = {k for k in before if before[k] != after[k]}
    explanation = Path(f'{folder.name}_문제설명.html')
    assert changed <= {note_path(folder).relative_to(folder), Path('.pack/assets/note-template.html'), explanation}
    assert note_path(folder).relative_to(folder) in changed
    # 문제설명은 템플릿 사본이 바뀐 만큼, 즉 열 배치 CSS 블록만 달라진다.
    if explanation in changed:
        strip = lambda b: re.sub(r'/\* explanation-table-layout:start \*/.*?/\* explanation-table-layout:end \*/', '', b.decode('utf-8'), flags=re.S)
        assert strip(before[explanation]) == strip(after[explanation])
    assert (folder / '.pack/assets/note-template.html').read_bytes() == (ASSETS / 'note-template.html').read_bytes()
    assert check_pack(folder) == []
    assert upgrade_packs([folder]) == []


def test_failed_check_rolls_back(tmp_path, monkeypatch):
    folder = pack_with_layout(tmp_path)
    before = snapshot(folder)
    import scripts.lab.review_pack.table_layout_upgrade as module
    monkeypatch.setattr(module, 'check_pack', lambda f: ['broken'])
    with pytest.raises(ValueError, match='broken'):
        upgrade_packs([folder], apply=True, backup_root=tmp_path / 'backup')
    assert snapshot(folder) == before
