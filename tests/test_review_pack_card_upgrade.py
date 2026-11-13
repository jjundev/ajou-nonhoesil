from pathlib import Path
import re
import shutil

import pytest

from scripts.lab.review_pack.card_upgrade import CSS_END, CSS_START, GUARD_NEW, GUARD_OLD, upgrade_card_html, upgrade_packs
from scripts.lab.review_pack.checks import check_pack

PACKS = Path('복습노트')
NEW_GUARD = ".closest('.widget, .equation-card, .table-card, .katex-display, .table-wrap, svg, input, details')"


def old_html():
    return '''<html><style>
    .katex-display { overflow-x: auto; overflow-y: hidden; padding: var(--s1) 0; }
    .table-wrap { overflow-x: auto; }
    </style><body><main><section id="learning"><article class="topic" id="t-a"><h3>A</h3>
    <div class="table-wrap"><table><tr><th>A</th></tr><tr><td>0</td></tr></table></div>
    <p>$$A=B$$</p><p>문장 속 $A$ 식</p></article></section></main>
    <script>if (e.target.closest('.widget, .katex-display, .table-wrap, svg, input, details')) return;</script></body></html>'''


def downgrade(text):
    # 발행본은 이미 업그레이드됐으므로 카드·CSS·선택자를 벗겨 업그레이드 전 형태로 되돌린다.
    text = re.sub(r'<div class="table-card" role="group" aria-label="표">(<table\b.*?</table>)</div>', r'\1', text, flags=re.S)
    text = re.sub(r'<div class="equation-card" role="group" aria-label="수식">(<p\b.*?</p>)</div>', r'\1', text, flags=re.S)
    start, end = text.index(CSS_START), text.index(CSS_END)
    start, end = text.rindex('\n', 0, start) + 1, text.index('\n', end) + 1
    return (text[:start] + text[end:]).replace(GUARD_NEW, GUARD_OLD)


def pack_copy(tmp_path, name='실험05'):
    vendor = tmp_path / '.vendor'
    if not vendor.exists():
        vendor.symlink_to((PACKS / '.vendor').resolve(), target_is_directory=True)
    target = tmp_path / name
    shutil.copytree(PACKS / name, target)
    note = note_path(target)
    note.write_bytes(downgrade(note.read_bytes().decode('utf-8')).encode('utf-8'))
    return target


def snapshot(folder):
    return {p.relative_to(folder): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


def note_path(folder):
    return folder / f'{folder.name}_실험설명.html'


def test_wraps_body_and_adds_css():
    out = upgrade_card_html(old_html())
    assert out.count('aria-label="표"') == 1 and out.count('aria-label="수식"') == 1
    assert out.count('    .table-card { margin') == 1
    assert NEW_GUARD in out
    assert '<p>문장 속 $A$ 식</p>' in out


def test_crlf_page_gets_crlf_css():
    out = upgrade_card_html(old_html().replace('\n', '\r\n'))
    assert out.count('    .table-card { margin') == 1
    assert '\n' not in out.replace('\r\n', '')


def test_upgrade_is_idempotent():
    once = upgrade_card_html(old_html())
    assert upgrade_card_html(once) == once


def test_css_already_present_wraps_body_only():
    once = upgrade_card_html(old_html())
    unwrapped = once.replace('<div class="table-card" role="group" aria-label="표">', '', 1)
    unwrapped = unwrapped.replace('</table></div></div>', '</table></div>', 1)
    again = upgrade_card_html(unwrapped)
    assert again.count('    .table-card { margin') == 1 and again.count('aria-label="표"') == 1


def test_missing_anchor_raises():
    with pytest.raises(ValueError):
        upgrade_card_html(old_html().replace('padding: var(--s1) 0; }', '}'))


def test_dry_run_writes_nothing(tmp_path):
    folder = pack_copy(tmp_path)
    before = snapshot(folder)
    assert upgrade_packs([folder]) == [note_path(folder).resolve()]
    assert snapshot(folder) == before


def test_unknown_page_aborts_batch_before_writes(tmp_path):
    good, bad = pack_copy(tmp_path, '실험05'), pack_copy(tmp_path, '실험04')
    note_path(bad).write_text('<html>unknown</html>', encoding='utf-8')
    before = snapshot(good)
    with pytest.raises(ValueError):
        upgrade_packs([good, bad], apply=True, backup_root=tmp_path / 'backup')
    assert snapshot(good) == before
    assert not (tmp_path / 'backup').exists()


def test_apply_keeps_md_and_other_pages(tmp_path):
    folder = pack_copy(tmp_path)
    before = snapshot(folder)
    backup = tmp_path / 'backup'
    upgrade_packs([folder], apply=True, backup_root=backup)
    after = snapshot(folder)
    note = note_path(folder).relative_to(folder)
    assert {k for k in before if before[k] != after[k]} == {note}
    assert (backup / folder.name / note).read_bytes() == before[note]
    assert check_pack(folder) == []
    assert upgrade_packs([folder]) == []


def test_backup_inside_pack_rejected(tmp_path):
    folder = pack_copy(tmp_path)
    before = snapshot(folder)
    with pytest.raises(ValueError):
        upgrade_packs([folder], apply=True, backup_root=folder / 'bk')
    assert snapshot(folder) == before
