"""실험08 은행 수입 RUN에 사람이 저작한 원고를 조립해요."""
from pathlib import Path
import sys, json, hashlib, html, re
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))
from h import p, table, sumd, sumparts, pull_layouts
from content import TOPICS
from questions import Q, ORDER
from quiz_content import ITEMS, BOARD_PINS, BOARD_NETS
from scripts.lab.review_pack.work_table import mark_work_tables
import figures

R = Path(sys.argv[1]).resolve()
M = json.loads((R / 'manifest.json').read_text(encoding='utf8'))
I = json.loads((R / 'authoring-index.json').read_text(encoding='utf8'))
B = json.loads((R / 'evidence/question-bank.json').read_text(encoding='utf8'))
O = {x['id']: x for x in B['occurrences']}
BQ = {x['id']: x for x in B['questions']}
ADDED = {'s-manual08', 's-board', 's-scope', 's-spec08', 's-netlist08'}
M['sources'] = [s for s in M['sources'] if s['id'] not in ADDED]
M['problems'] = [x for x in M['problems'] if x.get('bank_question_id')]
MAN = 's-manual08'


def addsrc(sid, path, kind='manual', edition='current'):
    M['sources'].append(dict(id=sid, path=path, sha256=hashlib.sha256((REPO / path).read_bytes()).hexdigest(), kind=kind, edition=edition))


addsrc(MAN, '강의노트/실험8_Counter_회로정정본.pdf')
addsrc('s-scope', '강의노트/공지사항/2026-09-14_[필독]_논리회로실험_보고서_관련_공지.md', 'notice')
addsrc('s-board', '강의노트/공지사항/Breadboard.pdf', 'notice')
addsrc('s-spec08', '보고서/실험08/체크리스트/명세.md', 'record')
addsrc('s-netlist08', '보고서/실험08/결선도/netlist.md', 'record')


def ref(page):
    return dict(source_id=MAN, pdf_page=page, printed_page=None)


def nref(sid):
    return dict(source_id=sid, pdf_page=None, printed_page=None)


M.update(title='Counter — 클럭을 세어 숫자로 보여 줘요', edition_status='current', note_presentation_version=2, note_summary_version=2, review_presentation_version=2, problem_explanation_version=2, quiz_practice_version=1, figure_manifest='figures/redraw-manifest.json', checks=dict.fromkeys(['source_visual', 'content', 'independent', 'browser'], 'not_run'), explanation_checks=dict.fromkeys(['source_visual', 'content', 'independent', 'browser'], 'not_run'))
NOTES = {
 't-start': '교안 표지는 25-1이에요. 보고서 범위(실험 1, 3)는 공지에서 확인했어요.',
 't-async': '교안 본문은 조합을 00, 01, 10, 11로 적고 파형은 00, 10, 01, 11이에요. 파형과 p9 출력 순서를 따랐어요(netlist M10). 글리치·리플 용어는 교안 밖 보충이에요.',
 't-decode': 'Y0~Y3은 교안 이름이 아니라 명세의 이름이에요. 출력 번호 0~3은 p5 그림을 따랐어요.',
 't-sync': '실험 2는 보고서 범위 밖이에요. J1=B′, K1=1, J2=A, K2=1은 p10 회로를 직접 읽었고 2017-1 기출 회로와 같아요.',
 't-7490': 'p6 핀맵의 6·7번 No Connect와 p7·p11의 R9 충돌은 netlist M4, 스위치 D0는 M7, IC 표기 차이는 M5예요. 2진·5진 나눔은 p6 내부 회로의 클럭 경로로 확인했고 실제 측정은 없어요.',
 't-7447': '머리글 DBCA와 값 순서 D, C, B, A는 netlist M9, 숫자 9의 d 세그먼트 차이는 M8(TI SDLS111 p3)이에요. 오픈 컬렉터 설명은 netlist 37행이 인용한 TI SDLS111 p1이에요.',
 't-fnd': 'p12 그림과 p16 핀표의 FND 핀 충돌은 netlist M2, 표시기 이름은 M3, 330Ω 수량은 M6이에요.',
}
EXTRA = {'t-start': [nref('s-scope')], 't-decode': [nref('s-spec08')], 't-7490': [nref('s-netlist08')], 't-7447': [nref('s-netlist08')], 't-fnd': [nref('s-netlist08')], 't-async': [nref('s-netlist08')]}
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
        from h import layer
        body = layer('eli5', '작은 예부터 살펴봐요', first + sep) + layer('formal', '조건과 작동 원리를 확인해요', rest)
    fragment, entries = pull_layouts(body, lambda n, t=tid: f'{t}/{n}')
    note_layout += entries
    (R / 'sections' / f'{tid}.html').write_text(fragment + sumparts(**summ), encoding='utf8')
(R / 'sections/table-layout.json').write_text(json.dumps(dict(version=1, tables=note_layout), ensure_ascii=False, indent=2), encoding='utf8')

P = {x['id']: x for x in M['problems']}
rows = []
exp_layout = []
SUPPLEMENT = {'q-sync-wave', 'q-mod-and-double', 'q-sync-improve', 'q-async-sync-compare'}


def strip(s):
    return pull_layouts(s, lambda n: '')[0]


for pid in ORDER:
    q = Q[pid]
    x = P[pid]
    x.update(title=q['title'], status='included', reason='고유 기출·미확인 문항을 원문 조건 그대로 수록해요', topics=[q['topic']], scope='current', given_answer=None, derived_answer=re.sub(r'<[^>]+>', '', q['answer']), answer_status=q['status'], duplicate_of=None, workbook_fragment=f'workbook/{pid}.json', explanation_fragment=f'problem-explanations/{pid}.html')
    x.pop('fragment', None)
    rep = O[BQ[pid]['representative_occurrence_id']]
    original = ''.join(p(html.escape(b['text'])) for b in rep['blocks'] if b['type'] == 'text' and b['id'].endswith('-text'))
    obj = dict(original=original, conditions=q.get('conditions', ''), ask=p(q['ask']), problem_figures=q.get('figs', []), hints=[dict(label='접근 순서', html=p(q['hint']))], solution=dict(steps=[dict(label=a, html=b) for a, b in q['steps']] + [dict(label='검산', html=p(q['verify'])), dict(label='주의', html=p(q.get('wb_pitfall', q['pitfall'])))], answer=p(q['answer'])), notes=[])
    rows.append((x, obj, q))

for typ, suffix, title, topic, page, cond, ask, answer, reason, verify, pitfall, cue, start in ITEMS:
    pid = 'q-qp-e08-' + suffix
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
        conditions += table(['핀', '이름', '역할'], BOARD_PINS, 'itt') + '<div class="work-board"><img src="figures/questions/and-blank.png" alt="v1 배포 PDF 작도용 빈 보드"></div>'
        x['sources'] += [dict(source_id='s-board', pdf_page=1, printed_page=None)]
        pf = ['and-given']
        steps = [('연결 기준', p(answer) + table(['넷', '핀'], BOARD_NETS, 'tb') + p('외부 A, B는 신호원이고 Y는 측정점이에요. IC 위치·홀 좌표가 달라도 같은 넷이면 인정해요.')),
                 ('완성 결선도', '<p>그림은 A=B=0인 예예요. 입력 점퍼의 레일 쪽을 +5V로 옮기면 입력이 1이에요.</p><img src="figures/solutions/and-complete.png" width="270" style="max-width:100%;height:auto" alt="완성 결선도: 74HC08 AND 한 개">'),
                 ('논리 검산', p(reason) + p(verify) + p(pitfall))]
    q = dict(title=title, topic=topic, answer=answer, hint=cue, understand=f'{title}: 조건을 읽고 판단 근거를 말로 설명하는 연습이에요.', cue=cue, recall=[f'“{title}”에 쓰인 조건이 단서예요. {reason}'], start=start, verify=verify, pitfall=pitfall, retry=['조건을 다시 적어요.', start, verify], sum_key=cue, steps=steps)
    obj = dict(original=p(ask), conditions=conditions, ask=p({'true_false': '참(T)·거짓(F) 판정', 'fill_blank': '빈칸의 값', 'short_answer': '이유를 담은 설명', 'breadboard': '완성한 작도'}[typ]), problem_figures=pf, hints=[dict(label='접근 단서', html=p(cue))], solution=dict(steps=[dict(label=a, html=b) for a, b in steps], answer=p(answer)), notes=[])
    rows.append((x, obj, q))
    M['problems'].append(x)

M['problems'] = [P[i] for i in ORDER] + [x for x in M['problems'] if not x.get('bank_question_id')]
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

for q in I['questions']:
    x = P[q['question_id']]
    q['authoring_status'] = 'ready' if x['status'] == 'included' else 'not_selected'
    q['selection_reason'] = x['reason']
(R / 'problem-explanations/table-layout.json').write_text(json.dumps(dict(version=1, tables=exp_layout), ensure_ascii=False, indent=2), encoding='utf8')
(R / 'manifest.json').write_text(json.dumps(M, ensure_ascii=False, indent=2), encoding='utf8')
(R / 'authoring-index.json').write_text(json.dumps(I, ensure_ascii=False, indent=2), encoding='utf8')
print('authored', len(rows), 'included')
