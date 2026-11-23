// 전원 인가 리셋. 핀맵에 리셋 핀이 없어서 전원을 넣은 뒤 CYCLES 클록 동안 rst를 1로 둔다.
module por #(parameter CYCLES = 65536) (
    input  clk,
    output reg rst
);
    // 리셋을 만드는 모듈은 스스로 리셋할 수 없으므로 초기값을 쓴다.
    reg [31:0] cnt;
    initial begin
        cnt = 0;
        rst = 1'b1;
    end

    always @(posedge clk)
        if (cnt == CYCLES - 1) rst <= 1'b0;
        else cnt <= cnt + 1;
endmodule
