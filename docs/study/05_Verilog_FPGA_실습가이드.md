# 05. Verilog HDL & FPGA 실습 가이드

> **Scope**: Verilog HDL 강의자료, Intel Quartus Prime Lite Edition, ModelSim-Altera, Altera Cyclone IV FPGA (DE0-Nano Board EP4CE22F17C6N), FSM 모델링  
> **Level**: 논리회로실험 및 디지털 시스템 설계 프로젝트 수강생 필독 가이드

---

## 📌 1. 30초 핵심 요약

```
[Verilog HDL & FPGA 설계 핵심 골든 룰]

   1. C언어와 Verilog의 결정적 차이
      • C 언어 : CPU가 메모리에서 명령어를 한 줄씩 가져와 순차 실행(Sequential Execution)하는 소프트웨어.
      • Verilog : 수많은 논리 게이트와 플립플롭이 물리적으로 결선되어 '동시에 병렬 동작(Concurrent Hardware)'하는 하드웨어 기술 언어.

   2. 2대 코딩 골든 룰 (Golden Rules)
      • [골든 룰 1] 조합논리회로(Combinational Logic) :
        → always @(*) 블록 사용 + 반드시 블로킹 할당(=) 적용.
        → if-else 모든 분기 완결 & case 문 default 필수 (의도치 않은 Latch 생성 원천 차단).
      • [골든 룰 2] 순차논리회로(Sequential Logic / Flip-Flop) :
        → always @(posedge clk or negedge rst_n) 블록 사용 + 반드시 논블로킹 할당(<=) 적용.
        → 동일 사이클 내 모든 우변(RHS) 평가 후 일괄 업데이트 (Race Condition 완벽 방지).

   3. FPGA 설계 핵심 프로세스
      • RTL 코딩 (.v) → ModelSim 시뮬레이션 검증 → Quartus 컴파일 & Pin Planner 핀 매핑 → JTAG 다운로드 (.sof).
```

---

## 📖 2. Verilog 핵심 문법 리마인드

### 2.1 ASIC vs FPGA 설계 흐름 (Design Flow)

```
       ┌─────────────────────────────────────────────────────────────┐
       │                  Digital IC Design Flow                     │
       └─────────────────────────────────────────────────────────────┘
                                Specification
                                      │
                                      ▼
                           RTL Design (Verilog HDL)
                                      │
                                      ▼
                        Functional Simulation (ModelSim) ◄── [Fail: RTL 수정]
                                      │ (Pass)
                                      ▼
                         Logic Synthesis (Quartus/DC)
                                      │
                                      ▼
                         Gate-Level Netlist Generation
                                      │
                                      ▼
                        Place & Route (Fitting / Layout)
                                      │
                                      ▼
                         Timing Simulation & STA Check
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
             [ FPGA Target ]                     [ ASIC Target ]
        Generate Bitstream (.sof)              GDSII Mask Tape-Out
        Download to Board (JTAG)               Foundry Fabrication
```

---

### 2.2 논리 상태 체계 및 데이터형 (Data Types)

#### (1) 4-State Logic 체계
Verilog의 모든 신호는 다음 4가지 논리 상태 중 하나를 갖는다:
- `0`: 논리 Low (Ground 전위, False).
- `1`: 논리 High (Power $V_{CC}$ 전위, True).
- `x` / `X`: 미지정 상태 (Unknown / Conflict, 시뮬레이션 초기화 안 됨).
- `z` / `Z`: 고임피던스 상태 (High-Impedance, 물리적 개방/플로팅/3-State 버스).

#### (2) 수치 리터럴 표기법
형식: `<비트폭>'<진법><수치>`
- `4'b1010` : 4비트 2진수 $1010_2$ (10진수 10)
- `8'hF0`   : 8비트 16진수 $\text{F0}_{16}$ (2진수 `8'b11110000`)
- `16'd1000`: 16비트 10진수 $1000_{10}$
- `32'hDEAD_BEEF`: 가독성을 위한 밑줄(`_`) 포함 32비트 16진수

#### (3) Net(`wire`) vs Variable(`reg`) 데이터 타입 구분

```
                    ┌────────────────────────────────────────┐
                    │          Verilog Data Types            │
                    └───────────────────┬────────────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
       ┌───────────────────┐                         ┌───────────────────┐
       │     Net Type      │                         │   Variable Type   │
       │     (`wire`)      │                         │     (`reg`)       │
       └─────────┬─────────┘                         └─────────┬─────────┘
                 │                                             │
      • 물리적 도선(Wire) 연결                      • 절차적 블록(always, initial)
      • 저장 능력 없음                              내부에서 값을 할당받는 변수
      • assign 연속할당문이나                       • 조합회로 기술 시: 게이트/도선
        모듈/게이트 출력으로 구동                   • 순차회로 기술 시: 플립플롭
```

> ⚠️ **핵심 주의**: `reg`로 선언되었다고 해서 반드시 하드웨어 플립플롭(레지스터)으로 합성되는 것은 아닙니다!  
> `always @(*)` 조합 논리 블록 내에서 기술된 `reg`는 물리적인 조합 게이트(도선)로 합성됩니다.

---

### 2.3 모델링 레벨 3종 비교

#### 1. 구조적 모델링 (Structural Modeling)
기본 게이트 프리미티브(`and`, `or`, `xor`, `not` 등) 또는 하위 모듈을 인스턴스화하여 물리적 회로망을 직접 결선.
```verilog
module full_adder_struct (
    input  wire a, b, cin,
    output wire sum, cout
);
    wire s1, c1, c2;

    xor u1 (s1, a, b);
    xor u2 (sum, s1, cin);
    and u3 (c1, a, b);
    and u4 (c2, s1, cin);
    or  u5 (cout, c1, c2);
endmodule
```

#### 2. 데이터플로우 모델링 (Dataflow Modeling)
`assign` 연속 할당문(Continuous Assignment)과 부울 연산자를 사용하여 신호 흐름 기술. 우변 신호 변경 즉시 좌변 `wire`로 전파.
```verilog
module full_adder_dataflow (
    input  wire a, b, cin,
    output wire sum, cout
);
    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (cin & (a ^ b));
endmodule
```

#### 3. 동작적 모델링 (Behavioral Modeling)
`always` 블록과 절차적 제어문(`if-else`, `case`)을 사용하여 알고리즘적 동작 기술.
```verilog
module full_adder_behavioral (
    input  wire a, b, cin,
    output reg  sum, cout
);
    always @(*) begin
        {cout, sum} = a + b + cin;
    end
endmodule
```

---

### 2.4 블로킹(`=`) vs 논블로킹(`<=`) 할당문의 근본적 차이

```
   [ 블로킹 할당 (Blocking: = ) ]            [ 논블로킹 할당 (Non-Blocking: <= ) ]
   
   always @(posedge clk) begin                always @(posedge clk) begin
       b = a;   // a의 새 값이 b에 즉시 반영      b <= a;  // clk 엣지 시점의 a의 이전 값 예약
       c = b;   // c는 b의 새 값(즉, a)을 받음    c <= b;  // clk 엣지 시점의 b의 이전 값 전달
   end                                        end
   
   [결과: 단 1개의 FF로 축퇴 (오합성!)]       [결과: 완벽한 2단 시프트 레지스터 파이프라인 형성]
   
        ┌───┐                                      ┌───┐       ┌───┐
   a ───┤ D ├── b ─── c                       a ───┤ D ├── b ──┤ D ├── c
        │   │                                      │   │       │   │
  clk ──┤ > │                                clk ──┤ > │   clk─┤ > │
        └───┘                                      └───┘       └───┘
```

#### Verilog 4단계 이벤트 큐 스케줄링 (Stratified Event Queue)
1. **Active Queue**: 블로킹 할당(`=`) 실행, 논블로킹 할당(`<=`) 우변(RHS) 수식 평가, `assign` 평가, 게이트 지연 계산.
2. **Inactive Queue**: `#0` 지연 이벤트 처리.
3. **NBA Update Queue**: 모든 논블로킹 할당(`<=`) 좌변(LHS) 변수 일괄 업데이트.
4. **Postponed Queue**: 모든 신호 안정화 후 `$monitor`, `$strobe` 출력 실행.

> 💡 **골든 룰 요약**:
> - **조합 논리 회로 (`always @(*)`)** $\to$ **반드시 블로킹 할당 (`=`)** 사용!
> - **동기식 순차 논리 회로 (`always @(posedge clk)`)** $\to$ **반드시 논블로킹 할당 (`<=`)** 사용!
> - 단일 `always` 블록 내에서 `=`와 `<=`를 **절대 혼용하지 말 것**!

---

### 2.5 의도치 않은 Latch(래치) 생성 방지법

조합 논리 회로를 `always @(*)` 블록으로 기술할 때, 어떤 입력 조건에서 출력 변수의 값이 정의되지 않으면 합성기는 **"이전 값을 그대로 기억하라"**고 해석하여 불필요한 **투명 래치(Transparent Latch)**를 생성한다. 래치는 타이밍 분석을 어렵게 하고 글리치(Glitch) 및 시스템 오동작의 주원인이 된다.

```verilog
// ❌ [오류 예시: 불완전한 if-else로 인해 의도치 않은 Latch 생성]
always @(*) begin
    if (sel == 1'b1)
        out = data_in;
    // sel == 0일 때 out의 동작이 명시되지 않아 Latch 생성!
end

// ⭕ [올바른 예시 1: 모든 분기 완결 (Complete if-else)]
always @(*) begin
    if (sel == 1'b1)
        out = data_in;
    else
        out = 1'b0;
end

// ⭕ [올바른 예시 2: default 분기가 포함된 case 문]
always @(*) begin
    case (opcode)
        2'b00: result = a + b;
        2'b01: result = a - b;
        2'b10: result = a & b;
        default: result = 16'd0; // default 필수!
    endcase
end

// 🌟 [최고 권장: 방어적 디폴트 할당 패턴 (Default Assignment Pattern)]
always @(*) begin
    // 블록의 가장 첫 줄에 모든 출력 변수의 기본 디폴트값을 선제 할당!
    out    = 1'b0;
    result = 16'd0;

    if (sel) begin
        out = data_in;
    end
end
```

---

## ⏱️ 3. 필수 실전 하드웨어 모듈 코드 템플릿

### 3.1 템플릿 1: 50MHz $\to$ 1Hz / 1kHz 클록 분주기 (Clock Divider)

FPGA 온보드 50MHz 크리스탈 발진기 클록을 인간의 눈으로 볼 수 있는 1Hz(1초 주기) 또는 7세그먼트 스캔용 1kHz 클록으로 분주하는 파라미터형 모듈.

```verilog
// ============================================================================
// File: clk_divider.v
// Description: Parameterized Clock Divider (50MHz to Target Freq)
// ============================================================================
module clk_divider #(
    parameter INPUT_FREQ  = 50_000_000, // 50 MHz
    parameter TARGET_FREQ = 1           // 1 Hz
)(
    input  wire clk_in,    // 50MHz On-board Clock
    input  wire rst_n,     // Active-Low Asynchronous Reset
    output reg  clk_out    // Divided Clock Output
);
    // 분주 토글 카운트 계산: INPUT_FREQ / (2 * TARGET_FREQ)
    localparam TOGGLE_LIMIT = (INPUT_FREQ / (2 * TARGET_FREQ)) - 1;
    localparam WIDTH        = $clog2(TOGGLE_LIMIT + 1);

    reg [WIDTH-1:0] count;

    always @(posedge clk_in or negedge rst_n) begin
        if (!rst_n) begin
            count   <= {WIDTH{1'b0}};
            clk_out <= 1'b0;
        end else begin
            if (count >= TOGGLE_LIMIT) begin
                count   <= {WIDTH{1'b0}};
                clk_out <= ~clk_out; // Toggle Output Clock
            end else begin
                count   <= count + 1'b1;
            end
        end
    end
endmodule
```

---

### 3.2 템플릿 2: 4자리 7-Segment 동적 시분할 스캔 디스플레이 모듈

사람 눈의 잔상 효과(Persistence of Vision)를 이용하여 1kHz 스캔 주파수로 4개의 7세그먼트 디지트를 고속 순차 점등시키는 동적 구동 모듈.

```verilog
// ============================================================================
// File: seven_seg_4digit_dynamic.v
// Description: 4-Digit Dynamic Multiplexing 7-Segment Controller
// ============================================================================
module seven_seg_4digit_dynamic (
    input  wire        clk_scan,    // 1kHz Scanning Clock
    input  wire        rst_n,       // Active-Low Reset
    input  wire [3:0]  digit0,      // 1의 자리 (0~9)
    input  wire [3:0]  digit1,      // 10의 자리 (0~9)
    input  wire [3:0]  digit2,      // 100의 자리 (0~9)
    input  wire [3:0]  digit3,      // 1000의 자리 (0~9)
    output reg  [3:0]  com_anode,   // Common-Anode Digit Select (Active-Low: 0=ON)
    output reg  [6:0]  seg_cath     // Segments a~g (Active-Low: 0=ON, {g,f,e,d,c,b,a})
);
    reg [1:0] scan_cnt;
    reg [3:0] current_hex;

    // 1. 4-상태 스캔 카운터 (0 -> 1 -> 2 -> 3)
    always @(posedge clk_scan or negedge rst_n) begin
        if (!rst_n)
            scan_cnt <= 2'b00;
        else
            scan_cnt <= scan_cnt + 1'b1;
    end

    // 2. 디지트 선택 MUX (Common Anode 제어)
    always @(*) begin
        case (scan_cnt)
            2'b00: begin
                com_anode   = 4'b1110; // Digit 0 활성화
                current_hex = digit0;
            end
            2'b01: begin
                com_anode   = 4'b1101; // Digit 1 활성화
                current_hex = digit1;
            end
            2'b10: begin
                com_anode   = 4'b1011; // Digit 2 활성화
                current_hex = digit2;
            end
            2'b11: begin
                com_anode   = 4'b0111; // Digit 3 활성화
                current_hex = digit3;
            end
            default: begin
                com_anode   = 4'b1111;
                current_hex = 4'd0;
            end
        endcase
    end

    // 3. BCD to 7-Segment Decoder (Common Anode: 0일 때 LED 점등)
    // Bit mapping: [6:0] = {g, f, e, d, c, b, a}
    always @(*) begin
        case (current_hex)
            4'h0: seg_cath = 7'b1000000; // 0
            4'h1: seg_cath = 7'b1111001; // 1
            4'h2: seg_cath = 7'b0100100; // 2
            4'h3: seg_cath = 7'b0110000; // 3
            4'h4: seg_cath = 7'b0011001; // 4
            4'h5: seg_cath = 7'b0010010; // 5
            4'h6: seg_cath = 7'b0000010; // 6
            4'h7: seg_cath = 7'b1111000; // 7
            4'h8: seg_cath = 7'b0000000; // 8
            4'h9: seg_cath = 7'b0010000; // 9
            default: seg_cath = 7'b1111111; // All OFF
        endcase
    end
endmodule
```

---

### 3.3 템플릿 3: FSM (유한 상태 머신) 3-Block 표준 구조

디지털 하드웨어 설계의 사실상 표준(De-facto Standard)인 **3-Block FSM 구조** (상태 레지스터, 차기 상태 조합논리, 출력 조합논리 분리).

```
                      ┌────────────────────────────────────────────────────────┐
                      │                   3-Block FSM Pattern                  │
                      └────────────────────────────────────────────────────────┘
                                     ┌──────────────────┐
                      Inputs ───────►│  Block 2:        ├── Next State
                                     │  Next State Logic│──────┐
                                     │  (always @(*))   │      │
                                     └──────────────────┘      ▼
                                                        ┌─────────────┐
                                                  clk ─►│  Block 1:   │
                                                rst_n ─►│State Reg(FF)│
                                                        │(always @clk)│
                                                        └──────┬──────┘
                                     ┌──────────────────┐      │ Current State
                                     │  Block 3:        │◄─────┘
                      Inputs ───────►│  Output Logic    │
                       (Mealy only)  │  (always @(*))   ├───► Outputs
                                     └──────────────────┘
```

```verilog
// ============================================================================
// File: fsm_traffic_light.v
// Description: 3-Block Moore Finite State Machine Template
// ============================================================================
module fsm_traffic_light (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       timer_done,  // State Transition Trigger
    output reg  [2:0] light_rgb    // {Red, Yellow, Green}
);
    // 상태 정의 (One-Hot 또는 Binary Encoding)
    localparam S_GREEN  = 2'b00;
    localparam S_YELLOW = 2'b01;
    localparam S_RED    = 2'b10;

    reg [1:0] state_current;
    reg [1:0] state_next;

    // ------------------------------------------------------------------------
    // Block 1: State Register (동기식 순차회로, Non-blocking <=)
    // ------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state_current <= S_RED; // Reset State
        else
            state_current <= state_next;
    end

    // ------------------------------------------------------------------------
    // Block 2: Next State Logic (조합논리회로, Blocking =)
    // ------------------------------------------------------------------------
    always @(*) begin
        state_next = state_current; // Default Hold

        case (state_current)
            S_RED: begin
                if (timer_done)
                    state_next = S_GREEN;
            end
            S_GREEN: begin
                if (timer_done)
                    state_next = S_YELLOW;
            end
            S_YELLOW: begin
                if (timer_done)
                    state_next = S_RED;
            end
            default: state_next = S_RED;
        endcase
    end

    // ------------------------------------------------------------------------
    // Block 3: Output Logic (조합논리회로, Blocking =)
    // ------------------------------------------------------------------------
    always @(*) begin
        case (state_current)
            S_GREEN:  light_rgb = 3'b001; // Green ON
            S_YELLOW: light_rgb = 3'b010; // Yellow ON
            S_RED:    light_rgb = 3'b100; // Red ON
            default:  light_rgb = 3'b100;
        endcase
    end
endmodule
```

---

### 3.4 템플릿 4: Testbench 작성 및 ModelSim 시뮬레이션 코드

```verilog
// ============================================================================
// File: tb_fsm_traffic_light.v
// Description: Testbench Stimulus for FSM Verification
// ============================================================================
`timescale 1ns / 1ps

module tb_fsm_traffic_light;
    // 1. Testbench Signals
    reg        clk;
    reg        rst_n;
    reg        timer_done;
    wire [2:0] light_rgb;

    // 2. Instantiate Unit Under Test (UUT)
    fsm_traffic_light uut (
        .clk        (clk),
        .rst_n      (rst_n),
        .timer_done (timer_done),
        .light_rgb  (light_rgb)
    );

    // 3. Clock Generation (50MHz -> Period = 20ns)
    always #10 clk = ~clk;

    // 4. Stimulus Process
    initial begin
        // 초기화
        clk        = 1'b0;
        rst_n      = 1'b0;
        timer_done = 1'b0;

        // 비동기 리셋 해제
        #40;
        rst_n = 1'b1;
        $display("[Time %0t] Reset Released. Initial State = RED", $time);

        // 시나리오 1: RED -> GREEN 전환
        #60;
        timer_done = 1'b1;
        #20;
        timer_done = 1'b0;

        // 시나리오 2: GREEN -> YELLOW 전환
        #100;
        timer_done = 1'b1;
        #20;
        timer_done = 1'b0;

        // 시나리오 3: YELLOW -> RED 전환
        #100;
        timer_done = 1'b1;
        #20;
        timer_done = 1'b0;

        #200;
        $display("[Time %0t] Test Finished Successfully.", $time);
        $finish; // 시뮬레이션 종료
    end

    // 5. 모니터링 출력
    initial begin
        $monitor("Time=%4t | State RGB={R,Y,G}=%3b | Timer=%b",
                 $time, light_rgb, timer_done);
    end
endmodule
```

---

## 🎯 4. 퀴즈 / 과제 / 시험 단골 질문 Q&A (족보 적중)

### Q1. Verilog HDL에서 Blocking 할당문(`=`)과 Non-blocking 할당문(`<=`)의 차이점과 순차회로에서 블로킹 할당을 사용했을 때 발생하는 문제점을 설명하시오. (기말고사 빈출)
> **모범 답안:**
> - **Blocking (`=`)**: 문장이 나열된 순서대로 즉시 평가 및 할당이 실행되며, 현재 문장의 실행이 끝날 때까지 다음 문장을 차단함. **조합 논리 회로 (`always @(*)`)** 기술에 사용.
> - **Non-blocking (`<=`)**: 현재 클록 상승 엣지 시점에 모든 우변(RHS) 수식을 먼저 동시에 평가한 후, 타임스텝 종료 시점에 좌변(LHS) 변수들을 일괄 업데이트함. **동기식 순차 논리 회로 (`always @(posedge clk)`)**에 필수 사용.
> - **순차회로에서 블로킹 할당 사용 시 문제점**:
>   `always @(posedge clk)` 내에서 `b = a; c = b;`를 실행하면, 첫 줄에서 갱신된 `a`의 새 값이 즉시 `b`에 반영된 후 두 번째 줄이 실행되므로 `c`도 동일한 새 값을 받게 됨. 이로 인해 2단 시프트 레지스터가 단일 플립플롭으로 축퇴(오합성)되는 **레이스 컨디션(Race Condition)**이 발생함.

---

### Q2. 조합 논리 회로를 `always @(*)` 블록으로 기술할 때 의도치 않은 래치(Unintended Latch)가 생성되는 원인과 방지 대책 3가지를 기술하시오. (설계 과제 필수)
> **모범 답안:**
> - **발생 원인**: `if` 문에서 `else` 분기가 누락되거나, `case` 문에서 모든 가능한 입력 조건이 명시되지 않고 `default`가 누락된 경우, 합성기는 "명시되지 않은 조건에서는 이전 값을 기억하라"고 판단하여 불필요한 투명 래치(Latch)를 합성함.
> - **방지 대책 3가지**:
>   1. 모든 `if` 조건문에 빠짐없이 대응하는 `else` 분기를 작성한다.
>   2. 모든 `case` 문의 마지막에 `default:` 분기를 반드시 명시한다.
>   3. `always` 블록의 첫머리에 모든 출력 변수에 기본 디폴트값을 선제 할당하는 **방어적 디폴트 할당 패턴(Default Assignment Pattern)**을 적용한다.

---

### Q3. Verilog에서 `wire`와 `reg`의 근본적 차이점을 설명하고, "모든 `reg` 타입 변수는 하드웨어 플립플롭으로 합성되는가?"에 대해 논하시오.
> **모범 답안:**
> - **`wire`**: 물리적 도선(Net)을 나타내며 스스로 값을 저장하지 못하고 `assign` 연속할당문이나 하위 모듈/게이트의 출력에 의해 연속 구동됨.
> - **`reg`**: 절차적 블록(`always`, `initial`) 내부에서 좌변(LHS) 변수로 사용되어 값을 할당받는 데이터 저장소 역할을 모델링함.
> - **플립플롭 합성 여부**: **아니다.** `reg`가 엣지 트리거 순차 블록(`always @(posedge clk)`) 내부에서 할당되면 플립플롭(D-FF)으로 합성되지만, 레벨 민감 조합 블록(`always @(*)`) 내부에서 완전 분기로 기술되면 물리적인 단순 조합 논리 게이트 및 도선으로 합성된다.

---

### Q4. Moore FSM과 Mealy FSM의 차이점과 타이밍 및 하드웨어 특성을 비교하시오.
> **모범 답안:**
> - **Moore FSM**:
>   - 출력이 오직 **현재 상태(Current State)**에 의해서만 결정됨 ($Y = f(S)$).
>   - 입력 신호의 글리치(Glitch)가 출력으로 직접 전파되지 않아 안정적이나, 상태 전이를 거쳐야 출력이 변하므로 반응이 1클록 지연될 수 있음.
> - **Mealy FSM**:
>   - 출력이 **현재 상태와 현재 입력(Current State & Current Inputs)** 모두에 의해 즉각 결정됨 ($Y = g(S, X)$).
>   - 입력 변화에 즉각 반응하므로 Moore 머신 대비 적은 수의 상태(State)로 동일 기능을 구현할 수 있으나, 비동기 입력의 잡음이나 글리치가 출력으로 직접 전파될 위험이 있음.

---

### Q5. FSM을 설계할 때 1-Block이나 2-Block 방식보다 3-Block 표준 구조를 권장하는 이유는?
> **모범 답안:**
> 1. **가독성 및 유지보수성**: 상태 기억(FF), 상태 전이 조건(조합논리), 출력 생성(조합논리)이 물리적/논리적으로 명확히 분리되어 디버깅 및 수정이 매우 용이함.
> 2. **래치 생성 원천 차단**: 차기 상태 로직과 출력 로직이 분리되어 조건문 누락에 따른 의도치 않은 래치 발생 가능성을 최소화함.
> 3. **합성 최적화**: 합성 툴(Quartus)이 각 블록의 타이밍 경로와 리소스(LE)를 독립적으로 최적화하기에 가장 적합한 구조임.

---

## 🛠️ 5. Quartus & FPGA 하드웨어 실습 트러블슈팅 가이드

```
               [ Quartus Pin Planner 핀 매핑 주의사항 ]
   
   ┌─────────────────────────────────────────────────────────────┐
   │ 1. Device Family : Cyclone IV E (EP4CE22F17C6N - DE0-Nano)  │
   │ 2. On-board 50MHz Clock : PIN_R8                            │
   │ 3. Push Buttons (KEY0, KEY1) : Active-Low (누르면 0V 인가!)  │
   │ 4. I/O Standard : 3.3-V LVTTL (반드시 확인)                 │
   │ 5. Unused Pins : As input tri-stated with weak pull-up      │
   └─────────────────────────────────────────────────────────────┘
```

### 5.1 실전 트러블슈팅 체크리스트

| 문제 상황 (Issue) | 근본 원인 (Root Cause) | 해결 조치 (Solution) |
| :--- | :--- | :--- |
| **Quartus 컴파일 성공 후 FPGA 다운로드 시 아무 동작 안 함** | • Pin Planner에서 물리 핀 미할당 또는 타깃 디바이스 불일치<br>• JTAG 케이블 연결 불량 | • Pin Planner에서 `PIN_R8`(클록), `PIN_J15`(KEY0) 등 정확한 핀 번호 매핑 확인.<br>• Quartus Programmer에서 `USB-Blaster` 인식 확인 후 `.sof` 다운로드. |
| **7세그먼트 숫자가 모두 겹쳐서 흐릿하게 보임** | • 50MHz 고속 클록을 7세그먼트 스캔 클록으로 직접 인가함 | • 50MHz 클록을 클록 분주기(`clk_divider`)를 통해 **$1\text{ kHz}$ 스캔 클록**으로 낮추어 인가. |
| **푸시버튼을 누르지 않았는데 리셋이 걸려 동작하지 않음** | • 보드의 푸시버튼은 **Active-Low (기본 High, 누르면 Low)** 방식인데 코드에서 Active-High로 작성함 | • 리셋 감지 조건을 `if (!rst_n)` 또는 `always @(posedge clk or negedge rst_n)` 형태로 수정. |
| **ModelSim 시뮬레이션 파형이 모두 빨간색 'x'로 표시됨** | • 레지스터 초기화(Reset) 펄스 미인가로 인한 미지정(Unknown) 상태 전파 | • Testbench 초기 `initial` 블록에서 `rst_n = 0; #40; rst_n = 1;`을 주어 모든 레지스터를 강제 리셋 초기화. |
| **컴파일 경고: "Found 1 Inferred Latches" 발생** | • 조합논리 `always` 블록 내에서 `if-else` 누락 또는 `case` default 누락 | • 해당 모듈의 `always @(*)` 블록에서 모든 분기를 완결하거나 블록 서두에 디폴트값 선제 할당. |
| **미사용 핀(Unused Pins) 발열 및 간섭 현상** | • 기본 미사용 핀 설정이 `Outputs driving ground`로 되어 있어 쇼트 위험 | • Quartus 메뉴: `Assignments` $\to$ `Device` $\to$ `Device and Pin Options` $\to$ `Unused Pins`를 **"As input tri-stated with weak pull-up"**으로 변경. |
