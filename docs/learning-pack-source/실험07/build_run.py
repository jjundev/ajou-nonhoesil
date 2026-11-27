"""실험07 은행 수입 RUN에 사람이 저작한 원고를 조립해요."""
from pathlib import Path
import sys,json,hashlib,html
REPO=Path(__file__).resolve().parents[3];sys.path.insert(0,str(REPO));sys.path.insert(0,str(Path(__file__).parent))
from h import p,table,sumparts,pull_layouts
from content import TOPICS,Q,WARN
from quiz_content import ITEMS
from scripts.lab.review_pack.work_table import mark_work_tables
import figures
EXPLANATIONS = Path(__file__).with_name("problem-explanations")
R=Path(sys.argv[1]).resolve();M=json.loads((R/'manifest.json').read_text());I=json.loads((R/'authoring-index.json').read_text());B=json.loads((R/'evidence/question-bank.json').read_text());O={x['id']:x for x in B['occurrences']}
M['sources']=[s for s in M['sources'] if s['id'] not in {'s-manual07','s-board','s-basic','s-scope'}]
M['problems']=[x for x in M['problems'] if x.get('bank_question_id')]
MAN='s-manual07'
def addsrc(sid,path,kind='manual'):
 M['sources'].append(dict(id=sid,path=path,sha256=hashlib.sha256((REPO/path).read_bytes()).hexdigest(),kind=kind,edition='current'))
addsrc(MAN,'강의노트/실험7. Shift Register.pdf');addsrc('s-scope','강의노트/공지사항/2026-09-14_[필독]_논리회로실험_보고서_관련_공지.md','notice');addsrc('s-board','강의노트/공지사항/Breadboard.pdf','notice');addsrc('s-basic','강의노트/실험1. Basic Gates.pdf')
ref=lambda page:dict(source_id=MAN,pdf_page=page,printed_page=None)
M.update(title='Shift Register — 저장한 비트를 한 칸씩 옮겨요',edition_status='current',note_presentation_version=2,note_summary_version=2,note_reading_version=1,review_presentation_version=2,problem_explanation_version=2,quiz_practice_version=1,figure_manifest='figures/redraw-manifest.json',checks=dict.fromkeys(['source_visual','content','independent','browser'],'not_run'),explanation_checks=dict.fromkeys(['source_visual','content','independent','browser'],'not_run'))
M['topics']=[]
note_layout=[]
for tid,title,pages,body,summ in TOPICS:
 M['topics'].append(dict(id=tid,title=title,requires=[] if tid=='t-start' else ['t-start'],sources=[ref(pg) for pg in pages]+([dict(source_id='s-scope',pdf_page=None,printed_page=None)] if tid=='t-start' else []),fragment=f'sections/{tid}.html',md_notes='현재 배포 파일 표지는 25-1. 7496 제어 극성·엣지는 교안 본문/부록/과거 제공 답 사이 충돌을 유지해요.' if tid=='t-7496' else '링·존슨은 현재 교안의 수행 항목과 구분한 기출 대비 보충이에요.' if tid=='t-counters' else ''))
 (R/'sections').mkdir(exist_ok=True)
 if not body.startswith('<div class="layer'):
  raise ValueError(f'topic {tid} must start with explicit <div class="layer')
 note_body=body+sumparts(**summ)
 fragment,entries=pull_layouts(note_body,lambda n,t=tid:f'{t}/{n}')
 note_layout+=entries
 (R/'sections'/f'{tid}.html').write_text(fragment,encoding='utf8')
(R/'sections/table-layout.json').write_text(json.dumps(dict(version=1,tables=note_layout),ensure_ascii=False,indent=2),encoding='utf8')
P={x['id']:x for x in M['problems']};rows=[]
for q in Q:
 pid,title,topic,cue,_,reason,verify,pitfall,answer=q
 x=P[pid];x.update(title=title,status='included',reason='고유 기출·미확인 문항을 원문 조건 그대로 수록; 예상 JK 문항은 복사 입력 설계의 개념 공백을 보충',topics=[topic],scope='supplement' if pid in ['q-ring','q-johnson','q-johnson-nand'] else 'current',given_answer=None,derived_answer=answer,answer_status='disputed' if pid=='q-johnson-nand' else 'unresolved' if pid=='q-7496-block' else 'verified',duplicate_of=None,workbook_fragment=f'workbook/{pid}.json',explanation_fragment=f'problem-explanations/{pid}.html');x.pop('fragment',None)
 original=''.join(p(html.escape(b['text'])) for b in O[next(bq['representative_occurrence_id'] for bq in B['questions'] if bq['id']==pid)]['blocks'] if b['type']=='text')
 rows.append((x,dict(original=original,conditions=p('원문에 주어진 D F/F는 상승 엣지 기호예요. 첫 칸을 Q0로 정해요.') if pid=='q-ff-design' else '',ask='',problem_figures=['dff-given'] if pid=='q-ff-design' else ['ic7496-given'] if pid=='q-7496-block' else [],hints=[dict(label='접근 순서',html=p(cue))],solution=dict(steps=[dict(label='풀이',html=p(reason)+(f'<img src="figures/solutions/shift-complete.png" width="500" style="max-width:100%;height:auto" alt="4단 SIPO 완성 회로">' if pid=='q-ff-design' else '')),dict(label='검산',html=p(verify)),dict(label='주의',html=p(pitfall))],answer=p(answer)),notes=[p('보충 예상문항이며 실제 기출 여부를 뜻하지 않아요.')] if x['kind']=='predicted' else [])))
# 예상 7496 역할 문항은 내부 블록 기출과 동일한 개념만 반복하여 선별하지 않아요.
x=P['q-7496-role'];x.update(status='held',reason='예상문항의 7496 역할은 q-7496-block 기출에서 이미 다뤄 개념 공백이 없어요. 기출 중심 선별 원칙으로 비수록하며 원문·출처는 보존해요.',topics=[],derived_answer=None,given_answer=None,answer_status='unresolved')
for typ,suffix,title,topic,page,cond,ask,answer,reason,verify,pitfall in ITEMS:
 pid='q-qp-e07-'+suffix
 x=dict(id=pid,title=title,kind='practice',question_type=typ,status='included',reason='현재 교안 개념을 다른 퀴즈 유형으로 연습하는 자체 출제',topics=[topic],sources=[ref(page)],duplicate_of=None,scope='current',given_answer=None,derived_answer=answer,answer_status='verified',workbook_fragment=f'workbook/{pid}.json',explanation_fragment=f'problem-explanations/{pid}.html')
 cond=p(cond)+(p('보고서 지정 항목 밖의 교안 보충 내용을 연습해요. 시험 제외라는 뜻은 아니에요.') if topic in ['t-7496','t-counters'] else '');steps=[];pf=[]
 if typ=='true_false':steps=[dict(label='판정 근거',html=p(reason)),dict(label='문장 확인',html=p(pitfall)+p(verify))]
 elif typ=='fill_blank':steps=[dict(label='빈칸별 근거',html=p(reason)+p(verify)+p(pitfall))]
 elif typ=='short_answer':steps=[dict(label='모범 답',html=p(answer)+p(reason)),dict(label='채점 핵심',html=p(verify)),dict(label='허용 표현',html=p('같은 인과와 비트 순서를 밝힌 동치 표현을 인정해요. ')+p(pitfall))]
 else:
  pins=[['1,2','A1,B1','D 입력을 두 입력에 공통 연결'],['3','Y1','K 측정 출력'],['14','VCC','+5V'],['7','GND','0V'],['4,5,9,10,12,13','미사용 입력','수업 작도 명세: NC(개방), 실사용 일반 권장과 구분'],['6,8,11','미사용 출력','NC, 접지 금지']]
  cond+=table(['핀','이름','역할'],pins).replace('<table>','<table class="chip-spec">')+'<div class="work-board"><img src="figures/questions/inverter-blank.png" alt="v1 배포 PDF 작도용 빈 보드"></div>'
  x['sources'] += [dict(source_id='s-board',pdf_page=1,printed_page=None),dict(source_id='s-basic',pdf_page=8,printed_page=None)]
  pf=['inverter-given'];steps=[dict(label='연결 기준',html=p(answer)+table(['넷','핀'],[['+5V','14'],['GND','7'],['D','1,2'],['K','3'],['NC','4,5,6,8,9,10,11,12,13']])+p('외부 D는 신호원이고 K는 측정점이에요. IC 위치·홀 좌표가 달라도 같은 넷이면 인정해요.')),
  dict(label='완성 결선도',html='<p>그림은 D=0인 예예요. D 점퍼의 레일 쪽을 +5V로 옮기면 D=1이에요.</p><img src="figures/solutions/inverter-complete.png" width="270" style="max-width:100%;height:auto" alt="완성 결선도: NAND 보수 생성부">'),dict(label='논리 검산',html=p(reason)+p(verify))]
 cue={'true_false':'조건과 반례로 참·거짓을 판단해요','fill_blank':'비트 순서와 신호 역할을 먼저 정해요','breadboard':'같은 넷을 같은 도통 홀에 옮겨요','short_answer':'기능·이동 과정·조건을 연결해 설명해요'}[typ]
 rows.append((x,dict(original=p(ask),conditions=mark_work_tables(cond),ask='',problem_figures=pf,hints=[dict(label='접근 단서',html=p(cue))],solution=dict(steps=steps,answer=p(answer)),notes=[])))
 M['problems'].append(x)
# Drawings require question IDs/source refs already in the manifest.
figures.build(R,M)
(R/'workbook').mkdir(exist_ok=True);(R/'problem-explanations').mkdir(exist_ok=True)
for x,obj in rows:
 pid=x['id']
 (R/'workbook'/f'{pid}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
 fragment = EXPLANATIONS / f"{pid}.html"
 (R / "problem-explanations" / fragment.name).write_bytes(fragment.read_bytes())
for q in I['questions']:
 x=P[q['question_id']];q['authoring_status']='ready' if x['status']=='included' else 'not_selected';q['selection_reason']=x['reason']
layout = EXPLANATIONS / "table-layout.json"
(R / "problem-explanations" / layout.name).write_bytes(layout.read_bytes())
(R/'manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2),encoding='utf8');(R/'authoring-index.json').write_text(json.dumps(I,ensure_ascii=False,indent=2),encoding='utf8')
print('authored',len(rows),'included')
