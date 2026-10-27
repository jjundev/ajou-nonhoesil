"""Wrap published note tables and equations in cards without regenerating content.

python -m scripts.lab.review_pack.card_upgrade (--all | --folder DIR) [--apply --backup-dir DIR]
"""
import argparse
from pathlib import Path
import shutil

from .checks import check_pack
from .equation_cards import separate_equations
from .manifest import DATA, load_manifest, output_names
from .navigation_upgrade import ASSETS, ROOT, _atomic_write
from .table_cards import separate_tables

BODY_START = '<section id="learning">'
BODY_END = '</main>'
CSS_ANCHOR = '    .katex-display { overflow-x: auto; overflow-y: hidden; padding: var(--s1) 0; }'
CSS_START = '    .equation-card { margin'
CSS_END = '    .table-card > table { margin: 0; }'
CSS_PRESENT = '    .table-card { margin'
GUARD_OLD = ".closest('.widget, .katex-display, .table-wrap, svg, input, details')"
GUARD_NEW = ".closest('.widget, .equation-card, .table-card, .katex-display, .table-wrap, svg, input, details')"


def _card_css(newline):
    # 카드 규칙의 정본은 스킬 템플릿이다. 여기 복사해 두지 않는다.
    template = (ASSETS / 'note-template.html').read_text(encoding='utf-8')
    if template.count(CSS_START) != 1 or template.count(CSS_END) != 1:
        raise ValueError('Unsupported card CSS in note template')
    block = template[template.index(CSS_START):template.index(CSS_END) + len(CSS_END)]
    return newline.join(block.splitlines())


def upgrade_card_html(text: str) -> str:
    if text.count(BODY_START) != 1 or text.count(BODY_END) != 1 or text.index(BODY_START) > text.index(BODY_END):
        raise ValueError('Unsupported note body')
    start, end = text.index(BODY_START), text.index(BODY_END)
    text = text[:start] + separate_tables(separate_equations(text[start:end])) + text[end:]
    if CSS_PRESENT not in text:
        if text.count(CSS_ANCHOR) != 1:
            raise ValueError('Missing card CSS anchor')
        # 발행본은 CRLF일 수 있으므로 앵커 줄의 줄 끝을 그대로 따른다.
        at = text.index(CSS_ANCHOR) + len(CSS_ANCHOR)
        newline = '\r\n' if text.startswith('\r\n', at) else '\n'
        text = text[:at] + newline + _card_css(newline) + text[at:]
    if GUARD_NEW not in text:
        if text.count(GUARD_OLD) != 1:
            raise ValueError('Unsupported swipe guard')
        text = text.replace(GUARD_OLD, GUARD_NEW, 1)
    return text


def upgrade_packs(folders: list[Path], *, apply: bool = False,
                  backup_root: Path | None = None) -> list[Path]:
    folders = [Path(p).resolve() for p in folders]
    if len(set(folders)) != len(folders) or len({p.name for p in folders}) != len(folders):
        raise ValueError('Duplicate pack folders')
    changes = {}
    # Complete preflight for every pack before making any backup or mutation.
    for folder in folders:
        manifest = load_manifest(folder / DATA / 'manifest.json')
        names = output_names(manifest['experiment'], review_presentation_version=manifest.get('review_presentation_version'))
        path = folder / names['note_html']
        if path.is_symlink():
            raise ValueError('Symlink page: ' + str(path))
        original = path.read_bytes()
        try:
            upgraded = upgrade_card_html(original.decode('utf-8')).encode('utf-8')
        except ValueError as exc:
            raise ValueError(f'{path}: {exc}') from None
        if original != upgraded:
            changes[path] = (original, upgraded)
    if not apply or not changes:
        return list(changes)
    if backup_root is None:
        raise ValueError('Applying card changes requires a backup directory')
    backup_root = Path(backup_root).resolve()
    if backup_root.exists() or any(backup_root == f or backup_root.is_relative_to(f) for f in folders):
        raise ValueError('Backup directory must be new and outside the packs')
    for folder in folders:
        shutil.copytree(folder, backup_root / folder.name)
    written = []
    try:
        for path, (_, updated) in changes.items():
            _atomic_write(path, updated)
            written.append(path)
        errors = [f'{f.name}: {e}' for f in folders for e in check_pack(f)]
        if errors:
            raise ValueError('; '.join(errors))
    except Exception:
        for path in written:
            _atomic_write(path, changes[path][0])
        raise
    return list(changes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument('--all', action='store_true')
    scope.add_argument('--folder', type=Path)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--backup-dir', type=Path)
    args = ap.parse_args(argv)
    folders = sorted((ROOT / '복습노트').glob('실험[0-9][0-9]')) if args.all else [args.folder]
    try:
        changed = upgrade_packs(folders, apply=args.apply, backup_root=args.backup_dir)
    except (ValueError, OSError) as exc:
        ap.exit(1, str(exc) + '\n')
    for path in changed:
        print(path)
    print(f'{len(folders)} packs inspected; {len(changed)} files ' + ('updated' if args.apply else 'would change'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
