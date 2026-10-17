"""v1 배포 PDF를 바꾸지 않고 검증된 엔진 넷의 벡터 부품만 얹어요."""
import base64, hashlib, json, sys
from pathlib import Path
from xml.sax.saxutils import escape
from figlib import Fig, render_png, sha

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'.claude/skills/breadboard-diagram/scripts'))
from render_breadboard import BreadboardRenderer, _input_jumper
from scripts.lab.review_pack.breadboard_template import template_png

def engine():
    b=BreadboardRenderer(board='v1');c=b.cols['left'];y=b.r_y
    b.draw_chip('74HC00',10);b.connect_jacks();b.bridge_rails(c['vcc'],c['mid_vcc'],35,kind='vcc');b.connect_power(10)
    for name,row in [('S',10),('E',11),('R',14)]:_input_jumper(b,c,row,name,'SR input')
    b.step_wire([(c['c'],y(11)),(c['c'],y(13))],'sig','E pin2 to pin4')
    b.step_wire([(c['b'],y(12)),(220,y(12)),(220,y(10)-40),(445,y(10)-40),(445,y(15)),(c['h'],y(15))],'mid','pin3 to pin9')
    b.step_wire([(c['c'],y(15)),(210,y(15)),(210,y(16)+45),(455,y(16)+45),(455,y(11)),(c['i'],y(11))],'mid','pin6 to pin13')
    b.step_wire([(c['g'],y(16)),(c['g'],y(12))],'sig','Q pin8 to pin12')
    b.step_wire([(c['h'],y(13)),(c['h'],y(14))],'sig','Qbar pin11 to pin10')
    b.verify()
    expected=[{1},{2,4},{5},{3,9},{6,13},{8,12},{10,11},{7},{14}]
    actual=[]
    for n in b.nets():
        pins={int(t.rsplit(' ',1)[1]) for t in n['labels'] if ' pin ' in t}
        if pins:actual.append(pins)
    assert sorted(map(sorted,actual))==sorted(map(sorted,expected))
    return b

def create(run,manifest):
    from quiz import BOARD,MAN,ref
    template=REPO/'강의노트/공지사항/Breadboard.pdf'
    manifest['sources']=[s for s in manifest['sources'] if s['id']!=BOARD]
    manifest['sources'].append(dict(id=BOARD,path=template.relative_to(REPO).as_posix(),sha256=sha(template),kind='notice',edition='current'))
    pid='q-qp-e06-board-01';png,w,h=template_png()
    head=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>v1 PDF Enable SR latch</title>'
    bg=f'<image x="0" y="0" width="{w}" height="{h}" href="data:image/png;base64,{base64.b64encode(png).decode()}"/>'
    b=engine()
    # 300dpi PDF 홀 중심을 측정했어요. JPG 격자는 엔진 검증에만 쓰고 이 대응으로 투영해요.
    # y: PDF 1행 711.8, 63행 3352.0. 각 열은 PDF에서 개별 측정한 중심이에요.
    xs=[(174,394),(190,433),(239,563),(256,606),(272,649),(288,692),(305,734),(354,862),(370,904),(386,948),(403,990),(419,1033),(468,1161),(484,1201)]
    def mx(x):
        for (a,u),(z,v) in zip(xs,xs[1:]):
            if a<=x<=z:return u+(x-a)*(v-u)/(z-a)
        a,u=xs[0] if x<xs[0][0] else xs[-1];return u+(x-a)*2.606
    def my(y):return 711.8+(y-272)*(3352.0-711.8)/(62*16.345)
    colors={'vcc':'#dc2626','gnd':'#1665ca','mid':'#b06a00','sig':'#16814e'}
    parts=[];mapped=[]
    def text(x,y,t,size=40):parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial" font-size="{size}" fill="#111">{escape(t)}</text>')
    # IC body and pins first, wires on top. Pin1 top left, DIP notch at top.
    l,r=mx(312),mx(347);top,bottom=my(b.r_y(10)-10),my(b.r_y(16)+10)
    parts.append(f'<rect x="{l}" y="{top}" width="{r-l}" height="{bottom-top}" rx="20" fill="#e9edf2" stroke="#111" stroke-width="6"/>')
    parts.append(f'<path d="M{(l+r)/2-20},{top} a20,20 0 0 0 40,0" fill="none" stroke="#111" stroke-width="6"/>')
    for pin in range(1,15):
        row=10+pin-1 if pin<=7 else 10+14-pin
        x=mx(305 if pin<=7 else 354);yy=my(b.r_y(row));edge=l if pin<=7 else r
        parts.append(f'<path d="M{x},{yy} H{edge}" stroke="#111" stroke-width="7"/>')
        text(x-42 if pin<=7 else x+9,yy-8,str(pin),30)
    parts.append(f'<text x="{(l+r)/2}" y="{(top+bottom)/2}" text-anchor="middle" transform="rotate(-90 {(l+r)/2} {(top+bottom)/2})" font-family="Arial" font-size="38">74HC00</text>')
    for k,pts,desc in b._segments:
        out=[]
        for x,y in pts:
            jack=b._jack_at(x,y)
            if jack:out.append((1083 if jack=='red' else 1936,400))
            else:out.append((mx(x),my(y)))
        col=colors[k];coords=' '.join(f'{x:.1f},{y:.1f}' for x,y in out)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="white" stroke-width="13" stroke-linejoin="round"/>')
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{col}" stroke-width="7" stroke-linejoin="round"/>')
        for x,y in (out[0],out[-1]):parts.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{col}"/>')
        mapped.append(dict(kind=k,description=desc,engine_points=pts,pdf_points=out))
    for name,row in [('S',10),('E',11),('R',14)]:text(260,my(b.r_y(row))+12,name,48)
    text(1048,my(b.r_y(16))+12,'Q',46);text(1048,my(b.r_y(13))+12,'Q\u2032',46)
    blanks=run/'figures/questions'/f'{pid}-blank';complete=run/'figures/solutions'/f'{pid}-complete'
    blanks.with_suffix('.svg').write_text(head+bg+'</svg>',encoding='utf-8');blanks.with_suffix('.png').write_bytes(png)
    complete.with_suffix('.svg').write_text(head+bg+''.join(parts)+'</svg>',encoding='utf-8')
    render_png(complete.with_suffix('.svg'),complete.with_suffix('.png'),100)
    # Independent schematic, logically identical to the manual p7, with gate pin numbers.
    f=Fig(760,440,'Enable SR latch given circuit')
    gates=[]
    for x,y,label in [(130,80,'1,2 -> 3'),(130,270,'4,5 -> 6'),(450,80,'9,10 -> 8'),(450,270,'12,13 -> 11')]:
        g=f.and_(x,y,bubble=True);gates.append(g);f.text(x,y-14,label,size=22)
    a,c,q,nq=gates
    for name,pt in [('S',a['ins'][0]),('E',a['ins'][1]),('E',c['ins'][0]),('R',c['ins'][1])]:
        f.text(35,pt[1]+7,name);f.line([(65,pt[1]),pt])
    f.line([a['out'],q['ins'][0]]);f.line([c['out'],nq['ins'][1]])
    f.line([q['out'],(650,q['out'][1])]);f.text(670,q['out'][1]+7,'Q')
    f.line([nq['out'],(650,nq['out'][1])]);f.text(670,nq['out'][1]+7,'Q\u2032')
    f.line([(620,q['out'][1]),(620,210),(410,210),nq['ins'][0]]);f.dot(620,q['out'][1])
    f.line([(600,nq['out'][1]),(600,390),(390,390),(390,q['ins'][1][1]),q['ins'][1]]);f.dot(600,nq['out'][1])
    stem=run/'figures/questions'/f'{pid}-circuit';stem.with_suffix('.svg').write_text(f.svg(physical=(55,55*440/760)),encoding='utf-8');render_png(stem.with_suffix('.svg'),stem.with_suffix('.png'),55)
    regpath=run/'figures/redraw-manifest.json';reg=json.loads(regpath.read_text(encoding='utf-8'))
    refs=[ref(7),dict(source_id=BOARD,pdf_page=1,printed_page=None)]
    for suffix,role,stem,ww,hh in [('blank','problem',blanks,100,100*h/w),('complete','solution',complete,100,100*h/w),('circuit','problem',stem,55,55*440/760)]:
        reg['figures'].append(dict(id=pid+'-'+suffix,question_id=pid,role=role,svg=stem.with_suffix('.svg').relative_to(run).as_posix(),png=stem.with_suffix('.png').relative_to(run).as_posix(),svg_sha256=sha(stem.with_suffix('.svg')),png_sha256=sha(stem.with_suffix('.png')),w_mm=ww,h_mm=hh,source_asset_ids=[],source_refs=refs,derivation=f'교안 PDF p7의 NAND 넷으로 자체 저작. v1 원본={template.relative_to(REPO).as_posix()}, sha256={sha(template)}, 300dpi 전체 페이지. PDF 좌표와 엔진 좌표 대응: figures/quiz-board-mapping.json. 원본 JPG는 검증 엔진 좌표계로만 사용.',answer_exposure='none' if role=='problem' else 'present',review_status='not_run',review_notes='시각 검토 대기; engine verify 및 pin nets 전수 대조 통과'))
    regpath.write_text(json.dumps(reg,ensure_ascii=False,indent=2),encoding='utf-8')
    (run/'figures/quiz-board-mapping.json').write_text(json.dumps(dict(columns=xs,y_first=711.8,y_last=3352,segments=mapped,nets=[dict(labels=sorted(n['labels']),rails=sorted(n['rails'])) for n in b.nets()]),ensure_ascii=False,indent=2),encoding='utf-8')
