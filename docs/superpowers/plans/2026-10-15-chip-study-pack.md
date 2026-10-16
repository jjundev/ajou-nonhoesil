# 칩 정리 학습팩 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 실험01~05의 칩 번호·기능·전체 핀맵과 실제 사용 핀 중심 연습을 HTML 3개로 제공한다.

**Architecture:** 기존 review-pack의 로컬 노트 템플릿을 재사용하는 주제별 팩이다. 실험별 생성기 계약은 변경하지 않는다. 칩·문항 데이터와 재생성 스크립트는 출력 폴더의 .pack에 보존한다.

**Tech Stack:** Python, static HTML/CSS/JavaScript, inline SVG, existing note template.

**Spec:** 이 대화의 '칩 정리 학습팩 설계' 및 사용자 확정: 실험01~05만, 전체 핀맵 제공, 실제 사용하는 핀 중심 출제.

## Global Constraints

- 사용자에게 보이는 파일은 복습노트/칩 정리/정리노트.html, 문제풀이.html, 문제설명.html 세 개다.
- 실제 사용 10종을 핵심으로, 교안 준비물에 있으나 수행 제외인 139·148·153은 보충으로 구분한다.
- 칩 방향은 위에서 본 그림 기준이며 정확한 부품·핀 수를 명시한다.
- 새 연습은 기출로 표시하지 않는다. 실험06 이후 칩은 넣지 않는다.
- 네트워크 없이 학습 가능해야 한다. 원본 자료 및 기존 팩은 수정하지 않는다.
- 사용자 요청에 따라 계획 저장 후 현재 세션에서 직접 구현한다. 별도 승인 대기나 자동 커밋은 하지 않는다.

## Review Focus

- 74HC02는 일반 쿼드 게이트와 출력 핀 배치가 다름: 데이터 핀별 독립 기대값 대조.
- 74HC20의 3·11은 NC: 입력으로 오인하지 않는지 확인.
- 74HC42는 16핀·Active Low: 전원, 입력 가중치, 무효 BCD를 확인.
- 문제풀이와 문제설명의 ID·답이 일치하고 관련 노트 앵커가 존재해야 함.
- 모바일 핀 그림·표 가독성 및 인쇄에서 접힌 답안 누락 여부를 확인.

### Task 1: 자료와 칩 데이터 확정

**Files:** Create `복습노트/칩 정리/.pack/build.py`, `sources.json`.

- [x] 교안 준비물, 수행 범위 명세, 제조사 핀 설명을 대조한다.
- [x] 10종 핵심 칩과 3종 보충 칩에 전체 핀명, 기능, 관련 실험, 실제 사용 예를 기록한다.
- [x] 제조사 자료를 웹으로 확인하고 URL·참조 절을 sources.json에 남긴다. 직접 다운로드 403으로 PDF 로컬 보존은 하지 않는다.

### Task 2: 학습 문서 제작

**Files:** Create `정리노트.html`, `문제풀이.html`, `문제설명.html` and `.pack/` authoring assets.

- [x] 기존 로컬 노트 템플릿에서 공통 셸·목차·테마·요약을 재사용한다.
- [x] 전체 핀맵 SVG·핀 표·게이트 구성·동작표·배선 예·실수 비교를 생성한다.
- [x] 문항별 문제, 힌트, 짧은 답, 단계별 해설을 한 데이터에서 생성한다.
- [x] 문제풀이의 정답은 접어 두고 문제설명은 펼친 상태로 제공한다.
- [x] 모든 학습 문서·자원을 로컬 상대 경로로 연결한다.

### Task 3: 검증 및 전달

**Files:** Create `.pack/verify.py`, `.pack/검증결과.md`.

- [x] 독립 핀 기대값, 문항 정답 계산, 핀맵 완전성, 링크 대상을 검사한다.
- [x] 브라우저에서 PC·375px 모바일, 테마, 목차, 답안 열기, 인쇄 CSS를 확인한다.
- [x] 미확인 항목과 검증 범위를 기록한다.
- [x] 세 HTML 링크를 전달하고 정리노트를 앱에 연다.
