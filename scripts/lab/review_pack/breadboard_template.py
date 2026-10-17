"""Faithful 300 DPI rendering of the user-selected course v1 PDF form."""
import base64
from functools import lru_cache
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[3] / '강의노트/공지사항/Breadboard.pdf'


@lru_cache(maxsize=1)
def template_png():
    import pymupdf
    with pymupdf.open(TEMPLATE) as document:
        if len(document) != 1:
            raise ValueError('Breadboard v1 template must have one page')
        pix = document[0].get_pixmap(dpi=300, alpha=False)
        return pix.tobytes('png'), pix.width, pix.height


def is_template_image(node, svg):
    """Allow the exact original page, embedded once without geometry changes."""
    if any(n.tag.rsplit('}', 1)[-1] == 'image' for n in svg if n is not node):
        return False
    if node not in list(svg):
        return False
    png, width, height = template_png()
    expected = dict(x='0', y='0', width=str(width), height=str(height),
                    href='data:image/png;base64,'+base64.b64encode(png).decode())
    return node.attrib == expected and svg.get('viewBox') == f'0 0 {width} {height}'
