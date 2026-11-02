"""Small schematic drawing library for the 실험06 review pack (own drawings)."""
from xml.sax.saxutils import escape
import hashlib, struct
from pathlib import Path

INK = '#18212e'
BLUE = '#2674df'
BLUEBG = '#e8f1ff'
RED = '#c0392b'
GRN = '#1e7d4f'
GREY = '#6b7585'


class Fig:
    def __init__(self, w, h, title, desc=''):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.parts = []

    def raw(self, s):
        self.parts.append(s)

    def text(self, x, y, t, size=22, anchor='start', fill=INK, weight=None):
        w = f' font-weight="{weight}"' if weight else ''
        self.parts.append(f'<text x="{x:g}" y="{y:g}" font-size="{size}" text-anchor="{anchor}" fill="{fill}"{w}>{escape(t)}</text>')

    def line(self, pts, color=INK, width=3, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        p = ' '.join(f'{x:g},{y:g}' for x, y in pts)
        self.parts.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{d}/>')

    def dot(self, x, y, r=5.5, color=INK):
        self.parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r}" fill="{color}"/>')

    def rect(self, x, y, w, h, fill='#fff', stroke=INK, rx=8, sw=3):
        self.parts.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def circle(self, x, y, r, fill='#fff', stroke=INK, sw=3):
        self.parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def path(self, d, fill='#fff', stroke=INK, sw=3):
        self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')

    # ---- gates -------------------------------------------------------
    def and_(self, x, y, n=2, bubble=False, H=None, label='&', fill='#fff'):
        H = H or max(64, 28 * n + 10)
        fw = 26
        rx = H / 2
        self.path(f'M{x:g},{y:g} h{fw} a{rx:g},{H/2:g} 0 0 1 0,{H:g} h{-fw} z', fill=fill)
        ox = x + fw + rx
        oy = y + H / 2
        self.text(x + (fw + rx) / 2 - 2, oy + 8, label, size=22, anchor='middle', fill=GREY)
        if bubble:
            self.circle(ox + 7, oy, 7)
            ox += 14
        ins = [(x, y + H * (i + 1) / (n + 1)) for i in range(n)]
        return dict(ins=ins, out=(ox, oy), H=H)

    def or_(self, x, y, n=2, H=None, label='≥1'):
        H = H or max(64, 28 * n + 10)
        W = 92
        self.path(f'M{x:g},{y:g} Q{x+26:g},{y+H/2:g} {x:g},{y+H:g} C{x+45:g},{y+H:g} {x+75:g},{y+H*0.85:g} {x+W:g},{y+H/2:g} '
                  f'C{x+75:g},{y+H*0.15:g} {x+45:g},{y:g} {x:g},{y:g} Z')
        self.text(x + 48, y + H / 2 + 8, label, size=20, anchor='middle', fill=GREY)
        ins = []
        for i in range(n):
            f = (i + 1) / (n + 1)
            ins.append((x + 52 * f * (1 - f), y + H * f))
        return dict(ins=ins, out=(x + W, y + H / 2), H=H)

    def not_(self, x, y, H=44):
        W = 46
        self.path(f'M{x:g},{y:g} L{x:g},{y+H:g} L{x+W:g},{y+H/2:g} Z')
        self.circle(x + W + 7, y + H / 2, 7)
        return dict(ins=[(x, y + H / 2)], out=(x + W + 14, y + H / 2), H=H)

    def switch(self, x, y, label, color=INK):
        """Simple SPDT-style input switch ending at (x+70,y)."""
        self.circle(x, y - 22, 5)
        self.circle(x, y + 22, 5)
        self.circle(x + 40, y, 5)
        self.line([(x + 5, y - 22), (x + 36, y - 2)], color=color)
        self.line([(x + 45, y), (x + 74, y)])
        self.text(x - 12, y - 18, 'VCC', size=18, anchor='end', fill=GREY)
        self.text(x - 12, y + 30, 'GND', size=18, anchor='end', fill=GREY)
        self.text(x + 64, y - 14, label, size=22, anchor='end', fill=color, weight='bold')
        return (x + 74, y)

    def led(self, x, y, label):
        """Output LED symbol from (x,y) rightward: resistor, LED, ground."""
        self.line([(x, y), (x + 20, y)])
        self.path(f'M{x+20:g},{y:g} l8,-12 l12,24 l12,-24 l12,24 l8,-12', fill='none')
        self.line([(x + 60, y), (x + 82, y)])
        self.path(f'M{x+82:g},{y-14:g} L{x+82:g},{y+14:g} L{x+104:g},{y:g} Z', fill=BLUEBG, stroke=BLUE)
        self.line([(x + 104, y - 14), (x + 104, y + 14)], color=BLUE)
        self.line([(x + 104, y), (x + 128, y), (x + 128, y + 26)])
        self.line([(x + 116, y + 26), (x + 140, y + 26)])
        self.line([(x + 121, y + 32), (x + 135, y + 32)])
        self.text(x + 112, y - 24, label, size=22, anchor='middle', fill=BLUE, weight='bold')
        return (x + 140, y)

    def svg(self, physical=None, bg='#fff'):
        size = ''
        if physical:
            size = f' width="{physical[0]:g}mm" height="{physical[1]:g}mm"'
        head = (f'<svg xmlns="http://www.w3.org/2000/svg"{size} viewBox="0 0 {self.w:g} {self.h:g}" role="img" '
                f'font-family="Arial, \'Malgun Gothic\', sans-serif">')
        desc = f'<desc>{escape(self.desc)}</desc>' if self.desc else ''
        return (head + f'<title>{escape(self.title)}</title>' + desc +
                f'<rect width="{self.w:g}" height="{self.h:g}" fill="{bg}"/>' + ''.join(self.parts) + '</svg>')


def render_png(svg_path, png_path, w_mm, dpi=300):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    svg = Path(svg_path).read_text(encoding='utf-8')
    import re
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    px_w = round(w_mm / 25.4 * dpi)
    px_h = round(px_w * vb[3] / vb[2])
    html = ('<html><body style="margin:0;background:#fff">' +
            re.sub(r'<svg ', f'<svg style="display:block" ', re.sub(r' width="[^"]*mm" height="[^"]*mm"', f' width="{px_w}" height="{px_h}"', svg, count=1), count=1) +
            '</body></html>')
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport=dict(width=px_w, height=px_h), device_scale_factor=1)
        pg.set_content(html)
        pg.screenshot(path=str(png_path), clip=dict(x=0, y=0, width=px_w, height=px_h))
        b.close()
    im = Image.open(png_path).convert('RGB')
    im.save(png_path, dpi=(dpi, dpi))
    return im.size


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
