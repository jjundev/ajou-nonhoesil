# 실험4 기출 추출 — 새 세션 인계

## 현재 실험4 상태 (2026-09-30)

사용자 요청으로 세션 분리 순서를 변경해 현재 세션에서 원자료 직접 판독과 JSON 저장까지 완료했다.
[추출 JSON](../../../../문제은행/실험04/question-bank.json)과
[검증결과](../../../../문제은행/실험04/검증결과.md)를 먼저 확인한다.
상태는 complete_with_holds이며, 확인 기출 7개·예상문항 4개·기출 여부 미확인 3개·빈 번호 항목 1개를 보존했다.
다음 작업은 import 연결이며 Task 8을 바로 실행하지 않는다. 아래 요청문과 절차는 재추출이 필요한 경우의 참고 절차다.

이 문서를 새 세션에 전달해 원자료를 독립적으로 판독한다. 준비 세션의 임시 분석은 사용하지 않는다. 새 세션이나 학습팩 생성은 자동으로 시작하지 않는다.

## 새 세션 요청

```text
C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실
워크트리의 codex/logic-lab-review-pack 브랜치에서 작업해.

실험4 원자료 전체를 새로 판독해 문제은행/실험04/question-bank.json,
assets/, 검증결과.md를 만들어줘.

.claude/skills/logic-lab-review-pack/references/question-bank.md,
question-bank.schema.json과
docs/superpowers/specs/2026-09-29-question-bank-extraction-design.md를 먼저 읽어.

pdf 스킬로 회로·표·기호를 시각 대조하고 DOCX는 documents 스킬의 읽기 절차를 사용해.
tmp/review-pack-work/experiment04의 임시 분석은 열람하거나 전재하지 마.
제공 답안을 그대로 보존하되 독립 풀이, 학습팩 생성, Task 8,
원래 체크아웃 통합은 실행하지 마.
```

## 작업 순서

1. 지정 워크트리에서 `git status --short`, `git branch --show-current`를 확인한다. 다른 변경은 보존한다. 아래 inventory 결과를 파일시스템의 전체 목록과 대조한다. 확장자·파일명으로 후보를 제외하지 않는다.

   ```powershell
   python -m scripts.lab.review_pack.question_bank_cli inventory --root . --experiment 4
   ```

2. `tmp/question-bank/실험04-<고유실행ID>`를 새로 만든다. pdf/documents 스킬의 읽기·렌더 절차로 판독 자료를 만든다. 원본 PDF/DOCX/이미지는 수정하지 않는다. 지원하지 않는 파일도 source와 보류 이유를 남긴다.

3. 파일별 실제 페이지 수와 원문 메타데이터를 기록한다. 다음은 검증할 단서일 뿐 결론이 아니다: `2016-1` 파일명과 헤더 연도 차이, 종합본 안의 예상문제, 일부 해설의 데이터선·선택선 수, 비활성 출력 X 표기, 3상태 버퍼 부품명. 원문을 읽기 전에 확정값을 쓰지 않는다.

4. 모든 페이지/문서를 순서대로 확인해 occurrences, blocks, 원문 그림을 먼저 남긴다. 소문항과 공통 지문, 조건·표·수식·회로를 보존한다. 텍스트 추출만으로 오버바·엣지·활성 극성을 확정하지 않는다. 답 노출 그림에는 answer/mixed와 노출 상태를 기록한다.

5. 전체 등장 기록을 확인한 후 questions를 묶는다. 조건이 동일한 중복만 묶고 불확실한 쌍은 duplicate_candidate, 조건이 다른 문제는 variant_of로 연결한다. 분반·조건을 확인한 후 제공 답안을 연결하고, 충돌하는 답안을 모두 보존한다. 답안의 옳고 그름을 풀이로 확정하지 않는다.

6. 파일별 감사 단위를 모두 작성한다. 판독 불가/부분 판독, 지원 불가 파일, 연결 못한 답안에는 대상과 이유를 남긴다. 문항이 없는 페이지도 blank/reference로 표시한다. 예상문제는 문항 단위로 predicted를 표시해 보존한다.

7. 작업 폴더의 JSON을 검사한다. `--bank`에는 실제 작업 JSON 경로를 넣는다.

   ```powershell
   python -m scripts.lab.review_pack.question_bank_cli check --root . --bank tmp/question-bank/실험04-<고유실행ID>/question-bank.json
   ```

   검사기는 파일을 고치지 않는다. 오류를 수정한 뒤 다시 검사한다. pass는 기계 검사만 뜻한다. 실제 시각 대조 범위를 checks.source_visual에 기록하고 검증결과.md에 대상·결과·미해결을 쓴다. JSON과 검증결과.md가 모순되면 먼저 수정한다.

8. 마지막으로 원문·그림 hash를 다시 검사한다. status는 감사 사실에 따라 complete 또는 complete_with_holds로 정한다. draft는 작업 폴더에 보존하고 최종 은행으로 복사하지 않는다.

9. `문제은행/실험04/`가 없을 때만 JSON, assets, 검증결과.md를 복사한다. 기존 폴더가 있으면 덮어쓰지 않고 작업본과의 차이를 보고한다. 복사 후 최종 위치에서 검사한다.

   ```powershell
   python -m scripts.lab.review_pack.question_bank_cli check --root . --bank 문제은행/실험04/question-bank.json
   ```

## 완료 보고

JSON·검증결과 링크, 파일·페이지별 시각 대조 범위, 고유 기출/예상/미확인 수, 중복 묶음 및 후보, 판독 보류, 미연결·충돌 답안을 보고한다. 독립 풀이 검증이나 학생의 이해 완료를 주장하지 않는다. 원자료와 기존 학습팩이 수정되지 않았는지 git diff로 확인한다.

다음 단계는 별도 import 연결 설계·구현이다. 이 추출 결과를 현재 build에 바로 넣거나, 기존 계획 Task 8을 자동 재개하지 않는다.
