"""Wrap whole tables while preserving cells, blanks, and authored markup."""
from .equation_cards import _CardBlocks


class _Tables(_CardBlocks):
    card_class = 'table-card'

    def should_wrap(self, tag, source):
        return tag == 'table' and sum(row[0] == 'table' for row in self.stack) == 1


def separate_tables(source: str) -> str:
    parser = _Tables(source); parser.feed(source)
    for start, end in reversed(parser.ranges):
        source = (source[:start] + '<div class="table-card" role="group" aria-label="표">'
                  + source[start:end] + '</div>' + source[end:])
    return source
