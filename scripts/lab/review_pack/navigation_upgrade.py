"""Upgrade published navigation without regenerating authored content.

python -m scripts.lab.review_pack.navigation_upgrade --all [--apply --backup-dir DIR]
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile

from .html2md import Parser
from .manifest import DATA, load_manifest, output_names
from .navigation import check_navigation, render_navigation, navigation_items
from .workbook_render import read_workbook_payload

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / '.claude/skills/logic-lab-review-pack/assets'
CSS_ANCHOR = '    /* ---------- 한 화면에 하나씩 (JS가 켤 때만) ---------- */'
CSS_START = '    /* ---------- 내부 목차 ---------- */'
CSS_START_V1 = '    /* ---------- 자료 이동과 내부 목차 ---------- */'
HASH_OLD = "        const id = decodeURIComponent((hash || '').replace(/^#/, ''));"
HASH_NEW = """        let id;
        try { id = decodeURIComponent((hash || '').replace(/^#/, '')); } catch (e) { return { i: 0 }; }"""


def _upgrade_runtime(text, template):
    start_marker, end_marker = '      // 목차:', '      function indexFor(hash)'
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise ValueError('Unsupported topic navigation runtime')
    start, end = text.index(start_marker), text.index(end_marker)
    text = text[:start] + template[template.index(start_marker):template.index(end_marker)] + text[end:]
    old = "          const id = decodeURIComponent(a.getAttribute('href').slice(1));"
    new = "          let id;\n          try { id = decodeURIComponent(a.getAttribute('href').slice(1)); } catch (e) { return; }"
    text = text.replace(old, new)
    if HASH_OLD in text:
        text = _once(text, HASH_OLD, HASH_NEW)
    elif text.count(HASH_NEW) != 1:
        raise ValueError('Unsupported hash navigation runtime')
    return text


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unsupported navigation anchor: ' + old[:80])
    return text.replace(old, new, 1)


def _validate(text, expected_page):
    parser = Parser(); parser.feed(text)
    errors = check_navigation(parser.root, expected_page)
    if errors:
        raise ValueError('; '.join(errors))


def _strip_navigation_summary(text):
    patterns = (
        r'        <h3 class="nav-label">이 페이지 목차</h3>\n',
        r'        <p class="panel-meta">[^\n]*</p>\n',
        r'        <div class="progress" aria-hidden="true"><span id="progress-bar"></span></div>\n',
    )
    for pattern in patterns:
        if len(re.findall(pattern, text)) > 1:
            raise ValueError('Duplicate navigation summary')
        text = re.sub(pattern, '', text, count=1)
    for line in (
        "      const progressN = document.getElementById('progress-n');\n",
        "      const progressBar = document.getElementById('progress-bar');\n",
        "      const progressTotal = document.getElementById('progress-total');\n",
        "        progressN.textContent = String(done.size);\n",
        "        progressTotal.textContent = String(total);\n",
        "        progressBar.style.transform = 'scaleX(' + (total ? done.size / total : 0) + ')';\n",
    ):
        text = text.replace(line, '')
    return text


def upgrade_navigation_html(text: str, *, names: dict[str, str], kind: str) -> str:
    parser = Parser(); parser.feed(text)
    slots = render_navigation(names, kind, navigation_items(parser.root, kind))
    template = (ASSETS / f'{kind}-template.html').read_text(encoding='utf-8')
    css = template[template.index(CSS_START):template.index(CSS_ANCHOR)]
    if 'class="pack-nav"' in text:
        pattern = r'        <h3 class="nav-label">자료 이동</h3>\n        <nav class="pack-nav" aria-label="자료 이동">.*?</nav>\n        <hr class="nav-divider">\n'
        if len(re.findall(pattern, text, re.S)) != 1:
            raise ValueError('Unsupported document navigation block')
        text = re.sub(pattern, '', text, count=1, flags=re.S)
        text = text.replace("e.target.closest('.toc a, .pack-nav a')", "e.target.closest('.toc a')")
    if '<nav class="toc" aria-label="이 페이지 목차">' in text:
        text = _strip_navigation_summary(text)
        matches = list(re.finditer(r'<nav class="toc" aria-label="이 페이지 목차">.*?</nav>', text, re.S))
        if len(matches) != 1:
            raise ValueError('Unsupported topic navigation markup')
        text = _once(text, matches[0].group(), f'<nav class="toc" aria-label="이 페이지 목차">{slots["TOC"]}</nav>')
        _validate(text, names[kind + '_html'])
        markers = [m for m in (CSS_START, CSS_START_V1) if m in text]
        if len(markers) != 1 or text.count(markers[0]) != 1 or text.count(CSS_ANCHOR) != 1:
            raise ValueError('Unsupported navigation CSS')
        start, end = text.index(markers[0]), text.index(CSS_ANCHOR)
        return _upgrade_runtime(text[:start] + css + text[end:], template)
    panels = list(re.finditer(r'        <p class="panel-meta">.*?</nav>', text, re.S))
    if len(panels) != 1:
        raise ValueError('Unsupported navigation panel')
    old = panels[0].group()
    if old.count('<nav class="toc" aria-label="목차">') != 1:
        raise ValueError('Unsupported legacy TOC')
    new = f'        <nav class="toc" aria-label="이 페이지 목차">{slots["TOC"]}</nav>'
    result = _once(text, old, new)
    result = _once(result, CSS_ANCHOR, css + CSS_ANCHOR)
    result = _upgrade_runtime(result, template)
    result = _strip_navigation_summary(result)
    _validate(result, names[kind + '_html'])
    return result


def _atomic_write(path, data):
    mode = path.stat().st_mode & 0o777
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def upgrade_packs(folders: list[Path], *, apply: bool = False,
                  backup_root: Path | None = None) -> list[Path]:
    folders = [Path(p).resolve() for p in folders]
    if len(set(folders)) != len(folders) or len({p.name for p in folders}) != len(folders):
        raise ValueError('Duplicate pack folders')
    changes = {}
    # Complete preflight for every pack before making any backup or mutation.
    for folder in folders:
        manifest = load_manifest(folder / DATA / 'manifest.json')
        workbook = manifest.get('review_presentation_version') == 2
        names = output_names(manifest['experiment'], review_presentation_version=manifest.get('review_presentation_version'))
        for key in ('note', 'review', 'question'):
            if key + '_html' not in names:
                continue
            path = folder / names[key + '_html']
            if path.is_symlink():
                raise ValueError('Symlink page: ' + str(path))
            original = path.read_bytes()
            if key != 'note' and workbook:
                read_workbook_payload(path)  # Recognize the separate workbook format.
                continue
            upgraded = upgrade_navigation_html(original.decode('utf-8'), names=names, kind=key).encode('utf-8')
            if original != upgraded:
                changes[path] = (original, upgraded)
        for kind in ('note', 'review'):
            path = folder / DATA / 'assets' / f'{kind}-template.html'
            if path.is_symlink():
                raise ValueError('Symlink template: ' + str(path))
            original = path.read_bytes()
            updated = (ASSETS / path.name).read_bytes()
            if original != updated:
                changes[path] = (original, updated)
    if not apply or not changes:
        return list(changes)
    if backup_root is None:
        raise ValueError('Applying navigation changes requires a backup directory')
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
    folders = sorted((ROOT / '복습노트').glob('실험*')) if args.all else [args.folder]
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
