LIBRARY ieee;
USE ieee.std_logic_1164.all;
USE ieee.std_logic_arith.all;
USE ieee.std_logic_unsigned.all;

ENTITY segment IS
	PORT(
		clk400, clk100, mode			: IN	STD_LOGIC;
		tsec1, tmin1, thour1			: IN	STD_LOGIC_VECTOR(9 downto 0); 
		wsec_c2, wsec_c1, wsec1, wmin1	: IN	STD_LOGIC_VECTOR(9 downto 0); 
		tsec2, tmin2					: IN	STD_LOGIC_VECTOR(5 downto 0); 
		wmin2, wsec2					: IN	STD_LOGIC_VECTOR(5 downto 0); 
		thour2							: IN	STD_LOGIC_VECTOR(2 downto 0); 
		common							: BUFFER	STD_LOGIC_VECTOR(7 downto 0);	-- seg_select
		segs							: BUFFER	STD_LOGIC_VECTOR(6 downto 0));	-- seg_coding
END segment;

ARCHITECTURE a OF segment IS
SIGNAL ss1, ss2, mm1, mm2, hh1, hh2	: STD_LOGIC_VECTOR(6 downto 0) := "0000000";
SIGNAL com							: STD_LOGIC_VECTOR(7 downto 0) := "00000001";

--<DEF FUNCTION1>----------------------------------------------------------------------
	FUNCTION func_seg10(temp10	: STD_LOGIC_VECTOR) RETURN std_logic_vector IS
	VARIABLE seg_coding10 : std_logic_vector(6 downto 0);
	BEGIN
		IF (temp10 = "0000000001") THEN seg_coding10 := "0111111";	-- 0
		ELSIF (temp10 = "0000000010") THEN seg_coding10 := "0000110";	-- 1
		ELSIF (temp10 = "0000000100") THEN seg_coding10 := "1011011";	-- 2
		ELSIF (temp10 = "0000001000") THEN seg_coding10 := "1001111";	-- 3
		ELSIF (temp10 = "0000010000") THEN seg_coding10 := "1100110";	-- 4
		ELSIF (temp10 = "0000100000") THEN seg_coding10 := "1101101"; -- 5
		ELSIF (temp10 = "0001000000") THEN seg_coding10 := "1111101"; -- 6
		ELSIF (temp10 = "0010000000") THEN seg_coding10 := "0100111"; -- 7
		ELSIF (temp10 = "0100000000") THEN seg_coding10 := "1111111"; -- 8
		ELSIF (temp10 = "1000000000") THEN seg_coding10 := "1101111"; -- 9
		ELSE seg_coding10 := "0000000";
		END IF;

	RETURN (seg_coding10);
	END func_seg10;
-------------------------------------------------------------------------------------
--<DEF FUNCTION2>----------------------------------------------------------------------
	FUNCTION func_seg6(temp6	: STD_LOGIC_VECTOR) RETURN std_logic_vector IS
	VARIABLE seg_coding6 : std_logic_vector(6 downto 0);
	BEGIN
		IF (temp6 = "000001") THEN seg_coding6 := "0111111";	-- 0
		ELSIF (temp6 = "000010") THEN seg_coding6 := "0000110";	-- 1
		ELSIF (temp6 = "000100") THEN seg_coding6 := "1011011";	-- 2
		ELSIF (temp6 = "001000") THEN seg_coding6 := "1001111";	-- 3
		ELSIF (temp6 = "010000") THEN seg_coding6 := "1100110";	-- 4
		ELSIF (temp6 = "100000") THEN seg_coding6 := "1101101"; -- 5
		ELSE seg_coding6 := "0000000";
		END IF;

	RETURN (seg_coding6);
	END func_seg6;
-------------------------------------------------------------------------------------
--<DEF FUNCTION3>----------------------------------------------------------------------
	FUNCTION func_seg3(temp3 : STD_LOGIC_VECTOR) RETURN std_logic_vector IS
	VARIABLE seg_coding3 : std_logic_vector(6 downto 0);
	BEGIN
		IF (temp3 = "001") THEN seg_coding3 := "0111111";	-- 0
		ELSIF (temp3 = "010") THEN seg_coding3 := "0000110";	-- 1
		ELSIF (temp3 = "100") THEN seg_coding3 := "1011011";	-- 2
		ELSE seg_coding3 := "0000000";
		END IF;

	RETURN (seg_coding3);
	END func_seg3;
-------------------------------------------------------------------------------------

BEGIN

--<SEGMENT DISPLAY>------------------------------------------------------------------
	PROCESS (clk100)
	BEGIN
		IF (clk100'event AND clk100 = '1') THEN
			IF (mode = '0') THEN
				ss1 <= func_seg10(tsec1);
				ss2 <= func_seg6(tsec2);			
				mm1 <= func_seg10(tmin1);
				mm2 <= func_seg6(tmin2);			
				hh1 <= func_seg10(thour1);
				hh2 <= func_seg3(thour2);
				
			ELSIF (mode = '1') THEN
				ss1 <= func_seg10(wsec_c2);
				ss2 <= func_seg10(wsec_c1);
				mm1 <= func_seg10(wsec1);
				mm2 <= func_seg6(wsec2);
				hh1 <= func_seg10(wmin1);
				hh2 <= func_seg6(wmin2);
			END IF;
			
		END IF;
	END PROCESS;
-------------------------------------------------------------------------------------
--<SEGMENT SELECT>-------------------------------------------------------------------
	PROCESS(clk400)
	VARIABLE tempcom	: STD_LOGIC := '0';
	BEGIN
		IF (clk400'event AND clk400 = '1') THEN
			tempcom := com(7);
			FOR tc IN 0 TO 6 LOOP
				com(tc+1) <= com(tc);
			END LOOP;
			com(0) <= tempcom;
		END IF;
		
		CASE com IS
			WHEN "00000001" => segs <= ss1;
			WHEN "00000010" => segs <= ss2;
			WHEN "00000100" => segs <= "0000001";
			WHEN "00001000" => segs <= mm1;
			WHEN "00010000" => segs <= mm2;
			WHEN "00100000" => segs <= "0000001";
			WHEN "01000000" => segs <= hh1;
			WHEN "10000000" => segs <= hh2;
			WHEN OTHERS => segs <= "0000000";
		END CASE;
	END PROCESS;
	common <= com;
-------------------------------------------------------------------------------------	
END a;
