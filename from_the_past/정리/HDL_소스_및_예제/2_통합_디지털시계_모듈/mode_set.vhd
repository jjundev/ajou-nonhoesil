LIBRARY ieee;
USE ieee.std_logic_1164.all;
USE ieee.std_logic_arith.all;

ENTITY mode_set IS
	PORT(
		clk100							: IN	STD_LOGIC;
		reset, mode_in, time_set_in		: IN	STD_LOGIC;
		clear_in, start_stop_in			: IN	STD_LOGIC;		
		mode, disp_on_off, time_set		: BUFFER	STD_LOGIC;
		start_stop, clear				: BUFFER	STD_LOGIC);
END mode_set;

ARCHITECTURE a OF mode_set IS
	SIGNAL reset_s, mode_in_s, time_set_in_s	: STD_LOGIC;
	SIGNAL clear_in_s, start_stop_in_s			: STD_LOGIC;
BEGIN
	oneshot:
	PROCESS (clk100, reset, mode_in, time_set_in, clear_in, start_stop_in)
	BEGIN
		IF (clk100'event AND clk100 = '1') THEN
			reset_s <= reset; 
			disp_on_off <= NOT(reset AND NOT(reset_s));
						
			mode_in_s <= mode_in; 
			mode <= mode_in AND NOT(mode_in_s);
			
			time_set_in_s <= time_set_in;
			time_set <= time_set_in AND NOT(time_set_in_s);
						
			start_stop_in_s <= start_stop_in;
			start_stop <= start_stop_in AND NOT(start_stop_in_s);

			clear_in_s <= clear_in; 			
			clear <= clear_in AND NOT(clear_in_s);
		END IF;
	END PROCESS oneshot;
	

END a;

