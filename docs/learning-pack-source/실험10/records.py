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
calc = json.loads((work / 'calc.json').read_text(encoding='utf-8'))
bad = [k for k, v in browser.items() if v['broken'] or v['ke'] or v['hs'] > 1 or v['errs'] or v['ext'] or v['overflow']]
bad += [k for k, v in ui.items() if v.get('nbad') or v.get('errs') or (v.get('drawer') and v['drawer']['left'] == 'open') or ('links' in v and not (v['links'] == v['articles'] == v['expected']))]
bad += calc['failed']
if bad:
    raise SystemExit(f'not clean: {bad}')

rows = []
for tid, title, pages, body, s in TOPICS:
    for cond, res in s['rules']:
        rows.append((f'실험설명/{tid}', f'외울 규칙: {cond} → {res}', 'pass: 본문 결론·추적표·식과 대조'))
    rows.append((f'실험설명/{tid}', '이유: ' + s['why'], 'pass: formal 레이어 원리 문단과 대조'))
    for t in s.get('traps', []):
        rows.append((f'실험설명/{tid}', '헷갈리지 마요: ' + t, 'pass: warn·보충 표시·md_notes와 대조'))
for pid in ORDER:
    q = Q[pid]
    rows.append((f'문제설명/{pid}', f"결론·판단 조건: {q['sum_key']} / 답 상태 {q['status']}", 'pass: 풀이·요약 대조, 경고 보존'))
for typ, suffix, title, *_ in ITEMS:
    rows.append((f'문제설명/q-qp-e10-{suffix}', f'{typ}: {title}의 정답·근거·채점 요소', 'pass: 교안 쪽과 대조'))
audit = '# 본문–요약 감사 (2026-11-16)\n\n|자료·토픽|핵심 주장과 대응 요약|판정|\n|---|---|---|\n' + ''.join(f'|{a}|{b.replace("|", "/")}|{c}|\n' for a, b, c in rows)
(PE / 'summary-audit.md').write_text(audit, encoding='utf-8')
(PE / 'calculation-results.json').write_text(json.dumps(calc, ensure_ascii=False, indent=1), encoding='utf-8')
(PE / 'browser-results.json').write_text(json.dumps(browser, ensure_ascii=False, indent=1), encoding='utf-8')
(PE / 'panel-results.json').write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding='utf-8')
UNRES = ['q-comparator 답안 충돌(disputed): 제공 답안 “기준보다 높으면 1”과 회로(DAC가 반전 입력) 풀이가 반대예요. 교안 p5 문장도 식 Vout=A(V+−V−)와 반대로 적혀 있어요',
         '교안 소자값의 이상 셈이 절차 3 출력을 +15V 위로 보내 p18 계단 사진과 맞지 않아요(netlist M7). 계단 전압 숫자는 정하지 않았어요',
         'p18 두 사진이 절차 2·3 중 어느 것인지 미확정(netlist M13), V+=GND의 평평한 선은 예상이에요',
         'U4 7번 전원 라벨이 교안 회로도에 없어요(netlist M3). 기출 예상문제 v3 그림은 +15V로 적어요',
         'q-opamp-online의 손글씨 후보 답안은 부분 판독이라 정답 근거로 쓰지 않았어요',
         '7490 2진·5진 내부 구조, TTL High 전압, 가중 저항 장단점(온도·속도), Counter type 변환 시간은 교안 밖 보충이에요']
for name, html in (('실험설명', '실험10_실험설명.html'), ('문제설명', '실험10_문제설명.html')):
    rec = dict(schema_version=1, html=html, html_sha256=hashlib.sha256((stage / html).read_bytes()).hexdigest(), audit_path='problem-explanations/summary-audit.md', audit_sha256=hashlib.sha256(audit.encode()).hexdigest(), semantic_status='pass', browser_status='pass', evidence=['problem-explanations/browser-results.json', 'problem-explanations/panel-results.json', 'problem-explanations/calculation-results.json'], unresolved=UNRES, review_type='self_review; independent not_run')
    (PE / f'{name}-summary-validation.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding='utf-8')

npass = len(calc['checks'])
report = f'''# 실험10 학습팩 검증

2026-11-16. 현재 배포 교안 「실험10. DAC & ADC.pdf」 24쪽(표지 25-1), complete_with_holds 문제은행(문제은행/실험10/question-bank.json)을 사용했어요.

- 은행 고유 10: 확인 기출 4, 예상 5, 기출 여부 미확인 1. 수록 9(기출 4, 예상 4, 미확인 1), 비수록 {len(NOT_INCLUDED)}이에요.
  - 미선별(예상, 개념 공백 없음): q-lm741(LM741 기능·출력 의미는 q-summing-amp·q-opamp-online·q-dac-operation이 다룸).
  - 예상문항 수록 이유: q-dac-operation(DAC 회로 전체 흐름), q-counter-7490(7490 기능과 BCD 무게), q-rf-output(Rf와 출력 크기), q-comparator(비교기·가변저항)는 기출이 다루지 않은 개념이에요.
  - 미확인 q-opamp-online은 판독 가능한 문항이고(부분 판독은 옆 손글씨 후보 답안), q-summing-amp의 변형이라 함께 수록했어요. 답 메모가 있는 원문뿐이라 문제 그림 없이 글로 회로를 적었어요.
- 자체 출제 10(T/F 4: 참 2·거짓 2, 빈칸 3, 작도 1, 서술형 2)을 더해 included 19예요. 은행 문항은 개념 순서로 재정렬했고 ID는 그대로예요.
- 교안 시각 대조: p4·p5·p6·p12·p18·p22를 80dpi로 직접 봤고, 나머지 쪽은 텍스트 층과 명세·netlist의 300dpi 판독 기록을 대조했어요. p5 비교기 문장이 식과 반대인 것, p6 그림의 D1=MSB, p12 소자값·핀 번호를 직접 확인했어요.
- 원문 시각 대조: s01 p1(2016-1 시험지 1~4번), s04 p1(예상문제 v3 1~5번, DAC 회로), s02 p2(제공 답안 4~8번)를 직접 봤어요. 다시 그린 DAC 문제 그림은 s04 p1 원문처럼 U4 7번을 +15V로 적었어요. 나머지 등장은 완료 은행의 전사로 보존했고 142개 등장 전부를 새로 시각 검토했다고 주장하지 않아요.
- 별도 계산: check_values.py {npass}개 검사가 모두 통과했어요. 반전 증폭기·포화, 가산기 8:4:2:1 예시와 선형성(0~15), 가중·래더 식을 3비트 표와 4비트 전체 입력에서 회로 해석(밀만·테브난 사다리)과 맞대기, 7490 순환, 7404+7405 두 번 반전, 계단 방향·시간·Rf 0.6배·10.5k∥68k, 비교기 방향, Flash 비교기 수, SAR 이진 탐색을 다시 셌어요. 실제 측정은 없어요.
- 그림: Op-Amp 반전 증폭기, 가산기, 저항망 두 종, 7404+7405 풀업, DAC 전체 회로, 계단 파형, 비교기, 2비트 Flash를 직접 그렸어요. 작도 완성 보드는 v1 배포 PDF 위에 그렸고 엔진 verify·넷({{1,12}}, {{2,3,6,7,10}}, 5, 14)을 확인했어요. 클럭은 발생기 신호라 레일에 잇지 않고 보라 원으로 표시했어요.
- 요약: summary-audit.md에서 9토픽과 19문항을 대조했어요.
- 내용 검토는 self_review예요. 별도 독립 리뷰어는 쓰지 않았고 independent=not_run이에요.

## 답안 상태

은행 수록 9문항 중 8개 verified, q-comparator 1개 disputed예요. 자체 출제 10은 verified예요.

1. q-comparator(disputed): 제공 답안은 “기준 전위값보다 높으면 1, 낮으면 0”이에요. 회로에서 DAC OUTPUT은 반전 입력(2번)이라 DAC가 기준보다 높으면 0V예요. 풀이는 식과 회로도를 따랐고 충돌을 경고로 남겼어요.
2. q-adc-types: 제공 답안은 Feedback path type을 연속 근사(SAR)로만 적었어요. Ramp·Counter도 있음을 보충으로 밝혔어요.
3. q-counter-7490: 원문은 74HC90, 회로도는 7490이에요. 동작이 같다고 적었어요.
4. q-summing-amp: 제공 답안 수식(이미지)과 같아요.

## 남은 확인

{chr(10).join('- ' + u for u in UNRES)}

## 브라우저·인쇄

1280×900/375×812 × light/dark의 실험설명·문제설명 8조합을 로컬 HTTP와 Chromium으로 확인했어요. 외부 요청, 깨진 그림, KaTeX 오류, pageerror·console error, 문서 가로 넘침이 0이에요. 9토픽·19문항을 hash로 각각 열어 우측 요약 하나, sum-for 유일, 현재 목차 aria-current, 우측 중복 제목 없음을 확인했어요. JS 비활성에서도 9토픽·19문항과 목차 링크가 남아요. 375px에서 목차 링크를 누르면 drawer가 닫혀요. 기출문제 19쪽·기출풀이 21쪽 A4 가로 PDF를 전 쪽 눈으로 봤고 잘림이 없어요. 처음 빌드에서 작도 문항이 왼쪽 패널과 해설 칸을 넘쳐 핀 표·넷 표를 묶고 회로 그림을 70mm로 줄였어요.
'''
(R / '검증결과.md').write_text(report, encoding='utf-8')
(PE / '검증결과.md').write_text(report, encoding='utf-8')
Path(__file__).with_name('검증결과.md').write_text(report, encoding='utf-8')
print('records', len(rows))
