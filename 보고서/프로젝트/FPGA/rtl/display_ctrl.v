// 상태를 화면 여섯 글자로 바꾼다(조합 회로).
module display_ctrl (
    input  [2:0]  state,
    input  [2:0]  msg,
    input  [23:0] pw_in,
    input  [2:0]  len,
    input  [3:0]  sec10,
    input  [3:0]  sec1,
    input         is_guest,     // 방문자 번호로 열림
    output reg [29:0] chars     // 5비트 x 6. [29:25]가 맨 왼쪽
);
    `include "glyphs.vh"
    `include "door_defs.vh"

    // 입력한 자리는 숫자, 아직 누르지 않은 자리는 -
    wire [29:0] typed = {
        (len > 3'd0) ? {1'b0, pw_in[23:20]} : G_DASH,
        (len > 3'd1) ? {1'b0, pw_in[19:16]} : G_DASH,
        (len > 3'd2) ? {1'b0, pw_in[15:12]} : G_DASH,
        (len > 3'd3) ? {1'b0, pw_in[11:8]}  : G_DASH,
        (len > 3'd4) ? {1'b0, pw_in[7:4]}   : G_DASH,
        (len > 3'd5) ? {1'b0, pw_in[3:0]}   : G_DASH };

    always @(*)
        case (state)
            S_OPEN:
                if (is_guest) chars = {G_O, G_P, G_E, G_n, G_OFF, G_G};
                else          chars = {G_O, G_P, G_E, G_n, G_OFF, G_OFF};
            S_GUEST_PW:
                if (len == 3'd0) chars = {G_G, G_U, G_E, 5'd5, G_t, G_OFF};
                else             chars = typed;
            S_NEW_PW:
                if (len == 3'd0) chars = {G_n, G_E, G_W, G_OFF, G_OFF, G_OFF};
                else             chars = typed;
            S_NEW_CONFIRM:
                if (len == 3'd0) chars = {G_A, G_G, G_A, G_I, G_n, G_OFF};
                else             chars = typed;
            S_MSG:
                case (msg)
                    M_ERROR: chars = {G_E, G_r, G_r, G_o, G_r, G_OFF};
                    M_NONE:  chars = {G_n, G_o, G_n, G_E, G_OFF, G_OFF};
                    M_DONE:  chars = {G_d, G_o, G_n, G_E, G_OFF, G_OFF};
                    M_DEL:   chars = {G_d, G_E, G_L, G_OFF, G_OFF, G_OFF};
                    default: chars = {G_I, G_n, G_I, G_t, G_OFF, G_OFF};
                endcase
            S_LOCK: chars = {G_L, G_O, G_C, G_K, 1'b0, sec10, 1'b0, sec1};
            default: chars = typed;     // IDLE, CHECK(1클록이라 화면을 바꾸지 않는다)
        endcase
endmodule
