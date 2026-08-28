LIBRARY ieee;
USE ieee.std_logic_1164.all;
USE ieee.std_logic_unsigned.all;
USE ieee.std_logic_arith.all;

ENTITY stop_watch is
	PORT(
		clk, rst 						: IN std_logic;
		mode, start_stop, clear	 		: IN std_logic;
		wsec_c1, wsec_c2, wsec1, wmin1 	: BUFFER std_logic_vector(9 downto 0);
		wsec2, wmin2 					: BUFFER std_logic_vector(5 downto 0));
END stop_watch;

ARCHITECTURE a OF stop_watch IS
SIGNAL start_stop_set							: std_logic;
SIGNAL wsec_c1_a, wsec_c2_a, wsec1_a, wmin1_a 	: std_logic_vector(9 downto 0);
SIGNAL wsec2_a, wmin2_a 						: std_logic_vector(5 downto 0);

BEGIN
-------------------------------------------------------------------------
	PROCESS(clk,rst)
	BEGIN
		IF(rst = '1') THEN
			start_stop_set <= '0';
		ELSIF(clk'event AND clk = '1')THEN
			IF(mode = '1' AND start_stop = '1')THEN
			start_stop_set <= NOT (start_stop_set);
			END IF;
		END IF;
	END PROCESS;
--<Tsec_c>-----------------------------------------------------------------------		
	PROCESS(clk,rst)
	VARIABLE tsc, tssc		: STD_LOGIC := '0';
	BEGIN
		IF(rst='1' OR (mode='1'AND clear='1')) THEN
			wsec_c1_a <= "0000000001";
			wsec_c2_a <= "0000000001";
		ELSIF(clk'event AND clk='1') THEN
			IF(start_stop_set='1') THEN
				tsc := wsec_c1_a(9);
				FOR s IN 0 TO 8 LOOP
					wsec_c1_a(s+1) <= wsec_c1_a(s);
				END LOOP;
				wsec_c1_a(0) <= tsc;
				IF(wsec_c1_a(9) = '1') THEN
					tssc := wsec_c2_a(9);
					FOR ss IN 0 TO 8 LOOP
						wsec_c2_a(ss+1) <= wsec_c2_a(ss);
					END LOOP;
					wsec_c2_a(0) <= tssc;
				END IF;
			END IF;
		END IF;
	END PROCESS;
------------------------------------------------------------------------
--<Tsec>----------------------------------------------------------------
	PROCESS(clk,rst)
	VARIABLE ts, tss		: STD_LOGIC := '0';		
	BEGIN
		IF(rst='1' OR (mode='1'AND clear='1')) THEN
			wsec1_a <= "0000000001";
			wsec2_a <= "000001";		
		ELSIF(clk'event AND clk='1') THEN
			IF(start_stop_set='1' AND wsec_c2_a(9) = '1' AND wsec_c1_a(9) = '1') THEN
				ts := wsec1_a(9);
				FOR sss IN 0 TO 8 LOOP
					wsec1_a(sss+1) <= wsec1_a(sss);
				END LOOP;
				wsec1_a(0) <= ts;
				IF(wsec1_a(9) = '1' AND wsec_c2_a(9) = '1' AND wsec_c1_a(9) = '1') THEN
					tss := wsec2_a(5);
					FOR ssss IN 0 TO 4 LOOP
						wsec2_a(ssss+1) <= wsec2_a(ssss);
					END LOOP;
					wsec2_a(0) <= tss;
				END IF;
			END IF;
		END IF;
	END PROCESS;
------------------------------------------------------------------------
--<Tmin>----------------------------------------------------------------
	PROCESS(clk,rst)
	VARIABLE tm, tmm		: STD_LOGIC := '0';
	BEGIN
		IF(rst='1' OR (mode='1'AND clear='1')) THEN
			wmin1_a <= "0000000001";
			wmin2_a <= "000001";	
		ELSIF(clk'event AND clk = '1') THEN
			IF(start_stop_set = '1' AND wsec2_a(5) = '1' AND wsec1_a(9) = '1' AND wsec_c2_a(9) = '1' AND wsec_c1_a(9) = '1') THEN
				tm := wmin1_a(9);
				FOR m IN 0 TO 8 LOOP
					wmin1_a(m+1) <= wmin1_a(m);
				END LOOP;
				wmin1_a(0) <= tm;
				IF(wmin1_a(9) = '1' AND wsec2_a(5) = '1' AND wsec1_a(9) = '1' AND wsec_c2_a(9) = '1' AND wsec_c1_a(9) = '1') THEN
					tmm := wmin2_a(5);
					FOR mm IN 0 TO 4 LOOP
						wmin2_a(mm+1) <= wmin2_a(mm);
					END LOOP;
					wmin2_a(0) <= tmm;
				END IF;
			END IF;
		END IF;		
	END PROCESS;
------------------------------------------------------------------------
wsec_c1 <= wsec_c1_a;
wsec_c2 <= Wsec_c2_a;
wsec1 <= wsec1_a;
wsec2 <= wsec2_a;
wmin1 <= wmin1_a;
wmin2 <= wmin2_a;

END a;

