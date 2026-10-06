"""Author the 실험05 RUN: figures, fragments, workbook JSON, manifest, authoring index."""
import json, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.lab.review_pack.work_table import mark_work_tables, FIELDS
from figlib import render_png, sha
import figs
from sections import S, TOPICS
import problems as PR

REPO = Path(__file__).resolve().parents[2]
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'tmp/review-pack/실험05-r20261005a'
REVIEW = '--pass' in sys.argv  # mark figures reviewed only after visual check

manifest = json.loads((RUN / 'manifest.json').read_text(encoding='utf-8'))
index = json.loads((RUN / 'authoring-index.json').read_text(encoding='utf-8'))
bank = json.loads((RUN / 'evidence/question-bank.json').read_text(encoding='utf-8'))
assets = {a['id']: a for a in bank['assets']}
EXTRA_SOURCES = [
    dict(id='s-977902e67f269bac', path='강의노트/실험5. Decoder & Encoder.pdf', sha256='1f37ba56b7e9648c3ad7a6c8d895d236a5593dba74031d3b7d75b07f4c52dbf4', kind='manual', edition='current'),
    dict(id='s-130a964ad2ce2dbf', path='강의노트/공지사항/2026-09-14_[필독]_논리회로실험_보고서_관련_공지.md', sha256='49c08dec92f3f4c15395bccafdecde311c56df07f68041ef103641409b7d5d50', kind='notice', edition='unknown'),
    dict(id='s-d2c7c0c179bdd665', path='from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/74hc42-bcd-todecimal.jpg', sha256='3cce6fe75008b81476c6bb66e41251161818734b2710575913ebc95d49b28ab9', kind='datasheet', edition='unknown'),
]
have = {s['id'] for s in manifest['sources']}
for s_ in EXTRA_SOURCES:
    if s_['id'] not in have:
        manifest['sources'].append(s_)
by_path = {s['path']: s for s in manifest['sources']}
MAN = by_path['강의노트/실험5. Decoder & Encoder.pdf']['id']
problems = {p['id']: p for p in manifest['problems']}

# ------------------------------------------------------------------ figures
F = RUN / 'figures'
for sub in ('questions', 'solutions'):
    (F / sub).mkdir(parents=True, exist_ok=True)

note_figs = {
    'decoder-encoder-pair': figs.pair_fig(),
    'dec2x4-gates': figs.dec2x4_fig('2×4 디코더: NOT 2개와 AND 4개'),
    'bcd-decoder-74hc42': figs.bcd_decoder_fig(),
    'enc4x2-nand': figs.enc4x2_nand_fig('4×2 인코더: NOT 4개, 4입력 NAND 3개, 2입력 NAND 2개'),
    'hc148-block': figs.hc148_fig('74HC148 우선순위 인코더 블록도'),
    'excess3-encoder': figs.excess3_fig('십진수 0~5를 Excess-3 코드로 바꾸는 인코더', names=True),
    'demux-from-decoder': figs.demux_fig('디코더에서 만든 1×4 디멀티플렉서'),
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


GIVEN_EX = ('교안 p12와 기출 원문의 회로(스위치 6개, NOT 6개, 74HC20 4개)를 읽고 신호 연결을 직접 다시 그렸어요. 남는 NAND 입력은 VCC, 비트 이름과 SW5/SW0 위치는 원문과 같아요.')
GIVEN_EX_NOTE = '원문 회로의 NOT 배선과 74HC20 핀 연결을 확대해 대조했고, 같은 netlist를 계산해 Excess-3 값이 나오는지 확인했어요. 답 표는 그림에 넣지 않았어요.'
register('q-excess3-enc-exam-given-01', 'q-excess3-enc-exam', 'problem', figs.excess3_fig('Excess-3 인코더 회로 (문제)', names=True, compact=True), ['a-s03-p1-q5'], GIVEN_EX, GIVEN_EX_NOTE)
register('q-excess3-enc-6row-given-01', 'q-excess3-enc-6row', 'problem', figs.excess3_fig('Excess-3 인코더 회로 (문제)', names=True, compact=True), ['a-s11-p1-q7'], GIVEN_EX, GIVEN_EX_NOTE)
register('q-demux-from-dec-given-01', 'q-demux-from-dec', 'problem', figs.given_decoder_fig('2 to 4 디코더 게이트 회로 (문제)'), ['a-s05-p1-q3'],
         '원문 그림의 NOT 2개와 AND 4개 배선을 확대해 읽고 새로 그렸어요. 출력 이름은 원문처럼 붙이지 않았어요.',
         '위에서부터 S1S0=00, 01, 10, 11을 고르는 AND 순서와 NOT 위치를 원문 배선과 대조했어요. 정답(DMUX)은 그림에 없어요.')
register('q-74hc148-table-given-01', 'q-74hc148-table', 'problem', figs.given_148_fig('74HC148 우선순위 인코더 회로 (문제)'), ['a-s05-p1-q4'],
         '원문 그림의 74HC148 핀(IN0~IN7, EI, A0~A2, GS, EO)과 스위치 두 개의 짝수/홀수 묶음, EI의 GND 연결을 읽고 새로 그렸어요.',
         '스위치-입력 묶음은 문제 표의 행 패턴(짝수 입력끼리, 홀수 입력끼리 같은 값)과 원문 그림을 대조했어요. 출력 값은 그림에 없어요.')
register('q-dec2x4-design-solution-01', 'q-dec2x4-design', 'solution', figs.dec2x4_fig('2×4 디코더 완성 회로', a1='I1', a0='I0', outs=('O0', 'O1', 'O2', 'O3')), [],
         'NOT 2개와 2입력 AND 4개로 각 출력이 입력 조합 하나만 고르도록 직접 설계했어요.',
         '네 입력 조합을 계산해 각 출력이 번호와 맞는지, 게이트 수가 요구와 같은지 확인했어요.')
register('q-enc4x2-design-solution-01', 'q-enc4x2-design', 'solution', figs.enc4x2_nand_fig('4×2 인코더 NAND 구성 완성 회로'), [],
         '요구 게이트 수(NOT 4, 4입력 NAND 3, 2입력 NAND 2)에 맞춰 직접 설계했어요.',
         '한 줄만 켜진 네 경우를 회로대로 계산해 AB가 00, 01, 10, 11인지 확인했어요.')
register('q-demux-from-dec-solution-01', 'q-demux-from-dec', 'solution', figs.demux_fig('디코더를 활용한 1×4 디멀티플렉서 완성 회로'), [],
         '디코더의 AND를 3입력으로 바꾸고 D를 연결한 회로를 직접 그렸어요. 제공 답안의 74HC11 구성과 같은 구조예요.',
         '모든 S1S0·D 조합을 계산해 Yk=D·(S1S0=k)인지 확인했어요.')
register('q-demux-from-dec-graded-solution-01', 'q-demux-from-dec-graded', 'solution', figs.demux_fig('디코더를 활용한 1×4 디멀티플렉서 완성 회로'), [],
         '디코더의 AND를 3입력으로 바꾸고 D를 연결한 회로를 직접 그렸어요.',
         '모든 S1S0·D 조합을 계산해 Yk=D·(S1S0=k)인지 확인했어요.')

registry.sort(key=lambda r: r['id'])
(F / 'redraw-manifest.json').write_text(json.dumps(dict(schema_version=1, figures=registry), ensure_ascii=False, indent=2), encoding='utf-8')

# ------------------------------------------------------------------ fragments
(RUN / 'sections').mkdir(exist_ok=True)
(RUN / 'workbook').mkdir(exist_ok=True)
for tid, html in S.items():
    (RUN / 'sections' / f'{tid}.html').write_text(html, encoding='utf-8')
for pid, obj in PR.P.items():
    obj = {**obj, **{k: mark_work_tables(obj[k]) for k in FIELDS}}     # 채울 표는 풀이 칸으로
    (RUN / 'workbook' / f'{pid}.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

# ------------------------------------------------------------------ manifest
manifest['title'] = 'Decoder & Encoder — 코드와 켜진 줄을 서로 바꿔요'
manifest['edition_status'] = 'current'
manifest['checks'] = dict(source_visual='pass', content='self_review', independent='pass', browser='pass')
manifest['note_presentation_version'] = 2
manifest['review_presentation_version'] = 2
manifest['figure_manifest'] = 'figures/redraw-manifest.json'
NOTICE = 's-130a964ad2ce2dbf'
DS42 = 's-d2c7c0c179bdd665'
extra_src = {'t-start': [NOTICE], 't-bcd': [DS42]}
manifest['topics'] = [dict(id=i, title=t, requires=req,
                           sources=[dict(source_id=MAN, pdf_page=pg, printed_page=None) for pg in pages] +
                                   [dict(source_id=x, pdf_page=None, printed_page=None) for x in extra_src.get(i, [])],
                           fragment=f'sections/{i}.html', **({'md_notes': md} if md else {}))
                      for i, t, req, pages, md in TOPICS]

SCOPE_SUPP = {'q-demux-from-dec', 'q-demux-from-dec-graded'}
REASONS = {}
# non-included decisions: pid -> (status, reason, duplicate_of, authoring_status)
DECISIONS = {
    'q-prio-behavior': ('duplicate', '묻는 개념(동시 입력에서 우선순위 인코더가 어떤 출력을 내는가)과 모범 답이 q-prio-vs-binary 의 부분집합이에요.', 'q-prio-vs-binary', 'not_selected'),
    'q-quiz-excess3-merit': ('duplicate', 'Excess-3 코드의 장점(9의 보수)을 묻는 문항으로, q-excess3-why 의 답에 포함돼요. 문장은 달라요.', 'q-excess3-why', 'not_selected'),
    'q-sa-dec3x8': ('duplicate', '같은 문장의 3×8 디코더 진리표 문항이고 답 표도 같아요(열 순서만 A 쪽이 앞).', 'q-dec3x8', 'not_selected'),
    'q-sa-dec2x4-table': ('duplicate', '같은 문장·같은 답 표지만 이 자료에는 회로 그림이 없어요. 회로가 있는 q-quiz-dec2x4-table 로 풀어요.', 'q-quiz-dec2x4-table', 'not_selected'),
    'q-sa-excess3': ('duplicate', '“Excess-3 코드 설명(진리표, 사용이유)” 문항이고 제공 답은 사용 이유(9의 보수)뿐이에요. q-excess3-why 와 표(노트)로 다뤄요.', 'q-excess3-why', 'not_selected'),
    'q-sa-excess3-enc': ('duplicate', '같은 개념의 Excess-3 인코더 진리표 문항인데 이 자료에는 회로 그림과 표 입력 행이 없고 답 자리가 물음표뿐이에요. q-excess3-enc-6row 로 풀어요.', 'q-excess3-enc-6row', 'not_selected'),
    'q-quiz-latch-ff': ('other_experiment', 'Latch와 Flip-Flop는 실험 5(Decoder & Encoder)의 교안 범위가 아니에요. 순서회로 실험에서 다뤄요.', None, 'not_selected'),
    'q-quiz-rs-ff': ('other_experiment', 'R-S Flip-Flop 진리표는 실험 5(Decoder & Encoder)의 교안 범위가 아니에요. 순서회로 실험에서 다뤄요.', None, 'not_selected'),
    'q-quiz-jk-clr-pr': ('other_experiment', '74HC76 J-K Flip-Flop의 CLR/PR은 실험 5의 교안 범위가 아니에요. 플립플롭 실험에서 다뤄요.', None, 'not_selected'),
    'q-1of4-excess3-graded': ('held', '채점본 사진의 문항이 부분 판독이에요. 인쇄된 “1-out-of-4”와 열 머리가 취소선으로 지워지고 BCD가 손글씨로 쓰여 있어 공식 정정인지 응시자 메모인지 알 수 없어요. 세 번째 행이 0001로 인쇄되어 있어 q-1of4-excess3 와 조건이 달라요. 추측해 채우지 않았어요.', None, 'reading_hold'),
    'q-sa-enc-from-table': ('held', '표(Normal Count 00~11 → 1000, 0100, 0010, 0001)는 2비트 입력과 one-hot 출력이라 디코더로 보이는데 문장은 “Encoder 회로를 그려라”이고 제공 답이 물음표뿐이에요. 용어와 조건이 충돌해 조건을 정하지 못해 보류했어요.', None, 'held'),
}
for pid, p in problems.items():
    if pid in PR.P:
        p.update(status='included', topics=PR.PROBLEM_TOPICS[pid], title=PR.TITLES[pid],
                 reason='읽을 수 있는 고유 문항의 원문 조건을 수록하고 독립 풀이로 대조',
                 scope='supplement' if pid in SCOPE_SUPP else 'current', given_answer=None,
                 derived_answer=PR.DERIVED[pid], answer_status='verified', workbook_fragment=f'workbook/{pid}.json')
        p.pop('fragment', None)
    else:
        status, reason, dup, _ = DECISIONS[pid]
        p.update(status=status, reason=reason, duplicate_of=dup, topics=[], scope='supplement' if status == 'other_experiment' else 'current',
                 derived_answer=None, given_answer=None, answer_status='unresolved')
manifest['problems'] = list(problems.values())

# ------------------------------------------------------------------ authoring index
for q in index['questions']:
    pid = q['question_id']
    if pid in PR.P:
        q['authoring_status'] = 'ready'
        q['selection_reason'] = '원문 조건 대조 및 독립 계산을 진행할 저작 완료 문항'
    else:
        status, reason, dup, astat = DECISIONS[pid]
        q['authoring_status'] = astat
        q['selection_reason'] = reason

(RUN / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(RUN / 'authoring-index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print('ok', len(registry), 'figures;', len(PR.P), 'included;', len(DECISIONS), 'not included')
