# `camui20` 전 학기 실습보고서 병렬 PDF 변환 구현 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/전학기_모범_실습보고서_camui20/` 디렉토리 내의 11개 HWP 실습보고서를 멀티워커 병렬 Chrome CDP 자동화 엔진을 구축하여 고속으로 100% 무결성 PDF로 일괄 변환한다.

**Architecture:** 멀티프로세스 기반 병렬 변환기(`parallel_hwp_converter.py`). 각 워커는 독립된 포트(9222, 9223, ...)와 임시 유저 데이터 디렉토리를 가진 헤드리스 Chrome을 구동하여 Allinpdf를 통해 병렬로 변환 및 다운로드를 수행하며, 변환 완료 후 `%PDF-` 헤더 및 파일 무결성을 검증한다.

**Tech Stack:** Python 3 (concurrent.futures, subprocess, urllib, json, socket), Chrome DevTools Protocol (CDP), Allinpdf

---

## Global Constraints

- 11개 HWP 파일(`논리회로_실습보고서(1~12)-camui20.hwp`) 모두 원본 손실 없이 동일 폴더에 1:1 대응하는 `.pdf` 파일로 변환되어야 한다.
- 모든 생성된 PDF는 100바이트 이상이어야 하며 유효한 `%PDF-` 매직 넘버 헤더를 포함해야 한다.
- 각 병렬 워커는 독립된 원격 디버깅 포트와 `--user-data-dir`를 사용하여 상호 간섭 없이 실행되어야 한다.
- 변환 완료 후 `from_the_past/정리/README.md`의 인벤토리 설명을 업데이트한다.

---

## File Structure

- **생성/수정 대상 소스:**
  - Create: `scripts/parallel_hwp_converter.py` (멀티워커 병렬 HWP->PDF 변환 스크립트)
  - Create: `tests/test_parallel_hwp_converter.py` (워커 포트 할당 및 PDF 유효성 검사 단위 테스트)
  - Modify: `from_the_past/정리/README.md` (PDF 지원 안내 반영)
- **변환 산출물 (11개 PDF):**
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(1)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(2)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(3)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(4)-camui20.pdf` (기존 완료)
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(5)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(6)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(7)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(8)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(10)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(11)-camui20.pdf`
  - `from_the_past/정리/전학기_모범_실습보고서_camui20/논리회로_실습보고서(12)-camui20.pdf`

---


---

### Task 1: 멀티워커 병렬 HWP 변환기 구현 및 단위 테스트 작성

**Files:**
- Create: `scripts/parallel_hwp_converter.py`
- Create: `tests/test_parallel_hwp_converter.py`

**Interfaces:**
- Produces: `parallel_convert_hwp(files: list[str], max_workers: int = 3, force: bool = False) -> dict`

- [ ] **Step 1: 단위 테스트 작성 (TDD: 파일 탐색, 워커 격리, PDF 유효성 검증)**

```python
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts.parallel_hwp_converter import discover_hwp_files, validate_pdf, resolve_output_pdf_path

class TestParallelHWPConverter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = str(Path(tempfile.mkdtemp()).resolve())
        (Path(self.temp_dir) / "sub").mkdir()
        (Path(self.temp_dir) / "sub" / "doc1.hwp").write_text("dummy")
        (Path(self.temp_dir) / "sub" / "doc2.HWP").write_text("dummy")
        (Path(self.temp_dir) / "sub" / "ignore.txt").write_text("dummy")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_files(self):
        files = discover_hwp_files(self.temp_dir)
        self.assertEqual(len(files), 2)
        self.assertTrue(all(f.lower().endswith(".hwp") for f in files))

    def test_validate_pdf(self):
        valid_pdf = os.path.join(self.temp_dir, "valid.pdf")
        with open(valid_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n" + b"A" * 150 + b"\n%%EOF")
        self.assertTrue(validate_pdf(valid_pdf))

        invalid_pdf = os.path.join(self.temp_dir, "invalid.pdf")
        with open(invalid_pdf, "wb") as f:
            f.write(b"NOT A PDF")
        self.assertFalse(validate_pdf(invalid_pdf))

    def test_resolve_output_path(self):
        hwp = os.path.join(self.temp_dir, "test.hwp")
        pdf = resolve_output_pdf_path(hwp)
        self.assertEqual(pdf, os.path.join(self.temp_dir, "test.pdf"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실패 확인 (RED)**

Run: `python3 -m unittest tests/test_parallel_hwp_converter.py`
Expected: `ModuleNotFoundError: No module named 'scripts.parallel_hwp_converter'`

- [ ] **Step 3: `scripts/parallel_hwp_converter.py` 구현 (GREEN)**

포트 분할(기본 포트 9222부터 워커당 +1), 독립 `user-data-dir`, `ThreadPoolExecutor` 또는 `ProcessPoolExecutor` 기반 병렬 스케줄러, 실시간 진행률 및 재시도 로직 구현.

- [ ] **Step 4: 단위 테스트 통과 확인 (GREEN)**

Run: `python3 -m unittest tests/test_parallel_hwp_converter.py`
Expected: 3 tests PASS.

---

