// 50MHz에서 1클록짜리 enable 틱을 만든다.
// 나눈 신호를 클록으로 쓰지 않아서 전체 회로가 클록 하나로 돈다.
module tick_gen #(parameter CLK_PER_SEC = 50_000_000) (
    input  clk,
    input  rst,
    output reg tick_10ms,   // 키를 읽는 간격
    output reg tick_1k      // 7 Segment 자리를 바꾸는 간격
);
    localparam DIV_10MS = CLK_PER_SEC / 100;
    localparam DIV_1K   = CLK_PER_SEC / 1000;

    reg [31:0] cnt_10ms, cnt_1k;

    always @(posedge clk)
        if (rst) begin
            cnt_10ms  <= 0;
            cnt_1k    <= 0;
            tick_10ms <= 1'b0;
            tick_1k   <= 1'b0;
        end else begin
            tick_10ms <= (cnt_10ms == DIV_10MS - 1);
            tick_1k   <= (cnt_1k == DIV_1K - 1);
            cnt_10ms  <= (cnt_10ms == DIV_10MS - 1) ? 0 : cnt_10ms + 1;
            cnt_1k    <= (cnt_1k == DIV_1K - 1) ? 0 : cnt_1k + 1;
        end
endmodule
