"""Markdown-only references for version 2 learning notes."""
import re
from urllib.parse import quote

def topic_metadata(manifest):
    sources = {s['id']: s for s in manifest['sources']}
    result = {}
    def label(value):
        return str(value).replace('\\', '\\\\').replace('[', r'\[').replace(']', r'\]').replace('\n', ' ')
    for t in manifest['topics']:
        rows, links, refs = [], [], []
        for p in manifest['problems']:
            if p['status'] == 'included' and t['id'] in p['topics']:
                target = quote(f"실험{manifest['experiment']:02d}_기출풀이.md", safe='')
                links.append(f"[{label(p.get('title', p['id']))}]({target}#{p['id']})")
        if links:
            rows.append('이 개념으로 풀 문제: ' + ' · '.join(links))
        for r in t['sources']:
            source = sources[r['source_id']]
            url = '../../' + quote(source['path'], safe='/')
            title = label(source['path'])
            if r.get('pdf_page'):
                url += f"#page={r['pdf_page']}"
                title += f" · PDF p{r['pdf_page']}"
            refs.append(f'[{title}]({url})')
        if refs:
            rows.append('출처: ' + ' · '.join(refs))
        # Supplementary redraw provenance is Markdown only as well.
        if t.get('md_notes'):
            rows.append(t['md_notes'])
        result[t['id']] = '\n\n'.join(rows)
    return result

def forbidden_note_metadata(html_text):
    from .html2md import Parser
    parser = Parser(); parser.feed(html_text)
    def text(node):
        return ''.join(c if isinstance(c, str) else text(c) for c in node.children
                       if isinstance(c, str) or c.tag not in {'script', 'style'})
    return ('이 개념으로 풀 문제' in text(parser.root)
            or re.search(r'출처\s*:', text(parser.root)) is not None
            or any('sources' in n.attrs.get('class', '').split() for n in parser.root.walk()))

def check_note_metadata(manifest, html_text, md_text):
    if manifest.get('note_presentation_version') != 2:
        return []
    errors = []
    if forbidden_note_metadata(html_text):
        errors.append('note metadata must not appear in HTML')
    expected = topic_metadata(manifest)
    for ident, metadata in expected.items():
        if not metadata:
            continue
        marker = f'<a id="{ident}"></a>'
        section = md_text.partition(marker)[2]
        section = re.split(r'\n<a id="[^"\n]+"></a>\n### ', section, maxsplit=1)[0]
        if metadata not in section:
            errors.append(ident + ': missing Markdown note metadata')
    return errors
