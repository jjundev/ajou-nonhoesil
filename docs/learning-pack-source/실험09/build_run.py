"""실험09 은행 수입 RUN에 사람이 저작한 원고를 조립해요.

사용: python build_run.py <RUN> [reviewed]
reviewed 는 원문·내용·브라우저 검토를 실제로 마친 뒤에만 붙여요.
"""
from pathlib import Path
import sys, json, hashlib, html, re
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))
from h import p, table, sumd, sumparts, pull_layouts, layer
from content import TOPICS
from questions import Q, ORDER, NOT_INCLUDED
from quiz_content import ITEMS, BOARD_PINS, BOARD_NETS
from scripts.lab.review_pack.work_table import mark_work_tables
import figures

R = Path(sys.argv[1]).resolve()
M = json.loads((R / 'manifest.json').read_text(encoding='utf8'))
I = json.loads((R / 'authoring-index.json').read_text(encoding='utf8'))
B = json.loads((R / 'evidence/question-bank.json').read_text(encoding='utf8'))
O = {x['id']: x for x in B['occurrences']}
BQ = {x['id']: x for x in B['questions']}
ADDED = {'s-manual09', 's-board', 's-scope', 's-spec09', 's-netlist09'}
M['sources'] = [s for s in M['sources'] if s['id'] not in ADDED]
M['problems'] = [x for x in M['problems'] if x.get('bank_question_id')]
MAN = 's-manual09'


def addsrc(sid, path, kind='manual', edition='current'):
    M['sources'].append(dict(id=sid, path=path, sha256=hashlib.sha256((REPO / path).read_bytes()).hexdigest(), kind=kind, edition=edition))


addsrc(MAN, '강의노트/실험9. RAM.pdf')
addsrc('s-scope', '강의노트/공지사항/2026-09-14_[필독]_논리회로실험_보고서_관련_공지.md', 'notice')
addsrc('s-board', '강의노트/공지사항/Breadboard.pdf', 'notice')
addsrc('s-spec09', '보고서/실험09/체크리스트/명세.md', 'record')
addsrc('s-netlist09', '보고서/실험09/결선도/netlist.md', 'record')


def ref(page):
    return dict(source_id=MAN, pdf_page=page, printed_page=None)


def nref(sid):
    return dict(source_id=sid, pdf_page=None, printed_page=None)


M.update(title='RAM — 값을 쓰고 붙잡았다가 읽어요', edition_status='current', note_presentation_version=2, note_summary_version=2, review_presentation_version=2, problem_explanation_version=2, quiz_practice_version=1, figure_manifest='figures/redraw-manifest.json', checks=dict.fromkeys(['source_visual', 'content', 'independent', 'browser'], 'not_run'), explanation_checks=dict.fromkeys(['source_visual', 'content', 'independent', 'browser'], 'not_run'))
NOTES = {
 't-start': '교안 표지는 25-1이에요. 보고서 범위(실험 1, 2)는 2026-09-14 공지(_350547_1)와 config.EXPERIMENT_SCOPE[9]에서 확인했어요.',
 't-ram': 'p3 정의·쓰임 문장을 옮겼어요. SRAM·DRAM 비교와 휘발성의 원리 설명은 교안 밖 보충이에요. 전원을 다시 켠 뒤의 값은 교안에 없어요(netlist M9). 네 칸 추적표는 이해를 위한 예시예요.',
 't-latch': 'p2 목표의 “NAND SR Latch 기반”, p7 주의의 00 금지를 따랐어요. NAND 래치 규칙은 실험06 노트와 같고 check_values.py 가 네 입력 조합을 다시 계산했어요.',
 't-1bit': 'p4의 부울식은 S·R이 그림·표와 바뀌어 있어요(300dpi 판독, netlist M15). 회로도·표를 따랐어요. 표 첫 행(Selection=0이면 Q=0)도 회로의 유지와 달라요(M15). 회로 그림은 p4를 직접 다시 그렸고 Input 인버터가 R 쪽 AND로 가는 것을 400dpi 크롭으로 확인했어요.',
 't-2bit': 'p6 범례는 WR0을 A, WR1을 B 값으로 적지만 회로도는 WR1을 두 래치의 세트 쪽(2번), WR0을 리셋 쪽(5번)에 공통으로 잇는다(netlist M2, p6 400dpi 크롭 직접 판독). 추적표는 명세 T1 값이며 check_values.py 가 네 초기 상태 모두에서 다시 계산했어요. 실제 결선도는 U1·U2 게이트 자리를 바꿨어요(M13). 이 노트의 핀 번호는 교안 회로도 기준이에요.',
 't-rules': 'p7 주의 1의 괄호 IN0 = IN1′(300dpi 판독, 텍스트 추출은 바를 잃어요)의 해석은 netlist M3을 따랐어요. WR을 IN이 둘 다 0일 때만 바꾸는 규칙은 결선도 운영 규칙이에요(netlist 공통 규칙). ①~⑤의 결과는 check_values.py rules_checks 로 다시 계산했어요.',
 't-opendrain': '74HC03이 열린 드레인이라는 것은 .claude/데이터시트_출처.md 의 Nexperia 74HC_HCT03 서지 제목(“Quad 2-input NAND gate (open drain)”)과 p6의 10K 풀업에 근거해요. 데이터시트 본문과 전원 핀은 1차 자료로 확인하지 못했어요(netlist M6). LED 전류가 작다는 말은 M5의 계산(순방향 2V 가정, 약 0.29mA)에 근거한 예상이에요.',
 't-74670': 'p8 핀맵과 범례를 따랐어요. 핀은 TI SDLS193(SN74LS670) p1과 같고, RE=1일 때 고임피던스·Write/Read Function Table은 .claude/데이터시트_출처.md 와 netlist 의 2026-11-09 확인 기록이에요(이번에는 PDF를 다시 열지 못했어요, 네트워크 403). 주소 비트 순서 WB WA는 TI 표 기준이에요(M8). 수령 칩 계열은 확인 전이에요(M7). 쓰기·읽기 예시 값은 명세 T4의 저작 값이에요(M10). 쓰기·읽기 동시 가능은 핀 구성에서 읽은 보충이에요.',
}
EXTRA = {'t-start': [nref('s-scope')], 't-1bit': [nref('s-netlist09')], 't-2bit': [nref('s-netlist09'), nref('s-spec09')], 't-rules': [nref('s-netlist09')], 't-opendrain': [nref('s-netlist09')], 't-74670': [nref('s-netlist09'), nref('s-spec09')]}
if len(sys.argv) > 2 and sys.argv[2] == 'reviewed':
    # 검토를 실제로 마친 뒤에만 켜요. 별도 독립 리뷰는 하지 않았어요.
    done = dict(source_visual='pass', content='self_review', independent='not_run', browser='pass')
    M['checks'] = dict(done)
    M['explanation_checks'] = dict(done)
M['topics'] = []
note_layout = []
(R / 'sections').mkdir(exist_ok=True)
for tid, title, pages, body, summ in TOPICS:
    M['topics'].append(dict(id=tid, title=title, requires=[] if tid == 't-start' else ['t-start'], sources=[ref(pg) for pg in pages] + EXTRA.get(tid, []), fragment=f'sections/{tid}.html', md_notes=NOTES.get(tid, '')))
    if not body.startswith('<div class="layer'):
        first, sep, rest = body.partition('</p>')
        body = layer('eli5', '작은 예부터 살펴봐요', first + sep) + layer('formal', '조건과 작동 원리를 확인해요', rest)
    fragment, entries = pull_layouts(body, lambda n, t=tid: f'{t}/{n}')
    note_layout += entries
    (R / 'sections' / f'{tid}.html').write_text(fragment + sumparts(**summ), encoding='utf8')
(R / 'sections/table-layout.json').write_text(json.dumps(dict(version=1, tables=note_layout), ensure_ascii=False, indent=2), encoding='utf8')

P = {x['id']: x for x in M['problems']}
assert set(P) == set(ORDER) | set(NOT_INCLUDED), set(P) ^ (set(ORDER) | set(NOT_INCLUDED))
rows = []
exp_layout = []


def strip(s):
    return pull_layouts(s, lambda n: '')[0]


for pid, (status, _, reason) in NOT_INCLUDED.items():
    x = P[pid]
    x.update(status=status, reason=reason, topics=[], given_answer=None, derived_answer=None, answer_status='unresolved', duplicate_of=None)
    for k in ('fragment', 'workbook_fragment', 'explanation_fragment', 'title'):
        x.pop(k, None)

for pid in ORDER:
    q = Q[pid]
    x = P[pid]
    x.update(title=q['title'], status='included', reason='고유 기출·미확인 문항과 개념 공백을 보충하는 예상문항을 원문 조건 그대로 수록해요', topics=[q['topic']], scope=q.get('scope', 'current'), given_answer=None, derived_answer=re.sub(r'<[^>]+>', '', q['answer']), answer_status=q['status'], duplicate_of=None, workbook_fragment=f'workbook/{pid}.json', explanation_fragment=f'problem-explanations/{pid}.html')
    if x['kind'] == 'predicted':
        x['reason'] = '예상문항이지만 기출이 다루지 않은 개념(' + {'q-sram-cell': '한 비트를 붙잡는 저장 회로', 'q-read-op-rw': '읽기 때 Read/Write 값', 'q-write0': '1 bit RAM의 Reset 쪽 경로', 'q-apart1': '2bit RAM의 A part 선택과 1 쓰기'}[pid] + ')을 보충해서 수록해요'
    x.pop('fragment', None)
    rep = O[BQ[pid]['representative_occurrence_id']]
    original = ''.join(p(html.escape(b['text'])) for b in rep['blocks'] if b['type'] == 'text' and b['id'].endswith('-text'))
    obj = dict(original=original, conditions=q.get('conditions', ''), ask=p(q['ask']), problem_figures=q.get('figs', []), hints=[dict(label='접근 순서', html=p(q['hint']))], solution=dict(steps=[dict(label=a, html=b) for a, b in q['steps']] + [dict(label='검산', html=p(q['verify'])), dict(label='주의', html=p(q.get('wb_pitfall', q['pitfall'])))], answer=p(q['answer'])), notes=[])
    rows.append((x, obj, q))

for typ, suffix, title, topic, page, cond, ask, answer, reason, verify, pitfall, cue, start in ITEMS:
    pid = 'q-qp-e09-' + suffix
    x = dict(id=pid, title=title, kind='practice', question_type=typ, status='included', reason='현재 교안 개념을 다른 퀴즈 유형으로 연습하는 자체 출제', topics=[topic], sources=[ref(page)], duplicate_of=None, scope='current', given_answer=None, derived_answer=answer, answer_status='verified', workbook_fragment=f'workbook/{pid}.json', explanation_fragment=f'problem-explanations/{pid}.html')
    conditions = p(cond)
    pf = []
    if typ == 'true_false':
        steps = [('판정 근거', p(reason)), ('문장 확인', p(pitfall) + p(verify))]
    elif typ == 'fill_blank':
        steps = [('빈칸별 근거', p(reason) + p(verify) + p(pitfall))]
    elif typ == 'short_answer':
        steps = [('모범 답', p(answer) + p(reason)), ('채점 핵심', p(verify)), ('허용 표현', p('같은 인과와 순서를 밝힌 동치 표현을 인정해요. ') + p(pitfall))]
    else:
        conditions += table(['핀', '이름', '역할'], BOARD_PINS, 'itt') + '<div class="work-board"><img src="figures/questions/latch-blank.png" alt="v1 배포 PDF 작도용 빈 보드"></div>'
        x['sources'] += [dict(source_id='s-board', pdf_page=1, printed_page=None)]
        pf = ['latch-given']
        steps = [('연결 기준', p(answer) + table(['넷', '핀'], BOARD_NETS, 'tb') + p('외부 S′, R′는 신호원이고 Q는 측정점이에요. IC 위치·홀 좌표가 달라도 같은 넷이면 인정해요.')),
                 ('완성 결선도', '<p>그림은 S′, R′ 점퍼를 GND 레일에 둔 모습이에요. 실제로 쓸 때는 쉬는 값 1(+5V)로 옮겨 두고, Set·Reset할 때만 해당 점퍼를 0V로 내려요. 둘을 함께 0V에 두지 않아요.</p><img src="figures/solutions/latch-complete.png" width="270" style="max-width:100%;height:auto" alt="완성 결선도: 74HC00 NAND SR 래치">'),
                 ('논리 검산', p(reason) + p(verify) + p(pitfall))]
    q = dict(title=title, topic=topic, answer=answer, hint=cue, understand=f'{title}: 조건을 읽고 판단 근거를 말로 설명하는 연습이에요.', cue=cue, recall=[f'“{title}”에 쓰인 조건이 단서예요. {reason}'], start=start, verify=verify, pitfall=pitfall, retry=['조건을 다시 적어요.', start, verify], sum_key=cue, steps=steps)
    obj = dict(original=p(ask), conditions=conditions, ask=p({'true_false': '참(T)·거짓(F) 판정', 'fill_blank': '빈칸의 값', 'short_answer': '이유를 담은 설명', 'breadboard': '완성한 작도'}[typ]), problem_figures=pf, hints=[dict(label='접근 단서', html=p(cue))], solution=dict(steps=[dict(label=a, html=b) for a, b in steps], answer=p(answer)), notes=[])
    rows.append((x, obj, q))
    M['problems'].append(x)

M['problems'] = [P[i] for i in ORDER] + [x for x in M['problems'] if not x.get('bank_question_id')] + [P[i] for i in NOT_INCLUDED]
figures.build(R, M)
(R / 'workbook').mkdir(exist_ok=True)
(R / 'problem-explanations').mkdir(exist_ok=True)


def sect(key, title, body, cls='formal'):
    return f'<div class="layer {cls}" data-explanation="{key}"><span class="layer-title">{title}</span>{body}</div>'


for x, obj, q in rows:
    pid = x['id']
    topic = q['topic']
    solve_steps = obj['solution']['steps']
    solve = ''.join(f"<p><strong>{s['label']}:</strong></p>" + s['html'] for s in solve_steps if s['label'] not in ('검산', '주의'))
    solve = re.sub(r'<p>(<img[^>]+>)</p>|(<img[^>]+>)', lambda m: '<figure class="figure">' + (m.group(1) or m.group(2)) + '</figure>', solve).replace('src="figures/', 'src=".pack/figures/').replace(' style="max-width:100%;height:auto"', '')
    e = sect('understand', '이 문제에서 할 일', p(q['understand']), 'eli5')
    e += sect('recall', '이 문제를 봤을 때 떠올릴 개념과 공식', f'<p class="lead cue">{q["cue"]}</p>' + ''.join(p(t) for t in q['recall']))
    e += sect('start', '첫 줄을 이렇게 시작해요', p(q['start']) + f'<p><a href="{{{{NOTE_HREF}}}}#{topic}">필요한 개념으로 돌아가요</a></p>')
    e += sect('solve', '이유를 따라 완성해요', solve)
    e += sect('verify', '답과 검산을 확인해요', p('최종 답: ' + q['answer']) + p('검산: ' + q['verify']))
    e += sect('pitfall', '헷갈리기 쉬운 조건을 확인해요', p(q['pitfall']), 'warn')
    e += sect('retry', '설명을 닫고 다시 해 봐요', '<ol>' + ''.join(f'<li>{t}</li>' for t in q['retry']) + '</ol>')
    e += sumd(p('<strong>떠올릴 것:</strong> ' + q['cue']) + f'<p data-summary="recall">{q["recall"][0]}</p>' + p('첫 실행: ' + q['start']) + p('핵심: ' + q['sum_key']) + p('결론: ' + q['answer']) + p('검산: ' + q['verify']) + p('주의: ' + q['pitfall']))
    e, ents = pull_layouts(e, lambda n, i=pid: f'{i}/explanation/{n}')
    exp_layout += ents
    conditions, ents = pull_layouts(obj['conditions'], lambda n, i=pid: f'{i}/conditions/{n}')
    exp_layout += ents
    if x.get('question_type') == 'breadboard':
        conditions = conditions.replace('<table>', '<table class="chip-spec">')
    obj['conditions'] = mark_work_tables(conditions)
    obj['solution']['steps'] = [s for s in obj['solution']['steps'] if s['label'] not in q.get('wb_skip', ())]
    for s in obj['solution']['steps']:
        s['html'] = strip(s['html'])
        if q.get('wb_noimg'):
            s['html'] = re.sub(r'<p><img[^>]+></p>', '', s['html'])
    (R / 'workbook' / f'{pid}.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf8')
    (R / 'problem-explanations' / f'{pid}.html').write_text(e, encoding='utf8')

STAT = {pid: v[1] for pid, v in NOT_INCLUDED.items()}
for q in I['questions']:
    x = P[q['question_id']]
    q['authoring_status'] = 'ready' if x['status'] == 'included' else STAT[q['question_id']]
    q['selection_reason'] = x['reason']
(R / 'problem-explanations/table-layout.json').write_text(json.dumps(dict(version=1, tables=exp_layout), ensure_ascii=False, indent=2), encoding='utf8')
(R / 'manifest.json').write_text(json.dumps(M, ensure_ascii=False, indent=2), encoding='utf8')
(R / 'authoring-index.json').write_text(json.dumps(I, ensure_ascii=False, indent=2), encoding='utf8')
print('authored', len(rows), 'included')
