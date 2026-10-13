"""Prepare copied lab packs with updated introductions; never publish them.

python docs/learning-pack-source/refresh_motivation.py --root . --stage-root NEW_DIR
"""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.lab.review_pack.html2md import export_document
from scripts.lab.review_pack.manifest import DATA, output_names
from scripts.lab.review_pack.pack_md import write_pack_md
from scripts.lab.review_pack.note_metadata import topic_metadata

TITLE = '왜 이 회로를 쓰는지 먼저 알아봐요'
MD_NOTE = '도입의 상황은 이해를 위한 예시이며 측정값이 아니에요. 회로를 쓰는 이유와 입력·출력 예를 설명하고 이번 수행 항목에 연결했어요.'
REFERENCE_PAGES = {1: [5, 6], 2: [4, 10, 11], 3: [3], 4: [3, 5, 8, 11], 5: [3, 5, 9, 11]}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class _Spans(HTMLParser):
    """Locate original element bytes without serializing untouched HTML."""
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.offsets = [0]
        for match in re.finditer('\n', text):
            self.offsets.append(match.end())
        self.stack = []
        self.elements = []
        self.feed(text)
        self.close()

    def _position(self):
        line, column = self.getpos()
        return self.offsets[line-1] + column

    def handle_starttag(self, tag, attrs):
        start = self._position()
        if tag not in VOID:
            self.stack.append((tag, dict(attrs), start, start+len(self.get_starttag_text())))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                item = self.stack[i]
                parents = [(t, a) for t, a, _, _ in self.stack[:i]]
                end_start = self._position()
                self.elements.append((*item, end_start, self.text.index('>', end_start)+1, parents))
                del self.stack[i:]
                break


def _one(elements, tag, predicate):
    matches = [e for e in elements if e[0] == tag and predicate(e)]
    if len(matches) != 1:
        raise ValueError(f'Expected one {tag}, found {len(matches)}')
    return matches[0]


def _snapshot(folder):
    if folder.is_symlink() or any(p.is_symlink() for p in folder.rglob('*')):
        raise ValueError('Symlink in source pack')
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}


def prepare_stage(pack: Path, fragment: Path, stage: Path) -> Path:
    pack, fragment, stage = map(lambda p: Path(p).resolve(), (pack, fragment, stage))
    if stage.exists() or stage.is_relative_to(pack) or pack.is_relative_to(stage):
        raise ValueError('Stage must be new and outside the source pack')
    before = _snapshot(pack)
    manifest = json.loads((pack/DATA/'manifest.json').read_text(encoding='utf-8'))
    if not manifest['topics'] or manifest['topics'][0]['id'] != 't-start':
        raise ValueError('First topic must be t-start')
    names = output_names(manifest['experiment'], review_presentation_version=manifest.get('review_presentation_version'))
    note = names['note_html']
    owned_files = set(manifest['generated_files'])
    required = {note, DATA+'/'+Path(note).with_suffix('.md').name, DATA+'/manifest.json'}
    if not required <= owned_files or not owned_files <= before.keys():
        raise ValueError('Invalid generated file ownership')
    original = (pack/note).read_text(encoding='utf-8')
    elements = _Spans(original).elements
    article = _one(elements, 'article', lambda e: e[1].get('id') == 't-start')
    _one(elements, 'h3', lambda e: article[3] <= e[2] < e[5] <= article[4])
    link = _one(elements, 'a', lambda e: e[1].get('href') == '#t-start' and
                any(t == 'nav' and 'toc' in a.get('class', '').split() for t, a in e[6]))
    body = fragment.read_text(encoding='utf-8').strip()
    if re.search(r'<(?:script|article|h1)\b|\son\w+\s*=|javascript:', body, re.I):
        raise ValueError('Unsupported active or wrapped introduction fragment')
    body = re.sub(r'(\b(?:src|href)=[\"\x27])figures/', lambda m: m.group(1)+DATA+'/figures/', body)
    updated_article = original[article[2]:article[3]] + '<h3>'+html.escape(TITLE)+'</h3>'+body+'</article>'
    changes = [(article[2], article[5], updated_article), (link[3], link[4], html.escape(TITLE))]
    updated = original
    for start, end, value in sorted(changes, reverse=True):
        updated = updated[:start] + value + updated[end:]
    manifest['topics'][0]['title'] = TITLE
    manual = next(s for s in manifest['sources'] if s['kind'] == 'manual')
    refs = manifest['topics'][0]['sources']
    for page in REFERENCE_PAGES[manifest['experiment']]:
        if not any(r['source_id'] == manual['id'] and r.get('pdf_page') == page for r in refs):
            refs.append({'source_id': manual['id'], 'pdf_page': page, 'printed_page': None})
    notes = manifest['topics'][0].get('md_notes', '')
    if MD_NOTE not in notes:
        manifest['topics'][0]['md_notes'] = (notes+'\n\n'+MD_NOTE).strip()
    manifest['checks'] = {k: 'not_run' for k in manifest['checks']}
    owned_stage = False
    try:
        stage.mkdir(parents=True)
        owned_stage = True
        # User-added PDFs/memos belong to publish's preservation path, not to this stage.
        for relative in sorted(owned_files):
            target = stage/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pack/relative, target)
        (stage/note).write_text(updated, encoding='utf-8')
        md, _ = export_document(stage/note, note_metadata=topic_metadata(manifest))
        write_pack_md(stage, Path(note).with_suffix('.md').name, md)
        manifest['generated_files'] = sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
        (stage/DATA/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        if before != _snapshot(pack):
            raise ValueError('Source pack changed while preparing stage')
    except Exception:
        if owned_stage and stage.exists():
            shutil.rmtree(stage)
        raise
    return stage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--stage-root', type=Path, required=True)
    args = parser.parse_args(argv)
    root, stages = args.root.resolve(), args.stage_root.resolve()
    if stages.exists():
        parser.error('Stage root must be new')
    source = root/'docs/learning-pack-source'
    packs = [root/'복습노트'/f'실험{n:02d}' for n in range(1, 6)]
    if any(stages.is_relative_to(p) or p.is_relative_to(stages) for p in packs):
        parser.error('Stage root overlaps source packs')
    stages.mkdir(parents=True)
    try:
        for pack in packs:
            result = prepare_stage(pack, source/pack.name/'sections/t-start.html', stages/pack.name)
            print(result)
    except Exception:
        shutil.rmtree(stages)
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
