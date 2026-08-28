LIBRARY ieee;
USE ieee.std_logic_1164.all;
USE ieee.std_logic_unsigned.all;
USE ieee.std_logic_arith.all;

ENTITY time IS
	PORT(
		reset, mode, time_set, start_stop	: IN	STD_LOGIC;
		clk100, clear						: IN	STD_LOGIC;
		tsec1, tmin1, thour1				: BUFFER	STD_LOGIC_VECTOR(9 downto 0);
		tsec2, tmin2						: BUFFER	STD_LOGIC_VECTOR(5 downto 0);
		thour2								: BUFFER	STD_LOGIC_VECTOR(2 downto 0));		
END time;

ARCHITECTURE a OF time IS
SIGNAL sec_set				: UNSIGNED(6 downto 0) := "0000000";	-- 0 ~ 100(deciaml), 0 ~ 1100100(binary)	
SIGNAL ts1_a, tm1_a, th1_a	: STD_LOGIC_VECTOR(9 downto 0);
SIGNAL ts2_a, tm2_a			: STD_LOGIC_VECTOR(5 downto 0);
SIGNAL th2_a				: STD_LOGIC_VECTOR(2 downto 0);

BEGIN
--<clock count>---------------------------------------------
	PROCESS(clk100, reset)
	BEGIN
		IF(reset = '1') THEN
			sec_set <= "0000000";
		ELSIF(clk100'event AND clk100 = '1') THEN
			IF(sec_set=99) THEN
				sec_set <= "0000000";
			ELSE sec_set <= sec_set + 1;
			END IF;
		END IF;
	END PROCESS;
------------------------------------------------------------
--<sec count>-----------------------------------------------
	PROCESS(clk100, reset)
	VARIABLE ws, wss		: STD_LOGIC := '0';
	BEGIN
		IF(reset = '1' AND mode = '0') THEN
			ts1_a <= "0000000001";
			ts2_a <= "000001";			
		ELSIF(clk100'event AND clk100 = '1') THEN
			IF(sec_set = 99) THEN
				ws := ts1_a(9);
				FOR s IN 0 TO 8 LOOP
					ts1_a(s+1) <= ts1_a(s);
				END LOOP;
				ts1_a(0) <= ws;
				IF(ts1_a(9) = '1') THEN
					wss := ts2_a(5);
					FOR ss IN 0 TO 4 LOOP
						ts2_a(ss+1) <= ts2_a(ss);
					END LOOP;
					ts2_a(0) <= wss;
				END IF;
			END IF;
		END IF;
	END PROCESS;
------------------------------------------------------------
--<min count>-----------------------------------------------
	PROCESS(clk100, reset)
	VARIABLE wm, wmm		: STD_LOGIC := '0';
	BEGIN
		IF(reset = '1') THEN
			tm1_a <= "0000000001";
			tm2_a <= "000001";	
		ELSIF(clk100'event AND clk100 = '1') THEN
			IF((ts2_a(5) = '1' AND ts1_a(9) = '1' AND sec_set = 99) 
				OR (mode = '0' AND start_stop = '1' AND time_set = '1')) THEN -- minites edit
				wm := tm1_a(9);
				FOR m IN 0 to 8 LOOP
					tm1_a(m+1) <= tm1_a(m);
					END LOOP;
				tm1_a(0) <= wm;
				IF(tm1_a(9) = '1') THEN
					wmm := tm2_a(5);
					FOR mm IN 0 to 4 LOOP
						tm2_a(mm+1) <= tm2_a(mm);
					END LOOP;
					tm2_a(0) <= wmm;
				END IF;
			END IF;
		END IF;
	END PROCESS;
------------------------------------------------------------
--<hour count>----------------------------------------------
	PROCESS(clk100, reset)
	VARIABLE wh, whh		: STD_LOGIC := '0';	
	BEGIN
		IF(reset = '1') THEN
			th1_a <= "0000000001";
			th2_a <= "001";
		ELSIF(clk100'event AND clk100 = '1') THEN
			IF((tm2_a(5) = '1' AND tm1_a(9) = '1' AND ts2_a(5) = '1' AND ts1_a(9) = '1' AND sec_set = 99)
				OR (mode = '0' AND time_set = '1' AND clear = '1')) THEN -- hour edit
				IF (th2_a(1) <= '1' AND th1_a(9) = '1') THEN
					wh := th1_a(9);
					FOR h IN 0 to 8 LOOP
						th1_a(h+1) <= th1_a(h);
					END LOOP;
					th1_a(0) <= wh;
				ELSIF (th2_a(2) = '1' AND th1_a(3) = '1') THEN
					th1_a <= "0000000001";
					th2_a <= "001";
				ELSE
					whh := th2_a(2);
					FOR hh IN 0 to 1 LOOP
						th2_a(hh+1) <= th2_a(hh);
					END LOOP;
					th2_a(0) <= whh;
				END IF;
			END IF;
		END IF;
	END PROCESS;
------------------------------------------------------------
	tsec1 <= ts1_a;
	tsec2 <= ts2_a;
	tmin1 <= tm1_a;
	tmin2 <= tm2_a;
	thour1 <= th1_a;
	thour2 <= th2_a;		
END a;
