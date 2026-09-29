from datetime import date
import unicodedata
import pytest
from scripts.lab.review_pack.sources import inventory, resolve_experiments

def test_same_day_returns_both():
    assert resolve_experiments(today=date(2026, 9, 18)) == [2, 3]

def test_archive_without_report_folder(tmp_path):
    p = tmp_path / 'from_the_past/정리/강의노트/실험4.pdf'
    p.parent.mkdir(parents=True)
    p.write_bytes(b'fixture')
    assert inventory(tmp_path, 4)['manual']['edition'] == 'archive'
    assert not (tmp_path / '보고서').exists()

def test_current_preferred(tmp_path):
    for name in ('강의노트/실험4. MUX.pdf','from_the_past/정리/강의노트/실험4.pdf'):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'fixture')
    assert inventory(tmp_path, 4)['manual']['edition'] == 'current'

def test_unicode_quiz_path(tmp_path):
    folder = tmp_path / 'from_the_past/정리/퀴즈/실험4'
    folder.mkdir(parents=True)
    p = folder / unicodedata.normalize('NFD','기출 (1).pdf')
    p.write_bytes(b'fixture')
    rows = inventory(tmp_path, 4)['sources']
    assert len(rows) == 1
    assert (tmp_path / rows[0]['path']).is_file()

@pytest.mark.parametrize('number',[True,11,0,'4'])
def test_bad_number(number):
    with pytest.raises((TypeError,ValueError)):
        resolve_experiments(numbers=[number])

def test_end_of_term():
    assert resolve_experiments(today=date(2027,1,1)) == []

def test_content_hash_changes_but_id_stable(tmp_path):
    p = tmp_path / '강의노트/실험4.pdf'
    p.parent.mkdir()
    p.write_bytes(b'a')
    first = inventory(tmp_path,4)['manual']
    p.write_bytes(b'b')
    second = inventory(tmp_path,4)['manual']
    assert first['id'] == second['id']
    assert first['sha256'] != second['sha256']
