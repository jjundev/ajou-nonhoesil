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

### Task 2: 텀프로젝트 및 FPGA 설계 과제 자료 이동

**Files:**
- Source: `from_the_past/정리/나머지/`
- Target: `from_the_past/정리/텀프로젝트_설계/` 하위 3개 디렉토리

**Interfaces:**
- Consumes: `설계과제.pdf`, `설계환경구축및실습.pdf`, `설계 계획서.hwp`, `설계 제안서.hwp`, `project_2020-2_김지성`, `project verilog 압축 파일`, `calculator_modelsim`, `project2_201423042_홍선표`, `calculator.hwp`, `설계 코드-1.txt`, `VHDL_시계.hwp`
- Produces: 완벽히 정리된 텀프로젝트 레퍼런스 라이브러리

- [ ] **Step 1: 1_공식_가이드_및_기획 파일 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/설계과제.pdf" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/1_공식_가이드_및_기획/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/설계환경구축및실습.pdf" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/1_공식_가이드_및_기획/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/설계 계획서.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/1_공식_가이드_및_기획/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/설계 제안서.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/1_공식_가이드_및_기획/"
```

- [ ] **Step 2: 2_계산기_프로젝트_Verilog_2020_김지성 프로젝트 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/project_2020-2_김지성" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/2_계산기_프로젝트_Verilog_2020_김지성/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/project verilog 압축 파일" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/2_계산기_프로젝트_Verilog_2020_김지성/"
```

- [ ] **Step 3: 3_계산기_및_도어락_레퍼런스_VHDL 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/calculator_modelsim" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/project2_201423042_홍선표" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/calculator.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/설계 코드-1.txt" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/VHDL_시계.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL/"
```

- [ ] **Step 4: 이동 검증**

```bash
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/1_공식_가이드_및_기획"
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/2_계산기_프로젝트_Verilog_2020_김지성"
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/텀프로젝트_설계/3_계산기_및_도어락_레퍼런스_VHDL"
```
Expected: 모든 파일 및 폴더가 100% 정상 배치됨.

---

### Task 3: HDL 소스 코드, 디지털 시계 및 보드 핀맵/예제 이동

**Files:**
- Source: `from_the_past/정리/나머지/`
- Target: `from_the_past/정리/HDL_소스_및_예제/` 하위 4개 디렉토리
- Create: `from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/README.md`

- [ ] **Step 1: 1_스톱워치_모범코드_Wedu 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/Stopwatch" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/1_스톱워치_모범코드_Wedu/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/source" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/1_스톱워치_모범코드_Wedu/"
```

- [ ] **Step 2: 2_통합_디지털시계_모듈 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/watch_top.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/clk_gen.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/mode_set.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/time.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stop_watch.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/segment.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/참고자료_stop_watch.pdf" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/"
```

- [ ] **Step 3: 3_보드별_핀맵_및_기초예제 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/Nexys3_Master.ucf" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stopwatch.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stopwatch.xise" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/example" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/LICENSE" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/README" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/"
```

- [ ] **Step 4: _오류_및_미완성_코드 격리 및 README 작성**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stopwatch1" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stopwatch_book" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stopwatch_static.vhd" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/stopwatch_static.vhd.bak" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/새 텍스트 문서.txt" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/1-4133.txt" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/"
```

경고 README 작성:
```markdown
# ⚠️ 주의: 오류 및 미완성 코드 아카이브

이 디렉토리에 포함된 파일들은 과거 학생 과제 제출물 중 **문법 오류(Synthesis Error), 자리올림 로직 버그, 미연결 신호** 등이 포함되어 있어 실제 보드 동작이 보장되지 않는 파일들입니다.

- `stopwatch1/`: VHDL 듀얼 엣지 트리거 등 문법 오류로 합성 불가
- `stopwatch_static.vhd`: 48개 I/O 핀 요구 및 초 카운터 자리올림 로직 누락 버그
- `stopwatch_book/`: `SEL_ST_SP` 신호 미연결 및 클록 분주비 오류 (1MHz 생성)

**정상 동작 코드는 상위의 `1_스톱워치_모범코드_Wedu` 및 `2_통합_디지털시계_모듈`을 참조하세요.**
```

---

### Task 4: 가이드라인, 조교 채점 기준 및 서식 이동

**Files:**
- Source: `from_the_past/정리/나머지/`
- Target: `from_the_past/정리/가이드라인_및_기준/`

- [ ] **Step 1: 채점 기준 및 가이드라인 파일 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/실험보고서 평가기준.txt" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/가이드라인" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/예비보고서 양식.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/FPGA pin map (1).xlsx" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/read me.txt" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준/"
```

- [ ] **Step 2: 이동 검증**

```bash
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/가이드라인_및_기준"
```
Expected: 5개 항목 정상 존재 확인.

---

### Task 5: 소자 데이터시트, 오실로스코프 파형 및 영상 이동

**Files:**
- Source: `from_the_past/정리/나머지/`
- Target: `from_the_past/정리/소자_데이터시트_및_미디어/` 하위 3개 디렉토리

- [ ] **Step 1: 1_데이터시트_및_핀아웃 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/datasheet.pdf" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/keypad scan.pdf" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/ic칩.txt" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/147411.gif" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/74-76-diagram.jpg" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/74HC03.jpg" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/74HC20-pinout.jpg" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/74hc42-bcd-todecimal.jpg" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/74hc670.png" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/92110-74HC76-J-K-Flip-Flop-Pic002-700x700.jpg" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/"
```

- [ ] **Step 2: 2_실측_오실로스코프_파형 이동 (이미지 55개)**

```python
import os, shutil, glob

src_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지"
dst_dir = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/2_실측_오실로스코프_파형"

img_extensions = ('.jpg', '.png', '.gif')
for f in os.listdir(src_dir):
    if f.lower().endswith(img_extensions):
        shutil.move(os.path.join(src_dir, f), os.path.join(dst_dir, f))
```

- [ ] **Step 3: 3_실험실_실기영상_8주차 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/8주차 대면실험 영상"/* "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/3_실험실_실기영상_8주차/"
rmdir "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/8주차 대면실험 영상"
```

- [ ] **Step 4: 미디어 이동 검증**

```bash
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃"
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/2_실측_오실로스코프_파형"
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/소자_데이터시트_및_미디어/3_실험실_실기영상_8주차"
```

---

### Task 6: 전 학기 보고서(`camui20`) 및 실험 1 심화 보고서 이동

**Files:**
- Source: `from_the_past/정리/나머지/`
- Target: `from_the_past/정리/전학기_모범_실습보고서_camui20/` & `from_the_past/정리/예비보고서/실험1/`

- [ ] **Step 1: camui20 전 학기 실습보고서 11종 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지"/논리회로_실습보고서*.hwp "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/전학기_모범_실습보고서_camui20/"
```

- [ ] **Step 2: 실험 1 심화 과제 및 풀보고서 이동**

```bash
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/논회실 실험 1.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/실험1/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/실험1 과제1.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/실험1/"
mv "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/실험1 과제2.hwp" "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/실험1/"
```

- [ ] **Step 3: 보고서 이동 검증**

```bash
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/전학기_모범_실습보고서_camui20"
ls -la "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/예비보고서/실험1"
```
Expected: camui20 보고서 11개와 실험 1 심화 보고서 3개가 정상 이동됨.

---

### Task 7: 무결성 종합 감사, 잔여 디렉토리 정리 및 인벤토리 README 생성

**Files:**
- Delete: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지/`
- Create: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/README.md`

- [ ] **Step 1: 잔여 `나머지/` 디렉토리 완전 공백 검증 및 삭제**

```python
import os

target = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리/나머지"
if os.path.exists(target):
    remaining = [f for f in os.listdir(target) if not f.startswith(".")]
    print("Remaining items in 나머지:", remaining)
    assert len(remaining) == 0, f"Error: Remaining items exist: {remaining}"
    # Delete .DS_Store if present and rmdir
    ds_store = os.path.join(target, ".DS_Store")
    if os.path.exists(ds_store): os.remove(ds_store)
    os.rmdir(target)
    print("Successfully removed empty directory: 나머지")
```

- [ ] **Step 2: 전체 `정리/` 디렉토리 인벤토리 `README.md` 생성**

```markdown
# 📂 논리회로실험 과거 자료 정격 아카이브 (`from_the_past/정리`)

본 디렉토리는 아주대학교 논리회로실험 수강 및 FPGA 텀프로젝트를 위한 체계화된 레퍼런스 라이브러리입니다.

---

## 🗂️ 폴더별 상세 안내

1. **`강의노트/`**: 실험 1 ~ 10 주차별 이론 강의 슬라이드 및 실습 가이드 PDF
2. **`논회 강의노트/`**: Ch1 ~ Ch14 논리회로 이론 교재 정규 슬라이드
3. **`예비보고서/`**: 주차별 예비보고서 모음 (실험 1 ~ 12 및 실험 1 심화 풀세트)
4. **`결과보고서/`**: 주차별 결과보고서 모음 (실험 1 ~ 12)
5. **`퀴즈/`**: 실험 1 ~ 10 퀴즈 기출문제 및 정답 모음 (RENAME_MAP.md 포함)
6. **`전학기_모범_실습보고서_camui20/`**: 실험 1부터 12까지 전 학기 검토 질문 모범 답안 및 시뮬레이션 완벽 HWP 풀세트 (11종)
7. **`텀프로젝트_설계/`**:
   - `1_공식_가이드_및_기획/`: 공식 사양서, Quartus 환경설정 튜토리얼, 계획서/제안서
   - `2_계산기_프로젝트_Verilog_2020_김지성/`: 43p 만점 설계보고서 + Verilog 계산기 프로젝트 풀세트
   - `3_계산기_및_도어락_레퍼런스_VHDL/`: Structural VHDL RTL 계산기, ModelSim 자동 검증 TB, 디지털 도어락 VHDL
8. **`HDL_소스_및_예제/`**:
   - `1_스톱워치_모범코드_Wedu/`: 50MHz 단일클록 동기식 스톱워치 골드스탠다드
   - `2_통합_디지털시계_모듈/`: 24h 시계 + 스톱워치 + FND 동적 스캔 계층형 VHDL 시스템
   - `3_보드별_핀맵_및_기초예제/`: Nexys3, Basys2, DE0-Nano 보드 제약 파일 및 기본 예제
   - `_오류_및_미완성_코드/`: 문법 오류 및 미완성 학생 코드 격리 보관
9. **`가이드라인_및_기준/`**: 조교 공식 채점 루브릭(예보 20점/결보 23점+가산점 2점), 보고서 작성 가이드라인, DE0-Nano 핀맵
10. **`소자_데이터시트_및_미디어/`**:
    - `1_데이터시트_및_핀아웃/`: 74HC 소자 데이터시트 및 핀 다이어그램
    - `2_실측_오실로스코프_파형/`: TTL 인버터, 지연시간 등 브레드보드 실측 파형 캡처 55종
    - `3_실험실_실기영상_8주차/`: 8주차 대면실험 실기 시연 MP4 영상
```

- [ ] **Step 3: 최종 검증 스크립트 실행**

```bash
python3 -c '
import os

base = "/Users/hyunjun_macbook_pro/Documents/Univ/논회실/from_the_past/정리"
print("=== Current folders in 정리 ===")
for item in sorted(os.listdir(base)):
    if not item.startswith("."):
        sub = os.path.join(base, item)
        count = len(os.listdir(sub)) if os.path.isdir(sub) else os.path.getsize(sub)
        print(f"  [{item}] -> {count}")
'
```
Expected: `나머지`가 완전히 사라지고 10개 정돈된 카테고리 폴더 및 `README.md`가 깔끔하게 출력됨.
