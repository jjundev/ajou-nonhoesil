`timescale 1ns/1ps
// door_fsm 단독 검증. 1초를 100클록으로 줄이고 키를 직접 넣는다.
module tb_door_fsm;
    localparam CPS = 100;
    `include "door_defs.vh"
    reg clk = 0, rst = 1, key_valid = 0;
    reg [3:0] key = 0;
    wire [2:0] state, len;
    wire [2:0] msg;
    wire is_guest;
    wire [23:0] pw_in;
    wire [3:0] sec10, sec1;
    integer errors = 0, s, k, i, want_s, want_l, n, sec, q;
    reg [23:0] save;

    always #10 clk = ~clk;
    door_fsm #(.CLK_PER_SEC(CPS), .LOCK_SEC(10)) dut (.clk(clk), .rst(rst),
        .key_valid(key_valid), .key(key), .state(state), .msg(msg),
        .pw_in(pw_in), .len(len), .sec10(sec10), .sec1(sec1), .is_guest(is_guest));

    task err(input [8*40-1:0] m);
        begin
            errors = errors + 1;
            if (errors < 30) $display("FAIL %0s t=%0t state=%0d msg=%0d len=%0d pw=%h sec=%0d%0d (s=%0d k=%0d)",
                                      m, $time, state, msg, len, pw_in, sec10, sec1, s, k);
        end
    endtask
    task is(input [2:0] st, input [8*40-1:0] m); if (state !== st) err(m); endtask
    task is_msg(input [2:0] mm, input [8*40-1:0] m); if (state !== S_MSG || msg !== mm) err(m); endtask
    task is_buf(input [23:0] v, input [2:0] l, input [8*40-1:0] m);
        if (pw_in !== v || len !== l) err(m);
    endtask
    task do_reset; begin @(negedge clk) rst = 1; repeat (2) @(negedge clk); rst = 0; @(negedge clk); end endtask
    // 키 하나: 1클록 넣고 CHECK가 지나갈 때까지 2클록 더 기다린다
    task p(input [3:0] c);
        begin key = c; key_valid = 1; @(negedge clk); key_valid = 0; repeat (2) @(negedge clk); end
    endtask
    task type_n(input [23:0] v, input integer l);      // v의 위쪽부터 l자리
        for (i = 0; i < l; i = i + 1) p(v[23 - 4*i -: 4]);
    endtask
    task enter(input [23:0] v, input integer l); begin type_n(v, l); p(K_OK); end endtask
    task msg_end; begin n = 0; while (state === S_MSG && n < 1000) begin @(negedge clk); n = n + 1; end end endtask
    task wrong; begin enter(24'h999900, 4); msg_end; end endtask
    task open_default; begin enter(24'h123400, 4); is(S_OPEN, "open 1234"); end endtask
    task change(input [23:0] v, input integer l);
        begin
            p(K_CHG); is(S_NEW_PW, "chg"); enter(v, l); is(S_NEW_CONFIRM, "to confirm");
            is_buf(0, 0, "confirm starts empty");
            enter(v, l); is_msg(M_DONE, "done"); msg_end; is(S_IDLE, "idle after done"); is_buf(0, 0, "idle empty");
        end
    endtask
    task goto_state(input integer st);
        begin
            do_reset;
            case (st)
                S_OPEN: open_default;
                S_NEW_PW: begin open_default; p(K_CHG); end
                S_NEW_CONFIRM: begin open_default; p(K_CHG); enter(24'h567800, 4); end
                S_MSG: enter(24'h999900, 4);
                S_LOCK: begin wrong; wrong; wrong; end
                S_GUEST_PW: begin open_default; p(K_GST); end
                default: ;
            endcase
            is(st, "goto_state");
        end
    endtask
    // LOCK 전체를 매 클록 확인한다: total초 동안 1초마다 정확히 줄어드는가
    task lock_run(input integer total);
        begin
            is(S_LOCK, "lock entered");
            n = 0;
            while (state === S_LOCK && n < 10000) begin
                sec = total - n / CPS;
                if (sec10 !== sec / 10 || sec1 !== sec % 10) begin err("lock seconds"); n = 20000; end
                // 잠금 중 키를 계속 넣어도 무시
                key = n % 16; key_valid = 1;
                @(negedge clk); n = n + 1;
            end
            key_valid = 0;
            if (n !== total * CPS) err("lock length");
            is(S_IDLE, "idle after lock"); is_buf(0, 0, "buffer empty after lock");
        end
    endtask
    // LOCK으로 들어가기(첫 검사 시점이 0클록이 되도록 마지막 OK는 직접 넣는다)
    task to_lock(input empty_last);
        begin
            wrong; is(S_IDLE, "1st wrong"); wrong; is(S_IDLE, "2nd wrong");
            if (!empty_last) type_n(24'h999900, 4);
            key = K_OK; key_valid = 1; @(negedge clk); key_valid = 0;
            is(S_CHECK, "check state"); @(negedge clk);
        end
    endtask

    initial begin
        s = 0; k = 0;
        do_reset; is(S_IDLE, "reset"); is_buf(0, 0, "reset empty");
        if (sec10 !== 0 || sec1 !== 0) err("reset seconds");

        // ---- 7개 상태 x 키 16종
        for (s = 0; s <= 7; s = s + 1) if (s != S_CHECK)
            for (k = 0; k < 16; k = k + 1) begin
                goto_state(s);
                want_s = s; want_l = -1;
                if (s == S_IDLE || s == S_NEW_PW || s == S_NEW_CONFIRM || s == S_GUEST_PW) begin
                    want_l = (k <= 9) ? 1 : 0;
                    if (k == K_OK) begin want_s = S_MSG; want_l = -1; end
                end
                if (s == S_OPEN) begin
                    if (k == K_OK)  want_s = S_IDLE;
                    if (k == K_CHG) want_s = S_NEW_PW;
                    if (k == K_RST) want_s = S_MSG;
                    if (k == K_GST) want_s = S_GUEST_PW;
                end
                p(k);
                if (state !== want_s) err("state x key");
                if (want_l == 1) is_buf({k[3:0], 20'd0}, 1, "digit stored");
                if (want_l == 0) is_buf(0, 0, "buffer unchanged");
                if (want_s == S_MSG && s != S_MSG)
                    if (msg !== (s == S_IDLE ? M_NONE : s == S_OPEN ? M_INIT : s == S_GUEST_PW ? M_DEL : M_ERROR)) err("message kind");
            end

        // ---- 버퍼 편집(입력을 받는 세 상태 모두)
        for (s = 0; s <= 7; s = s + 1) if (s == S_IDLE || s == S_NEW_PW || s == S_NEW_CONFIRM || s == S_GUEST_PW) begin
            goto_state(s);
            p(K_BS); is_buf(0, 0, "BS on empty");
            type_n(24'h123456, 6); is_buf(24'h123456, 6, "six digits");
            p(7); is_buf(24'h234567, 6, "keep last six"); p(8); is_buf(24'h345678, 6, "keep last six again");
            p(K_BS); is_buf(24'h345670, 5, "BS 6"); p(K_BS); is_buf(24'h345600, 4, "BS 5");
            p(K_BS); is_buf(24'h345000, 3, "BS 4"); p(K_BS); is_buf(24'h340000, 2, "BS 3");
            p(K_BS); is_buf(24'h300000, 1, "BS 2"); p(K_BS); is_buf(0, 0, "BS 1");
            type_n(24'h987000, 3); p(K_CLR); is_buf(0, 0, "CLR"); is(s, "still same state");
            type_n(24'h987000, 3); p(K_GST); p(K_CHG); p(K_RST); is_buf(24'h987000, 3, "ignored keys");
        end

        // ---- 메시지 1.5초: 정확히 150클록, 그동안 키 무시, 만료 클록의 키도 무시
        s = 100; k = 0;
        do_reset; type_n(24'h999900, 4);
        key = K_OK; key_valid = 1; @(negedge clk); key_valid = 0; @(negedge clk);
        is_msg(M_ERROR, "Error shown"); n = 0;
        while (state === S_MSG && n < 1000) begin key = 5; key_valid = 1; @(negedge clk); n = n + 1; end
        key_valid = 0;
        if (n !== 150) err("message length");
        is(S_IDLE, "idle after Error"); is_buf(0, 0, "keys during message ignored");
        p(5); is_buf(24'h500000, 1, "key right after message");

        // ---- 비교: 길이, 0이 든 비밀번호
        do_reset; enter(24'h123400, 5); is_msg(M_ERROR, "12340 is not 1234"); msg_end;
        enter(24'h123000, 3); is_msg(M_ERROR, "123 is not 1234"); msg_end;
        open_default; p(K_OK); is(S_IDLE, "close"); is_buf(0, 0, "close clears");
        enter(24'h123400, 4); change(24'h000000, 4);
        enter(24'h000000, 5); is_msg(M_ERROR, "00000 is not 0000"); msg_end;
        enter(24'h000000, 0); is_msg(M_NONE, "empty is not 0000"); msg_end;
        enter(24'h000000, 4); is(S_OPEN, "0000 opens");
        change(24'h012345, 6); enter(24'h912345, 6); is_msg(M_ERROR, "first digit matters"); msg_end;
        type_n(24'h990123, 6); p(4); p(5); p(K_OK); is(S_OPEN, "last six digits are compared");
        change(24'h123400, 5);
        enter(24'h123400, 4); is_msg(M_ERROR, "1234 is not 12340"); msg_end;
        enter(24'h123400, 5); is(S_OPEN, "12340 opens");

        // ---- RST: 여섯 자리 비밀번호에서 1234로
        do_reset; open_default; change(24'h876543, 6); enter(24'h876543, 6); is(S_OPEN, "new pw");
        p(K_RST); is_msg(M_INIT, "InIt"); msg_end; is(S_IDLE, "idle after InIt"); is_buf(0, 0, "InIt clears");
        enter(24'h876543, 6); is_msg(M_ERROR, "old pw rejected"); msg_end; open_default;

        // ---- 변경 실패: 비밀번호와 실패 횟수 유지, OPEN 복귀
        p(K_OK); wrong; wrong;                          // 실패 2회
        open_default;                                   // 맞히면 0으로
        p(K_CHG); p(K_OK); is_msg(M_ERROR, "empty new pw"); msg_end; is(S_OPEN, "back to OPEN 0");
        p(K_CHG); enter(24'h555000, 3); is_msg(M_ERROR, "3 digits"); msg_end; is(S_OPEN, "back to OPEN 3");
        p(K_CHG); enter(24'h555500, 4); p(K_OK); is_msg(M_ERROR, "empty confirm"); msg_end; is(S_OPEN, "back to OPEN e");
        p(K_CHG); enter(24'h555500, 4); enter(24'h555600, 4); is_msg(M_ERROR, "mismatch"); msg_end; is(S_OPEN, "back to OPEN m");
        p(K_CHG); enter(24'h555500, 4); enter(24'h555500, 5); is_msg(M_ERROR, "mismatch length"); msg_end; is(S_OPEN, "back to OPEN l");
        p(K_OK); enter(24'h555500, 4); is_msg(M_ERROR, "not saved"); msg_end;   // 실패 1
        wrong; is(S_IDLE, "failed change is not counted");                      // 실패 2
        open_default;
        for (q = 4; q <= 6; q = q + 1) begin            // 4, 5, 6자리 저장
            change(24'h246802, q); enter(24'h246802, q); is(S_OPEN, "new length opens");
        end
        change(24'h246802, 6); enter(24'h246802, 6);    // 같은 비밀번호로 변경 허용
        is(S_OPEN, "same pw allowed");

        // ---- 잠금: 10, 20, 40, 40초, 맞히면 10초. 빈 입력도 오답
        do_reset;
        to_lock(0); lock_run(10);
        to_lock(1); lock_run(20);
        to_lock(0); lock_run(40);
        to_lock(0); lock_run(40);
        to_lock(0); lock_run(40);                       // 40초에서 계속 멈춘다
        to_lock(0); lock_run(40);
        open_default; p(K_OK);
        to_lock(0); lock_run(10);
        to_lock(0); lock_run(20);
        open_default; p(K_OK);
        // 빈 입력만 세 번
        do_reset;
        p(K_OK); is_msg(M_NONE, "nonE 1"); msg_end; p(K_OK); is_msg(M_NONE, "nonE 2"); msg_end;
        key = K_OK; key_valid = 1; @(negedge clk); key_valid = 0; @(negedge clk); lock_run(10);
        // 두 번 틀리고 맞히면 연속이 끊긴다
        do_reset; wrong; wrong; open_default; p(K_OK); wrong; wrong; is(S_IDLE, "streak broken");
        // 변경은 잠금 뒤에도 유지
        do_reset; open_default; change(24'h778899, 6); to_lock(0); lock_run(10);
        enter(24'h778899, 6); is(S_OPEN, "pw kept over lock");

        // ---- 방문자 번호(A4): 한 번만 열리고, 방문자는 닫기만 한다
        do_reset; open_default;
        p(K_GST); is(S_GUEST_PW, "guest entry"); enter(24'h246800, 4); is_msg(M_DONE, "guest saved"); msg_end;
        is(S_IDLE, "idle after guest");
        enter(24'h246800, 4); is(S_OPEN, "guest opens"); if (is_guest !== 1'b1) err("is_guest");
        for (k = 0; k < 16; k = k + 1) if (k != K_OK) begin p(k); is(S_OPEN, "guest ignores key"); end
        p(K_OK); is(S_IDLE, "guest closes");
        enter(24'h246800, 4); is_msg(M_ERROR, "guest used once"); msg_end;
        open_default; if (is_guest !== 1'b0) err("owner is not guest");
        p(K_GST); enter(24'h123400, 4); is_msg(M_ERROR, "guest equals owner"); msg_end; is(S_OPEN, "back to OPEN g");
        p(K_GST); enter(24'h135000, 3); is_msg(M_ERROR, "guest 3 digits"); msg_end; is(S_OPEN, "back to OPEN g3");
        p(K_GST); enter(24'h135700, 4); msg_end; open_default;
        p(K_GST); enter(24'h975310, 6); msg_end; open_default;           // 덮어쓰기
        p(K_OK); enter(24'h135700, 4); is_msg(M_ERROR, "old guest replaced"); msg_end;
        enter(24'h975310, 6); is(S_OPEN, "new guest opens"); p(K_OK);
        open_default; p(K_GST); enter(24'h135700, 4); msg_end; open_default;
        p(K_GST); p(K_OK); is_msg(M_DEL, "dEL"); msg_end; is(S_IDLE, "idle after dEL");
        enter(24'h135700, 4); is_msg(M_ERROR, "deleted guest"); msg_end;
        open_default; p(K_GST); enter(24'h135700, 4); msg_end; open_default;
        p(K_RST); msg_end; enter(24'h135700, 4); is_msg(M_ERROR, "RST clears guest"); msg_end;
        open_default; p(K_GST); enter(24'h135700, 4); msg_end; open_default; change(24'h432100, 4);
        enter(24'h135700, 4); is_msg(M_ERROR, "CHG clears guest"); msg_end;
        // 방문자 번호 오답도 세고, 방문자 성공은 연속을 끊는다
        do_reset; open_default; p(K_GST); enter(24'h246800, 4); msg_end;
        wrong; wrong; enter(24'h246800, 4); is(S_OPEN, "guest after 2 wrong"); p(K_OK);
        wrong; wrong; is(S_IDLE, "guest success resets streak");

        if (errors == 0) $display("RESULT PASS tb_door_fsm");
        else $display("RESULT FAIL tb_door_fsm errors=%0d", errors);
        $finish;
    end
endmodule
