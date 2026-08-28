# 논리회로실험 수강생 맞춤형 6개 모듈 스터디 가이드 구축 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 3년 전 논리회로를 수강하고 현재 기억이 흐릿한 상태에서 논리회로실험을 수강하는 학생을 위해, 이론 핵심 리마인드·실험 주차별 소자/원리·퀴즈/예비보고서 족보 포인트를 결합한 6개 모듈형 스터디 가이드(`docs/study/00~05.md` 및 `README.md`)를 작성한다.

**Architecture:** 이미 22개 PDF 전수 분석을 통해 구축된 고품질 도메인 리포트(`extracted_corpus/analysis_domain1~4.md` 및 `docs/강의노트_이론_실험_매핑_정리.md`)를 기반으로, 수강생의 인지 부하를 최소화하고 주차별 예습 루틴에 최적화된 마크다운 모듈 6종을 생성·배치한다.

**Tech Stack:** Markdown (GitHub GFM), KaTeX/LaTeX 수식, ASCII 회로/핀아웃 다이어그램, 진리표/여기표 테이블

## Global Constraints

- 대상 디렉토리: `docs/study/`
- 파일 명명 규칙:
  - `docs/study/README.md`
  - `docs/study/00_논리회로_핵심기초_30분_리마인드.md`
  - `docs/study/01_기본게이트_CMOS특성(실험1-2).md`
  - `docs/study/02_조합논리회로_실습(실험3-5).md`
  - `docs/study/03_순서논리회로_실습(실험6-8).md`
  - `docs/study/04_기억소자_신호변환(실험9-10).md`
  - `docs/study/05_Verilog_FPGA_실습가이드.md`
- 각 모듈별 필수 섹션 구성:
  1. 30초 핵심 요약 (이 주차에 이것만은 알고 가자)
  2. 이론 핵심 리마인드 (수식, 진리표, 동작 원리)
  3. 실습 부품 & 회로 결선 가이드 (74시리즈 IC 핀 번호, VCC/GND, 풀업/풀다운)
  4. 예비보고서 & 퀴즈 단골 질문 Q&A (족보 적중)
  5. 브레드보드 실습 트러블슈팅 & 오차 원인 분석

---

## File Structure

- Create: `docs/study/README.md` (학습 가이드맵 및 주차별 로드맵)
- Create: `docs/study/00_논리회로_핵심기초_30분_리마인드.md` (3년 공백 메우기 선수 복습)
- Create: `docs/study/01_기본게이트_CMOS특성(실험1-2).md` (실험 1, 2 대비)
- Create: `docs/study/02_조합논리회로_실습(실험3-5).md` (실험 3, 4, 5 대비)
- Create: `docs/study/03_순서논리회로_실습(실험6-8).md` (실험 6, 7, 8 대비)
- Create: `docs/study/04_기억소자_신호변환(실험9-10).md` (실험 9, 10 대비)
- Create: `docs/study/05_Verilog_FPGA_실습가이드.md` (Verilog 문법 및 FPGA 설계 프로젝트 대비)

---

### Task 1: 스터디 네비게이터 `docs/study/README.md` 및 선수 복습 모듈 `00_논리회로_핵심기초_30분_리마인드.md` 작성

**Files:**
- Create: `docs/study/README.md`
- Create: `docs/study/00_논리회로_핵심기초_30분_리마인드.md`

**Interfaces:**
- Consumes: `docs/강의노트_이론_실험_매핑_정리.md` (Section 1 & 2)
- Produces: 
  - `README.md`: 전체 6개 모듈 링크 및 주차별/시험별 커리큘럼 로드맵
  - `00_논리회로_핵심기초_30분_리마인드.md`: 기본 7대 게이트(AND/OR/NOT/NAND/NOR/XOR/XNOR) 기호 및 진리표, 부울 대수 기본 정리(드모르간, 흡수, 멱등), 2진수 2의 보수와 감산 원리, 카르노맵(K-Map) 묶는 법 3분 요약

- [ ] **Step 1: Write `docs/study/README.md`**
- [ ] **Step 2: Write `docs/study/00_논리회로_핵심기초_30분_리마인드.md`**
- [ ] **Step 3: Verify content clarity and markdown links**

---

### Task 2: 1~2주차 모듈 `docs/study/01_기본게이트_CMOS특성(실험1-2).md` 작성

**Files:**
- Create: `docs/study/01_기본게이트_CMOS특성(실험1-2).md`

**Scope:**
- 실험 1 (Basic Gates & De Morgan), 실험 2 (CMOS 전기적 특성)
- 이론 Ch1, Chap3-part1, Ch14-part1, Ch14-part2

**Content:**
- 74HC00, 02, 04, 08, 32, 86 14핀 DIP 핀아웃 맵
- CMOS 스위치 인버터 동작(PMOS Pull-up / NMOS Pull-down)
- $V_{OH}, V_{OL}, V_{IH}, V_{IL}$ 및 노이즈 마진($NM_H, NM_L$) 계산 공식과 수치 예제
- 전파 지연시간($t_{pd}$) 및 슈미트 트리거 인버터(74HC14) 히스테리시스 곡선
- 플로팅 입력 방지(풀업/풀다운 저항), LED $330\Omega$ 전류 제한 저항 계산
- 퀴즈/예비보고서 단골 Q&A (NAND가 NOR보다 빠른 이유, 플로팅 입력 위험성 등)

- [ ] **Step 1: Draft `docs/study/01_기본게이트_CMOS특성(실험1-2).md`**
- [ ] **Step 2: Review against lab 1, 2 requirements and exam questions**

---

### Task 3: 3~5주차 모듈 `docs/study/02_조합논리회로_실습(실험3-5).md` 작성

**Files:**
- Create: `docs/study/02_조합논리회로_실습(실험3-5).md`

**Scope:**
- 실험 3 (가산기 & 감산기), 실험 4 (Multiplexer & Demultiplexer), 실험 5 (Decoder & Encoder)
- 이론 Ch2-part1/2, Chap3-part1/2, Chap6

**Content:**
- 반가산기/전가산기/반감산기/전감산기 진리표 및 부울식 유도
- 4비트 2의 보수 가감산기 회로(74HC283 + XOR) 및 오버플로우 검출 조건 ($V = C_n \oplus C_{n-1}$)
- 8:1 MUX (74HC151), Dual 4:1 MUX (74HC153) 및 MUX를 이용한 임의 논리식 구현(Shannon 전개)
- 3:8 디코더 (74HC138) Active-Low 인에이블 결선 및 4:16 확장
- BCD-to-Decimal 디코더 (74HC42) 및 BCD-to-7Segment 구동 원리
- 8:3 우선순위 인코더 (74HC148) $\overline{GS}$ (Group Select) vs $\overline{EO}$ (Enable Out) 차이 및 16:4 확장
- 퀴즈/예비보고서 단골 Q&A (전가산기를 반가산기 2개로 구성하는 법, 우선순위 인코더 신호 해석 등)

- [ ] **Step 1: Draft `docs/study/02_조합논리회로_실습(실험3-5).md`**
- [ ] **Step 2: Review against lab 3, 4, 5 requirements and exam questions**

---

### Task 4: 6~8주차 모듈 `docs/study/03_순서논리회로_실습(실험6-8).md` 작성

**Files:**
- Create: `docs/study/03_순서논리회로_실습(실험6-8).md`

**Scope:**
- 실험 6 (래치와 플립플롭), 실험 7 (시프트 레지스터), 실험 8 (카운터)
- 이론 Chap9_10, Chap9_10_seq 1/2 & 2/2

**Content:**
- Latch vs Flip-Flop의 본질적 차이 (Level-sensitive vs Edge-triggered)
- SR, D, JK, T 플립플롭의 특성표(Characteristic Table)와 여기표(Excitation Table) 완벽 정리
- 주종형(Master-Slave) 플립플롭과 1's catching 현상
- 비동기 입력 ($\overline{PR}, \overline{CLR}$)의 최우선권 동작
- Setup Time($t_{su}$), Hold Time($t_h$), Clock-to-Q($t_{co}$) 및 준안정성(Metastability)
- 시프트 레지스터 4종(SISO, SIPO, PISO, PIPO) 및 7496 5비트 시프트 레지스터
- 링 카운터 vs 존슨 카운터 (상태 수 $N$ vs $2N$, 자기 기동성 이슈)
- 비동기 리플 카운터(Ripple Counter)의 전파지연 누적과 디코딩 글리치 vs 동기식 카운터
- 7490 10진 카운터(Mod-2 + Mod-5) 결선 및 7447 + FND 507 결선
- 퀴즈/예비보고서 단골 Q&A (래치와 FF의 차이, 리플 카운터의 한계, 존슨 카운터 자기기동 등)

- [ ] **Step 1: Draft `docs/study/03_순서논리회로_실습(실험6-8).md`**
- [ ] **Step 2: Review against lab 6, 7, 8 requirements and exam questions**

---

### Task 5: 9~10주차 모듈 `docs/study/04_기억소자_신호변환(실험9-10).md` 작성

**Files:**
- Create: `docs/study/04_기억소자_신호변환(실험9-10).md`

**Scope:**
- 실험 9 (RAM), 실험 10 (DAC & ADC)
- 이론 Ch1, Chap6, Ch14

**Content:**
- 6T SRAM 셀 vs 1T-1C DRAM 셀 원리 및 휘발성/비휘발성 메모리
- 16-bit RAM (7489 / 74189) $\overline{CS}, \overline{WE}$ 제어 타이밍 및 오픈 컬렉터 풀업 저항
- 가중 저항형 DAC vs R-2R 사다리형 DAC 전압 수식 유도 및 Thevenin 등가해석
- LM741 / LM324 OP-Amp 반전 가산기 가상 접지(Virtual Ground) 원리
- Flash ADC (병렬 비교기형), 계수형 ADC, SAR ADC, Dual-Slope ADC 원리 비교
- 양자화 오차 ($\pm \frac{1}{2}\text{ LSB}$), Step Size ($\Delta V$), Nyquist 표본화 정리 ($f_s \ge 2f_{\max}$)
- 퀴즈/예비보고서 단골 Q&A (R-2R이 가중저항보다 널리 쓰이는 이유, Flash ADC의 비교기 개수($2^n-1$), 전원 차단 시 RAM 휘발성 실험 등)

- [ ] **Step 1: Draft `docs/study/04_기억소자_신호변환(실험9-10).md`**
- [ ] **Step 2: Review against lab 9, 10 requirements and exam questions**

---

### Task 6: 설계 프로젝트 모듈 `docs/study/05_Verilog_FPGA_실습가이드.md` 작성 및 전체 검증

**Files:**
- Create: `docs/study/05_Verilog_FPGA_실습가이드.md`

**Scope:**
- Verilog 강의자료, FPGA 실습(Quartus Prime, ModelSim, Cyclone IV)
- 이론 Chap9_10 (FSM 모델링)

**Content:**
- Verilog 기본 문법 (`module`, `input/output`, `wire` vs `reg`)
- 데이터플로우(`assign`) vs 비헤이비어럴(`always`)
- **절대 규칙: 조합논리(`always @(*)`, `=`) vs 순차논리(`always @(posedge clk)`, `<=`)**
- `if-else` / `case` 불완전 분기로 인한 의도치 않은 Latch 생성 방지법
- 50MHz 시스템 클록을 1Hz / 1kHz로 낮추는 클록 분주기(Clock Divider) 코드 템플릿
- 4자리 7-Segment 동적 시분할 스캔 구동 회로 코드
- FSM 3-Block 표준 구조 및 Testbench 작성법
- Quartus 컴파일 & Pin Planner 핀 매핑 트러블슈팅

- [ ] **Step 1: Draft `docs/study/05_Verilog_FPGA_실습가이드.md`**
- [ ] **Step 2: Verify all 7 files in `docs/study/` directory**
- [ ] **Step 3: Run link integrity and format checks**

---

## Verification Plan

### Automated Tests
- `python3 -c "import os; files=['README.md', '00_논리회로_핵심기초_30분_리마인드.md', '01_기본게이트_CMOS특성(실험1-2).md', '02_조합논리회로_실습(실험3-5).md', '03_순서논리회로_실습(실험6-8).md', '04_기억소자_신호변환(실험9-10).md', '05_Verilog_FPGA_실습가이드.md']; assert all(os.path.exists(os.path.join('docs/study', f)) for f in files); print('All 7 study guide files exist!')"`
- `python3 -c "import os; szs=[os.path.getsize(os.path.join('docs/study', f)) for f in os.listdir('docs/study') if f.endswith('.md')]; assert all(s > 2000 for s in szs); print(f'Validated {len(szs)} markdown files, all substantive!')"`

### Manual Verification
- 3년 전 수강생 관점에서 `00편`부터 읽었을 때 개념 이해가 자연스럽고 직관적인지 점검.
- 실제 아주대 논리회로실험 기출 족보/퀴즈 내용과의 일치성 확인.
