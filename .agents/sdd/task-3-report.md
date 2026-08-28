# Task 3 Report: HDL 소스 코드, 디지털 시계 및 보드 핀맵/예제 이동

## Execution Status
- **Status:** DONE
- **Date:** 2026-08-27

---

## Completed Actions

### 1. Step 1: 스톱워치 모범코드 Wedu 이동 (`1_스톱워치_모범코드_Wedu`)
Moved the following 2 project directories (30 files total, 6,041,434 bytes) from `from_the_past/정리/나머지/` to `from_the_past/정리/HDL_소스_및_예제/1_스톱워치_모범코드_Wedu/`:
- `Stopwatch` (16 files, 4,948,215 bytes)
- `source` (14 files, 1,093,219 bytes)

### 2. Step 2: 통합 디지털시계 모듈 이동 (`2_통합_디지털시계_모듈`)
Moved the following 7 modular VHDL files & references from `from_the_past/정리/나머지/` to `from_the_past/정리/HDL_소스_및_예제/2_통합_디지털시계_모듈/`:
- `watch_top.vhd` (3,810 bytes)
- `clk_gen.vhd` (1,014 bytes)
- `mode_set.vhd` (1,054 bytes)
- `time.vhd` (3,491 bytes)
- `stop_watch.vhd` (3,429 bytes)
- `segment.vhd` (4,704 bytes)
- `참고자료_stop_watch.pdf` (414,028 bytes)

### 3. Step 3: 보드별 핀맵 및 기초예제 이동 (`3_보드별_핀맵_및_기초예제`)
Moved the following 6 items (1 directory + 5 files, 290 files total, 3,858,460 bytes) from `from_the_past/정리/나머지/` to `from_the_past/정리/HDL_소스_및_예제/3_보드별_핀맵_및_기초예제/`:
- `Nexys3_Master.ucf` (24,022 bytes)
- `stopwatch.vhd` (7,557 bytes)
- `stopwatch.xise` (41,072 bytes)
- `example` (285 files, 3,784,478 bytes)
- `LICENSE` (1,079 bytes)
- `README` (252 bytes)

### 4. Step 4: 오류 및 미완성 코드 격리 및 경고 README 작성 (`_오류_및_미완성_코드`)
Moved the following 6 items (2 directories + 4 files, 43 files total, 4,042,341 bytes) from `from_the_past/정리/나머지/` to `from_the_past/정리/HDL_소스_및_예제/_오류_및_미완성_코드/`:
- `stopwatch1` (13 files, 9,549 bytes) - 듀얼 엣지 트리거 등 문법 오류로 합성 불가
- `stopwatch_book` (26 files, 4,018,745 bytes) - `SEL_ST_SP` 미연결 및 클록 분주비 오류
- `stopwatch_static.vhd` (3,432 bytes) - 48개 I/O 핀 요구 및 초 카운터 자리올림 로직 누락 버그
- `stopwatch_static.vhd.bak` (3,423 bytes)
- `새 텍스트 문서.txt` (4,726 bytes)
- `1-4133.txt` (2,466 bytes)

Created warning `README.md` (714 bytes) documenting why these files are isolated and pointing to verified working reference codes.

---

## Verification Results
- **Item Count:** 21 items (5 directories + 16 files) moved + 1 README.md created.
- **File Count & Volume:** 370 source files (14,373,765 bytes) migrated + 1 README.md created.
- **Integrity Check:** Pre-move vs. post-move SHA-256 checksums matched 100% across all 370 files.
- **Directory Inspection:**
  - `1_스톱워치_모범코드_Wedu`: 2 directories (`Stopwatch`, `source`) present and verified.
  - `2_통합_디지털시계_모듈`: 7 files present and verified.
  - `3_보드별_핀맵_및_기초예제`: 1 directory (`example`) + 5 files present and verified.
  - `_오류_및_미완성_코드`: 2 directories (`stopwatch1`, `stopwatch_book`) + 4 files + 1 `README.md` present and verified.
- **Data Loss:** 0% (100% lossless migration).
