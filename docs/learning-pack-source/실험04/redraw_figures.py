"""Rebuild six original, static instructional SVGs without raster sources."""
from pathlib import Path
from html import escape

DEST = Path(__file__).parent/'figures'

class Drawing:
    def __init__(self, title, height=460):
        self.items = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 {height}" role="img">',
                      f'<title>{escape(title)}</title>',
                      '<style>text{font-family:Arial,"Malgun Gothic",sans-serif;font-size:24px;fill:#18212e} .wire{fill:none;stroke:#18212e;stroke-width:3;stroke-linejoin:round;stroke-linecap:round} .gate{fill:#fff;stroke:#18212e;stroke-width:3} .accent{fill:#e8f1ff;stroke:#2674df;stroke-width:3}</style>',
                      f'<rect width="640" height="{height}" rx="16" fill="#fff"/>']
    def text(self, x, y, value, anchor='start'):
        self.items.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}">{escape(value)}</text>')
    def wire(self, *points):
        self.items.append('<polyline class="wire" points="'+' '.join(f'{x},{y}' for x,y in points)+'"/>')
    def dot(self,x,y):
        self.items.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#18212e"/>')
    def gate(self,x,y,label,nand=False):
        self.items.append(f'<path class="gate" d="M{x},{y} h40 a35,35 0 0 1 0,70 h-40 z"/>')
        self.text(x+30,y+43,label,'middle')
        if nand:self.items.append(f'<circle class="gate" cx="{x+83}" cy="{y+35}" r="8"/>')
        return x+(91 if nand else 75),y+35
    def box(self,x,y,w,h,label,accent=False):
        self.items.append(f'<rect class="{"accent" if accent else "gate"}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')
        self.text(x+w/2,y+h/2+8,label,'middle')
    def save(self,name):
        DEST.mkdir(parents=True,exist_ok=True)
        (DEST/f'{name}.svg').write_text('\n'.join(self.items+['</svg>']),encoding='utf-8')

def mux2():
    d=Drawing('2×1 MUX: NOT 한 개와 AND 두 개, OR 한 개로 경로를 골라요')
    d.text(24,40,'2×1 MUX · Y = S′I0 + SI1')
    for y,data,control in [(110,'I0','S′'),(250,'I1','S')]:
        d.text(24,y+24,data);d.wire((60,y+16),(175,y+16))
        d.text(24,y+64,control);d.wire((60,y+54),(175,y+54))
        x,oy=d.gate(175,y,'&')
        d.wire((x,oy),(320,oy),(320,195 if y==110 else 235),(401.25,195 if y==110 else 235))
    # OR symbol: curved input side, pointed output side.
    d.items.append('<path class="gate" d="M390,175 Q420,215 390,255 Q455,255 475,215 Q455,175 390,175 Z"/>')
    d.text(430,223,'≥1','middle');d.wire((475,215),(580,215));d.text(590,223,'Y')
    d.text(24,400,'S');d.wire((55,392),(90,392))
    d.items.append('<path class="gate" d="M90,365 L90,419 L140,392 Z"/><circle class="gate" cx="148" cy="392" r="8"/>')
    d.wire((156,392),(205,392));d.text(215,400,'S′')
    d.text(320,400,'&: AND   ≥1: OR')
    d.save('mux2-gates')

def mux4():
    d=Drawing('활성 Low E를 갖는 NAND 기반 4×1 MUX',580)
    d.text(24,38,'4×1 MUX · E=0에서 동작해요')
    controls=['S1′ S0′','S1′ S0','S1 S0′','S1 S0']
    for k,y in enumerate([70,165,260,355]):
        d.text(24,y+23,f'I{k}, E′');d.text(24,y+56,controls[k])
        # Four separate inputs; named signals avoid ambiguous bus crossings.
        for offset in [10,27,44,61]:d.wire((160,y+offset),(205,y+offset))
        x,oy=d.gate(205,y,'&',True)
        lane=[380,355,355,380][k]
        d.wire((x,oy),(lane,oy),(lane,210+k*22),(430,210+k*22))
    d.items.append('<path class="gate" d="M430,190 h35 a65,65 0 0 1 0,130 h-35 z"/><circle class="gate" cx="538" cy="255" r="8"/>')
    d.text(465,263,'&','middle');d.wire((546,255),(585,255));d.text(595,263,'Y')
    d.text(24,475,'각 행의 네 입력을 모두 곱해요.')
    d.text(24,510,'입력 신호: S1, S0, E → NOT → S1′, S0′, E′')
    d.text(24,550,'E=1 → 앞 NAND 네 출력 1 → Y=0')
    d.save('mux4-enable')

def demux4():
    d=Drawing('1×4 DMUX: 각 주소의 AND 경로로 데이터를 보내요',560)
    d.text(24,38,'1×4 DMUX · 출력을 합치지 않아요')
    controls=['S1′ S0′','S1′ S0','S1 S0′','S1 S0']
    for k,y in enumerate([70,165,260,355]):
        d.text(24,y+24,'D');d.text(24,y+57,controls[k])
        for offset in [12,35,58]:d.wire((160,y+offset),(225,y+offset))
        x,oy=d.gate(225,y,'&');d.wire((x,oy),(475,oy));d.text(490,oy+8,f'Y{k}')
    d.text(24,470,'S1과 S0를 NOT에 넣어 보수를 만들어요.')
    d.text(24,510,'D=1, S1S0=10 → Y2=1, 나머지=0')
    d.text(24,546,'D=0 → Y0=Y1=Y2=Y3=0')
    d.save('demux4-gates')

def decoder():
    d=Drawing('디코더: 두 비트 주소를 네 선택 신호로 바꿔요',510)
    d.text(24,38,'2→4 디코더 · 활성 High 출력')
    d.text(24,160,'S1S0');d.wire((95,152),(160,152))
    d.box(160,80,170,220,'디코더',True)
    for k,y in enumerate([110,165,220,275]):
        d.wire((330,y),(410,y));d.text(425,y+8,f'C{k}')
    d.text(24,345,'주소 10 → C0,C1,C2,C3 = 0,0,1,0')
    d.text(24,390,'MUX: 각 Ck × Ik → 모두 OR → Y')
    d.text(24,435,'DMUX: 각 Ck × D → 출력 Yk')
    d.text(24,480,'DMUX에서 D=1로 고정하면 디코더예요.')
    d.save('decoder-routing')

def tristate():
    d=Drawing('활성 Low tri-state 버퍼 두 개를 공통 출력에 연결한 MUX',560)
    d.text(24,38,'Tri-state MUX · nOE=0에서 동작해요')
    for k,y,control in [(0,110,'S'),(1,300,'S′')]:
        d.text(24,y+48,f'I{k}');d.wire((65,y+40),(185,y+40))
        d.items.append(f'<path class="gate" d="M185,{y} L185,{y+80} L275,{y+40} Z"/>')
        d.items.append(f'<circle class="gate" cx="215" cy="{y+70}" r="8"/>')
        d.wire((215,y+78),(215,y+116));d.text(24,y+148,f'nOE{k} = {control}')
        d.wire((275,y+40),(445,y+40))
    d.wire((445,150),(445,340));d.dot(445,150);d.dot(445,340)
    d.wire((445,245),(580,245));d.dot(445,245);d.text(590,253,'Y')
    d.text(24,495,'S=0: I0를 보내요 / S=1: I1을 보내요')
    d.text(24,535,'꺼진 버퍼는 Z예요. Z는 논리 0이 아니에요.')
    d.save('tristate-bus')

def lab():
    d=Drawing('실험 조작 흐름: 입력과 선택선을 바꾸고 출력을 관찰해요',560)
    d.text(24,38,'입력을 바꾸고 예상값과 비교해요')
    d.text(24,85,'1-1 · MUX')
    d.box(24,110,170,75,'E=0',True);d.wire((194,147),(230,147))
    d.box(230,110,170,75,'주소 선택');d.wire((400,147),(436,147))
    d.box(436,110,180,75,'Y 관찰')
    d.text(24,225,'선택 입력 변경 → Y가 따라와요.')
    d.text(24,268,'비선택 입력 변경 → Y는 그대로예요.')
    d.text(24,325,'2-1 · DMUX')
    d.box(24,350,170,75,'D=1',True);d.wire((194,387),(230,387))
    d.box(230,350,170,75,'주소 선택');d.wire((400,387),(436,387))
    d.box(436,350,180,75,'Y0~Y3 관찰')
    d.text(24,475,'선택 출력 하나만 1이 돼요.')
    d.text(24,522,'D=0으로 바꾸면 네 출력이 모두 0이에요.')
    d.save('lab-signal-flow')

if __name__=='__main__':
    for draw in (mux2,mux4,demux4,decoder,tristate,lab):draw()
