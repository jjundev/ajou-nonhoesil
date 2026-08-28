# `from_the_past/정리` 소장 가치 자료 분류 및 신규 폴더 체계 재배치 구현 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/나머지`에 혼재된 118개 항목(파일 107개, 서브디렉토리 12개)을 용도별 5대 신규 폴더(`텀프로젝트_설계`, `HDL_소스_및_예제`, `가이드라인_및_기준`, `소자_데이터시트_및_미디어`, `전학기_모범_실습보고서_camui20`)와 기존 주차별 보고서 폴더로 100% 무손실 이동(`mv`) 배치하고, `나머지` 폴더를 정리한다.

**Architecture:** Python 스크립트 기반의 원자적 파일 이동 및 무결성 검증 파이프라인. 각 단계별로 디렉토리 생성 -> 파일 이동 -> 이동 전후 파일 수 및 해시/용량 검증 -> 최종 잔여 디렉토리 정리 및 인벤토리 README 생성을 수행한다.

**Tech Stack:** Python 3 (os, shutil, pathlib), Bash (mv, mkdir, ls)

## Global Constraints

- 모든 작업은 무손실(`mv`)로 수행되어야 하며, 어떠한 소스 파일이나 보고서 원문도 삭제되거나 덮어쓰여져서는 안 된다.
- `from_the_past/정리/나머지/_중복_및_제외`는 원천 백업 보존을 위해 `from_the_past/_원천_아카이브/`로 안전하게 상위 이동한다.
- `camui20` 전 학기 보고서(11종)는 사용자의 지정에 따라 독립 폴더 `from_the_past/정리/전학기_모범_실습보고서_camui20/`로 격리 보관한다.
- 미완성/문법 에러 파일(`stopwatch1`, `stopwatch_static.vhd` 등)은 `_오류_및_미완성_코드/` 하위 폴더로 격리하고 경고 안내 `README.md`를 포함한다.

---

## File Structure

- **신설 디렉토리:**
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/_원천_아카이브/`
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/` (하위 3개 폴더)
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/` (하위 4개 폴더)
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준/`
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/` (하위 3개 폴더)
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/전학기_모범_실습보고서_camui20/`
- **수정/추가 문서:**
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/README.md`
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/README.md` (전체 정리 디렉토리 맵)
- **삭제 대상:**
  - `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/` (파일 이동 완료 후 빈 디렉토리 삭제)

---


---

### Task 1: 디렉토리 스캐폴딩 및 원천 아카이브(`_중복_및_제외`) 격리

**Files:**
- Create: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/_원천_아카이브/`
- Create: `from_the_past/정리/` 하위 5대 신규 디렉토리 및 서브디렉토리 일체
- Modify: `from_the_past/정리/나머지/_중복_및_제외` -> `from_the_past/_원천_아카이브/`로 이동

**Interfaces:**
- Consumes: `from_the_past/정리/나머지/` 기존 경로
- Produces: 5대 신규 분류 디렉토리 트리 및 `_원천_아카이브/`

- [ ] **Step 1: 대상 디렉토리 트리 일괄 생성**

```bash
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/_원천_아카이브"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/1_공식_가이드_및_기획"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/2_계산기_프로젝트_Verilog_2020_김지성"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/1_스톱워치_모범코드_Wedu"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/2_실측_오실로스코프_파형"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/3_실험실_실기영상_8주차"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/전학기_모범_실습보고서_camui20"
mkdir -p "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/실험1"
```

- [ ] **Step 2: `_중복_및_제외` 폴더를 `_원천_아카이브`로 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/_중복_및_제외"/* "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/_원천_아카이브/"
rm -rf "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/_중복_및_제외"
```

- [ ] **Step 3: 생성 디렉토리 및 이동 검증**

```bash
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/_원천_아카이브"
```
Expected: `2020-2 논회실`, `논리회로실험` 폴더 정상 존재 확인.

---

