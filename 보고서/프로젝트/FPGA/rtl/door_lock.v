// 디지털 도어락 최상위. 모듈을 잇기만 한다.
module door_lock #(
    parameter CLK_PER_SEC = 50_000_000,
    parameter LOCK_SEC    = 10,
    parameter POR_CYCLES  = 65536,
    parameter BLANK_CLK   = 2500
) (
    input  clock_50m,
    input  [15:0] pb,
    output [5:0] fnd_s,
    output [7:0] fnd_d
);
    wire rst, tick_10ms, tick_1k;
    wire raw_valid, key_valid;
    wire [3:0] key_code, key;
    wire [2:0] state, len;
    wire [2:0] msg;
    wire is_guest;
    wire [23:0] pw_in;
    wire [3:0] sec10, sec1;
    wire [29:0] chars;

    por #(.CYCLES(POR_CYCLES)) u_por (.clk(clock_50m), .rst(rst));

    tick_gen #(.CLK_PER_SEC(CLK_PER_SEC)) u_tick (
        .clk(clock_50m), .rst(rst), .tick_10ms(tick_10ms), .tick_1k(tick_1k));

    key_input u_key (
        .clk(clock_50m), .rst(rst), .tick_10ms(tick_10ms), .pb(pb),
        .key_valid(raw_valid), .key_code(key_code));

    key_decode u_dec (
        .key_valid_in(raw_valid), .key_code(key_code),
        .key_valid(key_valid), .key(key));

    door_fsm #(.CLK_PER_SEC(CLK_PER_SEC), .LOCK_SEC(LOCK_SEC)) u_fsm (
        .clk(clock_50m), .rst(rst), .key_valid(key_valid), .key(key),
        .state(state), .msg(msg), .pw_in(pw_in), .len(len),
        .sec10(sec10), .sec1(sec1), .is_guest(is_guest));

    display_ctrl u_disp (
        .state(state), .msg(msg), .pw_in(pw_in), .len(len),
        .sec10(sec10), .sec1(sec1), .is_guest(is_guest), .chars(chars));

    seg_driver #(.BLANK_CLK(BLANK_CLK)) u_seg (
        .clk(clock_50m), .rst(rst), .tick_1k(tick_1k), .chars(chars),
        .fnd_s(fnd_s), .fnd_d(fnd_d));
endmodule
