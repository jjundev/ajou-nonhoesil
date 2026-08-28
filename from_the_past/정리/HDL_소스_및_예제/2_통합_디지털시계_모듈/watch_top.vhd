LIBRARY ieee;
USE ieee.std_logic_1164.all;

ENTITY watch_top IS
	PORT(
		x1, rst, mode_in, start_stop_in		: IN	STD_LOGIC;	-- x1 : 1Mhz
		clear_in, time_set_in				: IN	STD_LOGIC;
		common								: BUFFER	STD_LOGIC_VECTOR(7 downto 0);
		secg								: BUFFER	STD_LOGIC_VECTOR(6 downto 0));
END watch_top;

ARCHITECTURE a OF watch_top IS
--<clk_gen>**********************************************
COMPONENT clk_gen
	PORT(
		clk1m		: IN	STD_LOGIC;
		reset		: IN	STD_LOGIC;
		clk100		: BUFFER	STD_LOGIC;
		clk400		: BUFFER	STD_LOGIC);
END COMPONENT;
--*******************************************************
--<mode_set>*********************************************
COMPONENT mode_set
	PORT(
		clk100							: IN	STD_LOGIC;
		reset, mode_in, time_set_in		: IN	STD_LOGIC;
		clear_in, start_stop_in			: IN	STD_LOGIC;		
		mode, disp_on_off, time_set		: BUFFER	STD_LOGIC;
		start_stop, clear				: BUFFER	STD_LOGIC);
END COMPONENT;
--*******************************************************
--<time>*************************************************
COMPONENT time
	PORT(
		reset, mode, time_set, start_stop	: IN	STD_LOGIC;
		clk100, clear						: IN	STD_LOGIC;
		tsec1, tmin1, thour1				: BUFFER	STD_LOGIC_VECTOR(9 downto 0);
		tsec2, tmin2						: BUFFER	STD_LOGIC_VECTOR(5 downto 0);
		thour2								: BUFFER	STD_LOGIC_VECTOR(2 downto 0));		
END COMPONENT;
--*******************************************************
--<stop_watch>*******************************************
COMPONENT stop_watch
	PORT(
		clk, rst 						: IN std_logic;
		mode, start_stop, clear	 		: IN std_logic;
		wsec_c1, wsec_c2, wsec1, wmin1 	: BUFFER std_logic_vector(9 downto 0);
		wsec2, wmin2 					: BUFFER std_logic_vector(5 downto 0));
END COMPONENT;
--*******************************************************
--<segment>**********************************************
COMPONENT segment
	PORT(
		clk400, clk100, mode			: IN	STD_LOGIC;
		tsec1, tmin1, thour1			: IN	STD_LOGIC_VECTOR(9 downto 0); 
		wsec_c2, wsec_c1, wsec1, wmin1	: IN	STD_LOGIC_VECTOR(9 downto 0); 
		tsec2, tmin2					: IN	STD_LOGIC_VECTOR(5 downto 0); 
		wmin2, wsec2					: IN	STD_LOGIC_VECTOR(5 downto 0); 
		thour2							: IN	STD_LOGIC_VECTOR(2 downto 0); 
		common							: BUFFER	STD_LOGIC_VECTOR(7 downto 0);	-- seg_select
		segs							: BUFFER	STD_LOGIC_VECTOR(6 downto 0));	-- seg_coding
END COMPONENT;
--*******************************************************
--[SIGNAL]-----------------------------------------------
SIGNAL clk, clk400										: STD_LOGIC;	-- 100Hz, 400Hz
SIGNAL mode, clear, start_stop, time_set, disp_on_off	: STD_LOGIC;
SIGNAL tsec1, tmin1, thour1								: STD_LOGIC_VECTOR(9 downto 0);
SIGNAL tsec2, tmin2										: STD_LOGIC_VECTOR(5 downto 0);
SIGNAL thour2											: STD_LOGIC_VECTOR(2 downto 0); 
SIGNAL wsec_c2_s, wsec_c1_s, wsec1_s, wmin1_s			: STD_LOGIC_VECTOR(9 downto 0);
SIGNAL wsec2_s, wmin2_s									: STD_LOGIC_VECTOR(5 downto 0);
---------------------------------
--	x1, rst, mode_in, start_stop_in		: IN	STD_LOGIC;	-- x1 : 1Mhz
--	clear_in, time_set_in				: IN	STD_LOGIC;
--	common								: BUFFER	STD_LOGIC_VECTOR(7 downto 0);
--	secg								: BUFFER	STD_LOGIC_VECTOR(6 downto 0));
---------------------------------
BEGIN
u0 :	clk_gen PORT MAP (x1, rst, clk, clk400);
u1 :	mode_set PORT MAP (clk, rst, mode_in, time_set_in, clear_in, start_stop_in, mode, disp_on_off,
							time_set, start_stop, clear);
u2 :	time PORT MAP (rst, mode, time_set, start_stop, clk, clear, tsec1, tmin1, thour1, tsec2, tmin2, thour2);
u3 :	stop_watch PORT MAP (clk, rst, 
							mode, start_stop, clear, 
							wsec_c1_s, wsec_c2_s, wsec1_s, wmin1_s, 
							wsec2_s, wmin2_s);
u4 :	segment PORT MAP (clk400, clk, mode, tsec1, tmin1, thour1, wsec_c2_s, wsec_c1_s, wsec1_s, wmin1_s, tsec2, 
							tmin2, wmin2_s, wsec2_s, thour2, common, secg);
END a;
