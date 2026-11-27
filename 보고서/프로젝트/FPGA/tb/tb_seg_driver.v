`timescale 1ns/1ps
// seg_driver 단독 검증. 1ms 틱은 20클록, 블랭킹은 3클록으로 줄인다.
module tb_seg_driver;
    localparam T = 20, B = 3;
    reg clk = 0, rst = 1, tick = 0;
    reg [29:0] chars = 0;
    wire [5:0] fnd_s;
    wire [7:0] fnd_d;
    integer cnt = 0, errors = 0, i, k, m, blank_len = 0, seen = 0, lit;
    reg [7:0] tbl [0:31];
    reg [7:0] shown [0:5];

    always #10 clk = ~clk;
    always @(posedge clk) begin
        cnt  <= (cnt == T - 1) ? 0 : cnt + 1;
        tick <= (cnt == T - 1);
    end
    seg_driver #(.BLANK_CLK(B)) dut (.clk(clk), .rst(rst), .tick_1k(tick),
        .chars(chars), .fnd_s(fnd_s), .fnd_d(fnd_d));

    task err(input [8*32-1:0] msg);
        begin
            errors = errors + 1;
            if (errors < 20) $display("FAIL %0s t=%0t s=%b d=%h", msg, $time, fnd_s, fnd_d);
        end
    endtask

    // 매 클록 감시: 동시 점등, 자리 순서, 블랭킹 길이, 꺼진 동안의 세그먼트
    reg [5:0] prev_s = 6'b111111;
    always @(negedge clk) if ($time > 100) begin
        lit = 0;
        for (m = 0; m < 6; m = m + 1) if (fnd_s[m] === 1'b0) lit = lit + 1;
        if (^fnd_s === 1'bx || ^fnd_d === 1'bx) err("unknown output");
        else if (rst) begin
            if (prev_s === 6'b111111 && (fnd_s !== 6'b111111 || fnd_d !== 0)) err("on during reset");
            seen = 0; blank_len = 0;
        end else if (lit > 1) err("two digits on");
        else if (lit == 0) begin
            blank_len = blank_len + 1;
            if (fnd_d !== 0) err("segment on while blank");
        end else begin
            if (fnd_s !== prev_s) begin
                if (prev_s !== 6'b111111) err("no blank between digits");
                if (seen > 0 && blank_len !== B) err("blank length");
                if (fnd_s !== ~(6'b000001 << (5 - seen % 6))) err("digit order");
                seen = seen + 1;
            end
            blank_len = 0;
            for (m = 0; m < 6; m = m + 1) if (!fnd_s[m]) shown[m] = fnd_d;
        end
        prev_s = fnd_s;
    end

    initial begin
        for (i = 0; i < 32; i = i + 1) tbl[i] = 0;
        tbl[0]=8'h3F; tbl[1]=8'h06; tbl[2]=8'h5B; tbl[3]=8'h4F; tbl[4]=8'h66;
        tbl[5]=8'h6D; tbl[6]=8'h7D; tbl[7]=8'h07; tbl[8]=8'h7F; tbl[9]=8'h67;
        tbl[10]=8'h73; tbl[11]=8'h79; tbl[12]=8'h54; tbl[13]=8'h50; tbl[14]=8'h5C;
        tbl[15]=8'h5E; tbl[16]=8'h30; tbl[17]=8'h78; tbl[18]=8'h7E; tbl[19]=8'h77;
        tbl[20]=8'h3D; tbl[21]=8'h38; tbl[22]=8'h39; tbl[23]=8'h75; tbl[24]=8'h40; tbl[26]=8'h3E;
        repeat (100) @(posedge clk);
        #1 rst = 0;
        // 32코드를 여섯 자리 모두에서
        for (i = 0; i < 32; i = i + 1) begin
            for (k = 0; k < 6; k = k + 1) chars[k*5 +: 5] = (i + k) % 32;
            repeat (14*T) @(posedge clk);
            #1;
            for (k = 0; k < 6; k = k + 1)
                if (shown[k] !== tbl[(i + k) % 32]) err("glyph");
        end
        if (seen < 100) err("digits not scanned");
        // 동작 중 리셋
        rst = 1; repeat (3*T) @(posedge clk);
        #1 rst = 0; repeat (14*T) @(posedge clk);
        if (seen < 12) err("no scan after reset");
        if (errors == 0) $display("RESULT PASS tb_seg_driver");
        else $display("RESULT FAIL tb_seg_driver errors=%0d", errors);
        $finish;
    end
endmodule
