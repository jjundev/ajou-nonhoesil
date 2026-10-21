# 체크리스트 현장 텍스트 축소 Implementation Plan

> **For agentic workers:** Use executing-plans to implement task-by-task.

**Goal:** 승인된 삭제안을 공통 생성 규칙과 실험07 HTML/PDF에 적용한다.
**Architecture:** 기존 명세·netlist·sidecar의 계산과 배선 데이터는 유지하고 출력 단계에서 중복과 저작용 정보를 제외한다. 원본 자료와 작성된 기록은 보존한다.
**Tech Stack:** Python, HTML/CSS, headless Chrome, pytest.
**Spec:** 이 채팅의 2026-10-21 삭제 설계안 및 사용자의 '실험07 + 공통 생성 규칙만 추천안대로' 지시.

## Global Constraints
- 실험01~06 HTML/PDF, 모든 기록.md, 기존 사용자 변경은 수정하지 않는다.
- 공통면·종료면, 칩별 핀 배선표, 출처·유도 이유, 작성·사진 안내, 위치도 각주, 중복 배선목록은 출력하지 않는다.
- 단계 그림·연결/분리 좌표·입출력 위치도·조작·예상값·실측 빈칸·단위는 보존한다.
- 회로별 메모 하나로 불일치 빈표를 대체한다. 사진명 열은 유지한다.
- 자동 커밋·push는 하지 않는다. 사용자가 구현을 명시했으므로 계획 재승인 없이 현 작업공간에서 진행한다.

## Review Focus
- 순차 회로의 초기화·클럭 에지와 상태 행 순서 보존.
- 단계 없는 회로의 유일한 배선/계측 정보 보존.
- 칩별 미사용 핀의 지시가 다른 칩에 붙지 않음.
- 삭제된 공통면·종료면·머리글로 빈 PDF 쪽이 생기지 않음.
- PDF 출력 삭제가 record.py의 공유 GUIDE/기록 데이터를 변경하지 않음.

### Task 1: 출력 축소와 회귀 검사
**Files:** scripts/lab/render.py, scripts/lab/io_locations.py, tests/test_lab_render.py, tests/test_lab_observation_render.py, tests/test_lab_assembly_render.py, tests/test_lab_checklist_minimal.py.
- [x] 기존 검사 기준선 실행.
- [x] 실험07의 삭제 영역 부재와 단계·관측·실측 보존을 검사하고 실패 확인.
- [x] 공통 출력 제거, 단계 정보 중복 정리, 완성본과 기록 구역 축소 구현.
- [x] 이전 출력에만 해당하는 검사는 새 계약에 맞게 갱신하고 관련 검사 실행.

### Task 2: 생성 규칙과 실험07 산출물
**Files:** .claude/skills/prep-lab-checklist/{SKILL.md,template.html}, 보고서/실험07/체크리스트/체크리스트.{html,pdf}.
- [x] 생성 스킬·CSS를 새 출력 계약에 맞게 정리.
- [x] 명세/netlist 검증 후 기록 파생 단계를 건너뛰고 실험07 HTML → fit_pages → PDF 실행.
- [x] 전체 검사, HTML·그림 검사, PDF 렌더 시각 검사, 보호 파일 해시 및 diff 범위 검증.

## Progress
- Planning: 사용자 승인된 범위를 구체화. 별도 설계 재질문/워크트리/커밋을 추가하지 않고 현 작업공간에서 구현.

- Task 1: complete — 관련 검사 322 passed, 201 subtests passed. 기존 출력만 요구하던 검사는 삭제/갱신하고 작업·관측·실측 보존 검사를 추가했다.
- Task 2: complete — 실험07 PDF 31쪽, 그림 31개·조작/결과 표 15개·실측 빈칸 126개 보존. 보호 파일 20개 해시 동일.
- Review: 전원 조작을 sidecar 존재만으로 숨기는 문제를 정확히 일치하는 연결 절만 제거하도록 수정. 실험07 고유 투입/발생기/접지 조건은 setup에 보존. 단계가 있어도 완성본 JSON을 검증한다.
- Ruling: 검토자가 판단하지 않은 PDF 품질은 전 페이지 접촉 시트와 확대 화면, 쪽·텍스트 경계 검사로 확인. 기존 전체 검사 실패는 변경 전후 이름 집합이 동일하여 이 범위에서 수정하지 않는다.
- Full suite: 3343 passed, 1203 subtests passed, 73 skipped, 기존 8 failed/33 errors 동일. 마지막 메타 안내 한 줄 제거 후 관련 검사 322개 재통과.
- 검증 기록: /tmp/logic-checklist-verification.md. 커밋·push 없음.
