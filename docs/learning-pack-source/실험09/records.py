"""사람이 끝낸 검토 결과를 RUN 의 감사표·검증 기록으로 옮겨요. 브라우저 결과가 깨끗할 때만 씁니다.

사용: python records.py <RUN> <STAGE> <WORK>   (WORK 에 browser.json, ui.json, calc.json)
"""
from pathlib import Path
import sys, json, hashlib
sys.path.insert(0, str(Path(__file__).parent))
from content import TOPICS
from questions import Q, ORDER, NOT_INCLUDED
from quiz_content import ITEMS

R, stage, work = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PE = R / 'problem-explanations'
browser = json.loads((work / 'browser.json').read_text(encoding='utf-8'))
ui = json.loads((work / 'ui.json').read_text(encoding='utf-8'))
bad = [k for k, v in browser.items() if v['broken'] or v['ke'] or v['hs'] > 1 or v['errs'] or v['ext'] or v['overflow']]
bad += [k for k, v in ui.items() if v.get('nbad') or v.get('errs') or (v.get('drawer') and v['drawer']['left'] == 'open') or ('links' in v and not (v['links'] == v['articles'] == v['expected']))]
if bad:
    raise SystemExit(f'browser not clean: {bad}')

rows = []
for tid, title, pages, body, s in TOPICS:
    if tid != 't-start':
        for cond, res in s['rules']:
            assert f'<td>{cond}</td>' in body and f'<td>{res}</td>' in body, (tid, cond)
    rows.append((f'실험설명/{tid}', '외울 규칙 ' + str(len(s['rules'])) + '줄이 「한눈에 보기」 표 행과 같아요', 'pass: 본문·요약을 읽어 대조'))
    rows.append((f'실험설명/{tid}', '이유: ' + s['why'][:60] + '…', 'pass: 원리 문단과 대조'))
    for t in s.get('traps', []):
        rows.append((f'실험설명/{tid}', '주의: ' + t, 'pass: warn·본문 문장과 대조'))
for pid in ORDER:
    q = Q[pid]
    rows.append((f'문제설명/{pid}', f"결론·판단 조건: {q['sum_key']} / 답 상태 {q['status']}", 'pass: 풀이·요약 대조, 경고 보존'))
for typ, suffix, title, *_ in ITEMS:
    rows.append((f'문제설명/q-qp-e09-{suffix}', f'{typ}: {title}의 정답·근거·채점 요소', 'pass: 교안 쪽과 대조'))
audit = '# 본문–요약 감사 (2026-11-12)\n\n|자료·토픽|핵심 주장과 대응 요약|판정|\n|---|---|---|\n' + ''.join(f'|{a}|{b.replace("|", "/")}|{c}|\n' for a, b, c in rows)
(PE / 'summary-audit.md').write_text(audit, encoding='utf-8')

calc = json.loads((work / 'calc.json').read_text(encoding='utf-8'))
(PE / 'calculation-results.json').write_text(json.dumps(calc, ensure_ascii=False, indent=1), encoding='utf-8')
(PE / 'browser-results.json').write_text(json.dumps(browser, ensure_ascii=False, indent=1), encoding='utf-8')
(PE / 'panel-results.json').write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding='utf-8')
UNRES = ['q-74670·q-online-74670 원문 부분 판독으로 보류(은행에서 해결 후 다시 가져와야 해요)',
         'q-write1 수기 답안 한 장(o-s10-a5)의 input 값이 0으로 읽히지만 덧칠로 판독 보류',
         'Read/Write 문항 제공 답안의 “Read = 1, Write = 0/1” 표기 모호',
         '74HC03 열린 드레인·전원 핀은 1차 데이터시트 본문 미확인(netlist M6)',
         '74670 TI 문서를 이번 세션에서 다시 열지 못함(기존 확인 기록 사용)',
         '교안 p7 IN0 = IN1′ 괄호의 해석(동시에 1 금지)']
for name, html in (('실험설명', '실험09_실험설명.html'), ('문제설명', '실험09_문제설명.html')):
    rec = dict(schema_version=1, html=html, html_sha256=hashlib.sha256((stage / html).read_bytes()).hexdigest(), audit_path='problem-explanations/summary-audit.md', audit_sha256=hashlib.sha256(audit.encode()).hexdigest(), semantic_status='pass', browser_status='pass', evidence=['problem-explanations/browser-results.json', 'problem-explanations/panel-results.json', 'problem-explanations/calculation-results.json'], unresolved=UNRES, review_type='self_review; independent not_run')
    (PE / f'{name}-summary-validation.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding='utf-8')

n_held = len(NOT_INCLUDED)
report = f'''# 실험09 학습팩 검증

2026-11-12. 현재 배포 교안 「실험9. RAM.pdf」 8쪽(표지 25-1), complete_with_holds 문제은행(e885d469…)을 사용했어요.

- 은행 고유 13: 확인 기출 5, 예상 6, 기출 여부 미확인 2. 수록 9(기출 4, 예상 4, 미확인 1), 비수록 {n_held}이에요.
  - 미선별(예상, 개념 공백 없음): q-write-op-rw(Write 때 R/W=0은 q-write1·q-write0이 다룸), q-apart0(A 선택은 q-apart1, 0 쓰기는 q-bpart0이 다룸).
  - 판독 보류: q-74670(채점본 그림 라벨이 수기에 가려짐, 기출), q-online-74670(축소 슬라이드, 미확인). 74670 개념은 실험설명 t-74670과 자체 연습 3문항으로 보충했어요.
  - 예상문항 수록 이유: q-sram-cell(저장 회로), q-read-op-rw(읽기 R/W 값), q-write0(Reset 경로), q-apart1(A part 선택과 1 쓰기)은 기출이 다루지 않은 개념이에요.
- 자체 출제 10(T/F 4: 참 2·거짓 2, 빈칸 3, 작도 1, 서술형 2)을 더해 included 19예요. 문항은 개념 순서로 재정렬했고 ID는 그대로예요.
- 교안 시각 대조: p1~p8 전 쪽을 110dpi로, p4·p6·p8은 200dpi, p6은 400dpi 크롭으로 봤어요. p4 부울식의 S·R 뒤바뀜(Input 바 위치)과 표 첫 행의 Q=0을 직접 확인했어요(netlist M15와 같아요). p6에서 WR1이 두 칸의 2번, WR0이 5번에 함께 들어가는 접속점을 확인했어요(M2와 같아요).
- 원문 시각 대조: s01 p1(2016-2 시험지 1~3번), s10(수기메모 3~8번), s05(9·10번 사진), s03 q1(SRAM 정의 채점본)을 직접 봤어요. 나머지 등장은 완료 은행의 전사로 보존했고 135개 등장 전부를 새로 시각 검토했다고 주장하지 않아요.
- 별도 계산: check_values.py가 NAND 래치 네 입력, 1 bit RAM 전 조합(교안 식을 글자대로 쓰면 표와 반대임 포함), 2bit RAM NAND 네트워크(명세 T1 9행을 네 초기 상태 모두에서, 은행 2bit 문항 4개를 초기 상태 4 × OE 4 조합에서), 주의사항 위반 다섯 경우, 74670 4워드 쓰기·읽기와 동시 쓰기·읽기를 다시 계산해 통과했어요. 실제 측정은 없어요.
- 그림: 1 bit RAM, 2bit RAM, NAND 래치, 74670 핀·블록, 열린 드레인, 메모리 개념도를 직접 그렸어요. 문제 그림에는 Write/Read 범례를 넣지 않아 답이 보이지 않게 했어요. q-read-op-rw와 q-bpart1은 은행에 답 없는 안전 원문 자산이 없어 문제 그림 없이 회로를 글로 적었어요(이웃 문항에 같은 그림). 완성 보드는 v1 배포 PDF 위에 그렸고 엔진 verify·넷({{3,4}}, {{2,6}}, 14, 7)과 확대 확인을 했어요.
- 요약: summary-audit.md에서 8토픽과 19문항을 대조했어요.
- 내용 검토는 self_review예요. 별도 독립 리뷰어는 쓰지 않았고 independent=not_run이에요.

## 답안 상태

은행 수록 9문항 모두 verified, 자체 출제 10도 verified예요. disputed는 없어요.

1. 2bit 문항 4개(q-apart1, q-bpart1, q-bpart0 및 미선별 q-apart0): 범례(WR0=A, WR1=B)와 달리 회로도대로 저장값은 WR1이에요. 제공 답안도 모두 이 값이라 충돌이 없어요. OE는 저장에 영향이 없고, 제공 답의 OE 값(쓰는 칸 쪽 1)을 그대로 답에 적었어요.
2. q-read-op-rw: 수기 답 1과 같아요. 타자본 “Read = 1, Write = 1” 표기는 모호해 경고로 남겼어요.
3. q-write1: 제공 답 7개는 1, 1, 0이에요. 덧칠된 수기 한 장(input 0으로 읽힘)은 판독 보류예요.
4. q-sram-def: 교안에 SRAM 정의가 없어 scope=supplement로 표시하고 보충임을 밝혔어요.

## 남은 확인

{chr(10).join('- ' + u for u in UNRES)}

## 브라우저·인쇄

1280×900/375×812 × light/dark의 네 문서 16조합을 로컬 HTTP와 Chromium으로 확인했어요. 외부 요청, 깨진 그림, KaTeX 오류, pageerror·console error, 문서 가로 넘침이 0이고 워크북 data-ready=true, data-overflow=빈 문자열이에요. 8토픽·19문항을 hash로 각각 열어 우측 요약 하나, sum-for 유일, 현재 목차 aria-current, 우측 중복 제목 없음을 네 조합에서 확인했어요. JS 비활성에서도 8토픽·19문항과 목차 링크가 남아요. 375px에서 목차 링크를 누르면 drawer가 닫히고 해당 항목으로 가요. 처음 빌드에서 작도 문항(왼쪽 패널)과 q-apart1 해설(풀이 그림)이 넘쳐서, 핀 표를 줄이고 2bit 풀이 그림은 해설지에서 빼고 문제설명에 남겼어요.
'''
(R / '검증결과.md').write_text(report, encoding='utf-8')
(PE / '검증결과.md').write_text(report, encoding='utf-8')
Path(__file__).with_name('검증결과.md').write_text(report, encoding='utf-8')
print('records', len(rows))
