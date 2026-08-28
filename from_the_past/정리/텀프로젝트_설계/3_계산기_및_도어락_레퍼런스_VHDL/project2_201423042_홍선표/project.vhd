library ieee;  -- library 선언, ieee 라이브러리 사용함.						
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity project2 is	    --entity명이 project2
port (
-----------------------------
-- Pins declaration.
-----------------------------
-- on board clock source, PIN_R8
	clock_50m :in std_logic; -- 50MHz clock, 내장 clock
	pb : in std_logic_vector(16 downto 1);	 --버튼 스위치 입력 선언 (총 16개 버튼이 있으므로 16개 정의)
	fnd_s : out std_logic_vector(5 downto 0); --segment select 출력 선언 (연산자 및 ac 포함)
	fnd_d : out std_logic_vector(7 downto 0)); --segment data bus 출력 선언 ( )
end project2;

architecture body_project2 of project2 is --architecture project

--상태가 sw_idle, sw_s1, sw_s2, sw_s3, sw_s4, sw_s5, sw_s6, sw_result, sw_error, sw_operator을 갖는 state선언
type state is (sw_idle, sw_s1, sw_s2, sw_s3, sw_s4, sw_s5, sw_s6, sw_result, sw_error, sw_operator);

signal sw_status : state:=sw_idle;  --sw_status 신호선언 초기값에 sw_idle 대입
signal init_counter : std_logic_vector(31 downto 0) := "00000000000000000000000000000000"; --init_counter신호선언 clock 분주기
signal sw_clk : std_logic;	  --sw_clk신호선언, 버튼 감지용 clock
signal sw_toggle : std_logic:='0';
signal multi_check : std_logic := '0';

signal npb : std_logic_vector(16 downto 1):=X"0000"; --npb신호 선언, 스위치의 not값
signal pb_1st : std_logic_vector(16 downto 1):=X"0000"; --pb_1st신호선언, 스위치 처음 감지된값
signal pb_2nd : std_logic_vector(16 downto 1):=X"0000"; --pb_2nd신호선언, 스위치 두번째 감지된값

signal num_temp : integer:=0; --입력값 저장을 위한 변수
signal calc_flag : integer:=0; --동작관련 flag 변수
signal disp_flag : integer:=0; --동작관련 flag 변수
signal cal_result : integer := 0; --계산 결과 저장할 변수

--계산 결과 출력용 6자리 신호 정의, 0~9는 숫자와 동일값
signal num1_1 : integer range 0 to 20:=20; --display할 10^0자리 신호 선언
signal num1_2 : integer range 0 to 20:=20; --display할 10^1자리 신호 선언
signal num1_3 : integer range 0 to 20:=20; --display할 10^2자리 신호 선언
signal num1_4 : integer range 0 to 20:=20; --display할 10^3자리 신호 선언
signal num1_5 : integer range 0 to 20:=20; --display할 10^4자리 신호 선언
signal num1_6 : integer range 0 to 20:=20; --display할 10^5자리 신호 선언

--연산자 관련
signal opPast : integer range 0 to 4:=4; --0 : +, 1 : -, 2 : *, 3 : /, 4 : idle
signal opCurr : integer range 0 to 4:=4; --0 : +, 1 : -, 2 : *, 3 : /, 4 : idle

signal pass_ok : std_logic:='1'; --pass_ok,1?? ???? OK

-- 7-Segment관련 신호선언
signal fnd_clk : std_logic;	   --7segment clock
signal fnd_cnt : integer range 5 downto 0; --fnd count에 사용
signal seg_100000 : std_logic_vector(6 downto 0) := "0000000";	--segment 100000의 자리
signal seg_10000 : std_logic_vector(6 downto 0) := "0000000";	--segment 10000의 자리
signal seg_1000 : std_logic_vector(6 downto 0) := "0000000"; --segment 1000의 자리
signal seg_100 : std_logic_vector(6 downto 0) := "0000000";	 --segment 100의 자리
signal seg_10 : std_logic_vector(6 downto 0) := "0000000"; --segment 10의 자리
signal seg_1 : std_logic_vector(6 downto 0) := "0000000";  --segment 1의 자리

begin
npb <= not pb; --푸시버튼스위치는 눌렀을때 '0'이므로 not을 해준다.

process(clock_50m)	--감지신호가 clock_50m 인 process문
	begin
	if rising_edge(clock_50m) then	   --clock_50m이 상승에지 일때
		init_counter <= init_counter+1; --init_counter 하나씩 증가함.
	end if;
end process;
  
--스위치를 눌렀을때 glitch가 발생하며 한번 눌렀을때 여러차례 신호가 감지된다.
--이를 보완하기 위해 버튼 스위치는 클럭으로 감지한다.
--본 예제에서는 40ms 클럭을 사용하고 두번 감지하여 같을때 눌린것으로 인식한다.
--참고로 버튼을 사람이 눌렀을때 대략 30ms이상이 된다.

sw_clk <= init_counter(20); -- ~40ms clock,
fnd_clk <= init_counter(16); -- ~2ms clock, 50MHz 클럭을 17번 분주한 clock

process(sw_clk,npb,pb_1st,pb_2nd,sw_toggle)	 -- sw_clk,npb,pb_1st,PB_2nd,pb_toggle을 감지 신호로 하는 process문
	begin
	if rising_edge(sw_clk)then -- sw_clk가 상승에지일때,~40ms 클럭으로 눌림 감지
		pb_2nd <= pb_1st; --pb_2nd에 pb_1st를 대입
		pb_1st <= npb;	 --pb_1st에 npb를 대입

		if((pb_2nd = X"0000") and (pb_1st /= pb_2nd))then --pb_2nd가 X"0000"이고 pb_1st와 pb_2nd가 다른값 일때
			sw_toggle <= '1';	  -- sw_toggle에 1을 대입, 즉 버튼이 눌렸다면
		elsif(calc_flag = 1)then --calc_flag가 1이면
			if(opPast = 0)then --이전에 저장된 연산자를 이용하여 연산 -- 덧셈 선언
				cal_result <= cal_result + num_temp; --기존의 값에 연산을 하여 cal_result에 다시 저장
			elsif(opPast = 1)then
				cal_result <= cal_result - num_temp;
			elsif(opPast = 2)then
				cal_result <= cal_result * num_temp;
			elsif(opPast = 3)then
				cal_result <= cal_result / num_temp;
			else
				cal_result <= num_temp; --연산자가 선택되지 않은 경우, 그냥 저장
			end if;

			if(opCurr = 4) then --현재 연산자가 선택되지 않은 경우
				calc_flag <= 2;--calc_flag를 2로
			else
				calc_flag <= 0;--calc_flag, num_temp 초기화
				num_temp <= 0;
				disp_flag <= 1;--disp_flag를 1로
			end if;
		elsif(calc_flag = 2)then
			cal_result <= cal_result;
			calc_flag <= 0;
			num_temp <= 0;
			disp_flag <= 1;

		elsif(disp_flag = 1)then
			disp_flag <=0; --cal_result가 각 조건에 해당할 경우, 그에 해당하는 결과 출력
			if(cal_result >= 0 and cal_result < 10) then
				num1_1 <= 20;
				num1_2 <= 20;
				num1_3 <= 20;  
				num1_4 <= 20;
				num1_5 <= 20;
				num1_6 <= (cal_result mod 10); --cal_result의 첫째자리 출력
				
						   
			elsif(cal_result < 0) then
			   num1_1 <= 20;--null
				num1_2 <= 20;--null
				num1_3 <= 16;--E
				num1_4 <= 17;--r
				num1_5 <= 17;--r
				num1_6 <= 20;--null

			elsif(cal_result >= 10 and cal_result < 100) then
				num1_1 <= 20;
				num1_2 <= 20;
				num1_3 <= 20;
				num1_4 <= 20;
				num1_5 <= (cal_result mod 100) / 10; --cal_result의 둘째자리 출력
				num1_6 <= (cal_result mod 10); --cal_result의 첫째자리 출력
			elsif(cal_result >= 100 and cal_result < 1000) then
				num1_1 <= 20;
				num1_2 <= 20;
				num1_3 <= 20;
				num1_4 <= (cal_result mod 1000) / 100; --cal_result의 셋째자리 출력
				num1_5 <= (cal_result mod 100) / 10; --cal_result의 첫째자리 출력
				num1_6 <= (cal_result mod 10); --cal_result의 첫째자리 출력
			elsif(cal_result >= 1000 and cal_result < 10000) then
				num1_1 <= 20;
				num1_2 <= 20;
				num1_3 <= (cal_result mod 10000) / 1000; --cal_result의 넷째자리 출력
				num1_4 <= (cal_result mod 1000) / 100; --cal_result의 셋째자리 출력
				num1_5 <= (cal_result mod 100) / 10; --cal_result의 첫째자리 출력
				num1_6 <= (cal_result mod 10); --cal_result의 첫째자리 출력
			elsif(cal_result >= 10000 and cal_result < 100000) then
				num1_1 <= 20;
				num1_2 <= (cal_result mod 100000) / 10000; --cal_result의 다섯째자리 출력
				num1_3 <= (cal_result mod 10000) / 1000; --cal_result의 넷째자리 출력
				num1_4 <= (cal_result mod 1000) / 100; --cal_result의 셋째자리 출력
				num1_5 <= (cal_result mod 100) / 10; --cal_result의 첫째자리 출력
				num1_6 <= (cal_result mod 10); --cal_result의 첫째자리 출력 
			elsif(cal_result >= 100000 and cal_result < 1000000) then
				num1_1 <= cal_result / 100000; --cal_result의 여섯째자리 출력
				num1_2 <= (cal_result mod 100000) / 10000; --cal_result의 다섯째자리 출력
				num1_3 <= (cal_result mod 10000) / 1000; --cal_result의 넷째자리 출력
				num1_4 <= (cal_result mod 1000) / 100; --cal_result의 셋째자리 출력
				num1_5 <= (cal_result mod 100) / 10; --cal_result의 첫째자리 출력
				num1_6 <= (cal_result mod 10); --cal_result의 첫째자리 출력
			else
				num1_1 <= 20;--null
				num1_2 <= 20;--null
				num1_3 <= 16;--E
				num1_4 <= 17;--r
				num1_5 <= 17;--r
				num1_6 <= 20;--null -- Err 출력 
			end if;
		end if;

		if((sw_toggle = '1')and(pb_1st = pb_2nd))then --sw_toggle이 '1'이고 pb_1st와 pb_2nd가 같다면
			sw_toggle <= '0';	--sw_toggle에 '0'을 대입, 스위치를 계속 눌렀을때 연속 검출 방지
			case pb_1st is  --pb_1st의 값이
			
				when x"0_0_0_1" =>	  -- switch_1
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 1; --num1_6에 1 대입
						num_temp <= 1; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 1; --num1_6에 1 대입
						num_temp <= num1_6 * 10 + 1; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 1; --num1_6에 1 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 1;	--num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 1; --num1_6에 1 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 1;  --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 1; --num1_6에 1 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 1;  --num_temp에 현재 display된 값 대입			  
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6;  --sw_status에 sw_s6대입
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 1; --num1_6에 1 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 1;  --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;
				when x"0_0_0_2" =>	-- switch_2
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 2; --num1_6에 2 대입
						num_temp <= 2; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;--num1_5에 num1_6 
						num1_6 <= 2; --num1_6에 2 대입
						num_temp <= num1_6 * 10 + 2; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 2; --num1_6에 2 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 2; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 2; --num1_6에 2 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 2; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 2; --num1_6에 2 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 2; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 2; --num1_6에 2 대입  
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 2; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if; 
				when x"0_0_0_4" => -- switch_3
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 3; --num1_6에 3 대입
						num_temp <= 3;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 3; --num1_6에 3 대입
						num_temp <= num1_6 * 10 + 3; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 3; --num1_6에 3 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 3; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 3; --num1_6에 3 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 3; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 3; --num1_6에 3 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 3; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 3; --num1_6에 3 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 3; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;		
				
		when x"0_0_1_0" => -- switch_4
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 4; --num1_6에 4 대입
						num_temp <= 4;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 4; --num1_6에 4 대입
						num_temp <= num1_6 * 10 + 4; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 4; --num1_6에 4 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 4; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 4; --num1_6에 4 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 4; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 4; --num1_6에 4 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 4; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 4; --num1_6에 4 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 4; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;			
					when x"0_0_2_0" => -- switch_5
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 5; --num1_6에 5 대입
						num_temp <= 5;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 5; --num1_6에 5 대입
						num_temp <= num1_6 * 10 + 5; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 5; --num1_6에 5 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 5; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 5; --num1_6에 5 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 5; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 5; --num1_6에 5 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 5; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 5; --num1_6에 5 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 5; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;			
					when x"0_0_4_0" => -- switch_6
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 6; --num1_6에 6 대입
						num_temp <= 6;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 6; --num1_6에 6 대입
						num_temp <= num1_6 * 10 + 6; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 6; --num1_6에 6 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 6; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 6; --num1_6에 6 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 6; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 6; --num1_6에 6 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 6; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 6; --num1_6에 6 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 6; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;			
					when x"0_1_0_0" => -- switch_7
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 7; --num1_6에 7 대입
						num_temp <= 7;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 7; --num1_6에 7 대입
						num_temp <= num1_6 * 10 + 7; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 7; --num1_6에 7 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 7; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 7; --num1_6에 7 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 7; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 7; --num1_6에 7 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 7; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 7; --num1_6에 7 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 7; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;			
					when x"0_2_0_0" => -- switch_8
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 8; --num1_6에 8 대입
						num_temp <= 8;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 8; --num1_6에 8 대입
						num_temp <= num1_6 * 10 + 8; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 8; --num1_6에 8 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 8; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 8; --num1_6에 8 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 8; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 8; --num1_6에 8 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 8; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 8; --num1_6에 8 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 8; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;			when x"0_4_0_0" => -- switch_9
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 9; --num1_6에 9 대입
						num_temp <= 9;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 9; --num1_6에 9 대입
						num_temp <= num1_6 * 10 + 9; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 9; --num1_6에 9 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 9; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 9; --num1_6에 9 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 9; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 9; --num1_6에 9 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 9; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 9; --num1_6에 9 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 9; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;	
			when x"2_0_0_0" => -- switch_0
					if(sw_status = sw_idle or sw_status = sw_error)then --sw_status가 sw_idle 또는 sw_error이면
						sw_status <= sw_s1; --sw_status에 sw_s1대입
						num1_1 <= 20;--num1_1에 20 대입(빈칸)
						num1_2 <= 20;--num1_2에 20 대입(빈칸)
						num1_3 <= 20;--num1_3에 20 대입(빈칸)
						num1_4 <= 20;--num1_4에 20 대입(빈칸)
						num1_5 <= 20;--num1_5에 20 대입(빈칸)
						num1_6 <= 0; --num1_6에 0 대입
						num_temp <= 0;
					elsif(sw_status = sw_s1)then --sw_status가 sw_s1이면
						sw_status <= sw_s2; --sw_status에 sw_s2대입
						num1_5 <= num1_6;
						num1_6 <= 0; --num1_6에 0 대입
						num_temp <= num1_6 * 10 + 0; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s2)then --sw_status가 sw_s2이면
						sw_status <= sw_s3; --sw_status에 sw_s3대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 0; --num1_6에 0 대입
						num_temp <= num1_5 * 100 + num1_6 * 10 + 0; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s3)then --sw_status가 sw_s3이면
						sw_status <= sw_s4; --sw_status에 sw_s4대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 0; --num1_6에 0 대입
						num_temp <= num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 0; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s4)then --sw_status가 sw_s4이면
						sw_status <= sw_s5; --sw_status에 sw_s5대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 0; --num1_6에 0 대입
						num_temp <= num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 0; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s5)then --sw_status가 sw_s5이면
						sw_status <= sw_s6; --sw_status에 sw_s6대입 
						num1_1 <= num1_2;--num1_1에 num1_2 대입
						num1_2 <= num1_3;--num1_2에 num1_3 대입
						num1_3 <= num1_4;--num1_3에 num1_4 대입
						num1_4 <= num1_5;--num1_4에 num1_5 대입
						num1_5 <= num1_6;--num1_5에 num1_6 대입
						num1_6 <= 0; --num1_6에 0 대입
						num_temp <= num1_2 * 100000 + num1_3 * 10000 + num1_4 * 1000 + num1_5 * 100 + num1_6 * 10 + 0; --num_temp에 현재 display된 값 대입
					elsif(sw_status = sw_s6)then --sw_status가 sw_s6이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else
						null;
					end if;	
			
				when x"0_0_0_8" =>	-- switch_+ 
					if(sw_status = sw_idle)then --sw_status가 sw_idle이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else --sw_status가 sw_idle이외의 state이면
						sw_status <= sw_idle; --sw_status에 sw_idle대입
						calc_flag <= 1;			   
						opPast <= opCurr; --현재 저장된 operator opPast에 저장
						opCurr <= 0; --opCurr에 +에 해당하는 operator 값 대입
					end if;			
					
					when x"0_0_8_0" =>	-- switch_- 
					if(sw_status = sw_idle)then --sw_status가 sw_idle이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else --sw_status가 sw_idle이외의 state이면
						sw_status <= sw_idle; --sw_status에 sw_idle대입
						calc_flag <= 1;			   
						opPast <= opCurr; --현재 저장된 operator opPast에 저장
						opCurr <= 1; --opCurr에 -에 해당하는 operator 값 대입
					end if;			
					
					when x"0_8_0_0" =>	-- switch_* 
					if(sw_status = sw_idle)then --sw_status가 sw_idle이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
					else --sw_status가 sw_idle이외의 state이면
						sw_status <= sw_idle; --sw_status에 sw_idle대입
						calc_flag <= 1;			   
						opPast <= opCurr; --현재 저장된 operator opPast에 저장
						opCurr <= 2; --opCurr에 *에 해당하는 operator 값 대입
					end if;	
					
					when x"8_0_0_0" =>	-- switch_/ 
					if(sw_status = sw_idle)then --sw_status가 sw_idle이면
						sw_status <= sw_error; --sw_status에 sw_error대입
						num1_1 <= 20;--null
						num1_2 <= 20;--null
						num1_3 <= 16;--E
						num1_4 <= 17;--r
						num1_5 <= 17;--r
						num1_6 <= 20;--null
						
								
					elsif (num_temp /= 0) then
					   cal_result <= cal_result / num_temp;
    
					else --sw_status가 sw_idle이외의 state이면
						sw_status <= sw_idle; --sw_status에 sw_idle대입
						calc_flag <= 1;			   
						opPast <= opCurr; --현재 저장된 operator opPast에 저장
						opCurr <= 3; --opCurr에 /에 해당하는 operator 값 대입
					end if;	
			
			
					
					
				when x"1_0_0_0" =>	-- switch_=
					if(sw_status = sw_idle)then --sw_status가 sw_idle이면  
						num1_1 <= 20;
						num1_2 <= 20;
						num1_3 <= 20;
						num1_4 <= 20;
						num1_5 <= 20;
						num1_6 <= 0; -- 0 출력
					end if;
					sw_status <= sw_idle; --sw_status에 sw_idle대입	
					calc_flag <= 1;			   
					opPast <= opCurr; --현재 저장된 operator opPast에 저장
					opCurr <= 4; --opCurr 초기화
					
				when x"4_0_0_0" =>	-- switch_AC
					sw_status <= sw_idle; --sw_status에 sw_idle대입
					num1_1 <= 20;
					num1_2 <= 20;
					num1_3 <= 20;
					num1_4 <= 20;
					num1_5 <= 20;
					num1_6 <= 20; -- 모두 빈칸 출력
					cal_result <= 0; -- cal_result 초기화
					num_temp <= 0;
				when others => null;
			end case;
		end if;		
	end if;
end process;

process(num1_1, num1_2, num1_3, num1_4, num1_5, num1_6) --숫자 출력이므로 건드리지 않는다
begin
	if(num1_1 = 0)then  --num1_1이 0이면 
		seg_100000 <= B"0111111"; --seg_100000에 "0"에 해당하는 값을 대입
	elsif(num1_1 = 1)then  --num1_1이 1이면 
		seg_100000 <= B"0000110"; --seg_100000에 "1"에 해당하는 값을 대입
	elsif(num1_1 = 2)then  --num1_1이 2이면 
		seg_100000 <= B"1011011"; --seg_100000에 "2"에 해당하는 값을 대입
	elsif(num1_1 = 3)then  --num1_1이 3이면 
		seg_100000 <= B"1001111"; --seg_100000에 "3"에 해당하는 값을 대입
	elsif(num1_1 = 4)then  --num1_1이 4이면 
		seg_100000 <= B"1100110"; --seg_100000에 "4"에 해당하는 값을 대입
	elsif(num1_1 = 5)then  --num1_1이 5이면 
		seg_100000 <= B"1101101"; --seg_100000에 "5"에 해당하는 값을 대입
	elsif(num1_1 = 6)then  --num1_1이 6이면 
		seg_100000 <= B"1111101"; --seg_100000에 "6"에 해당하는 값을 대입
	elsif(num1_1 = 7)then  --num1_1이 7이면 
		seg_100000 <= B"0000111"; --seg_100000에 "7"에 해당하는 값을 대입
	elsif(num1_1 = 8)then  --num1_1이 8이면 
		seg_100000 <= B"1111111"; --seg_100000에 "8"에 해당하는 값을 대입
	elsif(num1_1 = 9)then  --num1_1이 9이면 
		seg_100000 <= B"1100111"; --seg_100000에 "9"에 해당하는 값을 대입
	elsif(num1_1 = 10)then  --num1_1이 10이면 
		seg_100000 <= B"1111000"; --seg_100000에 "10"에 해당하는 값을 대입
	elsif(num1_1 = 11)then  --num1_1이 11이면 
		seg_100000 <= B"1110011"; --seg_100000에 "11"에 해당하는 값을 대입
	elsif(num1_1 = 12)then  --num1_1이 12이면 
		seg_100000 <= B"1110111"; --seg_100000에 "12"에 해당하는 값을 대입
	elsif(num1_1 = 13)then  --num1_1이 13이면 
		seg_100000 <= B"1111100"; --seg_100000에 "13"에 해당하는 값을 대입
	elsif(num1_1 = 14)then  --num1_1이 14이면 
		seg_100000 <= B"0111001"; --seg_100000에 "14"에 해당하는 값을 대입
	elsif(num1_1 = 15)then  --num1_1이 15이면 
		seg_100000 <= B"1011110"; --seg_100000에 "15"에 해당하는 값을 대입
	elsif(num1_1 = 16)then  --num1_1이 16이면 
		seg_100000 <= B"1111001"; --seg_100000에 "16"에 해당하는 값을 대입
	elsif(num1_1 = 17)then  --num1_1이 17이면 
		seg_100000 <= B"1010000"; --seg_100000에 "17"에 해당하는 값을 대입
	elsif(num1_1 = 18)then  --num1_1이 18이면 
		seg_100000 <= B"1000000"; --seg_100000에 "18"에 해당하는 값을 대입
	elsif(num1_1 = 19)then  --num1_1이 19이면 
		seg_100000 <= B"1010100"; --seg_100000에 "19"에 해당하는 값을 대입
	else  --num1_1이 기타값이면 
		seg_100000 <= B"0000000"; --seg_100000에 아무것도 표시하지 않음
	end if;

	if(num1_2 = 0)then
		seg_10000 <= B"0111111";
	elsif(num1_2 = 1)then
		seg_10000 <= B"0000110";
	elsif(num1_2 = 2)then
		seg_10000 <= B"1011011";
	elsif(num1_2 = 3)then
		seg_10000 <= B"1001111";
	elsif(num1_2 = 4)then
		seg_10000 <= B"1100110";
	elsif(num1_2 = 5)then
		seg_10000 <= B"1101101";
	elsif(num1_2 = 6)then
		seg_10000 <= B"1111101";
	elsif(num1_2 = 7)then
		seg_10000 <= B"0000111"; 
	elsif(num1_2 = 8)then
		seg_10000 <= B"1111111";
	elsif(num1_2 = 9)then
		seg_10000 <= B"1100111";
	elsif(num1_2 = 10)then	
		seg_10000 <= B"1111000";
	elsif(num1_2 = 11)then	
		seg_10000 <= B"1110011"; 
	elsif(num1_2 = 12)then
		seg_10000 <= B"1110111";
	elsif(num1_2 = 13)then
		seg_10000 <= B"1111100";
	elsif(num1_2 = 14)then
		seg_10000 <= B"0111001"; 
	elsif(num1_2 = 15)then
		seg_10000 <= B"1011110";
	elsif(num1_2 = 16)then
		seg_10000 <= B"1111001"; 
	elsif(num1_2 = 17)then
		seg_10000 <= B"1010000";
	elsif(num1_2 = 18)then
		seg_10000 <= B"1000000";
	elsif(num1_2 = 19)then
		seg_10000 <= B"1010100";
	else 
		seg_10000 <= B"0000000"; 
	end if;

	if(num1_3 = 0)then
		seg_1000 <= B"0111111"; 
	elsif(num1_3 = 1)then
		seg_1000 <= B"0000110";
	elsif(num1_3 = 2)then
		seg_1000 <= B"1011011";
	elsif(num1_3 = 3)then	
		seg_1000 <= B"1001111"; 
	elsif(num1_3 = 4)then
		seg_1000 <= B"1100110"; 
	elsif(num1_3 = 5)then	
		seg_1000 <= B"1101101";
	elsif(num1_3 = 6)then	
		seg_1000 <= B"1111101"; 
	elsif(num1_3 = 7)then	
		seg_1000 <= B"0000111"; 
	elsif(num1_3 = 8)then	
		seg_1000 <= B"1111111"; 
	elsif(num1_3 = 9)then	
		seg_1000 <= B"1100111"; 
	elsif(num1_3 = 10)then	 
		seg_1000 <= B"1111000";
	elsif(num1_3 = 11)then	 
		seg_1000 <= B"1110011";
	elsif(num1_3 = 12)then	 
		seg_1000 <= B"1110111";
	elsif(num1_3 = 13)then	 
		seg_1000 <= B"1111100";
	elsif(num1_3 = 14)then	 
		seg_1000 <= B"0111001";
	elsif(num1_3 = 15)then	 
		seg_1000 <= B"1011110";
	elsif(num1_3 = 16)then	 
		seg_1000 <= B"1111001";
	elsif(num1_3 = 17)then	 
		seg_1000 <= B"1010000";
	elsif(num1_3 = 18)then	 
		seg_1000 <= B"1000000";
	elsif(num1_3 = 19)then	 
		seg_1000 <= B"1010100"; 
	else 
		seg_1000 <= B"0000000"; 
	end if;

	if(num1_4=0)then  
		seg_100 <= B"0111111"; 
	elsif(num1_4=1)then  
		seg_100 <= B"0000110"; 
	elsif(num1_4=2)then  
		seg_100 <= B"1011011"; 
	elsif(num1_4=3)then  
		seg_100 <= B"1001111"; 
	elsif(num1_4=4)then  
		seg_100 <= B"1100110"; 
	elsif(num1_4=5)then  
		seg_100 <= B"1101101"; 
	elsif(num1_4=6)then  
		seg_100 <= B"1111101"; 
	elsif(num1_4=7)then  
		seg_100 <= B"0000111"; 
	elsif(num1_4=8)then  
		seg_100 <= B"1111111"; 
	elsif(num1_4=9)then  
		seg_100 <= B"1100111"; 
	elsif(num1_4 = 10)then	 
		seg_100 <= B"1111000"; 
	elsif(num1_4 = 11)then	 
		seg_100 <= B"1110011"; 
	elsif(num1_4 = 12)then	 
		seg_100 <= B"1110111"; 
	elsif(num1_4 = 13)then	 
		seg_100 <= B"1111100"; 
	elsif(num1_4 = 14)then	 
		seg_100 <= B"0111001"; 
	elsif(num1_4 = 15)then	 
		seg_100 <= B"1011110"; 
	elsif(num1_4 = 16)then	 
		seg_100 <= B"1111001"; 
	elsif(num1_4 = 17)then	 
		seg_100 <= B"1010000"; 
	elsif(num1_4 = 18)then	 
		seg_100 <= B"1000000";
	elsif(num1_4 = 19)then	 
		seg_100 <= B"1010100"; 
	else  
		seg_100 <= B"0000000"; 
	end if;

	if(num1_5=0)then  
		seg_10 <= B"0111111";
	elsif(num1_5=1)then  
		seg_10 <= B"0000110";
	elsif(num1_5=2)then  
		seg_10 <= B"1011011";
	elsif(num1_5=3)then  
		seg_10 <= B"1001111";
	elsif(num1_5=4)then  
		seg_10 <= B"1100110";
	elsif(num1_5=5)then  
		seg_10 <= B"1101101";
	elsif(num1_5=6)then  
		seg_10 <= B"1111101";
	elsif(num1_5=7)then  
		seg_10 <= B"0000111";
	elsif(num1_5=8)then  
		seg_10 <= B"1111111";
	elsif(num1_5=9)then 
		seg_10 <= B"1100111";
	elsif(num1_5 = 10)then	 
		seg_10 <= B"1111000";
	elsif(num1_5 = 11)then	 
		seg_10 <= B"1110011";
	elsif(num1_5 = 12)then	 
		seg_10 <= B"1110111";
	elsif(num1_5 = 13)then	 
		seg_10 <= B"1111100";
	elsif(num1_5 = 14)then	 
		seg_10 <= B"0111001";
	elsif(num1_5 = 15)then	 
		seg_10 <= B"1011110";
	elsif(num1_5 = 16)then	 
		seg_10 <= B"1111001";
	elsif(num1_5 = 17)then	 
		seg_10 <= B"1010000";
	elsif(num1_5 = 18)then	 
		seg_10 <= B"1000000";
	elsif(num1_5 = 19)then	 
		seg_10 <= B"1010100"; 
	else  
		seg_10 <= B"0000000";
	end if;

	if(num1_6=0)then  
		seg_1 <= B"0111111"; 
	elsif(num1_6=1)then  
		seg_1 <= B"0000110"; 
	elsif(num1_6=2)then  
		seg_1 <= B"1011011"; 
	elsif(num1_6=3)then  
		seg_1 <= B"1001111"; 
	elsif(num1_6=4)then  
		seg_1 <= B"1100110"; 
	elsif(num1_6=5)then  
		seg_1 <= B"1101101"; 
	elsif(num1_6=6)then  
		seg_1 <= B"1111101"; 
	elsif(num1_6=7)then  
		seg_1 <= B"0000111"; 
	elsif(num1_6=8)then  
		seg_1 <= B"1111111"; 
	elsif(num1_6=9)then  
		seg_1 <= B"1100111"; 
	elsif(num1_6 = 10)then	 
		seg_1 <= B"1111000"; 
	elsif(num1_6 = 11)then	 
		seg_1 <= B"1110011"; 
	elsif(num1_6 = 12)then	 
		seg_1 <= B"1110111"; 
	elsif(num1_6 = 13)then	  
		seg_1 <= B"1111100"; 
	elsif(num1_6 = 14)then	  
		seg_1 <= B"0111001"; 
	elsif(num1_6 = 15)then	  
		seg_1 <= B"1011110"; 
	elsif(num1_6 = 16)then	  
		seg_1 <= B"1111001"; 
	elsif(num1_6 = 17)then	  
		seg_1 <= B"1010000"; 
	elsif(num1_6 = 18)then	
		seg_1 <= B"1000000";
	elsif(num1_6 = 19)then	
		seg_1 <= B"1010100"; 
	else 
		seg_1 <= B"0000000";
	end if;
end process;

process(fnd_clk,fnd_cnt) --감지신호가 fnd_clk, fnd_cnt인 process문
begin
	if rising_edge(fnd_clk)then  --fnd_clk가 상승에지 일때
		case fnd_cnt is			 --fnd_cnt 값을 확인하여
			when 5 =>			--5일때 
				fnd_d <= '0' & seg_100000; --fnd_d에 seg_100000을 대입 한다.
				fnd_cnt <= 4;    --fnd_cnt에 4대입
			when 4 =>			--4일때 
				fnd_d <= '0' & seg_10000; --fnd_d에 seg_10000을 대입 한다.
				fnd_cnt <= 3;	--fnd_cnt에 3대입
			when 3 =>			--3일때 
				fnd_d <= '0' & seg_1000; --fnd_d에 seg_1000을 대입 한다.
				fnd_cnt <= 2;	--fnd_cnt에 2대입
			when 2 =>			--2일때 
				fnd_d <= '0' & seg_100; --fnd_d에 seg_100을 대입 한다.
				fnd_cnt <= 1;	--fnd_cnt에 1대입
			when 1 =>			--1일때 
				fnd_d <= '0' & seg_10; --fnd_d에 seg_10을 대입 한다.
				fnd_cnt <= 0;
			when 0 =>			--0일때  
				fnd_d <= '0' & seg_1; --fnd_d에 seg_1을 대입 한다.
				fnd_cnt <= 5;
			when others =>		--기타 값일때 변화 없음
				null;
		end case;
		
		if(fnd_cnt = 5)then  --fnd_cnt 값이 5일때 
			fnd_s(5) <= '0';   --fnd_s(5)에 '0' 대입
		else             --fnd_cnt 값이 5이 아닐때
			fnd_s(5) <= '1';   --fnd_s(5)에 '1' 대입
		end if;

		if(fnd_cnt = 4)then  --fnd_cnt 값이 4일때 
			fnd_s(4) <= '0';   --fnd_s(4)에 '0' 대입
		else             --fnd_cnt 값이 4이 아닐때
			fnd_s(4) <= '1';   --fnd_s(4)에 '1' 대입
		end if;

		if(fnd_cnt = 3)then  --fnd_cnt 값이 3일때 
			fnd_s(3) <= '0';   --fnd_s(3)에 '0' 대입
		else             --fnd_cnt 값이 3이 아닐때
			fnd_s(3) <= '1';   --fnd_s(3)에 '1' 대입
		end if;

		if(fnd_cnt = 2)then  --fnd_cnt 값이 2일때 
			fnd_s(2) <= '0';   --fnd_s(2)에 '0' 대입
		else             --fnd_cnt 값이 2이 아닐때
			fnd_s(2) <= '1';   --fnd_s(2)에 '1' 대입
		end if;

		if(fnd_cnt = 1)then  --fnd_cnt 값이 1일때 
			fnd_s(1) <= '0';   --fnd_s(1)에 '0' 대입
		else             --fnd_cnt 값이 1이 아닐때
			fnd_s(1) <= '1';   --fnd_s(1)에 '1' 대입
		end if;

		if(fnd_cnt = 0)then  --fnd_cnt 값이 0일때 
			fnd_s(0) <= '0';   --fnd_s(0)에 '0' 대입
		else             --fnd_cnt 값이 0이 아닐때
			fnd_s(0) <= '1';   --fnd_s(0)에 '1' 대입
		end if;
	end if;
end process;
end body_project2;