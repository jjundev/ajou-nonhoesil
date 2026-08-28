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

