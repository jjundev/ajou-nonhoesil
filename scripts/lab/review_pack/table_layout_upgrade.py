"""Apply note table layout contracts to published notes without regenerating content.

python -m scripts.lab.review_pack.table_layout_upgrade (--all | --folder DIR) [--apply --backup-dir DIR]
"""
import argparse
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory

from .checks import check_pack
from .explanation_render import write_explanations
from .workbook_render import read_workbook_payload, workbook_source_path
from .manifest import DATA, load_manifest, output_names
from .navigation_upgrade import ASSETS, ROOT, _atomic_write
from .table_layout import TableLayoutError, layout_note_tables, load_note_layouts

BODY_START = '<section id="learning">'
BODY_END = '</main>'
CSS_START = '/* explanation-table-layout:start */'
CSS_END = '/* explanation-table-layout:end */'
CSS_ANCHOR = '    td:first-child, th:first-child { min-width: 6em; }'
LAYOUT_FILE = 'sections/table-layout.json'
TOPIC = re.compile(r'(<article class="topic" id="([^"]+)">)(.*?)(</article>)', re.S)


def _layout_css():
    # 열 배치 규칙의 정본은 스킬 템플릿이다. 여기 복사해 두지 않는다.
    lines = (ASSETS / 'note-template.html').read_text(encoding='utf-8').splitlines()
    starts = [i for i, l in enumerate(lines) if CSS_START in l]
    ends = [i for i, l in enumerate(lines) if CSS_END in l]
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError('Unsupported table layout CSS in note template')
    return lines[starts[0]:ends[0] + 1]


def _replace_css(text):
    newline = '\r\n' if '\r\n' in text else '\n'
    block = newline.join(_layout_css())
    if text.count(CSS_START) == 1 and text.count(CSS_END) == 1:
        start = text.rindex('\n', 0, text.index(CSS_START)) + 1
        end = text.index(CSS_END) + len(CSS_END)
        return text[:start] + block + text[end:]
    if CSS_START in text or CSS_END in text:
        raise ValueError('Unsupported table layout CSS')
    if text.count(CSS_ANCHOR) != 1:
        raise ValueError('Missing table layout CSS anchor')
    at = text.index(CSS_ANCHOR) + len(CSS_ANCHOR)
    return text[:at] + newline + newline + block + text[at:]


def upgrade_layout_html(text: str, layouts: dict) -> str:
    if text.count(BODY_START) != 1 or text.count(BODY_END) != 1 or text.index(BODY_START) > text.index(BODY_END):
        raise ValueError('Unsupported note body')
    start, end = text.index(BODY_START), text.index(BODY_END)
    body = text[start:end]
    topics = list(TOPIC.finditer(body))
    if len(topics) != body.count('<article'):
        raise ValueError('Unsupported topic markup')
    ids = {m.group(2) for m in topics}
    for entry in layouts['tables']:
        if entry['key'].split('/')[0] not in ids:
            raise TableLayoutError(entry['key'] + ': unknown topic')
    body = TOPIC.sub(lambda m: m.group(1) + layout_note_tables(m.group(2), m.group(3), layouts) + m.group(4), body)
    return _replace_css(text[:start] + body + text[end:])


def _rerender_explanation(folder, manifest):
    # check_pack은 문제설명을 동봉 템플릿으로 다시 그려 바이트를 비교한다.
    # 템플릿 사본을 바꾸면 문제설명도 새 템플릿으로 다시 그려야 일치한다.
    if manifest.get('problem_explanation_version') not in (1, 2):
        return {}
    question = read_workbook_payload(workbook_source_path(folder, manifest, 'question'))
    changes = {}
    with TemporaryDirectory(prefix='layout-upgrade-') as scratch:
        paths = write_explanations(
            manifest, question, folder / DATA, Path(scratch), folder / DATA / 'assets',
            note_template=ASSETS / 'note-template.html',
        )
        for path in paths.values():
            target = folder / path.relative_to(scratch)
            if target.is_symlink():
                raise ValueError('Symlink page: ' + str(target))
            original, updated = target.read_bytes(), path.read_bytes()
            if original != updated:
                changes[target] = (original, updated)
    return changes


def _own_layout_file(folder):
    # publish는 generated_files에 없는 파일을 사용자 파일로 본다. 열 배치 파일도 생성물로 등록한다.
    path = folder / DATA / 'manifest.json'
    original = path.read_bytes()
    raw = original.decode('utf-8')
    newline = '\r\n' if '\r\n' in raw else '\n'
    data = json.loads(raw)
    if json.dumps(data, ensure_ascii=False, indent=2) != raw.replace('\r\n', '\n'):
        raise ValueError(f'{path}: unsupported manifest formatting')
    owned = f'{DATA}/{LAYOUT_FILE}'
    if owned in data.get('generated_files', []):
        return {}
    data['generated_files'] = sorted([*data.get('generated_files', []), owned])
    return {path: (original, json.dumps(data, ensure_ascii=False, indent=2).replace('\n', newline).encode('utf-8'))}


def upgrade_packs(folders: list[Path], *, apply: bool = False,
                  backup_root: Path | None = None) -> list[Path]:
    folders = [Path(p).resolve() for p in folders]
    if len(set(folders)) != len(folders) or len({p.name for p in folders}) != len(folders):
        raise ValueError('Duplicate pack folders')
    changes = {}
    template = (ASSETS / 'note-template.html').read_bytes()
    # Complete preflight for every pack before making any backup or mutation.
    for folder in folders:
        manifest = load_manifest(folder / DATA / 'manifest.json')
        names = output_names(manifest['experiment'], review_presentation_version=manifest.get('review_presentation_version'))
        layouts = load_note_layouts(folder / DATA)
        if layouts is None:
            raise ValueError(f'{folder.name}: missing {DATA}/sections/table-layout.json')
        path = folder / names['note_html']
        copy = folder / DATA / 'assets/note-template.html'
        for p in (path, copy):
            if p.is_symlink():
                raise ValueError('Symlink page: ' + str(p))
        original = path.read_bytes()
        try:
            upgraded = upgrade_layout_html(original.decode('utf-8'), layouts).encode('utf-8')
        except ValueError as exc:
            raise ValueError(f'{path}: {exc}') from None
        if original != upgraded:
            changes[path] = (original, upgraded)
        changes.update(_own_layout_file(folder))
        if copy.read_bytes() != template:
            changes[copy] = (copy.read_bytes(), template)
            changes.update(_rerender_explanation(folder, manifest))
    if not apply or not changes:
        return list(changes)
    if backup_root is None:
        raise ValueError('Applying table layout changes requires a backup directory')
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
