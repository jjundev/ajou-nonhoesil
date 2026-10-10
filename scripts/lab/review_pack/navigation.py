"""The sidebar contains only the current document's contents."""
import html

from .html2md import Node


def navigation_items(root: Node, kind: str) -> list[dict[str, str]]:
    main = next((n for n in root.walk() if n.tag == 'main'), root)
    cls = 'topic' if kind == 'note' else 'card'
    def text(node):
        return ''.join(c if isinstance(c, str) else text(c) for c in node.children)
    items = []
    for node in main.walk():
        if node.tag != 'article' or cls not in node.attrs.get('class', '').split():
            continue
        title = next((n for n in node.walk() if n.tag == 'h3'), None)
        items.append({'id': node.attrs['id'], 'title': text(title).strip() if title else node.attrs['id']})
    return items


def render_navigation(names: dict[str, str], kind: str, items: list[dict] | None = None) -> dict[str, str]:
    if kind not in {'note', 'review'}:
        raise ValueError('Unknown navigation kind: ' + kind)
    links = []
    for item in items or []:
        id = html.escape(item['id'], quote=True)
        title = html.escape(item.get('title', item['id']))
        links.append(f'<li><a href="#{id}"><span class="toc-title">{title}</span></a></li>')
    return {'TOC': '<ol class="toc-list">' + ''.join(links) + '</ol>'}


def check_navigation(root: Node, expected_page: str) -> list[str]:
    errors = []
    if any(n.attrs.get('id') in {'progress-n', 'progress-total', 'progress-bar'} or
           'nav-label' in n.attrs.get('class', '').split() for n in root.walk()):
        errors.append('navigation: redundant sidebar heading or progress summary')
    if any(n.tag == 'nav' and 'pack-nav' in n.attrs.get('class', '').split() for n in root.walk()):
        errors.append('navigation: document navigation must not be in the sidebar')
    nodes = [n for n in root.walk() if n.tag == 'nav' and 'toc' in n.attrs.get('class', '').split()]
    if len(nodes) != 1:
        errors.append('navigation: expected one toc')
        return errors
    if nodes[0].attrs.get('aria-label') != '이 페이지 목차':
        errors.append('navigation: wrong toc label')
    lists = [n for n in nodes[0].children if isinstance(n, Node) and n.tag == 'ol' and n.attrs.get('class') == 'toc-list']
    if len(lists) != 1:
        errors.append('navigation: expected one flat topic list')
    ids = {n.attrs['id'] for n in root.walk() if 'id' in n.attrs}
    sections = [n for n in nodes[0].walk() if n.tag == 'a']
    articles = [n for n in root.walk() if n.tag == 'article' and
                any(c in n.attrs.get('class', '').split() for c in ('topic', 'card'))]
    if [n.attrs.get('href') for n in sections] != ['#'+n.attrs['id'] for n in articles]:
        errors.append('navigation: topic links must match article order')
    for link in sections:
        href = link.attrs.get('href', '')
        if not href.startswith('#') or href[1:] not in ids:
            errors.append('navigation: invalid in-page link: ' + href)
    return errors
