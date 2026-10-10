"""Separate standalone equations without changing their text or source markup."""
from html.parser import HTMLParser
import re
from .html2md import Parser


def standalone_equation(source: str) -> bool:
    parser = Parser(); parser.feed(source)
    if any(n.tag in {'img', 'svg', 'table', 'a', 'code'} for n in parser.root.walk()):
        return False
    def text(node):
        return ''.join(c if isinstance(c, str) else text(c) for c in node.children)
    value = text(parser.root).strip()
    if re.fullmatch(r'\$\$[\s\S]+\$\$|\$[^$]+\$|\\\[[\s\S]+\\\]|\\\([\s\S]+\\\)', value):
        return True
    # Plain Boolean/numeric equations: exclude prose, preserving equation numbers.
    return bool('=' in value and re.search(r'[A-Za-z0-9]', value)
                and not re.search(r'[가-힣]|[A-Za-z]{4,}', value))


class _CardBlocks(HTMLParser):
    card_class = 'equation-card'

    def should_wrap(self, tag, source):
        return tag == 'p' and standalone_equation(source)

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0]
        for match in re.finditer('\n', source):
            self.lines.append(match.end())
        self.stack = []
        self.ranges = []

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag in {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr'}:
            return
        inside = any(row[2] for row in self.stack)
        card = self.card_class in dict(attrs).get('class', '').split()
        self.stack.append((tag, self.source_offset(), inside or card))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                _, start, inside_card = self.stack[i]
                if not inside_card:
                    end = self.source.index('>', self.source_offset()) + 1
                    if self.should_wrap(tag, self.source[start:end]):
                        self.ranges.append((start, end))
                del self.stack[i:]
                break


def separate_equations(source: str) -> str:
    parser = _CardBlocks(source); parser.feed(source)
    for start, end in reversed(parser.ranges):
        source = (source[:start] + '<div class="equation-card" role="group" aria-label="수식">'
                  + source[start:end] + '</div>' + source[end:])
    return source
