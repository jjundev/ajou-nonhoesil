`timescale 1ns/1ps
// key_input 단독 검증. 10ms 틱은 200클록으로 줄인다.
module tb_key_input;
    localparam T = 200;             // 10ms에 해당하는 클록 수
    reg clk = 0, rst = 1;
    reg [15:0] pb = 16'hFFFF;
    reg tick = 0;
    wire key_valid;
    wire [3:0] key_code;
    integer cnt = 0, errors = 0, got = 0, last = -1, i, base;

    always #10 clk = ~clk;
    always @(posedge clk) begin
        cnt  <= (cnt == T - 1) ? 0 : cnt + 1;
        tick <= (cnt == T - 1);
    end
    key_input dut (.clk(clk), .rst(rst), .tick_10ms(tick), .pb(pb),
                   .key_valid(key_valid), .key_code(key_code));

    // key_valid가 1인 클록 수를 센다. 1클록보다 길면 횟수가 늘어 걸린다.
    always @(negedge clk) if (key_valid) begin got = got + 1; last = key_code; end

    task w(input integer n); begin repeat (n) @(posedge clk); #1; end endtask
    task release_all; begin pb = 16'hFFFF; w(4*T); end endtask
    task expect_n(input integer n, input integer code, input [8*28-1:0] name);
        begin
            if (got - base !== n || (n > 0 && last !== code)) begin
                errors = errors + 1;
                $display("FAIL %0s: count=%0d (want %0d) code=%0d (want %0d)", name, got - base, n, last, code);
            end
            base = got;
        end
    endtask

    initial begin
        base = 0;
        // 리셋 때 누르고 있던 키는 무시, 떼고 다시 누르면 받는다
        pb[5] = 0; w(10); rst = 0; w(6*T); expect_n(0, 0, "held through reset");
        release_all; expect_n(0, 0, "release after reset");
        pb[5] = 0; w(4*T); expect_n(1, 5, "press after reset"); release_all;
        base = got;
        // 16개 키 번호
        for (i = 0; i < 16; i = i + 1) begin
            pb[i] = 0; w(4*T); expect_n(1, i, "each key"); release_all; expect_n(0, 0, "release");
        end
        // 긴 누름
        pb[7] = 0; w(100*T); expect_n(1, 7, "long press"); release_all;
        // 누를 때와 뗄 때의 채터링(주기가 틱의 약수가 아니게)
        repeat (30) begin pb[3] = ~pb[3]; w(13); end
        pb[3] = 0; w(4*T); expect_n(1, 3, "press bounce");
        repeat (30) begin pb[3] = ~pb[3]; w(13); end
        pb[3] = 1; w(4*T); expect_n(0, 0, "release bounce");
        // 10ms보다 짧은 펄스: 틱과의 위상을 바꿔 가며 모두 무시해야 한다
        for (i = 0; i < T; i = i + 7) begin
            pb[9] = 0; w(T - 10); pb[9] = 1; w(4*T + i);
        end
        expect_n(0, 0, "short pulse");
        // 동시 누름, 하나만 떼도 무시, 모두 떼면 다시 받음
        pb[1] = 0; pb[2] = 0; w(4*T); expect_n(0, 0, "two keys");
        pb[2] = 1; w(4*T); expect_n(0, 0, "one of two released");
        release_all; pb[1] = 0; w(4*T); expect_n(1, 1, "after two keys");
        // 누른 채 다른 키 추가
        pb[8] = 0; w(4*T); expect_n(0, 0, "added key");
        pb[1] = 1; w(4*T); expect_n(0, 0, "first released");
        release_all; pb[8] = 0; w(4*T); expect_n(1, 8, "after added key"); release_all;
        // 모든 키를 함께
        pb = 0; w(4*T); expect_n(0, 0, "all keys"); release_all;
        // 빠른 반복
        repeat (10) begin pb[12] = 0; w(3*T); pb[12] = 1; w(3*T); end
        expect_n(10, 12, "ten presses");

        if (errors == 0) $display("RESULT PASS tb_key_input");
        else $display("RESULT FAIL tb_key_input errors=%0d", errors);
        $finish;
    end
endmodule
