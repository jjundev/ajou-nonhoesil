"""실험설명 읽기 방식 v1 검사.

manifest.note_reading_version=1 인 팩만 검사한다. 핵심을 빨리 찾게 하는 약속이다.
- 토픽 첫 레이어는 제목 바로 다음에 굵은 결론 문장(p.gist 안 <strong>)을 둔다.
- 레이어 제목은 내용을 말한다. 절차만 말하는 범용 제목은 쓰지 않는다.
- 행 수를 세거나 표를 외우지 말라는 군말 문장을 쓰지 않는다.
- 표 행 강조는 tr[data-row] 의 compare(비교할 행)·avoid(피할 행)만 쓰고, 비교 행은 두 개 이상이다.
"""
from .html2md import Node, Parser

GENERIC_TITLES = (
    '새 이름부터 알아봐요',
    '한눈에 보기',
    '작은 예부터 살펴봐요',
    '조건과 작동 원리를 확인해요',
    '헷갈리기 쉬운 것',
    '헷갈리기 쉬운 말',
)
FILLER = ('줄로 기억하면 충분해요', '외울 필요 없고')
ROW_MARKS = {'compare', 'avoid'}


def _text(node):
    return ''.join(c if isinstance(c, str) else _text(c) for c in node.children)


def _classes(node):
    return node.attrs.get('class', '').split()


def _elements(node):
    return [c for c in node.children if isinstance(c, Node)]


def reading_structure_errors(topic_id, html_text):
    parser = Parser()
    parser.feed(html_text)
    root = parser.root
    layers = [n for n in _elements(root) if n.tag == 'div' and 'layer' in _classes(n)]
    if not layers:
        return [topic_id + ': topic needs div.layer']
    first = _elements(layers[0])
    if (len(first) < 2 or 'layer-title' not in _classes(first[0])
            or first[1].tag != 'p' or 'gist' not in _classes(first[1])
            or not any(n.tag == 'strong' and _text(n).strip() for n in first[1].walk())):
        return [topic_id + ': first layer needs p.gist with <strong> right after its title']
    for layer in layers:
        title = next((_text(n).strip() for n in _elements(layer) if 'layer-title' in _classes(n)), '')
        if title in GENERIC_TITLES:
            return [topic_id + ': generic layer title ' + repr(title)]
    body = _text(root)
    for phrase in FILLER:
        if phrase in body:
            return [topic_id + ': filler sentence ' + repr(phrase)]
    for table in (n for n in root.walk() if n.tag == 'table'):
        marks = [n.attrs['data-row'] for n in table.walk() if n.tag == 'tr' and 'data-row' in n.attrs]
        if bad := [m for m in marks if m not in ROW_MARKS]:
            return [topic_id + ': unknown data-row ' + repr(bad[0])]
        if marks.count('compare') == 1:
            return [topic_id + ': data-row="compare" needs two or more rows in one table']
    return []
