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
        # md 는 자료 폴더 안에 있으므로 루트 기준으로 만든 기대값도 같은 기준으로 옮겨 비교한다.
        from .pack_md import to_data_frame
        if to_data_frame(metadata) not in section:
            errors.append(ident + ': missing Markdown note metadata')
    return errors

# 요약 칸은 이 순서로만 온다. 외울 규칙은 반드시, 이유·헷갈리지 마요는 비면 뺀다.
SUMMARY_PARTS = (('외울 규칙', 'sum-rules', 'ul'), ('이유', 'sum-why', 'p'), ('헷갈리지 마요', 'sum-traps', 'ul'))

def summary_structure_errors(topic_id, html_text):
    from .html2md import Parser, Node
    parser = Parser(); parser.feed(html_text)
    def text(node):
        return ''.join(c if isinstance(c, str) else text(c) for c in node.children)
    def classes(node):
        return node.attrs.get('class', '').split()
    sums = [n for n in parser.root.children if isinstance(n, Node) and 'sum' in classes(n)]
    if len(sums) != 1:
        return [topic_id + ': summary needs one direct div.sum']
    kids = [c for c in sums[0].children if isinstance(c, Node)]
    if any(isinstance(c, str) and c.strip() for c in sums[0].children):
        return [topic_id + ': summary text must sit inside its parts']
    if len(kids) % 2:
        return [topic_id + ': summary parts must be label + body pairs']
    seen = []
    for label, body in zip(kids[::2], kids[1::2]):
        part = next((x for x in SUMMARY_PARTS if x[0] == text(label).strip()), None)
        if label.tag != 'p' or 'sum-label' not in classes(label) or part is None:
            return [topic_id + ': unknown summary label ' + repr(text(label).strip())]
        name, cls, tag = part
        if body.tag != tag or cls not in classes(body) or not text(body).strip():
            return [topic_id + f': {name} needs {tag}.{cls}']
        if tag == 'ul' and (not any(n.tag == 'li' and text(n).strip() for n in body.children if isinstance(n, Node))
                            or any(isinstance(n, Node) and n.tag != 'li' for n in body.children)):
            return [topic_id + f': {name} needs li items']
        if ('sum-label-warn' in classes(label)) != (cls == 'sum-traps'):
            return [topic_id + ': only 헷갈리지 마요 label is sum-label-warn']
        seen.append(name)
    order = [x[0] for x in SUMMARY_PARTS]
    if not seen or seen[0] != '외울 규칙':
        return [topic_id + ': summary needs sum-rules first']
    if seen != sorted(set(seen), key=order.index):
        return [topic_id + ': summary parts out of order or repeated']
    return []
