// 도어락의 동작: 상태, 입력 버퍼, 비밀번호, 실패 횟수, 잠금 시간.
module door_fsm #(
    parameter CLK_PER_SEC = 50_000_000,
    parameter LOCK_SEC    = 10          // 첫 잠금 시간(초). 4배가 두 자리를 넘지 않게 1~24
) (
    input  clk,
    input  rst,
    input  key_valid,                   // 1클록
    input  [3:0] key,
    output reg [2:0]  state,
    output reg [2:0]  msg,
    output reg [23:0] pw_in,            // 입력 버퍼. [23:20]이 첫 숫자, 빈 자리는 항상 0
    output reg [2:0]  len,              // 입력한 자릿수 0~6
    output reg [3:0]  sec10,            // 잠금 남은 초의 십의 자리
    output reg [3:0]  sec1,             // 일의 자리
    output reg        is_guest          // OPEN이 방문자 번호로 열렸다
);
    `include "door_defs.vh"

    localparam [23:0] DEFAULT_PW  = 24'h123400;
    localparam [2:0]  DEFAULT_LEN = 3'd4;

    // 잠금 시간 1, 2, 4배. 나눗셈 회로가 생기지 않게 상수로 미리 계산한다.
    localparam BASE = (LOCK_SEC < 1) ? 1 : (LOCK_SEC > 24) ? 24 : LOCK_SEC;
    localparam [3:0] T0 = BASE / 10,       U0 = BASE % 10,
                     T1 = (BASE * 2) / 10, U1 = (BASE * 2) % 10,
                     T2 = (BASE * 4) / 10, U2 = (BASE * 4) % 10;
    localparam MSG_CLK = CLK_PER_SEC + CLK_PER_SEC / 2;     // 1.5초

    reg [23:0] pw;          // 저장된 비밀번호
    reg [2:0]  pw_len;
    reg [23:0] first;       // 변경할 때 첫 번째로 입력한 새 비밀번호
    reg [2:0]  first_len;
    reg [1:0]  fail;        // 연속 실패 횟수 0~2
    reg [1:0]  level;       // 잠금 단계 0~2 (1, 2, 4배)
    reg        ret_open;    // 메시지가 끝나면 1: OPEN, 0: IDLE
    reg [31:0] timer;       // LOCK의 1초, MSG의 1.5초
    reg [23:0] guest;       // 1회용 방문자 번호
    reg [2:0]  guest_len;
    reg        guest_valid;

    // ------------------------------------------------ 입력 버퍼 편집
    // 숫자, BS, CLR을 눌렀을 때의 다음 버퍼. 그 밖의 키면 그대로다.
    reg [23:0] edit_pw;
    reg [2:0]  edit_len;
    always @(*) begin
        edit_pw  = pw_in;
        edit_len = len;
        if (key <= 4'd9) begin
            if (len == 3'd6)
                edit_pw = {pw_in[19:0], key};       // 맨 앞을 버리고 마지막 6개만 남긴다
            else begin
                case (len)
                    3'd0:    edit_pw[23:20] = key;
                    3'd1:    edit_pw[19:16] = key;
                    3'd2:    edit_pw[15:12] = key;
                    3'd3:    edit_pw[11:8]  = key;
                    3'd4:    edit_pw[7:4]   = key;
                    default: edit_pw[3:0]   = key;
                endcase
                edit_len = len + 3'd1;
            end
        end else if (key == K_BS && len != 3'd0) begin
            case (len)
                3'd1:    edit_pw[23:20] = 4'd0;
                3'd2:    edit_pw[19:16] = 4'd0;
                3'd3:    edit_pw[15:12] = 4'd0;
                3'd4:    edit_pw[11:8]  = 4'd0;
                3'd5:    edit_pw[7:4]   = 4'd0;
                default: edit_pw[3:0]   = 4'd0;
            endcase
            edit_len = len - 3'd1;
        end else if (key == K_CLR) begin
            edit_pw  = 24'd0;
            edit_len = 3'd0;
        end
    end

    // 허수 입력: 입력한 숫자(마지막 여섯 개) 안에 pat이 끊기지 않고 들어 있는가.
    // 버퍼와 pat 모두 왼쪽부터 채우고 빈 자리는 0이다. pat은 4~6자리라 k번째 자리에서
    // 시작하는 경우는 k=0, 1, 2뿐이다. 버퍼를 k자리 왼쪽으로 밀고 앞 plen자리만 비교한다.
    function contains(input [23:0] buf_v, input [2:0] blen,
                      input [23:0] pat,   input [2:0] plen);
        integer k;
        reg [23:0] mask;
        begin
            mask = ~24'd0 << (4 * (6 - plen));
            contains = 1'b0;
            for (k = 0; k <= 2; k = k + 1)
                if (k + plen <= blen && (((buf_v << (4 * k)) ^ pat) & mask) == 24'd0)
                    contains = 1'b1;
        end
    endfunction

    wire pw_hit    = contains(pw_in, len, pw, pw_len);
    wire guest_hit = guest_valid && contains(pw_in, len, guest, guest_len);
    // 새 비밀번호 확인은 허수 없이 값과 길이가 그대로 같아야 한다(빈 자리가 0이라 한 번에 비교).
    wire first_ok  = (pw_in == first) && (len == first_len);

    // 입력을 받는 상태로 갈 때는 버퍼를 비운다.
    task go_entry(input [2:0] next);
        begin
            state <= next;
            pw_in <= 24'd0;
            len   <= 3'd0;
        end
    endtask

    task go_msg(input [2:0] m, input to_open);
        begin
            state    <= S_MSG;
            msg      <= m;
            ret_open <= to_open;
            timer    <= 0;
        end
    endtask

    task go_lock;
        begin
            state <= S_LOCK;
            timer <= 0;
            case (level)
                2'd0:    begin sec10 <= T0; sec1 <= U0; end
                2'd1:    begin sec10 <= T1; sec1 <= U1; end
                default: begin sec10 <= T2; sec1 <= U2; end
            endcase
            if (level != 2'd2) level <= level + 2'd1;   // 다음 잠금은 더 길게, 4배에서 멈춤
        end
    endtask

    always @(posedge clk)
        if (rst) begin
            state     <= S_IDLE;
            msg       <= M_ERROR;
            pw_in     <= 24'd0;
            len       <= 3'd0;
            sec10     <= 4'd0;
            sec1      <= 4'd0;
            pw        <= DEFAULT_PW;
            pw_len    <= DEFAULT_LEN;
            first     <= 24'd0;
            first_len <= 3'd0;
            fail      <= 2'd0;
            level     <= 2'd0;
            ret_open  <= 1'b0;
            timer     <= 0;
            guest     <= 24'd0;
            guest_len <= 3'd0;
            guest_valid <= 1'b0;
            is_guest  <= 1'b0;
        end else
            case (state)
                S_IDLE:
                    if (key_valid) begin
                        if (key == K_OK) state <= S_CHECK;
                        else begin
                            pw_in <= edit_pw;
                            len   <= edit_len;
                        end
                    end

                S_CHECK:
                    if (pw_hit || guest_hit) begin
                        state    <= S_OPEN;
                        fail     <= 2'd0;
                        level    <= 2'd0;
                        is_guest <= !pw_hit;            // 둘 다 들어 있으면 주인으로 연다
                        if (!pw_hit) guest_valid <= 1'b0;   // 방문자 번호는 한 번 쓰면 지운다
                    end else if (fail == 2'd2)
                        go_lock;                        // 세 번째 오답은 메시지 없이 잠근다
                    else begin
                        fail <= fail + 2'd1;
                        go_msg((len == 3'd0) ? M_NONE : M_ERROR, 1'b0);
                    end

                S_OPEN:
                    if (key_valid && is_guest) begin
                        if (key == K_OK) go_entry(S_IDLE);  // 방문자는 닫기만 한다
                    end else if (key_valid)
                        case (key)
                            K_OK:    go_entry(S_IDLE);
                            K_CHG:   go_entry(S_NEW_PW);
                            K_GST:   go_entry(S_GUEST_PW);
                            K_RST: begin
                                pw     <= DEFAULT_PW;
                                pw_len <= DEFAULT_LEN;
                                guest_valid <= 1'b0;
                                go_msg(M_INIT, 1'b0);
                            end
                            default: ;                  // 나머지 키는 무시
                        endcase

                S_NEW_PW:
                    if (key_valid) begin
                        if (key == K_OK) begin
                            if (len >= 3'd4) begin
                                first     <= pw_in;
                                first_len <= len;
                                go_entry(S_NEW_CONFIRM);
                            end else
                                go_msg(M_ERROR, 1'b1);
                        end else begin
                            pw_in <= edit_pw;
                            len   <= edit_len;
                        end
                    end

                S_NEW_CONFIRM:
                    if (key_valid) begin
                        if (key == K_OK) begin
                            if (first_ok) begin
                                pw     <= first;
                                pw_len <= first_len;
                                guest_valid <= 1'b0;    // 비밀번호가 바뀌면 방문자 번호도 지운다
                                go_msg(M_DONE, 1'b0);
                            end else
                                go_msg(M_ERROR, 1'b1);
                        end else begin
                            pw_in <= edit_pw;
                            len   <= edit_len;
                        end
                    end

                S_GUEST_PW:
                    if (key_valid) begin
                        if (key == K_OK) begin
                            if (len == 3'd0) begin
                                guest_valid <= 1'b0;    // 빈 입력은 방문자 번호 삭제
                                go_msg(M_DEL, 1'b0);
                            end else if (len >= 3'd4 && !pw_hit) begin
                                guest       <= pw_in;
                                guest_len   <= len;
                                guest_valid <= 1'b1;
                                go_msg(M_DONE, 1'b0);
                            end else
                                go_msg(M_ERROR, 1'b1);  // 1~3자리이거나 주인 비밀번호가 들어 있다
                        end else begin
                            pw_in <= edit_pw;
                            len   <= edit_len;
                        end
                    end

                S_MSG:                                  // 키 무시
                    if (timer == MSG_CLK - 1) begin
                        if (ret_open) state <= S_OPEN;
                        else go_entry(S_IDLE);
                    end else
                        timer <= timer + 1;

                S_LOCK:                                 // 키 무시
                    if (timer == CLK_PER_SEC - 1) begin
                        timer <= 0;
                        if (sec10 == 4'd0 && sec1 == 4'd1) begin
                            fail <= 2'd0;
                            go_entry(S_IDLE);
                        end else if (sec1 == 4'd0) begin
                            sec10 <= sec10 - 4'd1;
                            sec1  <= 4'd9;
                        end else
                            sec1 <= sec1 - 4'd1;
                    end else
                        timer <= timer + 1;

                default: go_entry(S_IDLE);
            endcase
endmodule
