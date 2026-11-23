// 키패드 입력: 반전 -> 동기화 -> 디바운스 -> 한 번 누름에 key_valid 1클록.
module key_input (
    input  clk,
    input  rst,
    input  tick_10ms,
    input  [15:0] pb,           // 누르면 0
    output reg key_valid,       // 1클록
    output reg [3:0] key_code   // 눌린 pb 번호. key_valid와 같은 클록에 유효
);
    wire [15:0] npb = ~pb;      // 누르면 1

    // pb는 클록과 무관하게 바뀌므로 플립플롭 두 단을 거쳐 준안정을 막는다.
    reg [15:0] meta, sync;
    reg [15:0] prev;            // 10ms 전에 읽은 값
    reg armed;                  // 모든 키가 떨어진 것을 확인했는가

    // 한 비트만 1인가: 가장 낮은 1을 지웠을 때 0이 되면 1이 하나뿐이다.
    wire one_key = (sync != 0) && ((sync & (sync - 16'd1)) == 0);

    // 한 비트만 1일 때 그 비트의 번호
    reg [3:0] code;
    integer i;
    always @(*) begin
        code = 4'd0;
        for (i = 0; i < 16; i = i + 1)
            if (sync[i]) code = i[3:0];
    end

    always @(posedge clk)
        if (rst) begin
            // '모두 눌림'에서 시작한다. 0에서 시작하면 전원을 넣을 때
            // 누르고 있던 키가 새로 누른 것으로 인식될 수 있다.
            meta      <= 16'hFFFF;
            sync      <= 16'hFFFF;
            prev      <= 16'hFFFF;
            armed     <= 1'b0;
            key_valid <= 1'b0;
            key_code  <= 4'd0;
        end else begin
            meta      <= npb;
            sync      <= meta;
            key_valid <= 1'b0;

            if (tick_10ms) begin
                prev <= sync;
                if (sync == prev) begin             // 두 번 같은 값 = 떨림이 끝남
                    if (sync == 0)
                        armed <= 1'b1;              // 모두 뗌: 다음 누름을 받을 준비
                    else begin
                        armed <= 1'b0;              // 다시 모두 뗄 때까지 받지 않음
                        if (armed && one_key) begin
                            key_valid <= 1'b1;
                            key_code  <= code;
                        end
                    end
                end
            end
        end
endmodule
