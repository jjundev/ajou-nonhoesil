# 강의노트(이론 vs 실험) 교집합 및 매핑 완전 분석 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `from_the_past/정리/논회 강의노트`(이론 11개 PDF)와 `from_the_past/정리/강의노트`(실험 11개 PDF) 총 22개 문서를 전수 탐색하여, 겹치는 개념·수식·소자·회로 동작 원리를 빠짐없이 정리한 최종 종합 매핑 보고서(`docs/강의노트_이론_실험_매핑_정리.md`)를 작성한다.

**Architecture:** PyMuPDF(fitz) 기반의 텍스트/슬라이드 전수 추출 파이프라인을 구축하고, 4개 도메인 클러스터(기초/CMOS, 조합논리, 순서논리, 메모리/신호변환/HDL)로 분할하여 병렬 서브에이전트를 통해 심층 대조 분석을 수행한 뒤, 이를 단일 체계적 종합 문서로 병합·검증한다.

**Tech Stack:** Python 3, PyMuPDF (fitz), Markdown (GitHub GFM, KaTeX/LaTeX 수식, 다이어그램/테이블 지원)

## Global Constraints

- 대상 디렉토리 1 (실험): `from_the_past/정리/강의노트` (11개 PDF: 실험1~10, Verilog 강의자료)
- 대상 디렉토리 2 (이론): `from_the_past/정리/논회 강의노트` (11개 PDF: Ch1, Ch2-part1/2, Chap3-part1/2, Chap6, Chap9_10, Chap9_10_sequential 1/2 & 2/2, Ch14-part1/2)
- 누락 방지: 22개 PDF 전 파일, 전 슬라이드를 전수 검사하여 매핑 누락이 없도록 구조화.
- 출력 산출물: `docs/강의노트_이론_실험_매핑_정리.md` (한글 Markdown, 이론↔실험 대응표, 세부 공통 개념/차이점/실습 소자 매핑 포함).

---

## File Structure

- Create: `scripts/extract_pdf_corpus.py` (22개 PDF 텍스트 및 슬라이드 메타데이터를 JSON/Markdown으로 덤프하는 스크립트)
- Create: `docs/강의노트_이론_실험_매핑_정리.md` (최종 종합 분석 및 교차 매핑 보고서)
- Create: `docs/plans/2026-08-17-lecture-notes-overlap-analysis.md` (본 계획서)

---

### Task 1: 22개 PDF 전수 텍스트 & 슬라이드 인덱스 추출 파이프라인 구축

**Files:**
- Create: `scripts/extract_pdf_corpus.py`
- Test: `scripts/extract_pdf_corpus.py` 실행 및 JSON 출력 검증

**Interfaces:**
- Consumes: `from_the_past/정리/강의노트/*.pdf`, `from_the_past/정리/논회 강의노트/*.pdf`
- Produces: `extracted_corpus/theory_summary.json`, `extracted_corpus/lab_summary.json` (각 슬라이드별 번호, 제목, 키워드, 본문 텍스트가 정형화된 JSON 데이터)

- [ ] **Step 1: Write the extraction script**

```python
# scripts/extract_pdf_corpus.py
import fitz
import os
import json
import unicodedata

def extract_pdf_data(folder_path, output_json):
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    results = {}
    normalized_files = sorted(os.listdir(folder_path))
    for f in normalized_files:
        if not f.endswith('.pdf'):
            continue
        fp = os.path.join(folder_path, f)
        doc = fitz.open(fp)
        pages_data = []
        for page_idx, page in enumerate(doc):
            text = page.get_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            title = lines[0] if lines else f"Page {page_idx + 1}"
            pages_data.append({
                "page_num": page_idx + 1,
                "title": title,
                "full_text": text
            })
        results[f] = {
            "file_name": f,
            "total_pages": len(doc),
            "pages": pages_data
        }
    with open(output_json, 'w', encoding='utf-8') as out:
        json.dump(results, out, ensure_ascii=False, indent=2)
    print(f"Extracted {len(results)} files to {output_json}")

if __name__ == '__main__':
    extract_pdf_data('from_the_past/정리/논회 강의노트', 'extracted_corpus/theory_corpus.json')
    extract_pdf_data('from_the_past/정리/강의노트', 'extracted_corpus/lab_corpus.json')
```

- [ ] **Step 2: Run script to verify extraction**

Run: `python3 scripts/extract_pdf_corpus.py`
Expected: PASS with 11 theory files and 11 lab files successfully extracted to `extracted_corpus/`.

- [ ] **Step 3: Verify extracted JSON corpus integrity**

Run: `python3 -c "import json; t=json.load(open('extracted_corpus/theory_corpus.json')); l=json.load(open('extracted_corpus/lab_corpus.json')); print(f'Theory files: {len(t)}, Lab files: {len(l)}'); assert len(t)==11 and len(l)==11"`
Expected: Output `Theory files: 11, Lab files: 11`

---

### Task 2: 도메인 1 심층 분석 - 기초 논리 게이트 & CMOS 전기적 특성

**Files:**
- Modify: `docs/강의노트_이론_실험_매핑_정리.md` (도메인 1 섹션 작성)

**Scope / Target Documents:**
- 실험: `실험1.pdf` (Basic Gates & De Morgan), `실험2.pdf` (CMOS 전기적 특성)
- 이론: `Ch1.pdf` (Introduction, Gates), `Chap3-part1.pdf` (Switching Algebra, Theorems), `Ch14-part1.pdf` (MOSFET switch, CMOS gates), `Ch14-part2.pdf` (CMOS dynamic behavior, VTC, Noise Margin, Fanout)

**Interfaces:**
- Consumes: `extracted_corpus/theory_corpus.json`, `extracted_corpus/lab_corpus.json`
- Produces: 도메인 1 상세 매핑 (이론 ↔ 실험 슬라이드 매핑표, 드모르간/스위칭대수 공통점, VTC/Noise Margin/전파지연/소비전력 수식 및 실습 IC(74HC00, 74HC04 등) 매핑)

- [ ] **Step 1: Perform deep cross-mapping analysis for Domain 1**
- [ ] **Step 2: Write Section 1 into `docs/강의노트_이론_실험_매핑_정리.md`**
- [ ] **Step 3: Review Section 1 completeness against all Domain 1 slides**

---

### Task 3: 도메인 2 심층 분석 - 조합논리 회로 (가산기, 감산기, MUX/DEMUX, Decoder/Encoder)

**Files:**
- Modify: `docs/강의노트_이론_실험_매핑_정리.md` (도메인 2 섹션 작성)

**Scope / Target Documents:**
- 실험: `실험3.pdf` (가산기 & 감산기), `실험4.pdf` (MUX & DEMUX), `실험5.pdf` (Decoder & Encoder)
- 이론: `Ch2-part1.pdf`, `Ch2-part2.pdf` (Number systems, BCD, 2's complement), `Chap3-part1.pdf`, `Chap3-part2_with_answers.pdf` (Combinational synthesis, K-map), `Chap6_Mux_Enc_Dec_new.pdf` (Decoder, Encoder, Priority Encoder, MUX, DEMUX)

**Interfaces:**
- Consumes: `extracted_corpus/theory_corpus.json`, `extracted_corpus/lab_corpus.json`
- Produces: 도메인 2 상세 매핑 (반가산기/전가산기/감산기 진리표 및 부울식, 2의 보수 연산과 오버플로우, MUX를 이용한 논리함수 합성, 디코더 확장 및 74HC138/74HC148/74HC42/74HC283 실습 소자 핀아웃 및 제어 신호 대조)

- [ ] **Step 1: Perform deep cross-mapping analysis for Domain 2**
- [ ] **Step 2: Write Section 2 into `docs/강의노트_이론_실험_매핑_정리.md`**
- [ ] **Step 3: Review Section 2 completeness against all Domain 2 slides**

---

### Task 4: 도메인 3 심층 분석 - 순서논리 회로 (래치, 플립플롭, 시프트 레지스터, 카운터, FSM)

**Files:**
- Modify: `docs/강의노트_이론_실험_매핑_정리.md` (도메인 3 섹션 작성)

**Scope / Target Documents:**
- 실험: `실험6.pdf` (래치와 플립플롭), `실험7.pdf` (Shift Register), `실험8.pdf` (Counter)
- 이론: `Chap9_10.pdf` (State Machines, Sequential Logic Elements), `Chap9_10_sequentialcircuit(1_2).pdf` (Bistable elements, SR/D/JK/T FF, Master-Slave, 타이밍), `Chap9_10_sequentialcircuit(2_2).pdf` (동기 순서회로 해석 및 설계, 여기표, 상태 다이어그램, 카운터 설계)

**Interfaces:**
- Consumes: `extracted_corpus/theory_corpus.json`, `extracted_corpus/lab_corpus.json`
- Produces: 도메인 3 상세 매핑 (래치 vs 플립플롭 레벨/엣지 트리거 특성, Setup/Hold time 및 Metastability, 시프트 레지스터 4종(SISO/SIPO/PISO/PIPO), 링/존슨 카운터 자기기동성, 비동기 리플 카운터 vs 동기식 카운터 설계, 74HC76, 7496, 7490 IC 실습 매핑)

- [ ] **Step 1: Perform deep cross-mapping analysis for Domain 3**
- [ ] **Step 2: Write Section 3 into `docs/강의노트_이론_실험_매핑_정리.md`**
- [ ] **Step 3: Review Section 3 completeness against all Domain 3 slides**

---

### Task 5: 도메인 4 심층 분석 - 메모리, 신호 변환(DAC/ADC) 및 Verilog HDL

**Files:**
- Modify: `docs/강의노트_이론_실험_매핑_정리.md` (도메인 4 섹션 작성)

**Scope / Target Documents:**
- 실험: `실험9.pdf` (RAM), `실험10.pdf` (DAC & ADC), `Verilog_강의자료.pdf` (ASIC/FPGA, Verilog 문법)
- 이론: `Ch1.pdf` (Analog vs Digital), `Chap6_Mux_Enc_Dec_new.pdf` (ROM/PLA/Memory 기초), `Chap9_10` (순서회로 HDL 모델링)

**Interfaces:**
- Consumes: `extracted_corpus/theory_corpus.json`, `extracted_corpus/lab_corpus.json`
- Produces: 도메인 4 상세 매핑 (SRAM vs DRAM, 7489/74189 RAM 동작 타이밍, R-2R Ladder 및 가중저항 DAC, Flash/SAR ADC 동작 원리 및 양자화 오차, Verilog 문법 및 조합/순차 모델링 비교)

- [ ] **Step 1: Perform deep cross-mapping analysis for Domain 4**
- [ ] **Step 2: Write Section 4 into `docs/강의노트_이론_실험_매핑_정리.md`**
- [ ] **Step 3: Review Section 4 completeness against all Domain 4 slides**

---

### Task 6: 종합 매핑 매트릭스, 차이점 정리 및 최종 검증

**Files:**
- Modify: `docs/강의노트_이론_실험_매핑_정리.md` (총괄 요약 매트릭스, 이론 전용/실험 전용 차이점, 학습 가이드라인 추가)

**Interfaces:**
- Consumes: Sections 1~4
- Produces: 
  1. 전체 22개 PDF ↔ 주제별 통합 Cross-Reference Table
  2. 이론에는 있으나 실험에는 없는 내용 (K-Map Quine-McCluskey, Floating Point, PLA/PAL 상세 등)
  3. 실험에는 있으나 이론에는 적은 내용 (실제 74HC IC 핀아웃, 디바운싱 회로, OP-Amp 비교기 회로, Verilog Testbench 실습 등)
  4. 최종 통합 문서 포맷팅 및 완전성 검증

- [ ] **Step 1: Synthesize all 4 domains into a master cross-reference matrix**
- [ ] **Step 2: Add comprehensive theoretical vs experimental differential insights**
- [ ] **Step 3: Validate markdown formatting, latex equations, and complete coverage**

---

## Verification Plan

### Automated Tests
- `python3 -c "import json; assert len(json.load(open('extracted_corpus/theory_corpus.json')))==11"`
- `python3 -c "import os; assert os.path.exists('docs/강의노트_이론_실험_매핑_정리.md') and os.path.getsize('docs/강의노트_이론_실험_매핑_정리.md') > 10000"`

### Manual Verification
- `docs/강의노트_이론_실험_매핑_정리.md` 내 10개 실험 및 Verilog, 11개 이론 챕터의 전수 포함 여부 체크리스트 대조.
- 수식(KaTeX), 회로도 설명, 진리표, IC 명칭의 정확성 검토.
