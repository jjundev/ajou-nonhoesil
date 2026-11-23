// 여섯 글자를 7 Segment에 한 자리씩 돌아가며 켠다.
module seg_driver #(parameter BLANK_CLK = 2500) (   // 50us @ 50MHz
    input  clk,
    input  rst,
    input  tick_1k,
    input  [29:0] chars,        // 5비트 x 6. [29:25]가 맨 왼쪽
    output reg [5:0] fnd_s,     // 자리 선택. 0이 켜짐, [5]가 맨 왼쪽
    output reg [7:0] fnd_d      // {dp,g,f,e,d,c,b,a}. 1이 켜짐
);
    `include "glyphs.vh"

    reg [2:0]  pos;             // 지금 자리 5(왼쪽)~0(오른쪽)
    reg        blanking;        // 자리를 바꾸고 아직 끈 상태
    reg [31:0] blank_cnt;

    // 지금 자리의 글자
    reg [4:0] ch;
    always @(*)
        case (pos)
            3'd5:    ch = chars[29:25];
            3'd4:    ch = chars[24:20];
            3'd3:    ch = chars[19:15];
            3'd2:    ch = chars[14:10];
            3'd1:    ch = chars[9:5];
            default: ch = chars[4:0];
        endcase

    reg [7:0] seg;
    always @(*)
        case (ch)
            5'd0: seg = 8'h3F;  5'd1: seg = 8'h06;  5'd2: seg = 8'h5B;
            5'd3: seg = 8'h4F;  5'd4: seg = 8'h66;  5'd5: seg = 8'h6D;
            5'd6: seg = 8'h7D;  5'd7: seg = 8'h07;  5'd8: seg = 8'h7F;
            5'd9: seg = 8'h67;
            G_P: seg = 8'h73;   G_E: seg = 8'h79;   G_n: seg = 8'h54;
            G_r: seg = 8'h50;   G_o: seg = 8'h5C;   G_d: seg = 8'h5E;
            G_I: seg = 8'h30;   G_t: seg = 8'h78;   G_W: seg = 8'h7E;
            G_A: seg = 8'h77;   G_G: seg = 8'h3D;   G_L: seg = 8'h38;
            G_C: seg = 8'h39;   G_K: seg = 8'h75;   G_DASH: seg = 8'h40;
            default: seg = 8'h00;
        endcase

    always @(posedge clk)
        if (rst) begin
            pos       <= 3'd0;      // 첫 틱에 5(맨 왼쪽)로 간다
            blanking  <= 1'b0;
            blank_cnt <= 0;
            fnd_s     <= 6'b111111;
            fnd_d     <= 8'h00;
        end else if (tick_1k) begin
            // 자리를 바꾸는 동안 모두 꺼서 앞 자리 글자가 비치지 않게 한다.
            pos       <= (pos == 3'd0) ? 3'd5 : pos - 3'd1;
            blanking  <= 1'b1;
            blank_cnt <= 0;
            fnd_s     <= 6'b111111;
            fnd_d     <= 8'h00;
        end else if (blanking) begin
            if (blank_cnt == BLANK_CLK - 1) begin
                blanking <= 1'b0;
                fnd_s    <= ~(6'b000001 << pos);
                fnd_d    <= seg;
            end else
                blank_cnt <= blank_cnt + 1;
        end
endmodule
