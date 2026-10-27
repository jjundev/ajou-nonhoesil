"""Apply three-part note summaries to published notes without regenerating content.

python -m scripts.lab.review_pack.summary_upgrade (--all | --folder DIR) [--apply --backup-dir DIR]
"""
import argparse
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from .checks import check_pack
from .html2md import export_document
from .manifest import DATA, load_manifest, output_names
from .navigation_upgrade import ROOT, _atomic_write
from .note_metadata import summary_structure_errors, topic_metadata
from .note_summary import SUMMARY_FILE, check_topic_ids, load_note_summaries, lost_tokens, replace_summary
from .pack_md import to_data_frame
from .table_layout_upgrade import BODY_END, BODY_START, TOPIC


def upgrade_summary_html(text: str, summaries: dict, topic_ids: list[str]) -> str:
    if text.count(BODY_START) != 1 or text.count(BODY_END) != 1 or text.index(BODY_START) > text.index(BODY_END):
        raise ValueError('Unsupported note body')
    start, end = text.index(BODY_START), text.index(BODY_END)
    body = text[start:end]
    topics = list(TOPIC.finditer(body))
    if len(topics) != body.count('<article') or [m.group(2) for m in topics] != list(topic_ids):
        raise ValueError('Unsupported topic markup')
    check_topic_ids(summaries, topic_ids)

    def one(m):
        topic_id, old = m.group(2), m.group(3)
        new = replace_summary(topic_id, old, summaries[topic_id])
        if lost := lost_tokens(old, new):
            raise ValueError(f'{topic_id}: lost tokens ' + ', '.join(lost))
        if errors := summary_structure_errors(topic_id, new):
            raise ValueError(errors[0])
        return m.group(1) + new + m.group(4)
    return text[:start] + TOPIC.sub(one, body) + text[end:]


def _note_md(html_text, name, manifest):
    # export_document는 경로를 읽는다. 새 HTML은 임시 폴더에 같은 이름으로 써서 MD로 바꾼다(그림은 쓰지 않는다).
    with TemporaryDirectory(prefix='summary-upgrade-') as scratch:
        path = Path(scratch) / name
        path.write_text(html_text, encoding='utf-8')
        return to_data_frame(export_document(path, export=False, note_metadata=topic_metadata(manifest))[0])


def _upgrade_manifest(path, original):
    # 요약 파일도 생성물로 등록하고 build 검사 플래그를 켠다. 형식 검사는 table_layout_upgrade와 같다.
    raw = original.decode('utf-8')
    newline = '\r\n' if '\r\n' in raw else '\n'
    data = json.loads(raw)
    if json.dumps(data, ensure_ascii=False, indent=2) != raw.replace('\r\n', '\n'):
        raise ValueError(f'{path}: unsupported manifest formatting')
    if 'note_presentation_version' not in data:
        raise ValueError(f'{path}: note_summary_version needs note_presentation_version')
    owned = f'{DATA}/{SUMMARY_FILE}'
    if data.get('note_summary_version') != 2:
        data = {k: v for k, v in data.items() if k != 'note_summary_version'}
        at = list(data).index('note_presentation_version') + 1
        items = list(data.items())
        data = dict(items[:at] + [('note_summary_version', 2)] + items[at:])
    if owned not in data.get('generated_files', []):
        data['generated_files'] = sorted([*data.get('generated_files', []), owned])
    return json.dumps(data, ensure_ascii=False, indent=2).replace('\n', newline).encode('utf-8'), data


def upgrade_packs(folders: list[Path], *, apply: bool = False,
                  backup_root: Path | None = None) -> list[Path]:
    folders = [Path(p).resolve() for p in folders]
    if len(set(folders)) != len(folders) or len({p.name for p in folders}) != len(folders):
        raise ValueError('Duplicate pack folders')
    changes = {}
    # Complete preflight for every pack before making any backup or mutation.
    for folder in folders:
        manifest_path = folder / DATA / 'manifest.json'
        manifest = load_manifest(manifest_path)
        names = output_names(manifest['experiment'], review_presentation_version=manifest.get('review_presentation_version'))
        summaries = load_note_summaries(folder / DATA)
        if summaries is None:
            raise ValueError(f'{folder.name}: missing {DATA}/{SUMMARY_FILE}')
        html_path, md_path = folder / names['note_html'], folder / DATA / names['note_md']
        for p in (html_path, md_path, manifest_path):
            if p.is_symlink():
                raise ValueError('Symlink page: ' + str(p))
        original = html_path.read_bytes()
        md_original = md_path.read_bytes()
        if _note_md(original.decode('utf-8'), html_path.name, manifest).encode('utf-8') != md_original:
            raise ValueError(f'{folder.name}: note MD differs from HTML; refusing to overwrite')
        try:
            upgraded = upgrade_summary_html(original.decode('utf-8'), summaries, [t['id'] for t in manifest['topics']])
        except ValueError as exc:
            raise ValueError(f'{html_path}: {exc}') from None
        manifest_original = manifest_path.read_bytes()
        manifest_updated, new_manifest = _upgrade_manifest(manifest_path, manifest_original)
        md_updated = _note_md(upgraded, html_path.name, new_manifest).encode('utf-8')
        for path, before, after in ((html_path, original, upgraded.encode('utf-8')), (md_path, md_original, md_updated),
                                    (manifest_path, manifest_original, manifest_updated)):
            if before != after:
                changes[path] = (before, after)
    if not apply or not changes:
        return list(changes)
    if backup_root is None:
        raise ValueError('Applying summary changes requires a backup directory')
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
    folders = ([p for p in sorted((ROOT / '복습노트').glob('실험[0-9][0-9]')) if (p / DATA / SUMMARY_FILE).is_file()]
               if args.all else [args.folder])
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
