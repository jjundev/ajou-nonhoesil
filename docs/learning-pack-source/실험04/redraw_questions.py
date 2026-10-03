"""Directly authored schematics; source scans are only provenance, never pixels."""
from pathlib import Path
from html import escape
import hashlib
import json
import pymupdf as fitz

ROOT=Path(__file__).parent

class Drawing:
    def __init__(self,title):
        self.title=title;self.parts=[]
    def text(self,x,y,text,size=26,anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="Arial" fill="#222" font-size="{size}" text-anchor="{anchor}">{escape(text)}</text>')
    def wire(self,*pts):
        self.parts.append('<polyline class="wire" points="'+' '.join(f'{x:g},{y:g}' for x,y in pts)+'"/>')
    def dot(self,x,y): self.parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#222"/>')
    def box(self,x,y,w,h): self.parts.append(f'<rect class="gate" x="{x}" y="{y}" width="{w}" height="{h}"/>')
    def inv(self,x,y,input_name,output_name,ref='NOT'):
        self.text(x-8,y-35,ref,20)
        self.wire((x-75,y),(x,y));self.text(x-80,y-10,input_name,24)
        self.parts.append(f'<path class="gate" d="M{x},{y-25} L{x},{y+25} L{x+50},{y} Z"/><circle class="gate" cx="{x+58}" cy="{y}" r="8"/>')
        self.wire((x+66,y),(x+120,y));self.text(x+125,y+8,output_name,24)
    def and_gate(self,x,y,inputs,*,nand=False,ref='AND',height=80):
        r=height/2
        self.parts.append(f'<path class="gate" d="M{x},{y} h50 a{r},{r} 0 0 1 0,{height} h-50 Z"/>')
        self.text(x+38,y+r+9,'&',26,'middle');self.text(x,y-4,ref,20)
        for i,signal in enumerate(inputs):
            iy=y+height*(i+0.5)/len(inputs)
            self.wire((x-70,iy),(x,iy));self.text(x-85,iy+7,signal,24,'end')
        ox=x+50+r;oy=y+r
        if nand:
            self.parts.append(f'<circle class="gate" cx="{ox+8}" cy="{oy}" r="8"/>'); ox+=16
        return ox,oy
    def or_gate(self,x,y,height=120):
        self.parts.append(f'<path class="gate" d="M{x},{y} Q{x+50},{y+height/2} {x},{y+height} Q{x+110},{y+height} {x+150},{y+height/2} Q{x+110},{y} {x},{y} Z"/>')
        self.text(x+72,y+height/2+9,'OR',24,'middle')
        return x+150,y+height/2
    def buffer(self,x,y,*,given=False,ref='74HC125'):
        self.parts.append(f'<path class="gate" d="M{x},{y} L{x},{y+120} L{x+130},{y+60} Z"/>')
        self.text(x,y-20,ref,24)
        self.parts.append(f'<circle class="gate" cx="{x+42}" cy="{y+100}" r="8"/>')
        self.wire((x+42,y+108),(x+42,y+155))
        if given:
            self.wire((x-170,y+60),(x,y+60));self.text(x-170,y+45,'A',28)
            self.wire((x+130,y+60),(x+300,y+60));self.text(x+300,y+45,'B',28)
            self.text(x-20,y+47,'2',22);self.text(x+140,y+47,'3',22)
            self.text(x+58,y+145,'1',22);self.text(x+42,y+190,'nOE',28,'middle')
        return x+130,y+60
    def save(self,relative):
        path=ROOT/relative;path.parent.mkdir(parents=True,exist_ok=True)
        self.text(30,575,'Same signal label = same connected net.',20)
        # MuPDF's SVG reader does not apply class styles. Keep explicit paint
        # attributes so the PNG and browser vector show the same connections.
        body='\n'.join(self.parts).replace('class="wire"','class="wire" fill="none" stroke="#222" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"')
        body=body.replace('class="gate"','class="gate" fill="white" stroke="#222" stroke-width="3"')
        svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="140mm" height="84mm" viewBox="0 0 1000 600" role="img">'
             f'<title>{escape(self.title)}</title><style>text{{font-family:Arial,sans-serif;fill:#222}}'
             '.wire{fill:none;stroke:#222;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}'
             '.gate{fill:white;stroke:#222;stroke-width:3}</style><rect width="1000" height="600" fill="white"/>'+body+'</svg>')
        path.write_text(svg,encoding='utf-8',newline='\n')
        with fitz.open(stream=svg.encode('utf-8'),filetype='svg') as image:
            with fitz.open(stream=image.convert_to_pdf(),filetype='pdf') as pdf:
                pdf[0].get_pixmap(matrix=fitz.Matrix(300/72,300/72),alpha=False).save(path.with_suffix('.png'))
        return path

def mux2(graded=False):
    signal='Sel' if graded else 'S';a,b=('X0','X1') if graded else ('I0','I1')
    d=Drawing('지정 게이트로 구성한 2×1 MUX 완성 회로')
    d.text(30,38,'2 x 1 MUX',32)
    for y,inputs,target in [(125,[a,signal+"'"],225),(305,[b,signal],275)]:
        ox,oy=d.and_gate(300,y,inputs)
        lane=520
        # Match the curved input boundary of the OR symbol.
        t=(target-190)/120;edge=730+100*t*(1-t)
        d.wire((ox,oy),(lane,oy),(lane,target),(edge,target))
    ox,oy=d.or_gate(730,190)
    d.wire((ox,oy),(950,oy));d.text(965,oy+8,'Y')
    d.inv(270,490,signal,signal+"'")
    return d

def demux2():
    d=Drawing('1×2 DMUX의 독립된 두 출력')
    d.text(30,38,'1 x 2 DMUX',32)
    for y,control,out in [(125,"S'",'Y0'),(305,'S','Y1')]:
        x,oy=d.and_gate(360,y,['D',control]);d.wire((x,oy),(800,oy));d.text(820,oy+8,out,28)
    d.inv(280,490,'S',"S'")
    return d

def mux4(given=False):
    d=Drawing('활성 Low enable을 갖는 원문 NAND 기반 4×1 MUX' if given else '지정 게이트로 설계한 4×1 MUX')
    d.text(30,34,'4 x 1 MUX / '+('74HC20 NAND network' if given else '2 NOT / 4 AND / 1 OR'),28)
    if given:
        targets=[240,280,320,360]
        for k,y in enumerate([70,175,280,385]):
            s1="S1'" if k<2 else 'S1';s0="S0'" if k%2==0 else 'S0'
            ref=['U1A','U1B','U2A','U2B'][k]+' 74HC20'
            ox,oy=d.and_gate(370,y,[f'D{k}',s0,s1,"E'"],nand=True,ref=ref)
            lane=[620,580,580,620][k];target=targets[k]
            d.wire((ox,oy),(lane,oy),(lane,target),(770,target))
        ox,oy=d.and_gate(770,220,['','','',''],nand=True,ref='U3A 74HC20',height=160)
        d.wire((ox,oy),(965,oy));d.text(970,oy+8,'Y',24)
        for x,signal,ref in [(115,'S0','U4A'),(420,'S1','U4B'),(745,'E','U4C')]:
            d.inv(x,515,signal,signal+"'",ref+' 74HC04')
        d.text(30,555,'Input block: +5 V / GND',20)
    else:
        for k,y in enumerate([70,175,280,385]):
            s1="S1'" if k<2 else 'S1';s0="S0'" if k%2==0 else 'S0'
            ox,oy=d.and_gate(370,y,[f'I{k}',s1,s0],ref='AND '+str(k))
            target=[240,280,320,360][k];t=(target-210)/180;edge=760+100*t*(1-t)
            lane=[620,580,580,620][k]
            d.wire((ox,oy),(lane,oy),(lane,target),(edge,target))
        ox,oy=d.or_gate(760,210,180);d.wire((ox,oy),(950,oy));d.text(960,oy+8,'Y')
        d.inv(250,520,'S1',"S1'");d.inv(650,520,'S0',"S0'")
    return d

def mux4_block():
    d=Drawing('원문 4×1 MUX의 블록도: 내부 회로는 설계할 부분')
    d.text(30,38,'4 x 1 MUX / given block',30);d.box(400,100,230,340)
    d.text(515,205,'4 x 1',36,'middle');d.text(515,250,'MUX',36,'middle')
    for k,y in enumerate([140,220,300,380]):
        d.text(210,y+8,f'I{k}',30);d.wire((260,y),(400,y));d.text(420,y+8,str(k),26)
    d.wire((630,270),(850,270));d.text(865,278,'Y',30)
    for x,name in [(460,'S1'),(570,'S0')]:
        d.wire((x,440),(x,520));d.text(x,550,name,30,'middle')
    return d

def tristate(given=False):
    d=Drawing('원문 74HC125의 A/nOE/B와 활성 Low 제어' if given else '활성 Low 버퍼 두 개와 NOT으로 구성한 MUX')
    d.text(30,38,'74HC125 / active LOW nOE',30)
    if given:
        d.buffer(420,175,given=True,ref='U1A 74HC125')
    else:
        for k,y in [(0,85),(1,290)]:
            ox,oy=d.buffer(380,y,ref=f'Buffer {k} / 74HC125')
            d.wire((200,oy),(380,oy));d.text(170,oy+8,f'I{k}',26,'end')
            d.wire((ox,oy),(790,oy))
            d.text(470,y+140,f'nOE{k} = '+('S' if k==0 else "S'"),25)
        d.wire((790,145),(790,350));d.dot(790,145);d.dot(790,350)
        d.dot(790,247);d.wire((790,247),(935,247));d.text(950,255,'Y',28)
        d.inv(215,510,'S',"S'")
    return d

def decoder():
    d=Drawing('디코더의 선택 신호로 MUX와 DMUX 데이터 경로를 구성')
    d.text(30,38,'Decoder -> selected data path',30)
    for y,label in [(140,'MUX'),(350,'DMUX')]:
        d.box(180,y-60,190,120);d.text(275,y+8,'Decoder',26,'middle')
        d.text(30,y+8,'S1 S0',24);d.wire((120,y),(180,y))
        d.wire((370,y),(510,y),(510,y-20),(580,y-20));d.text(400,y-15,'Ck',24)
        ox,oy=d.and_gate(580,y-40,['Ck','Ik' if label=='MUX' else 'D'])
        d.wire((ox,oy),(760,oy));d.text(580,y-72,label,28)
        if label=='MUX':
            d.box(760,y-45,160,90);d.text(840,y+8,'OR all k',24,'middle');d.text(945,y+8,'Y',24)
            d.wire((920,y),(935,y))
        else: d.text(780,y+8,'Yk',28)
    d.text(60,520,'D = 1: DMUX outputs are decoder outputs.',24)
    return d

def main():
    manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    old_path=ROOT/'figures/redraw-manifest.json'
    old=json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {'figures':[]}
    old={f['id']:f for f in old['figures']}
    specs=[('q-mux4','problem',mux4(True),'a-s03-p1-o-s03-q2'),
           ('q-design4','problem',mux4_block(),'a-s07-p1-o-s07-q5'),
           ('q-tri','problem',tristate(True),'a-s03-p1-o-s03-q3'),
           ('q-mux2','solution',mux2(),None),('q-demux2','solution',demux2(),None),
           ('q-design4','solution',mux4(),None),('q-decoder','solution',decoder(),None),
           ('q-tri','solution',tristate(),None),('q-mux2-graded','solution',mux2(True),None)]
    records=[]
    questions={p['id']:p for p in manifest['problems']}
    for ident,role,drawing,asset in specs:
        suffix='given' if role=='problem' else 'solution'
        folder='questions' if role=='problem' else 'solutions'
        relative=f'figures/{folder}/{ident}-{suffix}-01.svg';svg=drawing.save(relative);png=svg.with_suffix('.png')
        row=dict(id=ident+'-'+suffix+'-01',question_id=ident,role=role,svg=relative,
            png=png.relative_to(ROOT).as_posix(),svg_sha256=hashlib.sha256(svg.read_bytes()).hexdigest(),
            png_sha256=hashlib.sha256(png.read_bytes()).hexdigest(),w_mm=140.0,h_mm=84.0,
            source_asset_ids=[asset] if asset else [],source_refs=questions[ident]['sources'],
            derivation='원문에서 읽은 논리 조건을 직접 도식화했어요. 같은 신호 이름은 같은 연결 노드예요.' if role=='problem' else '문제 조건에서 도출한 완성 회로예요. 같은 신호 이름은 같은 연결 노드예요.',
            answer_exposure='none' if role=='problem' else 'present',review_status='not_run',review_notes='원문·배선 시각 대조 전')
        prior=old.get(row['id'])
        if prior and all(prior.get(k)==row[k] for k in ('svg_sha256','png_sha256','source_refs','source_asset_ids','role','answer_exposure')):
            row['review_status']=prior['review_status'];row['review_notes']=prior['review_notes']
        records.append(row)
    old_path.write_text(json.dumps(dict(schema_version=1,figures=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Redrawn diagrams: {len(records)} SVG / {len(records)} PNG')

if __name__=='__main__': main()
