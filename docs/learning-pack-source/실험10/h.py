"""HTML helpers for note fragments and workbook entries."""
import html as _h
import re

# 표 열 배치 코드: 표를 쓸 때 열마다 역할을 직접 밝혀요. 머리글 이름으로 추측하지 않아요.
#   i 순번, n 입력 신호, c 제어 신호, m 중간 신호, o 출력 신호, b 출력 묶음(버스)
#   B 입력 묶음, T 조건 글, O 결과 글, t 설명 글
COLS = {
    'i': ('index', 'index', '순서'),
    'n': ('input', 'signal', '입력'),
    'c': ('control', 'signal', '제어'),
    'm': ('intermediate', 'signal', '중간'),
    'o': ('output', 'signal', '출력'),
    'b': ('output', 'bus', '출력'),
    'B': ('input', 'bus', '입력'),
    'T': ('input', 'text', '조건'),
    'O': ('output', 'text', '결과'),
    't': ('description', 'text', '설명'),
}


def esc(s):
    return _h.escape(s, quote=True)


def layer(kind, title, *body):
    return f'<div class="layer {kind}"><span class="layer-title">{title}</span>' + ''.join(body) + '</div>'


def p(t):
    return f'<p>{t}</p>'


def gist(t):
    """토픽 첫 레이어 제목 바로 다음의 결론 문단이에요. 첫 문장은 <strong> 으로 감싸요."""
    return f'<p class="gist">{t}</p>'


def tex(t):
    return f'<p>$${t}$$</p>'


def table(headers, rows, cols, cls='table-wrap', marks=None):
    """cols 는 열마다 COLS 코드 한 글자예요. build_run 이 data-l 을 읽어 표 배치로 옮기고 지워요.
    marks 는 {행 번호(0부터): 'compare'|'avoid'} 예요. 비교할 행·피할 행을 템플릿이 칠해요."""
    if len(cols) != len(headers):
        raise ValueError(f'cols {cols} for {headers}')
    marks = marks or {}
    if any(k >= len(rows) or v not in ('compare', 'avoid') for k, v in marks.items()):
        raise ValueError(f'marks {marks} for {len(rows)} rows')
    head = '<thead><tr>' + ''.join(f'<th>{c}</th>' for c in headers) + '</tr></thead>'
    row = lambda i: f'<tr data-row="{marks[i]}">' if i in marks else '<tr>'
    body = '<tbody>' + ''.join(row(i) + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for i, r in enumerate(rows)) + '</tbody>'
    return f'<div class="{cls}"><table data-l="{cols}">{head}{body}</table></div>'


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


TABLE = re.compile(r'<table data-l="([^"]+)">(.*?)</table>', re.S)
TH = re.compile(r'<th>(.*?)</th>', re.S)


def plain(s):
    return ' '.join(re.sub(r'<[^>]+>', '', s).split())


def pull_layouts(html_text, key_of):
    """HTML 의 data-l 표지를 지우고, 표 순서대로 배치 항목을 만들어요."""
    entries = []

    def one(m):
        cols, inner = m.group(1), m.group(2)
        headers = [plain(h) for h in TH.findall(inner)]
        meta = [COLS[c] for c in cols]
        columns = [dict(role=r, kind=k, group=g) for r, k, g in meta]
        bounds = [dict(left=i, kind='major') for i in range(len(meta) - 1) if meta[i][2] != meta[i + 1][2]]
        entries.append(dict(key=key_of(len(entries)), expected_headers=headers, columns=columns, boundaries=bounds))
        return f'<table>{inner}</table>'

    return TABLE.sub(one, html_text), entries
