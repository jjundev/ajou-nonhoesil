`timescale 1ns/1ps
// 도어락 전체 검증. pb를 눌러 평가 항목 E1~E10과 추가 구현 A1~A4를 재생하고
// 화면에 나가는 신호에서 여섯 글자를 복원해 비교한다.
module tb_door_lock;
    localparam CPS = 20000, T = CPS/100;
    reg clk = 0;
    reg [15:0] pb = 16'hFFFF;
    wire [5:0] fnd_s;
    wire [7:0] fnd_d;
    integer errors = 0, k, m, j, sec;
    reg [47:0] shown = 0;
    reg [8*8-1:0] tag = "start";
    reg [47:0] lockmsg;

    always #10 clk = ~clk;
    door_lock #(.CLK_PER_SEC(CPS), .LOCK_SEC(10), .POR_CYCLES(50), .BLANK_CLK(1)) dut (
        .clock_50m(clk), .pb(pb), .fnd_s(fnd_s), .fnd_d(fnd_d));
    always @(negedge clk)
        for (m = 0; m < 6; m = m + 1) if (fnd_s[m] === 1'b0) shown[m*8 +: 8] = fnd_d;

    function [7:0] g(input [7:0] c);
        case (c)
            "0": g=8'h3F; "1": g=8'h06; "2": g=8'h5B; "3": g=8'h4F; "4": g=8'h66;
            "5": g=8'h6D; "6": g=8'h7D; "7": g=8'h07; "8": g=8'h7F; "9": g=8'h67;
            "O": g=8'h3F; "P": g=8'h73; "E": g=8'h79; "n": g=8'h54; "r": g=8'h50;
            "o": g=8'h5C; "d": g=8'h5E; "I": g=8'h30; "t": g=8'h78; "W": g=8'h7E;
            "A": g=8'h77; "G": g=8'h3D; "L": g=8'h38; "C": g=8'h39; "K": g=8'h75;
            "-": g=8'h40; "U": g=8'h3E; "S": g=8'h6D; default: g=8'h00;
        endcase
    endfunction
    task check(input [47:0] s);
        reg [47:0] e;
        begin
            for (k = 0; k < 6; k = k + 1) e[k*8 +: 8] = g(s[k*8 +: 8]);
            if (shown !== e) begin
                errors = errors + 1;
                if (errors < 30) $display("FAIL [%0s] t=%0t want '%0s' %h got %h", tag, $time, s, e, shown);
            end
        end
    endtask
    task w(input integer c); begin repeat (c) @(posedge clk); #1; end endtask
    task press(input integer n); begin pb[n] = 0; w(4*T); pb[n] = 1; w(4*T); end endtask
    // 화면에 쓰인 이름의 키를 누른다: 숫자, K=OK C=CHG R=RST B=BS X=CLR Z=pb11
    task ch(input [7:0] c);
        case (c)
            "1": press(0); "2": press(1); "3": press(2);  "C": press(3);
            "4": press(4); "5": press(5); "6": press(6);  "R": press(7);
            "7": press(8); "8": press(9); "9": press(10); "Z": press(11);
            "K": press(12); "0": press(13); "B": press(14); "X": press(15);
            default: ;
        endcase
    endtask
    task keys(input [8*12-1:0] s); for (j = 11; j >= 0; j = j - 1) ch(s[j*8 +: 8]); endtask
    task wait_msg; w(CPS + CPS/2); endtask
    task wrong;
        begin keys("9999K"); check("Error "); wait_msg; check("------"); end
    endtask
    // 세 번째 오답 OK 직후부터 잠금이 끝날 때까지 1초마다 확인하고, 그동안 키를 누른다
    task lock_run(input integer total);
        begin
            for (sec = total; sec >= 1; sec = sec - 1) begin
                lockmsg = "LOCK00";
                lockmsg[15:8] = 48 + sec/10; lockmsg[7:0] = 48 + sec%10;
                check(lockmsg);
                press(sec % 16);
                check(lockmsg);
                w(CPS - 8*T);
            end
            check("------");
        end
    endtask
    task three_wrong(input integer total);
        begin wrong; wrong; keys("9999K"); lock_run(total); end
    endtask

    initial begin
        w(10*T); check("------");
        tag = "R1";  keys("1"); check("1-----"); keys("2"); check("12----");
                     keys("Z"); check("12----"); keys("3"); check("123---");
                     keys("4"); check("1234--"); keys("5"); check("12345-"); keys("Z"); check("12345-");
                     keys("6"); check("123456"); keys("7890"); check("567890"); keys("X"); check("------");
                     keys("Z"); check("------"); keys("CR"); check("------");
        tag = "E1";  keys("1234K"); check("OPEn  "); keys("5BX"); check("OPEn  "); keys("K"); check("------");
                     wrong;
                     keys("1234K"); check("OPEn  "); keys("K");
        tag = "E5";  keys("K"); check("nonE  "); wait_msg; check("------");
                     keys("K"); check("nonE  "); wait_msg;
                     keys("K"); lock_run(10);               // 빈 입력도 오답 3회
                     keys("1234KK"); check("------");
        tag = "E2";  three_wrong(10);
        tag = "E3";  three_wrong(20);
        tag = "A2";  three_wrong(40); three_wrong(40);
                     keys("1234KK"); three_wrong(10); keys("1234KK"); check("------");
        tag = "E9";  wrong; wrong; keys("9999K"); check("LOCK10");
                     w(8*CPS); pb[4] = 0; w(3*CPS); check("------");   // 잠금 중 누른 키를 쥔 채 해제
                     pb[4] = 1; w(4*T); check("------");
                     keys("1"); check("1-----"); keys("234K"); check("OPEn  ");
        tag = "E4";  keys("C"); check("nEW   "); keys("5"); check("5-----"); keys("B"); check("nEW   ");
                     keys("56789K"); check("AGAIn "); keys("5"); check("5-----"); keys("X"); check("AGAIn ");
                     keys("56789K"); check("donE  "); wait_msg; check("------");
                     keys("1234K"); check("Error "); wait_msg;
                     keys("56789K"); check("OPEn  ");
        tag = "E4b"; keys("C56789K"); keys("56789K"); check("donE  "); wait_msg;  // 같은 값으로 변경
                     keys("56789K"); check("OPEn  ");
        tag = "E6";  keys("CK"); check("Error "); wait_msg; check("OPEn  ");
                     keys("C123K"); check("Error "); wait_msg; check("OPEn  ");
        tag = "A3";  keys("C1111K"); check("AGAIn "); keys("1112K"); check("Error "); wait_msg; check("OPEn  ");
                     keys("C1111K"); keys("K"); check("Error "); wait_msg; check("OPEn  "); keys("K");
                     keys("1111K"); check("Error "); wait_msg; keys("56789K"); check("OPEn  ");
        tag = "E7";  keys("R"); check("InIt  "); wait_msg; check("------");
                     keys("56789K"); check("Error "); wait_msg;
                     keys("1234K"); check("OPEn  "); keys("K");
        tag = "E8";  keys("1234567"); check("234567"); keys("K"); check("Error "); wait_msg;
                     keys("991234"); check("991234"); keys("X1234K"); check("OPEn  ");
                     keys("C234567K"); keys("234567K"); check("donE  "); wait_msg;
                     keys("1234567K"); check("OPEn  "); keys("R"); wait_msg;
        tag = "E10"; keys("1234K"); check("OPEn  "); keys("C4321K"); keys("4321K"); check("donE  "); wait_msg;
                     keys("C"); check("------");            // 변경 뒤에는 닫혀 있다
                     wrong; keys("4321K"); check("OPEn  ");
                     keys("C8765K"); keys("8766K"); check("Error "); wait_msg; check("OPEn  ");
                     keys("C8765K"); keys("8765K"); check("donE  "); wait_msg;
                     keys("8765K"); check("OPEn  "); keys("K");
        tag = "A1";  keys("123"); check("123---"); keys("B"); check("12----"); keys("X"); check("------");
                     keys("B"); check("------"); keys("87659B"); check("8765--"); keys("K"); check("OPEn  ");
        tag = "A4";  keys("Z"); check("GUESt "); keys("2468"); check("2468--"); keys("B"); check("246---");
                     keys("X"); check("GUESt "); keys("2468K"); check("donE  "); wait_msg; check("------");
                     keys("2468K"); check("OPEn G"); keys("CRZ5BX"); check("OPEn G"); keys("K"); check("------");
                     keys("2468K"); check("Error "); wait_msg;
                     keys("8765K"); check("OPEn  ");
                     keys("Z8765K"); check("Error "); wait_msg; check("OPEn  ");
                     keys("Z123K"); check("Error "); wait_msg; check("OPEn  ");
                     keys("Z1357K"); wait_msg; keys("8765K"); keys("ZK"); check("dEL   "); wait_msg; check("------");
                     keys("1357K"); check("Error "); wait_msg;
                     keys("8765K"); keys("Z1357K"); wait_msg; keys("8765K"); keys("R"); wait_msg;
                     keys("1357K"); check("Error "); wait_msg;
                     keys("1234K"); keys("Z1357K"); wait_msg; keys("1234K"); keys("C4321K"); keys("4321K"); wait_msg;
                     keys("1357K"); check("Error "); wait_msg; keys("4321K"); check("OPEn  ");

        if (errors == 0) $display("RESULT PASS tb_door_lock");
        else $display("RESULT FAIL tb_door_lock errors=%0d", errors);
        $finish;
    end
endmodule
