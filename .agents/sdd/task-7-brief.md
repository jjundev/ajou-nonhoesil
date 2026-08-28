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
