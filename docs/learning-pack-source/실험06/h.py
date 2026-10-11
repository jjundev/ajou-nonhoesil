"""HTML helpers for note fragments and workbook entries."""
import html as _h


def esc(s):
    return _h.escape(s, quote=True)


def layer(kind, title, *body):
    return f'<div class="layer {kind}"><span class="layer-title">{title}</span>' + ''.join(body) + '</div>'


def p(t):
    return f'<p>{t}</p>'


def tex(t):
    return f'<p>$${t}$$</p>'


def table(headers, rows, cls='table-wrap'):
    head = '<thead><tr>' + ''.join(f'<th>{c}</th>' for c in headers) + '</tr></thead>'
    body = '<tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + '</tbody>'
    return f'<div class="{cls}"><table>{head}{body}</table></div>'


def fig(src, alt, cap):
    return f'<figure class="figure"><img src="{src}" alt="{esc(alt)}"><figcaption>{cap}</figcaption></figure>'


def hint(t):
    return f'<details class="hint"><summary>힌트</summary>{t}</details>'


def sol(t):
    return f'<details class="solution"><summary>연습 답</summary>{t}</details>'


def ul(items):
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def sumd(t):
    return f'<div class="sum" hidden>{t}</div>'
