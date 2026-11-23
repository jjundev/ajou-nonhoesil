`timescale 1ns/1ps
// 최상위 검증. pb를 누르고 화면에 나가는 신호에서 여섯 글자를 복원해 비교한다.
module tb_board_check;
    localparam CPS = 20000, T = CPS/100;
    reg clk = 0;
    reg [15:0] pb = 16'hFFFF;
    wire [5:0] fnd_s;
    wire [7:0] fnd_d;
    integer errors = 0, i, k, m, n = 0;
    reg [47:0] shown = 0;

    always #10 clk = ~clk;
    board_check #(.CLK_PER_SEC(CPS), .POR_CYCLES(50), .BLANK_CLK(1)) dut (
        .clock_50m(clk), .pb(pb), .fnd_s(fnd_s), .fnd_d(fnd_d));
    always @(negedge clk)
        for (m = 0; m < 6; m = m + 1) if (fnd_s[m] === 1'b0) shown[m*8 +: 8] = fnd_d;

    // 문자를 기대 세그먼트로 바꾼다(공백은 끔)
    function [7:0] g(input [7:0] c);
        case (c)
            "0": g=8'h3F; "1": g=8'h06; "2": g=8'h5B; "3": g=8'h4F; "4": g=8'h66;
            "5": g=8'h6D; "6": g=8'h7D; "7": g=8'h07; "8": g=8'h7F; "9": g=8'h67;
            "O": g=8'h3F; "P": g=8'h73; "E": g=8'h79; "n": g=8'h54; "r": g=8'h50;
            "o": g=8'h5C; "d": g=8'h5E; "I": g=8'h30; "t": g=8'h78; "W": g=8'h7E;
            "A": g=8'h77; "G": g=8'h3D; "L": g=8'h38; "C": g=8'h39; "K": g=8'h75;
            "-": g=8'h40; default: g=8'h00;
        endcase
    endfunction
    task check(input [47:0] s);
        reg [47:0] e;
        begin
            for (k = 0; k < 6; k = k + 1) e[k*8 +: 8] = g(s[k*8 +: 8]);
            if (shown !== e) begin
                errors = errors + 1;
                $display("FAIL screen want '%0s' %h got %h", s, e, shown);
            end
        end
    endtask
    task w(input integer c); begin repeat (c) @(posedge clk); #1; end endtask
    task press(input integer p);
        begin pb[p] = 0; w(4*T); pb[p] = 1; w(4*T); n = (n + 1) % 100; end
    endtask
    task check_key(input integer p);
        reg [7:0] a, b, c, d;
        begin
            a = 48 + p/10; b = 48 + p%10; c = 48 + n/10; d = 48 + n%10;
            check({a, b, "--", c, d});
        end
    endtask

    initial begin
        w(10*T); check("------");
        for (i = 0; i < 16; i = i + 1) if (i != 11) begin press(i); check_key(i); end
        press(11); check("OPEn  "); press(11); check("Error ");
        press(11); check("nonE  "); press(11); check("donE  ");
        press(11); check("InIt  "); press(11); check("nEW   ");
        press(11); check("AGAIn "); press(11); check("LOCK09");
        press(11); check("OPEn  "); press(11); check("Error ");
        press(0); check_key(0);               // pb11도 횟수에 들어간다
        press(11); check("OPEn  ");           // 다시 들어가면 처음 화면부터
        press(0); check_key(0);
        while (n != 99) begin press(6); check_key(6); end
        press(6); check_key(6);               // 99 -> 00
        if (n !== 0) begin errors = errors + 1; $display("FAIL wrap not reached"); end
        // 동시 누름은 세지 않는다
        pb[4] = 0; pb[5] = 0; w(4*T); pb = 16'hFFFF; w(4*T); check_key(6);
        if (errors == 0) $display("RESULT PASS tb_board_check");
        else $display("RESULT FAIL tb_board_check errors=%0d", errors);
        $finish;
    end
endmodule
