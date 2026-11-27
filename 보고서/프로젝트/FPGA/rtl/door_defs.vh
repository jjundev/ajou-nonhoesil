// 도어락 공통 정의. 모듈 안에서 include 해서 쓴다.
// 키: 0~9는 숫자 그대로
localparam [3:0] K_OK = 4'd10, K_CHG = 4'd11, K_RST = 4'd12,
                 K_BS = 4'd13, K_CLR = 4'd14, K_GST = 4'd15;   // K_GST: pb11 방문자
// 상태
localparam [2:0] S_IDLE = 3'd0, S_CHECK = 3'd1, S_OPEN = 3'd2, S_NEW_PW = 3'd3,
                 S_NEW_CONFIRM = 3'd4, S_MSG = 3'd5, S_LOCK = 3'd6,
                 S_GUEST_PW = 3'd7;
// 메시지
localparam [2:0] M_ERROR = 3'd0, M_NONE = 3'd1, M_DONE = 3'd2, M_INIT = 3'd3,
                 M_DEL = 3'd4;
