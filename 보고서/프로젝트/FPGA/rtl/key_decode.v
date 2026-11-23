// pb 번호를 숫자나 기능 키로 바꾼다(조합 회로라 key_valid와 같은 클록에 나간다).
module key_decode (
    input  key_valid_in,
    input  [3:0] key_code,
    output key_valid,
    output reg [3:0] key
);
    `include "door_defs.vh"

    assign key_valid = key_valid_in;

    always @(*)
        case (key_code)
            4'd0:    key = 4'd1;
            4'd1:    key = 4'd2;
            4'd2:    key = 4'd3;
            4'd3:    key = K_CHG;
            4'd4:    key = 4'd4;
            4'd5:    key = 4'd5;
            4'd6:    key = 4'd6;
            4'd7:    key = K_RST;
            4'd8:    key = 4'd7;
            4'd9:    key = 4'd8;
            4'd10:   key = 4'd9;
            4'd12:   key = K_OK;
            4'd13:   key = 4'd0;
            4'd14:   key = K_BS;
            4'd15:   key = K_CLR;
            default: key = K_NONE;      // pb11
        endcase
endmodule
