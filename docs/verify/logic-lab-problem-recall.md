# 핵심 개념 보충 발행 검토

## 실험01 — 12문항

| 문항 ID | 단서 | 개념/기호 | 적용 조건/선택 이유 | 소문항 범위 | 원문 path/PDF page | 경고 보존 | 요약 일치 | 검토 결과/저자 재계산 |
|---|---|---|---|---|---|---|---|---|
| q-tt3-4row | 3 Input·빈 네 행 | ABC 입력, AND·OR·NOR·XOR, 보수 | 0/1·지정 000/001/101/111만; XOR 홀짝 | 4행×4열 | 기출_단답형.pdf p1 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 000→0010; 001→0101; 101→0100; 111→1101 |
| q-tt3-8row | 3 input·여덟 행 | 2³=8, ABC 순서, 게이트별 출력 | 각 열 같은 입력·3입력 XOR 홀수 조건 | 8행×4열 | 예상문제_v1.pdf p1 | 기존 pitfall 그대로 | 본문과 일치 | self_review; AND=111만 1; NOR=000만 1; XOR=001/010/100/111 |
| q-xor2-tt | 2-input XOR·L/H | 서로 다름, L=0/H=1, A′B+AB′ | 두 입력·표 기호로 복원 | 4행 | 기출_문제.pdf p1; 기출_정답.pdf p1 | 기존 pitfall 그대로 | 본문과 일치 | self_review; LL/LH/HL/HH→L/H/H/L |
| q-xor-graded | 1-1 symbol/table; 1-2 function | 추가 곡선·네 행·A′B+AB′ | 0/1 두 입력·기호/표/식 동치 | 1-1 기호+표; 1-2 식 | 기출_채점본.jpg (PDF page 없음) | 기존 pitfall 그대로 | 본문과 일치 | self_review; 01/10만 1; 11에서 두 곱항 0 |
| q-switching | 반복 P와 Q 전체 보수 | OR/AND/보수, 항등·멱등·흡수·분배 | PQ+PQ′ 구조; Q 전체 보수라 묶기 선택 | 식 단순화 전체 | 기출_단답형.pdf p1; 예상문제_v1.pdf p2 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 32조합: PQ+PQ′=V′+X |
| q-demorgan | De Morgan·중첩 윗줄 | 곱/합 보수·연산 교환·이중 보수 | 보수가 묶음 전체; 바깥부터 적용 | 식 전개 전체 | 예상문제_v1.pdf p1–2 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 32조합: 원식=ABC+D+E |
| q-deq | D/E/Q·출력 버블·B 접속점 | 중간 노드·OR/AND·결과 보수 | 그림 연결에 따라 D/E 각각 읽기; 충돌 유지 | D; E; Q | 기출_문제.pdf p1; 기출_정답.pdf p1 | 답안 충돌 보존 | 본문과 일치 | self_review; 8조합: D=(A+B)′,E=BC,Q=D+E |
| q-logicdiagram | 변형 없이·첫 괄호 윗줄 | NOT→괄호 OR/NOR→최종 AND | 보수 첫 괄호만·연산구조 보존 | 회로 전체 | 예상문제_v1.pdf p1 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 16조합: P=(A+B′)′,R=C+D′,F=PR |
| q-nand-xor | NAND만으로 XOR | (XY)′·서로 다름·공유 N1 | NAND만·중간 보수 매단계 계산 | NAND 회로+4행 | 기출_단답형.pdf p1; 예상문제_v1.pdf p1 | 기존 pitfall 그대로 | 본문과 일치 | self_review; N1/N2/N3/출력: 00=1110,01=1101,10=1011,11=0110 |
| q-nand3 | 2-input AND와 NAND 지정 | (ABC)′·곱 결합·최종 반전 | 첫 AND→마지막 NAND | 회로 전체 | 기출_문제.pdf p1; 강의노트 p13 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 8조합: 111만 0 |
| q-nor3-or-inv | OR와 Inverter 지정 | (A+B+C)′·합 결합·NOT | 최종 합만 반전·입력 개별 반전 아님 | 회로 전체 | 기출_채점본.jpg; 강의노트 p14 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 8조합: 000만 1 |
| q-cmos-nand3 | CMOS 3-input NAND | PMOS 0/NMOS 1·직렬/병렬 | 안정된 0/1·정적 이상적 CMOS | PMOS/NMOS 전체 회로 | 예상문제_v1.pdf p2 | 기존 pitfall 그대로 | 본문과 일치 | self_review; 8조합: pull-up=NOT pull-down; 111만 down 연결 |

원문·계산·브라우저 상세 기록: `docs/learning-pack-source/실험01/problem-explanations/검증결과.md`

실험01 발행 완료: v2 12문항; source_visual=pass, content=self_review, browser=pass, independent=not_run. 전후170개 설명 밖 파일 해시·문항/출처/토픽/기존checks 일치, 설명 밖 신규/삭제0. 원래 여섯 구역과 경고는12문항 모두 문자열 보존.

백업: `C:/Users/Hyunjun/.codex/worktrees/logic-lab-problem-recall/논회실/복습노트/실험01.backup-a390ed552fcf`

브라우저 실제 검토:48회(375×900/1280×900 × light/dark ×12문항), 화면96개, 모든 recall/요약 판독; no-JS12문항. 상세 증거는 `output/validation/problem-recall/browser-01.json`, `source-01/`, `browser-01/`에 있어요. 다른 실험은 이 기록의 완료 대상이 아니에요.
