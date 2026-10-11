"""Author the 실험06 RUN: figures, fragments, workbook JSON, explanations, manifest, authoring index."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.lab.review_pack.work_table import mark_work_tables, FIELDS
from figlib import render_png, sha
import figs
from sections import S, TOPICS
import problems as PR
from explanations import E

REPO = Path(__file__).resolve().parents[3]
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else REPO / 'tmp/review-pack/실험06-r20261011a'
REVIEW = '--pass' in sys.argv  # mark figures reviewed only after visual check

manifest = json.loads((RUN / 'manifest.json').read_text(encoding='utf-8'))
index = json.loads((RUN / 'authoring-index.json').read_text(encoding='utf-8'))
bank = json.loads((RUN / 'evidence/question-bank.json').read_text(encoding='utf-8'))
assets = {a['id']: a for a in bank['assets']}
MAN = 's-a9792f60486135b0'
NOTICE = 's-130a964ad2ce2dbf'
DS76 = 's-9ab67da34de194d4'
PIN76 = 's-597ad821dc922e60'
EXTRA_SOURCES = [
    dict(id=MAN, path='강의노트/실험6. Latch & Flip-Flop.pdf', sha256='dbacbefa5f6ef60738f2749aabd7ccbaeaa55d9c87416dee368d5d231e52de37', kind='manual', edition='current'),
    dict(id=NOTICE, path='강의노트/공지사항/2026-09-14_[필독]_논리회로실험_보고서_관련_공지.md', sha256='49c08dec92f3f4c15395bccafdecde311c56df07f68041ef103641409b7d5d50', kind='notice', edition='unknown'),
    dict(id=DS76, path='from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/74-76-diagram.jpg', sha256='c9ee65eab8aa988e1d1719bcc57f1095dcd1fe1e1bd592a8cb1d52f566f5d1fb', kind='datasheet', edition='unknown'),
    dict(id=PIN76, path='from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/92110-74HC76-J-K-Flip-Flop-Pic002-700x700.jpg', sha256='2f43076301a1de5fc03e3912522d423854b0f8a8d3d15cac1019ec76f8c8d2da', kind='datasheet', edition='unknown'),
]
have = {s['id'] for s in manifest['sources']}
for s_ in EXTRA_SOURCES:
    if s_['id'] not in have:
        manifest['sources'].append(s_)
problems = {p['id']: p for p in manifest['problems']}

# ------------------------------------------------------------------ figures
F = RUN / 'figures'
for sub in ('questions', 'solutions'):
    (F / sub).mkdir(parents=True, exist_ok=True)

note_figs = {
    'memory-sr-timing': figs.memory_fig('Enable이 1인 SR 래치가 S·R 펄스 뒤에도 값을 기억하는 타이밍도'),
    'sr-basic-nand': figs.latch('NAND 두 개로 만든 기본 S-R 래치', 'basic', w=760),
    'sr-latch-enable': figs.latch('Enable이 있는 SR 래치 (실험 1)', 'sr'),
    'd-latch': figs.latch('Enable이 있는 D 래치 (실험 2-1)', 'd'),
    'jk-latch': figs.jk_latch('Enable이 있는 JK 래치 (실험 3-1, 보충)'),
    'level-vs-edge': figs.level_edge_fig('D 래치와 D 플립플롭의 비교 타이밍도'),
    'hc76-pinout': figs.hc76_fig('74HC76 핀 배치'),
    'tff-from-jk': figs.tff_fig('J-K 플립플롭으로 만든 T 플립플롭'),
}
for name, fg in note_figs.items():
    figs.save(fg, F / f'{name}.svg')

W_MM = 150.0
registry = []


def refs_for(pid, asset_ids=None):
    q = problems[pid]
    if asset_ids:
        keys = set()
        for aid in asset_ids:
            loc = assets[aid]['location']
            keys.add((loc['source_id'], loc['pdf_page']))
        got = [r for r in q['sources'] if (r['source_id'], r['pdf_page']) in keys]
        if got:
            return got
    return [q['sources'][0]]


def register(fid, pid, role, fg, asset_ids, derivation, notes):
    sub = 'questions' if role == 'problem' else 'solutions'
    svg = F / sub / f'{fid}.svg'
    png = F / sub / f'{fid}.png'
    h_mm = round(W_MM * fg.h / fg.w, 3)
    svg.write_text(fg.svg(physical=(W_MM, h_mm)), encoding='utf-8')
    render_png(svg, png, W_MM, dpi=300)
    registry.append(dict(
        id=fid, question_id=pid, role=role, svg=f'figures/{sub}/{fid}.svg', png=f'figures/{sub}/{fid}.png',
        svg_sha256=sha(svg), png_sha256=sha(png), w_mm=W_MM, h_mm=h_mm,
        source_asset_ids=asset_ids, source_refs=refs_for(pid, asset_ids), derivation=derivation,
        answer_exposure='none' if role == 'problem' else 'present',
        review_status='pass' if REVIEW else 'not_run', review_notes=notes))


register('q-sr-nand-00-given-01', 'q-sr-nand-00', 'problem', figs.latch('기본 S-R latch 회로 (문제)', 'basic', w=760), ['a-s02-p2-o-s02-q8'],
         '기출_단답형 8번 그림의 NAND 두 개(74HC00 1·2→3, 4·5→6)와 교차 되먹임(2번←Q′, 4번←Q)을 읽고 새로 그렸어요.',
         'S가 1번, R이 5번에 들어가고 2번에 Q′, 4번에 Q가 연결된 것을 원문과 대조했어요. 답(Q=Q′=1)은 그림에 없어요.')
register('q-rs-latch-given-01', 'q-rs-latch', 'problem', figs.latch('R-S Latch 회로 (문제)', 'sr', ('S', 'C', 'R')), ['a-s03-p1-o-s03-q2'],
         '예상문제 2번 그림(74HC00 1·2→3, 4·5→6, 9·10→8, 12·13→11)의 배선을 읽고 새로 그렸어요. 입력 이름은 원문처럼 S·C·R이에요.',
         '10번에 Q′, 12번에 Q가 되먹여지는 것을 원문과 대조했어요. 진리표 답은 그림에 없어요.')
register('q-rs-quiz-given-01', 'q-rs-quiz', 'problem', figs.latch('R-S Latch 회로 (문제)', 'sr', ('S', 'C', 'R')), ['a-s08-p1-o-s08-q1'],
         '퀴즈 해설 1번 문제 상자의 R-S Latch 그림을 읽고 새로 그렸어요. 해설의 노란 피드백 선은 넣지 않았어요.',
         '문제 상자 그림과 같은 연결(앞단 NAND 2개, 교차 NAND 2개)인지 대조했어요. 변형 회로(답)는 그림에 없어요.')
register('q-dff-table-given-01', 'q-dff-table', 'problem', figs.latch('D F/F 회로 (문제)', 'd', ('S', 'C')), ['a-s05-p1-o-s05-q3'],
         '예상 v3 3번 그림(74HC04 1→2, 74HC00 4개)을 읽고 새로 그렸어요. 원문처럼 입력 이름을 S·C로 두었어요.',
         'S가 1번 핀과 NOT 입력으로 갈라지고 NOT 출력이 5번 핀으로 가는 것을 원문과 대조했어요. 답 표는 그림에 없어요.')
register('q-jkff-short-given-01', 'q-jkff-short', 'problem', figs.jk_latch('J-K F/F 회로 (문제)', ('J', 'C', 'K')), ['a-s02-p2-o-s02-q6'],
         '기출_단답형 6번 그림(74HC10 1·2·13→12, 3·4·5→6, 74HC00 1·2→3, 4·5→6)을 읽고 새로 그렸어요.',
         '1번 핀에 Q′, 5번 핀에 Q가 되먹여지는 루프를 원문과 대조했어요. 답 표는 그림에 없어요.')
register('q-rs-quiz-solution-01', 'q-rs-quiz', 'solution', figs.jk_latch('R-S Latch를 변형한 JK Latch (S 자리가 J, R 자리가 K)', ('J', 'C', 'K')), [],
         '해설의 “Q′ 값 피드백, Q 값 피드백” 변형을 3입력 NAND 회로로 직접 다시 그렸어요.',
         '게이트 지연 모델로 네 J·K 조합과 짧은 C 펄스의 Toggle을 계산해 확인했어요.')
register('q-dff-design-solution-01', 'q-dff-design', 'solution', figs.latch('D F/F 진리표를 만족하는 회로', 'd', ('D', 'C')), [],
         'S=D, R=D′인 Enable SR 래치를 직접 설계해 그렸어요(NOT 1, NAND 4).',
         '게이트 모델로 표의 세 행(C=1, D=0/1, C=0 유지)을 계산해 확인했어요.')
register('q-jkff-design-solution-01', 'q-jkff-design', 'solution', figs.jk_latch('J-K F/F 진리표를 만족하는 회로', ('J', 'C', 'K')), [],
         'J·C·Q′, K·C·Q를 받는 3입력 NAND 두 개와 교차 NAND 두 개로 직접 설계해 그렸어요.',
         '게이트 모델로 표의 다섯 행을 계산했고, C=1 유지 시 race-around와 짧은 펄스의 단일 Toggle을 확인했어요.')
register('q-tff-solution-01', 'q-tff', 'solution', figs.tff_fig('J-K F/F로 만든 T F/F'), [],
         'J와 K를 T로 묶은 블록도를 직접 그렸어요. 클록 원은 74HC76(하강 엣지) 기준이에요.',
         'T=0 유지, T=1 Toggle을 74HC76 동작 모델로 확인했어요.')

registry.sort(key=lambda r: r['id'])
(F / 'redraw-manifest.json').write_text(json.dumps(dict(schema_version=1, figures=registry), ensure_ascii=False, indent=2), encoding='utf-8')

# ------------------------------------------------------------------ fragments
(RUN / 'sections').mkdir(exist_ok=True)
(RUN / 'workbook').mkdir(exist_ok=True)
(RUN / 'problem-explanations').mkdir(exist_ok=True)
for tid, html in S.items():
    (RUN / 'sections' / f'{tid}.html').write_text(html, encoding='utf-8')
for pid, obj in PR.P.items():
    obj = {**obj, **{k: mark_work_tables(obj[k]) for k in FIELDS}}     # 채울 표는 풀이 칸으로
    (RUN / 'workbook' / f'{pid}.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
for pid, html in E.items():
    (RUN / 'problem-explanations' / f'{pid}.html').write_text(html, encoding='utf-8')

# ------------------------------------------------------------------ manifest
manifest['title'] = 'Latch & Flip-Flop — 1비트를 기억하는 회로'
manifest['edition_status'] = 'current'
FINAL = '--final' in sys.argv  # only after source/content/independent/browser checks are recorded in 검증결과.md
CHK = dict(source_visual='pass', content='self_review', independent='pass', browser='pass') if FINAL else \
    dict(source_visual='not_run', content='not_run', independent='not_run', browser='not_run')
manifest['checks'] = dict(CHK)
manifest['note_presentation_version'] = 2
manifest['review_presentation_version'] = 2
manifest['problem_explanation_version'] = 1
manifest['explanation_checks'] = dict(CHK)
if FINAL:
    (RUN / '검증결과.md').write_bytes((Path(__file__).parent / '검증결과.md').read_bytes())
manifest['figure_manifest'] = 'figures/redraw-manifest.json'
extra_src = {'t-start': [NOTICE], 't-74hc76': [DS76, PIN76]}
manifest['topics'] = [dict(id=i, title=t, requires=req,
                           sources=[dict(source_id=MAN, pdf_page=pg, printed_page=None) for pg in pages] +
                                   [dict(source_id=x, pdf_page=None, printed_page=None) for x in extra_src.get(i, [])],
                           fragment=f'sections/{i}.html', **({'md_notes': md} if md else {}))
                      for i, t, req, pages, md in TOPICS]

DECISIONS = {
    'q-dlatch-design': ('duplicate', '주어진 D·C·Q(t) 진리표와 요구(표를 만족하는 회로 설계)가 q-dff-design 과 같아요. 대상 이름만 “D Latch”/“D F/F”로 달라요. 표가 레벨 동작이라 설계 답(D 래치)도 같아요. 이름 차이는 q-dff-design 풀이에서 설명해요.', 'q-dff-design', 'not_selected'),
    'q-jklatch-design': ('duplicate', '주어진 J·K·C·Q(t) 진리표와 요구가 q-jkff-design 과 같아요. 대상 이름만 “J-K Latch”/“J-K F/F”로 달라요. 설계 답(JK 래치)도 같아요.', 'q-jkff-design', 'not_selected'),
    'q-rs-ff': ('duplicate', '같은 R-S 회로(S·C·R, 74HC00 4개)를 주고 진리표를 채우는 문항이에요. 이름(R-S F/F)과 “회로설계로 대체될 수 있음” 문구만 달라요. q-rs-latch 로 풀어요.', 'q-rs-latch', 'not_selected'),
    'q-rs-ff-short': ('duplicate', '같은 R-S 회로와 진리표 작성 요구예요(기출_단답형 4번, 실제 시행 근거 미확인). q-rs-latch 로 풀어요.', 'q-rs-latch', 'not_selected'),
    'q-dff-short': ('duplicate', '같은 D 회로(입력 표기 S·C)와 진리표 작성 요구예요(기출_단답형 5번). q-dff-table 로 풀어요. 이 자료 답안 둘째 행 “0 1 1”의 오기는 q-dff-table 노트에 남겼어요.', 'q-dff-table', 'not_selected'),
    'q-jkff-table': ('held', '대표 등장(예상 v3 4번)과 종합본 등장 모두 부분 판독이에요. v3에서는 J-K 회로가 4·5번 문장 뒤에 있어 어느 문항의 그림인지 확정할 수 없고, 종합본 4번 아래 그림은 D 회로예요. 조건을 추측해 채우지 않았어요. 같은 요구는 회로 소속이 분명한 q-jkff-short 로 다뤄요.', None, 'reading_hold'),
}
ordered = []
for pid in PR.ORDER:
    if pid in problems:
        p = problems[pid]
        p.update(status='included', topics=PR.PROBLEM_TOPICS[pid], title=PR.TITLES[pid],
                 reason='읽을 수 있는 고유 문항의 원문 조건을 수록하고 게이트 모델 계산으로 대조',
                 scope='supplement' if pid in PR.SCOPE_SUPP else 'current', given_answer=None,
                 derived_answer=PR.DERIVED[pid], answer_status='verified', workbook_fragment=f'workbook/{pid}.json',
                 explanation_fragment=f'problem-explanations/{pid}.html', duplicate_of=None)
        p.pop('fragment', None)
    else:  # new practice question
        p = dict(id=pid, kind='practice', status='included',
                 reason='기출에 없는 74HC76 하강 엣지·비동기 우선 추적을 보충하는 새 연습(실험 3-2 범위)',
                 topics=PR.PROBLEM_TOPICS[pid], sources=[], duplicate_of=None, scope='current', given_answer=None,
                 derived_answer=PR.DERIVED[pid], answer_status='verified', title=PR.TITLES[pid],
                 workbook_fragment=f'workbook/{pid}.json', explanation_fragment=f'problem-explanations/{pid}.html')
    ordered.append(p)
for pid, p in problems.items():
    if pid in PR.P:
        continue
    status, reason, dup, _ = DECISIONS[pid]
    p.update(status=status, reason=reason, duplicate_of=dup, topics=[], scope='current',
             derived_answer=None, given_answer=None, answer_status='unresolved')
    ordered.append(p)
manifest['problems'] = ordered

for q in index['questions']:
    pid = q['question_id']
    if pid in PR.P:
        q['authoring_status'] = 'ready'
        q['selection_reason'] = '원문 조건 대조 및 게이트 모델 계산을 마친 저작 완료 문항'
    else:
        status, reason, dup, astat = DECISIONS[pid]
        q['authoring_status'] = astat
        q['selection_reason'] = reason

(RUN / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(RUN / 'authoring-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print('ok', len(registry), 'figures;', len(PR.P), 'included;', len(DECISIONS), 'not included')
