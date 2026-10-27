"""Published note summaries move to rules / why / traps in place."""
import json
import shutil
import pytest
from scripts.lab.review_pack import summary_upgrade
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.navigation_upgrade import ROOT
from scripts.lab.review_pack.note_summary import SUMMARY_FILE, summary_text
from scripts.lab.review_pack.summary_upgrade import TOPIC, upgrade_packs

def snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob('*')) if p.is_file()}

def write_json(pack, topics):
    (pack / '.pack' / SUMMARY_FILE).write_text(json.dumps({'schema_version': 1, 'topics': topics}, ensure_ascii=False), encoding='utf-8')

def passing_topics(pack):
    html = (pack / '실험01_실험설명.html').read_text(encoding='utf-8')
    return {m.group(2): {'rules': [['요약', summary_text(m.group(3))]]} for m in TOPIC.finditer(html)}

@pytest.fixture
def pack(tmp_path):
    folder = tmp_path / '실험01'
    shutil.copytree(ROOT / '복습노트/실험01', folder)
    write_json(folder, passing_topics(folder))
    return folder

def test_dry_run_lists_three_files_and_writes_nothing(pack):
    before = snapshot(pack)
    changed = upgrade_packs([pack])
    assert {p.name for p in changed} == {'실험01_실험설명.html', '실험01_실험설명.md', 'manifest.json'}
    assert snapshot(pack) == before

def test_apply_upgrades_and_passes_check(pack, tmp_path):
    upgrade_packs([pack], apply=True, backup_root=tmp_path / 'bak')
    m = json.loads((pack / '.pack/manifest.json').read_text(encoding='utf-8'))
    assert m['note_summary_version'] == 2
    assert list(m).index('note_summary_version') == list(m).index('note_presentation_version') + 1
    assert '.pack/sections/note-summaries.json' in m['generated_files']
    assert check_pack(pack) == []
    assert (tmp_path / 'bak/실험01').is_dir()
    assert (pack / '실험01_실험설명.html').read_text(encoding='utf-8').count('<p class="sum-label">외울 규칙</p>') == len(m['topics'])

def test_rerun_is_noop(pack, tmp_path):
    upgrade_packs([pack], apply=True, backup_root=tmp_path / 'bak')
    assert upgrade_packs([pack]) == []

def test_lost_fact_is_refused(pack):
    topics = passing_topics(pack)
    rule = topics['t-start']['rules'][0]
    assert '74HC86' in rule[1]
    rule[1] = rule[1].replace('74HC86', '')
    write_json(pack, topics)
    with pytest.raises(ValueError, match='t-start: lost tokens 74HC86'):
        upgrade_packs([pack])

def test_topic_mismatch_is_refused(pack):
    topics = passing_topics(pack)
    del topics['t-lab']
    write_json(pack, topics)
    with pytest.raises(ValueError, match='t-lab: missing summary'):
        upgrade_packs([pack])

def test_drifted_md_is_refused(pack):
    md = pack / '.pack/실험01_실험설명.md'
    md.write_text(md.read_text(encoding='utf-8') + '\n손으로 고친 줄\n', encoding='utf-8')
    with pytest.raises(ValueError, match='note MD differs'):
        upgrade_packs([pack])

def test_check_failure_rolls_back(pack, tmp_path, monkeypatch):
    before = snapshot(pack)
    monkeypatch.setattr(summary_upgrade, 'check_pack', lambda f: ['boom'])
    with pytest.raises(ValueError, match='boom'):
        upgrade_packs([pack], apply=True, backup_root=tmp_path / 'bak')
    assert snapshot(pack) == before

def test_apply_requires_new_backup_dir_outside_pack(pack):
    with pytest.raises(ValueError, match='backup'):
        upgrade_packs([pack], apply=True)
    with pytest.raises(ValueError, match='Backup directory'):
        upgrade_packs([pack], apply=True, backup_root=pack / 'bak')
