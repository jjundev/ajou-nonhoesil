"""실험10 은행 수입 RUN에 사람이 저작한 원고를 조립해요.

사용: python build_run.py <RUN> [reviewed]
reviewed 는 원문·내용·브라우저 검토를 실제로 마친 뒤에만 붙여요.
"""
from pathlib import Path
import sys, json, hashlib, html, re
from shutil import copyfile
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))
from h import p, table, sumparts, pull_layouts, layer
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
ADDED = {'s-manual10', 's-board', 's-scope', 's-spec10', 's-netlist10'}
M['sources'] = [s for s in M['sources'] if s['id'] not in ADDED]
M['problems'] = [x for x in M['problems'] if x.get('bank_question_id')]
MAN = 's-manual10'


def addsrc(sid, path, kind='manual', edition='current'):
    M['sources'].append(dict(id=sid, path=path, sha256=hashlib.sha256((REPO / path).read_bytes()).hexdigest(), kind=kind, edition=edition))


addsrc(MAN, '강의노트/실험10. DAC & ADC.pdf')
addsrc('s-scope', '강의노트/공지사항/2026-09-14_[필독]_논리회로실험_보고서_관련_공지.md', 'notice')
addsrc('s-board', '강의노트/공지사항/Breadboard.pdf', 'notice')
addsrc('s-spec10', '보고서/실험10/체크리스트/명세.md', 'record')
addsrc('s-netlist10', '보고서/실험10/결선도/netlist.md', 'record')


def ref(page):
    return dict(source_id=MAN, pdf_page=page, printed_page=None)


def nref(sid):
    return dict(source_id=sid, pdf_page=None, printed_page=None)


M.update(title='D/A & A/D Converter — 숫자를 전압으로, 전압을 숫자로', edition_status='current', note_presentation_version=2, note_summary_version=2, note_reading_version=1, review_presentation_version=2, problem_explanation_version=2, quiz_practice_version=1, figure_manifest='figures/redraw-manifest.json', checks=dict.fromkeys(['source_visual', 'content', 'independent', 'browser'], 'not_run'), explanation_checks=dict.fromkeys(['source_visual', 'content', 'independent', 'browser'], 'not_run'))
NOTES = {
 't-start': '교안 표지는 25-1이에요. 보고서 범위(실험 1) DAC)는 2026-09-14 공지(_350547_1)와 config.EXPERIMENT_SCOPE[10]에서 확인했어요(명세 근거와 범위). DAC 정의·쓰임은 p7, ADC 정의는 p13이에요. 4비트 변환 표는 이해를 위한 예시이고 check_values.py가 다시 계산했어요. 내림차순 계단 그림은 p18에 근거한 개형이에요.',
 't-opamp': 'p3 정의(Vout = A(V+−V−), A는 수만~수백만), p4 반전 증폭기 식과 그림을 옮겼어요. 가상 접지 용어와 LM741 출력 한계는 교안 밖 보충이에요. 추적표 값은 check_values.py 가 다시 계산했어요.',
 't-summing': 'p11 반전 가산증폭기 식을 옮겼어요. 식의 R1~R4와 회로도 R1~R4(1.5k 풀업)의 이름 겹침은 명세 토큰 표의 판독을 따랐어요. 24k·12k·6k·3k 예시는 이해를 위한 값이고 check_values.py 가 다시 계산했어요.',
 't-network': 'p6 그림과 두 식을 300dpi로 다시 읽어 직접 다시 그렸어요(D1이 MSB, 가중 저항 RL ≫ R, 래더 끝 2R 접지). 장단점은 교안 본문에 없고 기출 제공 답안과 일반 지식에서 가져온 보충이에요. 3비트 예시 값은 check_values.py 가 두 식과 저항망 노드 해석(가중: 밀만, 래더: 회로 해석)으로 다시 계산했어요.',
 't-7490': 'p8 카운트 순서(0000~1001 반복), p10 LSB·MSB 표시, p8·p15·p16 회로도 핀(CLKA 14, CLKB 1, R01 2, R02 3, R91 6, R92 7, QA 12, QB 9, QC 8, QD 11)을 따랐어요. 전원 5·10번은 netlist 핀아웃 출처(TI SDLS940A, 실험08 기록 경유)예요. 2진·5진 단 구조는 칩 자료에서 가져온 보충이에요. 초기화 입력이 없어 시작 값이 정해지지 않는다는 판단은 명세를 따랐어요.',
 't-oc': 'p9 문장(정확히 GND 또는 Vcc, Open-collector IC 05와 Pull up 저항, IC 04로 반전 피하기)과 p10 회로 값을 따랐어요. 경로 저항 합(24.1k·12k·6k·3k)은 명세에 있는 V+=GND일 때의 이상 셈이에요. 스위치 동작과 풀업 접점 전압은 이상 모델로 설명했어요. 74HC05가 open-drain이라는 것은 netlist 핀아웃 출처(TI SCLS080F 2026-11-16 확인)예요.',
 't-dac': 'p10~p12 회로, p16·p17 절차, p18 예상 결과(내림차순 계단), p19~p21 절차 4~6을 따랐어요. V+=GND에서 평평한 선 예상은 명세 T3의 판단이고, p18 두 사진의 절차 대응은 미확정이에요(netlist M13). 교안 소자값의 이상 셈이 +15V를 넘는 문제는 netlist M7, U4 7번 라벨 없음은 M3이에요(기출 예상문제 v3의 같은 회로 그림은 7번을 +15V로 적어 이 노트·명세의 +15V 연결과 맞아요), LM741 단일 전원 문제는 M11이에요. 1kHz에서 1ms·10ms, Rf 0.6배, 10.5k∥68k ≈ 9.1k는 check_values.py 셈이에요. 절차 4~6을 따로 하는 순서는 명세의 결정이에요(M9). 출력 식 V+ + Rf·Σ(V+−Vi)/Ri와 기준·입력을 하나씩 바꾸는 예시는 이상 Op-Amp의 KCL 셈으로 보충했어요.',
 't-comparator': 'p5 비교기 정의와 p22 회로(DAC OUTPUT → 2번, R13 330 가운데 단자 → 3번, 7번 +15V, 4번 0, 출력 15V 또는 0V), p23·p24 절차를 따랐어요. p5 문장(“V+ 기준 Vin(V−)이 작다면 Vs−”)은 같은 쪽 식과 반대라 식을 따랐어요(300dpi 판독). 실험 2는 보고서 범위 밖(명세)이에요. 추적표 전압은 이해를 위한 예시예요.',
 't-adc': 'p13의 두 type과 세 feedback 방식(Ramp, Counter, SAR)을 옮겼어요. 2ⁿ−1은 p13을 300dpi로 읽어 확인했어요(텍스트 추출은 위첨자를 잃어 2n-1로 나와요). Flash 2비트 예시, SAR 예시와 비교기 수는 check_values.py가 다시 계산했어요. 실험 2를 Counter type으로 본 것과 Counter 변환 시간이 입력에 따라 달라진다는 것은 보충이에요.',
}
EXTRA = {'t-start': [nref('s-scope'), nref('s-spec10')], 't-7490': [nref('s-netlist10')], 't-oc': [nref('s-netlist10'), nref('s-spec10')], 't-dac': [nref('s-netlist10'), nref('s-spec10')], 't-comparator': [nref('s-spec10')], 't-summing': [nref('s-spec10')]}
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
        x['reason'] = '예상문항이지만 기출이 다루지 않은 개념(' + {'q-dac-operation': '교안 DAC 회로 전체의 신호 흐름', 'q-counter-7490': '7490 카운터의 기능과 BCD 출력의 무게', 'q-rf-output': '귀환 저항 Rf와 출력 크기', 'q-comparator': '비교기 동작과 가변저항의 역할'}[pid] + ')을 보충해서 수록해요'
    x.pop('fragment', None)
    rep = O[BQ[pid]['representative_occurrence_id']]
    original = ''.join(p(html.escape(b['text'])) for b in rep['blocks'] if b['type'] == 'text' and b['id'].endswith('-text'))
    obj = dict(original=original, conditions=q.get('conditions', ''), ask=p(q['ask']), problem_figures=q.get('figs', []), hints=[dict(label='접근 순서', html=p(q['hint']))], solution=dict(steps=[dict(label=a, html=b) for a, b in q['steps']] + [dict(label='검산', html=p(q['verify'])), dict(label='주의', html=p(q.get('wb_pitfall', q['pitfall'])))], answer=p(q['answer'])), notes=[])
    rows.append((x, obj, q))

for typ, suffix, title, topic, page, cond, ask, answer, reason, verify, pitfall, cue, start in ITEMS:
    pid = 'q-qp-e10-' + suffix
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
        conditions += table(['핀', '이름', '역할'], BOARD_PINS, 'itt') + '<div class="work-board"><img src="figures/questions/counter-blank.png" alt="v1 배포 PDF 작도용 빈 보드"></div>'
        x['sources'] += [dict(source_id='s-board', pdf_page=1, printed_page=None)]
        pf = ['counter-given']
        steps = [('연결 기준', p(answer) + table(['넷', '핀'], BOARD_NETS, 'tb') + p('CLK는 외부 신호원이고 QA~QD는 측정점이에요. IC 위치·홀 좌표가 달라도 같은 넷이면 인정해요.')),
                 ('완성 결선도', '<p>초록 선은 QA(12번) → CLKB(1번), 파란 선은 GND, 빨간 선은 +5V예요. 보라 원은 신호발생기를 물릴 CLK(14번) 자리와 QA~QD 측정점이에요. 7490은 5번이 +5V, 10번이 GND예요.</p><img src="figures/solutions/counter-complete.png" width="270" style="max-width:100%;height:auto" alt="완성 결선도: 7490 BCD 카운터">'),
                 ('논리 검산', p(reason) + p(verify) + p(pitfall))]
    q = {}
    obj = dict(original=p(ask), conditions=conditions, ask=p({'true_false': '참(T)·거짓(F) 판정', 'fill_blank': '빈칸의 값', 'short_answer': '이유를 담은 설명', 'breadboard': '완성한 작도'}[typ]), problem_figures=pf, hints=[dict(label='접근 단서', html=p(cue))], solution=dict(steps=[dict(label=a, html=b) for a, b in steps], answer=p(answer)), notes=[])
    rows.append((x, obj, q))
    M['problems'].append(x)

M['problems'] = [P[i] for i in ORDER] + [x for x in M['problems'] if not x.get('bank_question_id')] + [P[i] for i in NOT_INCLUDED]
figures.build(R, M)
(R / 'workbook').mkdir(exist_ok=True)
(R / 'problem-explanations').mkdir(exist_ok=True)


explanation_source = Path(__file__).with_name('problem-explanations')
for x, obj, q in rows:
    pid = x['id']
    conditions = strip(obj['conditions'])
    if x.get('question_type') == 'breadboard':
        conditions = conditions.replace('<table>', '<table class="chip-spec">')
    obj['conditions'] = mark_work_tables(conditions)
    obj['solution']['steps'] = [s for s in obj['solution']['steps'] if s['label'] not in q.get('wb_skip', ())]
    for s in obj['solution']['steps']:
        s['html'] = strip(s['html'])
        if q.get('wb_noimg'):
            s['html'] = re.sub(r'<p><img[^>]+></p>', '', s['html'])
    (R / 'workbook' / f'{pid}.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf8')
    copyfile(explanation_source / f'{pid}.html', R / 'problem-explanations' / f'{pid}.html')

STAT = {pid: v[1] for pid, v in NOT_INCLUDED.items()}
for q in I['questions']:
    x = P[q['question_id']]
    q['authoring_status'] = 'ready' if x['status'] == 'included' else STAT[q['question_id']]
    q['selection_reason'] = x['reason']
copyfile(explanation_source / 'table-layout.json', R / 'problem-explanations/table-layout.json')
(R / 'manifest.json').write_text(json.dumps(M, ensure_ascii=False, indent=2), encoding='utf8')
(R / 'authoring-index.json').write_text(json.dumps(I, ensure_ascii=False, indent=2), encoding='utf8')
print('authored', len(rows), 'included')
