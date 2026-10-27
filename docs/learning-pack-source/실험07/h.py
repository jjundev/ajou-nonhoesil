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


def sumparts(rules, why=None, traps=()):
    """요약 세 칸: rules 는 (조건, 결과) 목록, why 는 1~2문장, traps 는 주의 목록."""
    out = '<p class="sum-label">외울 규칙</p><ul class="sum-rules">' + ''.join(f'<li><b>{c}</b> → {r}</li>' for c, r in rules) + '</ul>'
    if why:
        out += f'<p class="sum-label">이유</p><p class="sum-why">{why}</p>'
    if traps:
        out += '<p class="sum-label sum-label-warn">헷갈리지 마요</p><ul class="sum-traps">' + ''.join(f'<li>{t}</li>' for t in traps) + '</ul>'
    return f'<div class="sum" hidden>{out}</div>'
