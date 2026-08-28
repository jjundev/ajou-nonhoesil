LIBRARY ieee;
USE ieee.std_logic_1164.all;
USE ieee.std_logic_arith.all;

ENTITY clk_gen IS
	PORT(
		clk1m		: IN	STD_LOGIC;
		reset		: IN	STD_LOGIC;
		clk100		: BUFFER	STD_LOGIC;
		clk400		: BUFFER	STD_LOGIC);
END clk_gen;

ARCHITECTURE a OF clk_gen IS
	SIGNAL cnt5000	: INTEGER RANGE 0 to 5000;
	SIGNAL cnt1250	: INTEGER RANGE 0 to 1250;

BEGIN
	div10000:
	PROCESS (reset, clk1m)
	BEGIN
		WAIT UNTIL clk1m = '1';

		IF (reset = '1') THEN
			clk100 <= '0';
			cnt5000 <= 0;
			
		ELSIF (clk1m'event AND clk1m = '1') THEN
		
			IF(cnt5000 = 4999) THEN
				cnt5000 <= 0;
				clk100 <= NOT (clk100);
			ELSE cnt5000 <= cnt5000 + 1;

			END IF;

		END IF;

	END PROCESS div10000;
	
	div2500:
	PROCESS (reset, clk1m)
	BEGIN
		WAIT UNTIL clk1m = '1';

		IF (reset = '1') THEN
			clk400 <= '0';
			cnt1250 <= 0;
			
		ELSIF (clk1m'event AND clk1m = '1') THEN
		
			IF(cnt1250 = 1249) THEN
				cnt1250 <= 0;
				clk400 <= NOT (clk400);
			ELSE cnt1250 <= cnt1250 + 1;

			END IF;

		END IF;

	END PROCESS div2500;	
END a;
