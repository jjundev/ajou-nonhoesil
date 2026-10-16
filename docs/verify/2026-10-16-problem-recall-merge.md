# 2026-10-16 회상 기능 브랜치 병합 검증

대상: `main` (`34ca5f8d`) + `codex/logic-lab-problem-recall` (`c5f9a26c`). 사용자가 현재 상태 백업, 양쪽 변경 통합, 재생성·테스트, 병합 커밋·push 및 병합된 브랜치/worktree 정리를 승인했다.

## 백업

- 경로: `C:\Users\Hyunjun\Desktop\현준대학\26-2\논회실-merge-backup-20261016-213501`
- `working-tree.zip`: 당시 작업 파일 5,169개 후보와 Git index·HEAD·ORIG_HEAD·MERGE_HEAD·MERGE_MSG·MERGE_MODE·AUTO_MERGE. ZIP CRC 전체 검사 통과.
- `repository.bundle`: 모든 refs의 커밋 이력. `git bundle verify` 통과.
- 당시 status·unmerged index·branches·worktrees 목록을 함께 보존했다.
- 연결 worktree의 무시 파일 2,567개(원본 322,454,284바이트)는 `worktree-ignored-files.zip`으로 별도 보존하고 전체 CRC 검사를 통과했다.
- `integration-verification/`: 새 stage, 브라우저 결과, 전후 SHA-256, 발행 백업 경로 및 대표 스크린샷.

## 병합 기준

- main의 `.pack/` 배치, 표 레이아웃 JSON·CSS 동기화, 짧은 cue·이유·기존 풀이와 경고를 유지했다.
- 브랜치의 상세 개념·공식·성립 조건·요약과 전용 문제설명 스킬을 통합했다. 전용 스킬도 main의 `.agents/skills` 링크 규칙으로 연결했다.
- v2는 understand→recall→start→solve→verify→pitfall→retry. 단서 문장과 상세 개념은 하나의 recall 안에 둔다.
- v1의 원래 여섯 구역과 main의 recall-first 확장을 모두 읽으며 새 explain-stage 기본값은 v2다.
- 충돌한 원고에서 recall/요약 이외 구역의 텍스트 차이는 0건이었다. 실험06은 explanations.E를 정본으로 유지하고 HTML 조각 14개와 바이트 일치를 확인했다.
- main에서 제거된 옛 `자료/` 결과물과 동기 설명 갱신 테스트는 되살리지 않았다.
- 실험02 netlist는 두 부모 커밋에 공통인 LF 원본 바이트로 복원했다. 내용과 고정 checksum은 변경하지 않았다.

## 재생성·보존

| 실험 | 문항 | 보존한 비설명 파일 | 발행 전 자동 백업 |
|---|---:|---:|---|
| 실험01 | 12 | 170 | `실험01.backup-e152e8268bc1` |
| 실험02 | 14 | 184 | `실험02.backup-e3a22b397ccf` |
| 실험03 | 15 | 162 | `실험03.backup-e3b4d0892ffc` |
| 실험04 | 12 | 166 | `실험04.backup-8158de33c874` |
| 실험05 | 19 | 172 | `실험05.backup-3c7109a517cc` |
| 실험06 | 14 | 204 | `실험06.backup-e3d282237421` |

총 86문항을 설명 전용 stage로 재생성했다. main 기준 비설명 파일 1,058개와 전체 원문 SHA-256·문항 상태를 유지했다. 문제지·해설지 HTML/MD/PDF는 다시 만들지 않았다. source_visual 상태는 원문과 본문을 보존한 기존 검토 기록을 승계하며 이번 병합에서 새 시각검토를 실시했다는 뜻이 아니다. 내용 통합은 self_review, 새 독립 내용 검토는 not_run으로 기록했다.

## 검증

- 초기 코드·stage·v1/v2·렌더링 회귀 테스트: 95 passed. 이후 원래 v1 및 cue+상세 recall 조합 회귀 두 개를 추가했다.
- 별도 read-only 코드 리뷰: 중대한 지적 없음. 두 부모 대비 API·저장 경로·스킬 연결·버전 계약 확인. 86개 조각의 v2 검증과 엄격한 태그 균형 검사 통과. 이 리뷰는 실험 내용의 독립 검토로 표시하지 않는다.
- 새 stage 브라우저 검사: 86문항 × 375/1280px × light/dark = 344 문항 화면 검사. 회상·요약·목차·그림·수식·문서 가로 넘침·pageerror 검사 통과. 여섯 팩에서 JS 비활성 본문·목차 확인. 대표 스크린샷 시각 확인.
- 여섯 stage 및 발행 후 여섯 대상 모두 check_pack 통과. 발행 후 비설명 파일 해시 대조 통과.
- 첫 전체 테스트: 2 failed, 3394 passed, 7 skipped, 1249 subtests passed. 신규 cue 회귀 fixture의 요약 순서와 기존 결선도 AST 검사기의 f-string 파일명 가정 때문에 실패했다.
- 테스트만 수정했다: cue 요약을 계약대로 앞에 두고, 빌더 중복 검사는 사용하지 않는 파일명을 해석하지 않고 빌더 이름을 그대로 전부 검사한다. 별도 재리뷰에서 검사 약화 없음 확인. 해당 두 파일 재검증: 40 passed, 22 subtests passed.
- 두 번째 전체 테스트: 1 failed, 3394 passed, 7 skipped, 1250 subtests passed. 실패는 변경하지 않은 `test_affected_trace.py`의 네이티브 `os.spawnve` 자식 프로세스가 Python 3.14.7/Windows에서 `0xC0000005`로 종료한 경우다. 단독 재실행은 통과했으나 파일 전체를 다시 실행할 때 추적 유무 양쪽 native spawn에서 재발했다.
- 저장소·추적 훅 없는 최소 `os.spawnve` 코드도 같은 Python 3.14에서 접근 위반을 재현했다. 빈 환경과 상속 환경, 감사 훅 유무 모두에서 발생했다. 환경만의 문제라는 가설은 기각하고 테스트 변경은 되돌렸다.
- 최종 검증은 파일 단위로 나눈다. `test_affected_trace.py`는 설치된 Python 3.11 기반 임시 venv(pytest 9.1.1/xdist 3.8.0)에서 원래 내용 그대로 실행하고, 나머지 전체는 Python 3.14에서 실행한다. 테스트를 skip하거나 assert를 완화하지 않는다. 최종 결과는 아래에 기록한다.


## 최종 결과와 남은 환경 한계

후속 처리: 아래는 병합 당시 결과다. Windows 네이티브 오류의 원인과 이후 수정·재검증은 [별도 기록](2026-10-16-windows-native-spawn.md)을 따른다.

- Python 3.14, `python -m pytest tests/ -q --ignore=tests/test_affected_trace.py`: **3373 passed, 5 skipped, 1250 subtests passed**, 실패 0. JUnit: `full-suite-verified.xml`.
- 원래 `tests/test_affected_trace.py` 전체를 Python 3.11 임시 venv에서 검증: **20 passed, 2 skipped, 2 failed**. 두 실패는 동일한 Windows `os.spawnve` 접근 위반이다. JUnit: `trace-py311-tests.xml`.
- 따라서 **전체 스위트 통과라고 보고하지 않는다**. 병합 관련 학습팩·생성기·브라우저·기존 보고서·결선도 검사는 통과했지만 이 호스트의 네이티브 프로세스 테스트 두 건은 미해결이다. 저장소와 감사 훅을 제외한 최소 실행에서도 같은 오류가 났고 Python 버전을 바꿔도 재현됐다. 해당 테스트/추적기 세 파일은 main과 동일하며 회상 브랜치에는 원래 없다.
- 새 테스트/생성 코드의 실패 두 건은 수정 후 통과했고 별도 재리뷰에서 검사 약화가 없음을 확인했다. 네이티브 런타임 문제 때문에 원래 검사를 삭제하거나 skip하지 않았다.
- 전체 실행 종료 후 여섯 발행본을 다시 check_pack하고 원문 및 비설명 파일 1,058개의 해시를 재확인했다. 전부 통과했다.
- 사용자가 승인한 병합·push와 병합된 로컬 브랜치/worktree 정리를 진행한다. 런타임 문제를 회상 기능 회귀로 취급하거나 전체 통과로 숨기지 않는다. 최종 커밋/원격/정리 상태는 Git 및 백업의 완료 기록으로 확인한다.
