// 보드 점검용 최상위. 도어락이 아니라 키 입력과 화면만 확인한다.
//   키를 누르기 전 : ------
//   pb11이 아닌 키 : [pb 번호 2자리]--[누른 횟수 2자리]
//   pb11           : 도어락에서 쓸 글자 화면을 차례로 표시
module board_check #(
    parameter CLK_PER_SEC = 50_000_000,
    parameter POR_CYCLES  = 65536,
    parameter BLANK_CLK   = 2500
) (
    input  clock_50m,
    input  [15:0] pb,
    output [5:0] fnd_s,
    output [7:0] fnd_d
);
    `include "glyphs.vh"
    localparam [1:0] V_START = 2'd0, V_KEY = 2'd1, V_PAGE = 2'd2;

    wire rst, tick_10ms, tick_1k, key_valid;
    wire [3:0] key_code;

    por #(.CYCLES(POR_CYCLES)) u_por (.clk(clock_50m), .rst(rst));
    tick_gen #(.CLK_PER_SEC(CLK_PER_SEC)) u_tick (
        .clk(clock_50m), .rst(rst), .tick_10ms(tick_10ms), .tick_1k(tick_1k));
    key_input u_key (
        .clk(clock_50m), .rst(rst), .tick_10ms(tick_10ms), .pb(pb),
        .key_valid(key_valid), .key_code(key_code));

    reg [1:0] view;
    reg [2:0] page;
    reg [3:0] last;             // 마지막 키 번호
    reg [3:0] cnt10, cnt1;      // 누른 횟수의 십의 자리, 일의 자리

    always @(posedge clock_50m)
        if (rst) begin
            view  <= V_START;
            page  <= 3'd0;
            last  <= 4'd0;
            cnt10 <= 4'd0;
            cnt1  <= 4'd0;
        end else if (key_valid) begin
            last <= key_code;
            if (cnt1 == 4'd9) begin
                cnt1  <= 4'd0;
                cnt10 <= (cnt10 == 4'd9) ? 4'd0 : cnt10 + 4'd1;
            end else
                cnt1 <= cnt1 + 4'd1;

            if (key_code == 4'd11) begin
                view <= V_PAGE;
                page <= (view == V_PAGE) ? page + 3'd1 : 3'd0;
            end else
                view <= V_KEY;
        end

    wire [4:0] last10 = (last >= 4'd10) ? 5'd1 : 5'd0;
    wire [4:0] last1  = (last >= 4'd10) ? {1'b0, last} - 5'd10 : {1'b0, last};

    reg [29:0] chars;
    always @(*)
        case (view)
            V_KEY: chars = {last10, last1, G_DASH, G_DASH, 1'b0, cnt10, 1'b0, cnt1};
            V_PAGE:
                case (page)
                    3'd0:    chars = {G_O, G_P, G_E, G_n, G_OFF, G_OFF};
                    3'd1:    chars = {G_E, G_r, G_r, G_o, G_r, G_OFF};
                    3'd2:    chars = {G_n, G_o, G_n, G_E, G_OFF, G_OFF};
                    3'd3:    chars = {G_d, G_o, G_n, G_E, G_OFF, G_OFF};
                    3'd4:    chars = {G_I, G_n, G_I, G_t, G_OFF, G_OFF};
                    3'd5:    chars = {G_n, G_E, G_W, G_OFF, G_OFF, G_OFF};
                    3'd6:    chars = {G_A, G_G, G_A, G_I, G_n, G_OFF};
                    default: chars = {G_L, G_O, G_C, G_K, 5'd0, 5'd9};
                endcase
            default: chars = {6{G_DASH}};
        endcase

    seg_driver #(.BLANK_CLK(BLANK_CLK)) u_seg (
        .clk(clock_50m), .rst(rst), .tick_1k(tick_1k), .chars(chars),
        .fnd_s(fnd_s), .fnd_d(fnd_d));
endmodule
