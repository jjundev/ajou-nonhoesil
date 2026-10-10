"""저장 규칙: 복습노트 실험 폴더에는 문서(.md·.html·.pdf)와 자료/ 만 둔다."""
import hashlib
from pathlib import Path
import pytest
from scripts.lab import migrate_pack_layout as mig
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import DATA, data_url, link_data, strip_data

NOTES = Path('복습노트')
PACKS = sorted(p for p in NOTES.glob('실험[0-9][0-9]') if p.is_dir())

def test_link_helpers():
    assert DATA == '자료'
    assert data_url('figures/a.svg') == '자료/figures/a.svg'
    assert strip_data('자료/figures/a.svg') == 'figures/a.svg'
    assert strip_data('figures/a.svg') == 'figures/a.svg'
    text = '<img src="figures/a.svg"><img src=\'assets/b.png\'><a href="실험05_실험설명.html#x">'
    assert link_data(text) == '<img src="자료/figures/a.svg"><img src=\'자료/assets/b.png\'><a href="실험05_실험설명.html#x">'
    assert link_data(link_data(text)) == link_data(text)      # 두 번 달아도 접두가 겹치지 않는다

@pytest.mark.parametrize('pack', PACKS, ids=lambda p: p.name)
def test_pack_root_holds_only_documents_and_data_folder(pack):
    for entry in pack.iterdir():
        if entry.name == '.DS_Store':
            continue
        if entry.is_dir():
            assert entry.name == DATA, f'{entry.name}/ 는 자료/ 안에 둔다'
        else:
            assert entry.suffix in {'.md', '.html', '.pdf'}, f'{entry.name} 는 자료/ 안에 둔다'
    assert (pack / DATA / 'manifest.json').is_file()
    for name in ('assets', 'evidence', 'figures'):
        assert (pack / DATA / name).is_dir()

@pytest.mark.parametrize('pack', PACKS, ids=lambda p: p.name)
def test_published_pack_passes_checks(pack):
    assert check_pack(pack) == []

def test_migration_is_noop_on_migrated_packs():
    def tree(folder):
        return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in folder.rglob('*') if p.is_file()}
    for pack in PACKS:
        before = tree(pack)
        lines = mig.migrate(pack, apply=True)
        assert '이미' in lines[0]
        assert tree(pack) == before
