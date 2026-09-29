# tests/test_review_pack_question_bank_sources.py
from pathlib import Path
import pytest
from scripts.lab.review_pack.question_bank_sources import inventory_quiz_sources

def test_all_extensions_are_in_inventory(tmp_path):
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4/원본_docx'; folder.mkdir(parents=True)
    for name in ('원본.doc','unknown.bin','문제.pdf','note.jpg','복사.docx'): (folder/name).write_bytes(b'evidence')
    rows=inventory_quiz_sources(tmp_path,4)
    assert len(rows)==5
    assert {r['format'] for r in rows}=={'doc','other','pdf','image','docx'}
    assert all(r['processing']=='pending' for r in rows)

def test_empty_source_folder_is_not_success(tmp_path):
    with pytest.raises(ValueError): inventory_quiz_sources(tmp_path,4)

def test_source_id_survives_content_change(tmp_path):
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4'; folder.mkdir(parents=True)
    path=folder/'문제.txt'; path.write_bytes(b'one'); first=inventory_quiz_sources(tmp_path,4)[0]
    path.write_bytes(b'two'); second=inventory_quiz_sources(tmp_path,4)[0]
    assert first['id']==second['id'] and first['sha256']!=second['sha256']
# question_bank_sources 테스트 파일
def test_source_symlink_is_rejected(tmp_path):
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4'; folder.mkdir(parents=True)
    target=tmp_path/'outside.txt'; target.write_text('x',encoding='utf-8')
    try: (folder/'link.txt').symlink_to(target)
    except OSError: pytest.skip('host cannot create symlink; record this validation limit')
    with pytest.raises(ValueError): inventory_quiz_sources(tmp_path,4)

def test_nfd_filename_keeps_resolvable_path(tmp_path):
    import unicodedata
    folder=tmp_path/'from_the_past/정리/퀴즈/실험4'; folder.mkdir(parents=True)
    path=folder/unicodedata.normalize('NFD','기출.txt'); path.write_bytes(b'x')
    row=inventory_quiz_sources(tmp_path,4)[0]
    assert (tmp_path/row['path']).is_file()


