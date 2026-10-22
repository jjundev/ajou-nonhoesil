"""Discover local evidence without initializing report directories."""
from datetime import date
from pathlib import Path
import hashlib
import json
import unicodedata
from scripts.lab import config

def resolve_experiments(*, numbers=None, week=None, today=None):
    if numbers is not None and week is not None:
        raise ValueError('Specify experiment numbers or week, not both')
    if numbers is not None:
        for n in numbers:
            config.experiment_folder_name(n)
        return sorted(set(numbers))
    if week is not None:
        return config.experiments_in_week(week)
    upcoming = config.next_experiments(today)
    return upcoming[1] if upcoming else []

def file_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def inventory(root, experiment):
    root = Path(root).resolve()
    config.experiment_folder_name(experiment)
    old = root / '복습노트' / config.experiment_folder_name(experiment) / config.PACK_DATA_DIR / 'manifest.json'
    old_ids = {}
    if old.exists():
        data = json.loads(old.read_text(encoding='utf-8'))
        old_ids = {unicodedata.normalize('NFC',s['path']): s['id'] for s in data['sources']}
    rows = {}
    def add(path, kind, edition='unknown'):
        path = path.resolve()
        if not path.is_file() or not path.is_relative_to(root):
            return None
        rel = path.relative_to(root).as_posix()
        norm = unicodedata.normalize('NFC',rel)
        if rel not in rows:
            rows[rel] = dict(id=old_ids.get(norm,'s-'+hashlib.sha256(norm.encode()).hexdigest()[:16]),
                             path=rel, sha256=file_sha256(path),kind=kind,edition=edition)
        return rows[rel]
    manual = None
    for p in config.manual_candidates(experiment, root=root):
        p = p if p.is_absolute() else root / p
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            edition = 'current' if rel.startswith('강의노트/') else 'archive' if rel.startswith(config.MANUAL_ARCHIVE+'/') else 'unknown'
            manual = add(p,'manual',edition)
            break
    folders = [
        (f'from_the_past/정리/퀴즈/실험{experiment}','quiz'),
        ('from_the_past/정리/논회 강의노트','theory'),
        ('from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃','datasheet'),
        ('강의노트/공지사항','notice'),
        (config.experiment_dir(experiment),'report'),
    ]
    for folder, kind in folders:
        for p in sorted((root / folder).rglob('*')):
            if p.suffix.lower() not in {'.pdf','.md','.png','.jpg','.jpeg','.docx','.txt'}:
                continue
            if 'review_round' in p.name or '손그림검토' in p.parts:
                continue
            actual = 'stt' if 'STT' in p.parts else 'record' if (p.name in {'명세.md','기록.md','netlist.md'} or unicodedata.normalize('NFC', p.name).endswith('_기록.md')) else kind
            add(p,actual)
    return dict(experiment=experiment,manual=manual,sources=list(rows.values()),scope_tokens=config.scope_tokens(experiment))
