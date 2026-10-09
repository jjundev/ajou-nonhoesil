"""Workbook page defects that must stop one problem before any paid request."""
from pathlib import Path
import re,unicodedata
from .page_layout import page_layout
RAW_LATEX=re.compile(r'\$[^$\n]*\\[A-Za-z]|\$[A-Za-z]+_\{')
def _panel_right(page):
    panels=[d['rect'] for d in page.get_drawings() if d.get('fill') and
        max(abs(a-b) for a,b in zip(d['fill'],(246/255,246/255,243/255)))<.002]
    return max(panels,key=lambda r:r.get_area()).x1 if panels else 286
def input_defects(pdf,page_index):
    import fitz
    defects=[]
    with fitz.open(Path(pdf)) as doc:
        page=doc[page_index]; text=unicodedata.normalize('NFC',page.get_text())
        m=RAW_LATEX.search(text)
        if m: defects.append({'code':'raw_latex','detail':m[0][:60]})
        right=_panel_right(page)
        # The '답' label block opens the answer box; a solution figure must end above it.
        answer=[b[1] for b in page.get_text('blocks') if b[0]>=right and unicodedata.normalize('NFC',b[4]).strip().splitlines()[:1]==['답']]
        limit=min(answer) if answer else page_layout(page.rect.width,page.rect.height)['body_bottom']
        for info in page.get_image_info():
            x0,y0,x1,y1=info['bbox']
            if x0>=right and y1>limit+.5:
                defects.append({'code':'clipped_figure','detail':'image bottom %.1f below answer top %.1f'%(y1,limit)}); break
    return defects
