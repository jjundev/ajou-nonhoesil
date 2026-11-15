"""Serialize updates to a pack and install already validated files."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory, gettempdir
import unicodedata

try:
    import fcntl
except ImportError:
    import msvcrt
    fcntl = None


@contextmanager
def pack_write_lock(folder):
    # The lock lives outside generated_files and survives pack directory swaps.
    target = unicodedata.normalize('NFC', os.path.normcase(str(Path(folder).resolve())))
    ident = hashlib.sha256(target.encode()).hexdigest()
    lock = Path(gettempdir()) / ('logic-lab-pack-' + ident + '.lock')
    with lock.open('a+b') as handle:
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise ValueError('다른 작업에서 같은 학습팩을 갱신 중입니다: ' + target) from None
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def replace_workbook_files(files, output_dir):
    """Stage writable copies alongside their destinations and restore on failure."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.workbook-publish-', dir=output_dir) as scratch:
        stage = Path(scratch)
        backups = {}
        staged = {}
        for i, (destination, source) in enumerate(files.items()):
            if destination.exists():
                original = stage / f'{i}.old'
                shutil.copy2(destination, original)
                backups[destination] = original
            staged[destination] = Path(shutil.copy2(source, stage / f'{i}.new'))
        written = []
        try:
            for destination, candidate in staged.items():
                os.replace(candidate, destination)
                written.append(destination)
        except OSError:
            for destination in reversed(written):
                if destination in backups:
                    os.replace(backups[destination], destination)
                else:
                    destination.unlink()
            raise
