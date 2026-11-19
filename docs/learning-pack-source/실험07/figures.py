"""교안 회로를 직접 그린 벡터 원고와 300dpi 워크북 그림."""
from figlib import Fig,render_png,sha
from pathlib import Path
import json,base64,sys
REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'.claude/skills/breadboard-diagram/scripts'))
from render_breadboard import BreadboardRenderer,_input_jumper
from scripts.lab.review_pack.breadboard_template import template_png
from scripts.lab.review_pack.note_schematic import SchematicSymbols, write_note_schematics

def chain(n=4):
 f=Fig(1000,290,'공통 클록의 D 시프트 레지스터')
 for i in range(n):
  x=110+i*210;f.rect(x,55,140,125);f.text(x+12,87,'D');f.text(x+105,87,'Q');f.text(x+45,125,f'FF{i}')
  f.path(f'M{x},145 l18,10 l-18,10',fill='none');f.line([(x,155),(x-25,155),(x-25,230)]);f.dot(x-25,230)
  f.line([(x+140,80),(x+175,80)]);f.text(x+150,55,f'Q{i}',size=20)
  f.line([(x+160,80),(x+160,25)]);f.text(x+160,20,f'P{i}',size=18,anchor='middle')
  if i<n-1:f.line([(x+175,80),(x+210,80)])
 f.text(15,87,'S');f.line([(40,80),(110,80)]);f.line([(45,230),(85+(n-1)*210,230)]);f.text(10,270,'CLK: common rising edge / P0...P3: parallel outputs',size=23)
 return f

def dff():
 f=Fig(300,200,'문제에 주어진 D F/F 기호');f.rect(95,30,110,135);f.text(105,63,'D');f.text(170,63,'Q');f.text(160,135,'Q̅');f.line([(25,55),(95,55)]);f.line([(205,55),(270,55)]);f.line([(205,130),(270,130)]);f.line([(25,115),(95,115)]);f.path('M95,103 l20,12 l-20,12',fill='none');return f

def internal(detail=False):
 f=Fig(1200,470 if detail else 340,'7496 내부 5단 구조와 비동기 제어')
 for i in range(5):
  x=145+i*205;f.rect(x,160,135,150);f.text(x+15,190,'S');f.text(x+15,287,'R');f.text(x+96,190,'Q');f.text(x+78,287,'Qbar',size=18);f.text(x+48,233,f'FF{i}',size=24)
  f.line([(x+135,185),(x+190,185)]);f.line([(x+165,185),(x+165,120)]);f.dot(x+165,185);f.text(x+142,105,['QA15','QB14','QC13','QD11','QE10'][i],size=20)
  if i<4:
   f.line([(x+190,185),(x+205,185)]);f.line([(x+135,282),(x+190,282),(x+190,282),(x+205,282)])
  if detail:
   g=f.and_(x+30,40,bubble=True,H=50);f.text(x+5,26,'P'+['A2','B3','C4','D6','E7'][i],size=18);f.line([(x+10,25),(x+10,g['ins'][0][1]),g['ins'][0]]);f.line([(x+18,10),(x+18,g['ins'][1][1]),g['ins'][1]])
   f.line([g['out'],(x+115,g['out'][1]),(x+115,135),(x+65,135),(x+65,160)]);f.circle(x+65,156,4);f.text(x+5,135,'PRESET',size=18)
   f.circle(x+65,314,4);f.line([(x+65,318),(x+65,365)]);f.dot(x+65,365)
   f.path(f'M{x},228 l14,10 l-14,10',fill='none');f.circle(x-5,238,5);f.line([(x-10,238),(x-16,238),(x-16,415)]);f.dot(x-16,415)
  else:f.text(x+10,145,'PE & preset',size=18)
 if detail:
  f.text(5,160,'SER9',size=18);f.line([(5,185),(45,185)]);f.path('M45,172 l23,13 l-23,13');f.circle(73,185,5);f.line([(78,185),(97,185)]);f.path('M97,172 l23,13 l-23,13');f.circle(125,185,5);f.line([(130,185),(145,185)]);f.line([(85,185),(85,282),(145,282)]);f.dot(85,185)
  f.text(5,350,'CLR16',size=18);f.path('M70,350 l20,15 l-20,15');f.circle(95,365,5);f.line([(100,365),(1030,365)]);f.text(5,420,'CP1',size=18);f.path('M70,400 l20,15 l-20,15');f.circle(95,415,5);f.line([(100,415),(950,415)]);f.text(15,460,'S/R paths are complementary; common clock & clear; VCC5 GND12',size=22)
  # common PE bus to every preset NAND input
  f.text(5,26,'PE8',size=18);f.line([(55,10),(983,10)])
 else:
  f.text(5,195,'SER9');f.line([(75,185),(145,185)]);f.text(20,335,'5 storage stages / common clock and clear / VCC5 GND12',size=24)
 return f

def inverter():
 f=Fig(620,210,'74HC00 NAND의 두 입력을 묶은 보수 생성기');g=f.and_(210,70,bubble=True);f.text(30,100,'D');f.line([(65,93),(160,93),(160,g['ins'][0][1]),g['ins'][0]]);f.line([(160,93),(160,g['ins'][1][1]),g['ins'][1]]);f.dot(160,93);f.line([g['out'],(470,g['out'][1])]);f.text(490,112,'K');f.text(190,50,'1,2 → 3',size=24);f.text(20,190,'74HC00: VCC14=+5V, GND7=0V',size=23);return f


class NoteFig(SchematicSymbols, Fig):
    pass


def note_shift():
    f = NoteFig(890, 285, '공통 클록을 사용하는 4단 D 시프트 레지스터')
    f.line([(82, 120), (125, 120)])
    f.junction(82, 120)
    f.label(60, 129, 'S', anchor='end')
    f.line([(74, 247), (684, 247)])
    f.junction(74, 247, node='clk', color='red')
    f.label(52, 255, 'CLK', anchor='end', node='clk', color='red')
    for i in range(4):
        x = 125 + i * 195
        row = 120
        f.rect(x, 82, 122, 126, fill='#e8f1ff')
        f.label(x + 20, row + 8, 'D')
        f.label(x + 102, row + 8, 'Q', anchor='end')
        f.label(x + 64, 169, 'FF', sub=str(i), anchor='middle')
        f.path(f'M{x},176 l16,10 l-16,10', fill='none')
        f.line([(x, 186), (x - 26, 186), (x - 26, 247)])
        f.junction(x - 26, 247, node='clk', color='red')
        branch = x + 154
        f.line([(x + 122, row), (x + 195 if i < 3 else branch, row)])
        f.line([(branch, row), (branch, 62)])
        if i < 3:
            f.junction(branch, row, node=f'q{i}')
        f.junction(branch, 54, node=f'q{i}')
        f.label(branch, 26, 'P', sub=str(i), anchor='middle', node=f'q{i}')
    return f


def note_internal():
    f = NoteFig(1410, 493, '7496의 5단 시프트 및 비동기 프리셋 구조',
                '각 단의 Q와 Q′가 다음 단 S와 R로 연결된다. PE와 개별 PRESET이 1이면 해당 단을 비동기로 세트한다.')
    f.raw('<g transform="translate(20,0)">')
    f.line([(93, 65), (1111, 65)])
    f.junction(93, 65, node='pe', color='red')
    f.label(71, 73, 'PE 8', anchor='end', node='pe', color='red')
    f.line([(93, 421), (1271, 421)])
    f.line([(93, 461), (1141, 461)])
    f.junction(93, 421, node='clear', color='red')
    f.junction(93, 461, node='cp')
    f.label(71, 429, 'CLR 16', anchor='end', size=22, node='clear', color='red')
    f.label(71, 469, 'CP 1', anchor='end', node='cp', size=22)

    f.line([(55, 218), (81, 218)])
    f.junction(55, 218)
    f.label(53, 190, 'SER 9', anchor='middle', size=22)
    first = f.not_(81, 196)
    second = f.not_(157, 196)
    f.line([first['out'], second['ins'][0]])
    f.line([second['out'], (236, 218)])
    f.line([(150, 218), (150, 309), (236, 309)])
    f.junction(150, 218)

    for i, (bit, preset, output) in enumerate(zip('ABCDE', (2, 3, 4, 6, 7), (15, 14, 13, 11, 10))):
        x = 236 + 232 * i
        f.rect(x, 190, 132, 162, fill='#e8f1ff', rx=5)
        f.label(x + 20, 226, 'S')
        f.label(x + 20, 317, 'R')
        f.label(x + 110, 226, 'Q', anchor='end', node=f'q{bit}')
        f.label(x + 110, 317, 'Q′', anchor='end', node=f'qb{bit}', color='red')
        f.label(x + 66, 277, f'FF {bit}', anchor='middle')

        # Both preset controls go into the same asynchronous set gate.
        gate = f.and_(x - 35, 103, H=56, bubble=True, label='')
        preset_x, enable_x = x - 73, x - 53
        f.line([(preset_x, 39), (preset_x, gate['ins'][0][1]), gate['ins'][0]])
        f.junction(preset_x, 39)
        f.label(preset_x, 23, f'{bit} {preset}', anchor='middle', size=22)
        f.line([(enable_x, 65), (enable_x, gate['ins'][1][1]), gate['ins'][1]])
        f.crossing(preset_x, 65)
        f.junction(enable_x, 65, node='pe', color='red')
        f.line([gate['out'], (x + 66, gate['out'][1]), (x + 66, 183)])
        f.circle(x + 66, 186.5, 3.5)

        # The external falling edge is shown at each stage's clock pin.
        f.path(f'M{x},246 l14,10 l-14,10', fill='none')
        f.circle(x - 5, 256, 5)
        f.line([(x - 10, 256), (x - 23, 256), (x - 23, 461)])
        f.junction(x - 23, 461, node='cp')
        f.circle(x + 107, 357, 5)
        f.line([(x + 107, 362), (x + 107, 421)])
        f.junction(x + 107, 421, node='clear', color='red')

        tap = x + 158
        right = x + 232 if i < 4 else tap
        f.line([(x + 132, 218), (right, 218)])
        f.line([(tap, 218), (tap, 362)])
        if i < 4:
            f.junction(tap, 218, node=f'q{bit}')
            f.line([(x + 132, 309), (right, 309)])
            f.crossing(tap, 309)
            f.crossing(right - 23, 309)
        f.junction(tap, 362, node=f'q{bit}')
        f.label(tap, 392, 'Q', sub=bit, suffix=f' {output}', anchor='middle', size=22, node=f'q{bit}')
        f.crossing(x - 23, 421)
    f.crossing(213, 309)
    f.raw('</g>')
    return f


def draw_note_schematics(output_dir: Path) -> tuple[Path, ...]:
    return write_note_schematics(output_dir, {'shift': note_shift(), 'internal': note_internal()})


def build(run,m):
 F=run/'figures';(F/'questions').mkdir(parents=True,exist_ok=True);(F/'solutions').mkdir(exist_ok=True);reg=[]
 def register(fid,pid,role,f,ww=120,ids=[]):
  sub='questions' if role=='problem' else 'solutions';stem=F/sub/fid
  stem.with_suffix('.svg').write_text(f.svg(physical=(ww,ww*f.h/f.w)),encoding='utf8');render_png(stem.with_suffix('.svg'),stem.with_suffix('.png'),ww)
  q=next(x for x in m['problems'] if x['id']==pid)
  reg.append(dict(id=fid,question_id=pid,role=role,svg=f'figures/{sub}/{fid}.svg',png=f'figures/{sub}/{fid}.png',svg_sha256=sha(stem.with_suffix('.svg')),png_sha256=sha(stem.with_suffix('.png')),w_mm=ww,h_mm=ww*f.h/f.w,source_asset_ids=ids,source_refs=q['sources'][:1],derivation='원문 핀·신호·공통 클록·단계 간 Q/보수 경로를 읽어 직접 재제작한 벡터 그림. 문제와 완성 해설을 분리했어요.',answer_exposure='none' if role=='problem' else 'present',review_status='not_run',review_notes='시각 대조 대기'))
 draw_note_schematics(F)
 register('dff-given','q-ff-design','problem',dff(),45,['a-s05-p1-q2'])
 register('shift-complete','q-ff-design','solution',chain(),150)
 register('ic7496-given','q-7496-block','problem',internal(True),155,['a-s02-p1-q4'])
 pid='q-qp-e07-board-01';register('inverter-given',pid,'problem',inverter(),75)
 # engine validation is separate from the PDF coordinate projection
 b=BreadboardRenderer(board='v1');c=b.cols['left'];y=b.r_y
 b.draw_chip('74HC00',10);b.connect_jacks();b.bridge_rails(c['vcc'],c['mid_vcc'],35,kind='vcc');b.connect_power(10)
 _input_jumper(b,c,10,'D','external input D');b.step_wire([(c['c'],y(10)),(c['c'],y(11))],'sig','pin1 and pin2 tied to D')
 b.mark_unused_inputs([4,5,9,10,12,13],10);b.mark_unused_outputs([6,8,11],10)
 b.step_wire([(c['b'],y(12)),(220,y(12)),(220,y(20)),(c['b'],y(20))],'sig','K pin3 measurement point at b20');b.instrument(c['a'],12,'K','pin3 output measurement');b.verify()
 nets=[]
 for n in b.nets():
  pins={int(t.rsplit(' ',1)[1]) for t in n['labels'] if ' pin ' in t}
  if pins:nets.append(pins)
 assert {1,2} in nets and {14} in nets and {7} in nets
 png,w,h=template_png();head=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><title>v1 PDF NAND inverter board</title>';bg=f'<image x="0" y="0" width="{w}" height="{h}" href="data:image/png;base64,{base64.b64encode(png).decode()}"/>'
 xs=[(174,394),(190,433),(239,563),(256,606),(272,649),(288,692),(305,734),(354,862),(370,904),(386,948),(403,990),(419,1033),(468,1161),(484,1201)]
 def mx(x):
  for (a,u),(z,v) in zip(xs,xs[1:]):
   if a<=x<=z:return u+(x-a)*(v-u)/(z-a)
  a,u=xs[0] if x<174 else xs[-1];return u+(x-a)*2.606
 def my(yv):return 711.8+(yv-272)*(3352-711.8)/(62*16.345)
 parts=[]
 l,r=mx(312),mx(347);t,bot=my(y(10)-10),my(y(16)+10)
 parts.append(f'<rect x="{l}" y="{t}" width="{r-l}" height="{bot-t}" fill="#e5e7eb" stroke="#111" stroke-width="6"/><path d="M{(l+r)/2-20},{t} a20,20 0 0 0 40,0" fill="none" stroke="#111" stroke-width="6"/>')
 for pin in range(1,15):
  row=10+pin-1 if pin<=7 else 10+14-pin;xx=mx(305 if pin<=7 else 354);yy=my(y(row));edge=l if pin<=7 else r
  parts.append(f'<path d="M{xx},{yy} H{edge}" stroke="#111" stroke-width="7"/><text x="{xx-45 if pin<=7 else xx+10}" y="{yy-8}" font-size="30">{pin}</text>')
 parts.append(f'<text x="{(l+r)/2}" y="{(t+bot)/2}" font-size="34" text-anchor="middle" transform="rotate(-90 {(l+r)/2} {(t+bot)/2})">74HC00</text>')
 mapped=[]
 for k,pts,desc in b._segments:
  out=[(1083 if b._jack_at(x,yv)=='red' else 1936,400) if b._jack_at(x,yv) else (mx(x),my(yv)) for x,yv in pts];coords=' '.join(f'{x:.1f},{yv:.1f}' for x,yv in out);color={'vcc':'#dc2626','gnd':'#1665ca','sig':'#16814e','mid':'#b06a00'}[k]
  parts.append(f'<polyline points="{coords}" fill="none" stroke="white" stroke-width="13"/><polyline points="{coords}" fill="none" stroke="{color}" stroke-width="7"/>')
  for xx,yy in [out[0],out[-1]]:parts.append(f'<circle cx="{xx}" cy="{yy}" r="8" fill="{color}"/>')
  mapped.append(dict(kind=k,description=desc,pdf_points=out))
 parts.append(f'<text x="460" y="{my(y(9))-15}" font-size="48">D</text><text x="480" y="{my(y(20))+65}" font-size="48">K (pin3)</text>')
 for suffix,role,body in [('blank','problem',''),('complete','solution',''.join(parts))]:
  sub='questions' if role=='problem' else 'solutions';stem=F/sub/('inverter-'+suffix);stem.with_suffix('.svg').write_text(head+bg+body+'</svg>',encoding='utf8')
  if suffix=='blank':stem.with_suffix('.png').write_bytes(png)
  else:render_png(stem.with_suffix('.svg'),stem.with_suffix('.png'),100)
  reg.append(dict(id='inverter-'+suffix,question_id=pid,role=role,svg=f'figures/{sub}/inverter-{suffix}.svg',png=f'figures/{sub}/inverter-{suffix}.png',svg_sha256=sha(stem.with_suffix('.svg')),png_sha256=sha(stem.with_suffix('.png')),w_mm=100,h_mm=100*h/w,source_asset_ids=[],source_refs=[dict(source_id='s-board',pdf_page=1,printed_page=None)],derivation='v1 배포 강의노트/공지사항/Breadboard.pdf sha256='+sha(REPO/'강의노트/공지사항/Breadboard.pdf')+' 300dpi 전체 페이지. PDF 열 중심 394,433,563,606,649,692,734,862,904,948,990,1033,1161,1201; 행1=711.8 행63=3352. 엔진 JPG 좌표를 개별 선형 대응. verify와 핀1·2 동일 넷 대조.',answer_exposure='none' if role=='problem' else 'present',review_status='not_run',review_notes='PDF 홀·전원·핀 대조 대기'))
 (F/'quiz-board-mapping.json').write_text(json.dumps(dict(columns=xs,y_first=711.8,y_last=3352,segments=mapped,nets=[sorted(n) for n in nets]),ensure_ascii=False,indent=2))
 (F/'redraw-manifest.json').write_text(json.dumps(dict(schema_version=1,figures=reg),ensure_ascii=False,indent=2))
