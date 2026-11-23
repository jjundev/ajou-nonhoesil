// 7 Segment 글자 코드(5비트). 숫자 0~9는 코드도 0~9이고 O는 0과 같다.
// 모듈 안에서 include 해서 쓴다.
localparam [4:0] G_O = 5'd0,
                 G_P = 5'd10, G_E = 5'd11, G_n = 5'd12, G_r = 5'd13,
                 G_o = 5'd14, G_d = 5'd15, G_I = 5'd16, G_t = 5'd17,
                 G_W = 5'd18, G_A = 5'd19, G_G = 5'd20, G_L = 5'd21,
                 G_C = 5'd22, G_K = 5'd23, G_DASH = 5'd24, G_OFF = 5'd25;
