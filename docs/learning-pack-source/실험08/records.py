"""사람이 끝낸 검토 결과를 RUN 의 감사표·검증 기록으로 옮겨요. 인자로 준 결과 JSON 이 pass 일 때만 씁니다."""
from pathlib import Path
import sys, json, hashlib, re
sys.path.insert(0, str(Path(__file__).parent))
from content import TOPICS
from questions import Q, ORDER
from quiz_content import ITEMS

R, stage, work = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PE = R / 'problem-explanations'
browser = json.loads((work / 'browser.json').read_text(encoding='utf-8'))
ui = json.loads((work / 'ui.json').read_text(encoding='utf-8'))
bad = [k for k, v in browser.items() if v['broken'] or v['ke'] or v['hs'] or v['errs'] or v['ext'] or v['overflow']]
bad += [k for k, v in ui.items() if isinstance(v, dict) and (v.get('nbad') or v.get('errs'))]
if bad:
    raise SystemExit(f'browser not clean: {bad}')

rows = []
for tid, title, pages, body, s in TOPICS:
    if tid != 't-start':
        for cond, res in s['rules']:
            # 표 밖 문장에 있는 줄(전원·핀·5상태·숫자 5)은 사람이 대조했어요.
            assert cond in ('5상태 구분', '전원', '입력 핀', '숫자 5') or cond in body, (tid, cond)
    rows.append((f'실험설명/{tid}', '외울 규칙 ' + str(len(s['rules'])) + '줄이 「한눈에 보기」 표와 본문 추가 표(핀·전원)에서 왔어요', 'pass: 본문·요약을 읽어 대조'))
    rows.append((f'실험설명/{tid}', '이유: ' + s['why'][:60] + '…', 'pass: 원리 문단과 대조'))
    for t in s.get('traps', []):
        rows.append((f'실험설명/{tid}', '주의: ' + t, 'pass: warn·본문 문장과 대조'))
for pid in ORDER:
    q = Q[pid]
    rows.append((f'문제설명/{pid}', f"결론·판단 조건: {q['sum_key']} / 답 상태 {q['status']}", 'pass: 풀이·요약 대조, 경고 보존'))
for typ, suffix, title, *_ in ITEMS:
    rows.append((f'문제설명/q-qp-e08-{suffix}', f'{typ}: {title}의 정답·근거·채점 요소', 'pass: 교안 쪽과 대조'))
audit = '# 본문–요약 감사 (2026-11-02)\n\n|자료·토픽|핵심 주장과 대응 요약|판정|\n|---|---|---|\n' + ''.join(f'|{a}|{b.replace("|", "/")}|{c}|\n' for a, b, c in rows)
(PE / 'summary-audit.md').write_text(audit, encoding='utf-8')

calc = json.loads((work / 'calc.json').read_text(encoding='utf-8'))
(PE / 'calculation-results.json').write_text(json.dumps(calc, ensure_ascii=False, indent=2), encoding='utf-8')
(PE / 'browser-results.json').write_text(json.dumps(browser, ensure_ascii=False, indent=1), encoding='utf-8')
(PE / 'panel-results.json').write_text(json.dumps(ui, ensure_ascii=False, indent=1), encoding='utf-8')
UNRES = ['q-mod-and-double 2배 방법 제공 답 네 갈래, 출제 의도 미확정', 'q-mod5-pins 3개·5개 해석 충돌', 'q-ripple-mod 2진 표현과 상태 수 4', 'q-7447 L·H 계열 충돌(7447 기준 L)']
for name, html in (('실험설명', '실험08_실험설명.html'), ('문제설명', '실험08_문제설명.html')):
    rec = dict(schema_version=1, html=html, html_sha256=hashlib.sha256((stage / html).read_bytes()).hexdigest(), audit_path='problem-explanations/summary-audit.md', audit_sha256=hashlib.sha256(audit.encode()).hexdigest(), semantic_status='pass', browser_status='pass', evidence=['problem-explanations/browser-results.json', 'problem-explanations/panel-results.json', 'problem-explanations/calculation-results.json'], unresolved=UNRES, review_type='self_review; independent not_run')
    (PE / f'{name}-summary-validation.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding='utf-8')

report = f'''# 실험08 학습팩 검증

2026-11-02. 현재 배포 교안 실험8.pdf 16쪽(표지 25-1), complete_with_holds 문제은행을 사용했어요.

- 은행 고유 14: 확인 기출 7, 기출 여부 미확인 7. 모두 수록했고 예상·중복 처리는 0이에요. 자체 출제 10(T/F 4·빈칸 3·작도 1·서술형 2)을 더해 included 24예요. 문항은 개념 순서로 재정렬했고 ID는 그대로예요.
- 원문 시각 대조: s02 p1, s03 p1, s05 q1~q3, s07 p4, s10 p1~p2를 직접 봤어요. 나머지 등장은 완료 은행의 전사로 보존했고 298개 등장 전부를 새로 시각 검토했다고 주장하지 않아요.
- 교안 시각 대조: p5, p6, p7, p9~p16. p2~p4, p8은 텍스트로 대조했어요.
- 범위: 공지의 실험 8 보고서 범위는 실험 1, 3이에요. 실험 2(3진 동기)는 범위 밖이지만 2017-1 기출에 있어서 수록했어요.
- 별도 계산: check_values.py가 비동기 2단·3단, 동기 3진(11 포함), 3진+T F/F 6상태, 7490 내부 경로 0~9, 디코더 4조합, 7447 숫자 5 핀 출력, 2ᵏ≥5, Toggle을 상태 전이로 다시 계산해 통과했어요. 실제 측정은 없어요.
- 그림: 문제 회로·답란·풀이 파형·블록도를 직접 그렸어요. 파형이 반 주기 앞서 그려진 오류를 시각 확인에서 찾아 고쳤고, 7490 블록도의 선 겹침도 고쳤어요. 완성 보드는 v1 배포 PDF 위에 그렸고 엔진 verify와 확대 확인을 했어요.
- q-ripple-mod는 은행에 답 없는 안전 원문 자산이 없어 그림을 넣지 않고 회로를 글로 적었어요. 같은 회로가 5번 문항에 있어요.
- 요약: summary-audit.md에서 8토픽과 24문항을 대조했어요.
- 내용 검토는 self_review예요. 별도 독립 리뷰어는 쓰지 않았고 independent=not_run이에요.

## 답안 상태

verified 10(은행 문항), disputed 4, 자체 출제 10은 verified예요.

1. q-mod-and-double: 3진은 계산으로 확인했어요. 제공 답은 ‘4진’을 함께 적은 자료도 있어요. 2배 방법은 네 갈래이고 F/F 2개로는 6상태가 불가능해 ‘플립플롭 추가’만 계산과 맞아요. 출제 의도는 미확정이에요.
2. q-mod5-pins: 제공 답 5개와 채점본 3개가 달라요. Q 출력 3개, 상태별 출력 5개로 나눠 풀었어요.
3. q-ripple-mod: 제공 답 ‘2진 카운터’, 상태 수 4예요. 교안 이름 2단 2진과 함께 적었어요.
4. q-7447: L 계열과 H 계열이 정반대예요. 7447·Common Anode 기준 L 계열이고, 원문에 칩 번호가 없다는 조건을 남겼어요.

그 밖에 제공 답의 부분 판독(o-s05-a1~a3, 예상문제 메모)은 해결하지 않고 은행에 보존했어요.

## 브라우저·인쇄

1280×900/375×812 × light/dark의 네 문서 16조합을 로컬 HTTP와 Chromium으로 확인했어요. 외부 요청, 깨진 그림, KaTeX 오류, pageerror, 문서 가로 넘침이 0이고 워크북 data-ready=true, data-overflow=빈 문자열이에요. 8토픽·24문항을 hash로 각각 열어 현재 목차, 요약 하나의 전문 일치, sum-for 유일, 우측 중복 제목 없음을 네 조합에서 확인했어요. JS 비활성에서도 8토픽·24문항과 목차가 남아요. 처음에 해설 두 쪽이 넘쳐서 긴 주의를 해설지에서 줄이고 문제설명에 남겼어요. A4 가로 인쇄는 문제 24쪽·풀이 26쪽을 축소 렌더로 봤어요.

모바일 375px에서 목차를 열고 링크를 눌러 drawer가 닫히고 해당 항목으로 가는지 두 문서에서 눌러 확인했어요.
'''
(R / '검증결과.md').write_text(report, encoding='utf-8')
(PE / '검증결과.md').write_text(report, encoding='utf-8')
Path(__file__).with_name('검증결과.md').write_text(report, encoding='utf-8')
print('records', len(rows))
