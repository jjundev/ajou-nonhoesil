library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;	

entity STOP_WATCH_S is
 port(CLK,CLR,START_STOP: in std_logic;
	   mSEC_1_D,mSEC_10_D,SEC_1_D,SEC_10_D,MIN_1_D,MIN_10_D : out std_logic_vector(7 downto 0));
end STOP_WATCH_S;

architecture A_STOP_WATCH_S of STOP_WATCH_S is
 function DIS_SEG(COUNT: integer range 0 to 15) return std_logic_vector is
	variable SEG_DECODE: std_logic_vector(7 downto 0);
		begin
			case COUNT is
				
				when 0 => SEG_DECODE := "00111111";
				when 1 => SEG_DECODE := "00000110";
				when 2 => SEG_DECODE := "01011011";
				when 3 => SEG_DECODE := "01001111";
				when 4 => SEG_DECODE := "01100110";
				when 5 => SEG_DECODE := "01101101";
				when 6 => SEG_DECODE := "01111101";
				when 7 => SEG_DECODE := "00100111";
				when 8 => SEG_DECODE := "01111111";
				when 9 => SEG_DECODE := "01100111";
				when others => SEG_DECODE := "00000000";
			end case;
		return (SEG_DECODE);
	end DIS_SEG;
	
		signal mSEC_1_C, mSEC_10_C, SEC_1_C, SEC_10_C, MIN_1_C, MIN_10_C : integer range 0 to 9;
		signal ST_P : std_logic;

	begin
		B_ST_P: process(START_STOP, CLR)
			begin
				if CLR='1' then ST_P <='0';
				elsif (START_STOP'event and START_STOP='1') then ST_P <= not(ST_P);
				end if;
			end process;
			
		B_mSEC_1 : process(CLK)
			begin
				if CLR='1' then mSEC_1_C <=0;
				elsif (CLK'event and CLK='1') then
					if ST_P = '1' then 
						if mSEC_1_C = 9 then mSEC_1_C <= 0;
						else  mSEC_1_C <= mSEC_1_C + 1;
						end if;
					end if;
				end if;
			end process;
			
		B_mSEC_10 : process(CLK)
			begin
				if CLR='1' then mSEC_10_C <=0;
				elsif (CLK'event and CLK='1') then
					if ST_P = '1' then 
						if mSEC_10_C = 9 then mSEC_10_C <= 0;
						else  mSEC_10_C <= mSEC_10_C + 1;
						end if;
					end if;
				end if;
			end process;
			
		B_SEC_1 : process(CLK)
			begin
				if CLR='1' then SEC_1_C <=0;
				elsif (CLK'event and CLK='1') then
					if ST_P = '1' then 
						if mSEC_1_C =9 and mSEC_10_C = 9 then
							if SEC_1_C = 9 then SEC_1_C <=0;
							else  SEC_1_C <= SEC_1_C + 1;
							end if;
						end if;
					end if;
				end if;
			end process;
		
		B_SEC_10 : process(CLK)
			begin
				if CLR='1' then SEC_10_C <=0;
				elsif (CLK'event and CLK='1') then
					if ST_P = '1' then 
						if mSEC_1_C =9 and mSEC_10_C = 9 and SEC_1_C=9 then
							if SEC_10_C = 5 then SEC_10_C <=0;
							else  SEC_10_C <= SEC_10_C + 1;
							end if;
						end if;
					end if;
				end if;
			end process;
			
		B_MIN_1 : process(CLK)
			begin
				if CLR='1' then MIN_1_C <=0;
				elsif (CLK'event and CLK='1') then
					if ST_P = '1' then 
						if mSEC_1_C =9 and mSEC_10_C = 9 and SEC_1_C=9 and SEC_10_C =5 then
							if MIN_1_C = 9 then MIN_1_C <=0;
							else  MIN_1_C <= MIN_1_C + 1;
							end if;
						end if;
					end if;
				end if;
			end process;
			
		B_MIN_10 : process(CLK)
			begin
				if CLR='1' then MIN_10_C <=0;
				elsif (CLK'event and CLK='1') then
					if ST_P = '1' then 
						if mSEC_1_C =9 and mSEC_10_C = 9 and SEC_1_C=9 and SEC_10_C =5 and MIN_1_C=9 then
							if MIN_10_C = 5 then MIN_10_C <=0;
							else  MIN_10_C <= MIN_10_C + 1;
							end if;
						end if;
					end if;
				end if;
			end process;
			
		mSEC_1_D <= DIS_SEG(mSEC_1_C);
		mSEC_10_D <= DIS_SEG(mSEC_10_C);
		SEC_1_D <= DIS_SEG(SEC_1_C);
		SEC_10_D <= DIS_SEG(SEC_10_C);
		MIN_1_D <= DIS_SEG(MIN_1_C);
		MIN_10_D <= DIS_SEG(MIN_10_C);
		
end A_STOP_WATCH_S;