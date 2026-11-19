"""Standalone SVG presentation shared by the lab experiment notes."""

from base64 import b64encode
from functools import lru_cache
from io import BytesIO
from math import ceil
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

_SVG = '{http://www.w3.org/2000/svg}'
ET.register_namespace('', _SVG[1:-1])
_FONT = Path(__file__).resolve().parents[3] / (
    '.claude/skills/logic-lab-review-pack/assets/vendor/pretendard/Pretendard-SemiBold.woff2'
)
_SUBSET_FAMILY = 'Logic Lab Schematic'
_FIGURE_REF = re.compile(r'<img\b[^>]*\bsrc="\.pack/figures/([a-zA-Z0-9-]+\.svg)"[^>]*>')
_PRINT_STYLE = (
    '<style>@media print { .schematic-viewport { overflow: visible; } '
    '.schematic-viewport img { min-width: 0 !important; } }</style>'
)

# The existing Fig primitives use these colors for their symbols and wires.
_PALETTE = {
    '#fff': 'paper',
    '#18212e': 'ink',
    '#6b7585': 'muted',
    '#2674df': 'blue',
    '#e8f1ff': 'panel',
    '#c0392b': 'red',
    '#1e7d4f': 'green',
    '#b45309': 'amber',
}
_STYLE = """
:root {
  color-scheme: light dark;
  --paper: #ffffff; --ink: #18212e; --muted: #475569; --panel: #eaf2ff;
  --blue: #1658ac; --red: #ab2d20; --green: #176140; --amber: #8f4809;
}
@media (prefers-color-scheme: dark) {
  :root {
    --paper: #151d29; --ink: #e6eef8; --muted: #bac9dc; --panel: #263951;
    --blue: #8ec5ff; --red: #ffa697; --green: #85dcb4; --amber: #ffbf7f;
  }
}
.fig-paper { fill: var(--paper); }
.fig-ink { stroke: var(--ink); }
.fig-text, .fig-dot { fill: var(--ink); }
text { font-family: "Logic Lab Schematic"; font-weight: 600; font-style: normal; }
[data-node-color="blue"] { --node: var(--blue); }
[data-node-color="red"] { --node: var(--red); }
[data-node-color] { fill: var(--node); }
.fig-crossing { stroke: var(--paper); }
""" + ''.join(
    f'[data-{paint}="{color}"] {{ {paint}: var(--{color}); }}\n'
    for paint in ('fill', 'stroke')
    for color in _PALETTE.values()
)


@lru_cache(maxsize=32)
def _subset_font(font_path: Path, characters: str) -> str:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    options = subset.Options()
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=characters)
    with TTFont(font_path, recalcTimestamp=False) as font:
        subsetter.subset(font)
        # OFL reserves the original family name. Retain copyright and license records.
        names = font['name']
        for record in names.names:
            replacement = {
                1: _SUBSET_FAMILY, 3: f'{_SUBSET_FAMILY} SemiBold',
                4: f'{_SUBSET_FAMILY} SemiBold', 6: 'LogicLabSchematic-SemiBold',
                16: _SUBSET_FAMILY,
            }.get(record.nameID)
            if replacement:
                names.setName(replacement, record.nameID, record.platformID, record.platEncID, record.langID)
        buffer = BytesIO()
        font.save(buffer)
    return b64encode(buffer.getvalue()).decode('ascii')


def style_note_schematic(svg: str, *, font_path: Path) -> str:
    root = ET.fromstring(svg)
    root.attrib.pop('font-family', None)
    root.set('data-note-schematic', '1')
    labels = list(root.iter(_SVG + 'text'))
    characters = ''.join(sorted(set(''.join(''.join(label.itertext()) for label in labels))))
    font = _subset_font(font_path, characters)
    style = ET.Element(_SVG + 'style')
    style.text = (
        f'@font-face {{ font-family: "{_SUBSET_FAMILY}"; font-weight: 600; font-style: normal; '
        f'src: url(data:font/woff2;base64,{font}) format("woff2"); }}\n' + _STYLE
    )
    for element in root.iter():
        for paint in ('stroke', 'fill'):
            color = _PALETTE.get(element.get(paint))
            if color and not (paint == 'fill' and 'data-node-color' in element.attrib):
                element.set('data-' + paint, color)
    root.insert(0, ET.Element(_SVG + 'rect', width='100%', height='100%', attrib={'class': 'fig-paper'}))
    root.insert(0, style)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='unicode') + '\n'


class SchematicSymbols:
    """Semantic primitives that compose with the existing Fig geometry."""

    @staticmethod
    def _node_attributes(node, color):
        return f' data-node={quoteattr(node)} data-node-color={quoteattr(color)}' if node else ''

    def label(self, x, y, text, *, size=26, anchor='start', sub='', suffix='', super_='',
              node=None, color='blue'):
        markup = escape(text)
        if sub:
            markup += f'<tspan baseline-shift="sub" font-size="78%">{escape(sub)}</tspan>'
        if super_:
            markup += f'<tspan baseline-shift="super" font-size="78%">{escape(super_)}</tspan>'
        markup += escape(suffix)
        attributes = self._node_attributes(node, color)
        self.raw(f'<text class="fig-text" x="{x:g}" y="{y:g}" font-size="{size}"'
                 f' text-anchor="{anchor}"{attributes}>{markup}</text>')

    def junction(self, x, y, *, node=None, color='blue', radius=5):
        attributes = self._node_attributes(node, color)
        self.raw(f'<circle class="fig-dot" cx="{x:g}" cy="{y:g}" r="{radius:g}"{attributes}/>')

    def crossing(self, x, y, *, color='#18212e'):
        """A vertical wire passes over a horizontal wire with a visible gap."""
        self.raw(f'<path class="fig-crossing" d="M{x:g},{y - 9:g}v18" stroke-width="12"/>')
        self.line([(x, y - 9), (x, y + 9)], color=color)


def write_note_schematics(output_dir: Path, figures) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, figure in figures.items():
        path = output_dir / f'{name}.svg'
        path.write_text(style_note_schematic(figure.svg(), font_path=_FONT), encoding='utf-8')
        paths.append(path)
    return tuple(paths)


def add_schematic_viewports(html: str, figures_dir: Path) -> str:
    """Give wide note schematics a local horizontal viewport at readable scale."""
    def wrap(match):
        path = figures_dir / match[1]
        if not path.is_file():
            return match[0]
        with path.open(encoding='utf-8') as svg:
            opening_tag = svg.read(512).split('>', 1)[0] + '/>'
        if 'data-note-schematic="1"' not in opening_tag:
            return match[0]
        viewbox = ET.fromstring(opening_tag).get('viewBox')
        min_width = ceil(float(viewbox.split()[2]) * 0.72)
        image = match[0][:4] + (
            f' style="display:block;width:100%;min-width:{min_width}px;'
            'max-width:none;margin-inline:auto"'
        ) + match[0][4:]
        # .table-wrap is the template's horizontal scroll area, excluded from swipe navigation.
        return ('<div class="table-wrap schematic-viewport" tabindex="0" role="region" aria-label="회로도">'
                + image + '</div>')

    result = _FIGURE_REF.sub(wrap, html)
    return result.replace('</head>', _PRINT_STYLE + '\n</head>', 1) if result != html else html
