"""Inventory all quiz evidence, including unreadable and unsupported formats."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import unicodedata

from scripts.lab import config
from .sources import file_sha256


_FORMATS = {
    '.pdf': 'pdf', '.docx': 'docx', '.doc': 'doc',
    '.png': 'image', '.jpg': 'image', '.jpeg': 'image', '.webp': 'image',
    '.tif': 'image', '.tiff': 'image', '.txt': 'text', '.md': 'text',
}


def _reject_link(path):
    if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
        raise ValueError(f'Evidence link is not allowed: {path}')


def _evidence_path(base, relative):
    """Resolve canonical POSIX input under a trusted base without following links."""
    if (not isinstance(relative, str) or not relative or
            any(c in relative for c in ('\\', ':', '\x00')) or
            PurePosixPath(relative).is_absolute() or
            any(part in ('', '.', '..') for part in relative.split('/'))):
        raise ValueError('unsafe relative path')
    base = Path(base).absolute()
    _reject_link(base)
    target = base
    for part in relative.split('/'):
        target = target / part
        _reject_link(target)
    if not target.resolve().is_relative_to(base.resolve()):
        raise ValueError('outside base directory')
    return target


def inventory_quiz_sources(root: Path, experiment: int) -> list[dict]:
    """Return pending source records; filenames never prove exam provenance."""
    config.experiment_folder_name(experiment)
    root = Path(root).absolute()
    folder = _evidence_path(root, f'from_the_past/정리/퀴즈/실험{experiment}')
    if not folder.is_dir():
        raise ValueError(f'No quiz source files: {folder}')
    files = []

    def walk_error(error):
        raise error

    for directory, dirs, names in os.walk(folder, followlinks=False, onerror=walk_error):
        for name in dirs + names:
            _reject_link(Path(directory) / name)
        for name in names:
            path = Path(directory) / name
            if not path.is_file():
                raise ValueError(f'Not a regular evidence file: {path}')
            files.append(path)
    if not files:
        raise ValueError(f'No quiz source files: {folder}')
    seen_paths, seen_ids, rows = set(), set(), []
    for path in sorted(files):
        relative = path.relative_to(root).as_posix()
        normalized = unicodedata.normalize('NFC', relative)
        ident = 's-' + hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
        if normalized in seen_paths or ident in seen_ids:
            raise ValueError(f'Normalized source path/ID collision: {relative}')
        seen_paths.add(normalized)
        seen_ids.add(ident)
        fmt = _FORMATS.get(path.suffix.lower(), 'other')
        unit_kind = 'page' if fmt == 'pdf' else 'image' if fmt == 'image' else 'document'
        rows.append(dict(
            id=ident, path=relative, sha256=file_sha256(path), format=fmt,
            filename_metadata={'year': None, 'term': None},
            observed_metadata={'year': None, 'term': None}, conflicts=[],
            processing='pending', reason='', unit_kind=unit_kind,
            unit_count=None if fmt == 'pdf' else 1,
        ))
    return rows
