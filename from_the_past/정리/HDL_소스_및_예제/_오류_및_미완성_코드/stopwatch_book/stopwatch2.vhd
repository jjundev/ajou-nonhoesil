library ieee; use ieee.std_logic_1164.all; use ieee.std_logic_unsigned.all;

entity stopwatch2 is
port ( CLK, RESET, START_STOP : in std_logic;
		 COM0, COM1, COM2, COM3, COM4, COM5 : out std_logic;
		 a, b, c, d, e, f, g, dp : out std_logic );
end stopwatch2;
------------------------------------------------
--------------------top level entity
architecture A_stopwatch of stopwatch2 is
component F_100_Hz
	port ( CLK, CLR : in std_logic;
			 Hz_100 	 : out std_logic );
end component;

component SEL_ST_SP
	port ( START_STOP, CLK, CLR : in std_logic;
			 S_T_P 					 : out std_logic );
end component;

component TIME_Ctrl
	port ( CLK, CLR, S_T_P 				 : in std_logic;
			 MIN_L, MIN_H, SEC_L, SEC_H : out std_logic_vector(3 downto 0);
			 mSEC_L, mSEC_H 				 : out std_logic_vector(3 downto 0));
end component;

component SEG_Ctrl
	port ( CLK, CLR : in std_logic;
			 MIN_L, MIN_H, SEC_L, SEC_H : in std_logic_vector(3 downto 0);
			 mSEC_L, mSEC_H 				 : in std_logic_vector(3 downto 0);
			 COM			   				 : out std_logic_vector(5 downto 0);
			 SEG_CHAR 						 : out std_logic_vector(7 downto 0));
end component;

	signal CLR, Hz_100, S_T_P			 : std_logic;
	signal MIN_L, MIN_H, SEC_L, SEC_H : std_logic_vector(3 downto 0);
	signal mSEC_L, mSeC_H 				 : std_logic_vector(3 downto 0);
	signal COM 								 : std_logic_vector(5 downto 0);
	signal SEG_CHAR						 : std_logic_vector(7 downto 0);
	
	begin
		CLR <= not(RESET);
	freq_100		: F_100_Hz port map(CLK,CLR,Hz_100);
	start_stp	: SEL_ST_SP port map(START_STOP, CLK, CLR, S_T_P);
	time_contl  : TIME_Ctrl port map(Hz_100,CLR,S_T_P,Min_L,Min_H,SEC_L,SEC_H,mSEC_L,mSEC_H);
	segment_contl: SEG_Ctrl port map(CLK,CLR,Min_L,Min_H,SEC_L,SEC_H,mSEC_L,mSEC_H,COM,SEG_CHAR);
	
		COM0<=COM(5);COM1<=COM(4);COM2<=COM(3);COM3<=COM(2);COM4<=COM(1);COM5<=COM(0);
		a<=SEG_CHAR(6);b<=SEG_CHAR(5);c<=SEG_CHAR(4);d<=SEG_CHAR(3);e<=SEG_CHAR(2);f<=SEG_CHAR(1);g<=SEG_CHAR(0);dp<=SEG_CHAR(7);
	end A_stopwatch;
-----------------------------------------------------------
---------frequency(need to modify)
library ieee; use ieee.std_logic_1164.all; use ieee.std_logic_unsigned.all;

entity F_100_Hz is 
port (CLK, CLR : in std_logic;
		Hz_100 : out std_logic);
end F_100_Hz;

architecture A_F_100Hz of F_100_Hz is
	signal COUNT : std_logic_vector(5 downto 0);
	signal HZ_100s : std_logic;
 begin
	process(CLR,CLK)
		begin
			if( CLR = '0') then COUNT <="000000";
			elsif (CLK'event and CLK = '1') then 
				if(COUNT=49) then COUNT <="000000";		--why 49? is it 59?
				else COUNT <= COUNT+ '1';
				end if;
			end if;
	end process;
	
	process(CLR,CLK)
		begin
			if( CLR = '0') then Hz_100s <='0';
			elsif (CLK'event and CLK = '1') then 
				if(COUNT=49) then Hz_100s <= not Hz_100s;
				end if;
			end if;
	end process;
	
	Hz_100 <= Hz_100s;
end A_F_100Hz;
-----------------------------------------------------------
-------button about select stop or start
library ieee; use ieee.std_logic_1164.all; use ieee.std_logic_unsigned.all;


entity SEL_ST_SP is
port(START_STOP, CLK,CLR : in std_logic;
     S_T_P : out std_logic);
end SEL_ST_SP;

architecture A_SEL_ST_SP of SEL_ST_SP is
	signal Q : std_logic_vector(1 downto 0);
	signal Rising_Signal : std_logic;
	signal SS_T_P : std_logic;
begin
	process(CLR,CLK)
		begin
			if(CLR='0') then Q <="00";
			elsif(CLK'event and CLK = '1') then
				if(Rising_Signal='1') then SS_T_P <= not(SS_T_P);
				end if;
			end if;
	end process;
	
	S_T_P <= SS_T_P;
end A_SEL_ST_SP;
-------------------------------------------------------------
--------time controller 
library ieee; use ieee.std_logic_1164.all; use ieee.std_logic_unsigned.all;


entity TIME_Ctrl is 
port(CLK,CLR,S_T_P : in std_logic;
     MIN_L,MIN_H,SEC_L,SEC_H : out std_logic_vector(3 downto 0);
	  mSEC_H, mSEC_L : out std_logic_vector(3 downto 0));
	end TIME_Ctrl;

architecture A_TIME_Ctrl of TIME_Ctrl is
	signal MIN_S_L,MIN_S_H,SEC_S_L : std_logic_vector(3 downto 0);
	signal SEC_S_H,mSEC_S_L,mSEC_S_H : std_logic_vector(3 downto 0);
begin
mSEC_L_Signal : process(CLR,CLK)
	begin
		if(CLR='0') then mSEC_S_L <="0000";
		elsif(CLK'event and CLK='1') then
			if(S_T_P='1' and mSEC_S_L=9) then mSEC_S_L <= "0000";
			elsif(S_T_P='1') then mSEC_S_L <= mSEC_S_L+'1';
			end if;
		end if;
	end process;
	
mSEC_H_Signal : process(CLR,CLK)
	begin
		if(CLR='0') then mSEC_S_H <="0000";
		elsif(CLK'event and CLK='1') then
			if(S_T_P='1' and mSEC_S_H=9 and mSEC_S_L=9 ) then mSEC_S_H <= "0000";
			elsif(S_T_P='1' and mSEC_S_L=9) then mSEC_S_H <= mSEC_S_H+'1';
			end if;
		end if;
	end process;

SEC_L_Signal : process(CLR,CLK)
	begin
		if(CLR='0') then SEC_S_L <="0000";
		elsif(CLK'event and CLK='1') then
			if(S_T_P='1' and mSEC_S_H=9 and mSEC_S_L=9 and SEC_S_L=9 ) then SEC_S_L <= "0000";
			elsif(S_T_P='1' and mSEC_S_H=9 and mSEC_S_L=9) then SEC_S_L <= SEC_S_L+'1';
			end if;
		end if;
	end process;	

SEC_H_Signal : process(CLR,CLK)
	begin
		if(CLR='0') then SEC_S_H <="0000";
		elsif(CLK'event and CLK='1') then
			if(S_T_P='1' and SEC_S_H=5 and SEC_S_L=9 and mSEC_S_H=9 and mSEC_S_L=9 ) then SEC_S_H <= "0000";
			elsif(S_T_P='1' and SEC_S_L=9 and mSEC_S_H=9 and mSEC_S_L=9) then SEC_S_H <= SEC_S_H+'1';
			end if;
		end if;
	end process;	

Min_L_Signal : process(CLR,CLK)
	begin
		if(CLR='0') then Min_S_L <="0000";
		elsif(CLK'event and CLK='1') then
			if(S_T_P='1' and MIN_S_L=9 and SEC_S_H=5 and SEC_S_L=9 and mSEC_S_H=9 and mSEC_S_L=9 ) then MIN_S_L <= "0000";
			elsif(S_T_P='1' and SEC_S_H=5 and SEC_S_L=9 and mSEC_S_H=9 and mSEC_S_L=9) then MIN_S_L <= MIN_S_L+'1';
			end if;
		end if;
	end process;		
			
Min_H_Signal : process(CLR,CLK)
	begin
		if(CLR='0') then Min_S_H <="0000";
		elsif(CLK'event and CLK='1') then
			if(S_T_P='1' and MIN_S_H=5 and MIN_S_L=9 and SEC_S_H=5 and SEC_S_L=9 and mSEC_S_H=9 and mSEC_S_L=9 ) then MIN_S_H <= "0000";
			elsif(S_T_P='1' and MIN_S_L=9 and SEC_S_H=5 and SEC_S_L=9 and mSEC_S_H=9 and mSEC_S_L=9) then MIN_S_H <= MIN_S_H+'1';
			end if;
		end if;
	end process;

	mSEC_L <= mSEC_S_L; mSEC_H <= mSEC_S_H;
	SEC_L <= SEC_S_L; SEC_H <= SEC_S_H;
	MIN_L <= MIN_S_L; MIN_H <= MIN_S_H;
	
end A_TIME_Ctrl;
---------------------------------------------------------------
----------segment controller

library ieee; use ieee.std_logic_1164.all; use ieee.std_logic_unsigned.all;

entity SEG_Ctrl is 
port(CLK,CLR : in std_logic;
     mSEC_H, mSEC_L, SEC_L, SEC_H : in std_logic_vector(3 downto 0);	--modified
	  MIN_L,MIN_H : in std_logic_vector(3 downto 0);							--modified
	  COM : out std_logic_vector(5 downto 0);
	  SEG_CHAR : out std_logic_vector(7 downto 0));
end SEG_Ctrl;

--modified
architecture A_SEG_Ctrl of SEG_Ctrl is
	signal MUX_OUT : std_logic_vector(3 downto 0);
	signal COUNT : std_logic_vector(2 downto 0);

	begin 
		--module 6 counter
		process(CLK,CLR)
			begin
				if(CLR='0') then COUNT <= "111";
				elsif(CLK'event and CLK ='1') then 
					if(COUNT=5) then COUNT <="000";
					else COUNT <= COUNT +'1';
					end if;
				end if;
		end process;
		
		-- com signal gen: 3*8 decoder
		process(COUNT)
			begin
				case COUNT is
					when "000" => COM <="011111";
					when "001" => COM <="101111";
					when "010" => COM <="110111";
					when "011" => COM <="111011";
					when "100" => COM <="111101";
					when "101" => COM <="111110";
					when others => COM <="111111";
				end case;
		end process;
		
		--- 6_1 MUX(4bits)
		process(COUNT)
			begin
				case COUNT is
					when "000" => MUX_OUT <= MIN_H;
					when "001" => MUX_OUT <= MIN_L;
					when "010" => MUX_OUT <= SEC_H;
					when "011" => MUX_OUT <= SEC_L;
					when "100" => MUX_OUT <= mSEC_H;
					when others => MUX_OUT <= mSEC_L;
				end case;
		end process;
		
		---BCD to 7 Segment gen
		process(MUX_OUT)
			begin
				case MUX_OUT is
					when "0000" => SEG_CHAR <= "01111110";
					when "0001" => SEG_CHAR <= "00110000";
					when "0010" => SEG_CHAR <= "01101101";
					when "0011" => SEG_CHAR <= "01111001";
					when "0100" => SEG_CHAR <= "00110011";
					when "0101" => SEG_CHAR <= "01011011";
					when "0110" => SEG_CHAR <= "01011111";
					when "0111" => SEG_CHAR <= "01110000";
					when "1000" => SEG_CHAR <= "01111111";
					when "1001" => SEG_CHAR <= "01110011";
					when others => SEG_CHAR <= "00000000";
				end case;
		end process;
end A_SEG_Ctrl;
----------------------------
---------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;	

entity STOP_WATCH_S is
 port(CLK,CLR,START_STOP: in std_logic;
	   mSEC_1_D,mSEC_10_D,SEC_1_D,SEC_10_D,MIN_1_D,MIN_10_D : out std_logic_vector(7 downto 0));
end STOP_WATCH_S;

architecture A_STOP_WATCH_S of STOP_WATCH_S is
 function DIS_SEG(COUNT: integer range 0 to 15) return std_logic_vector is
	variable SEG_DECODE: std_logic_vector(6 downto 0);
		begin
			case COUNT is
				
				when 0 => SEG_DECODE := "0111111";
				when 1 => SEG_DECODE := "0000110";
				when 2 => SEG_DECODE := "1011011";
				when 3 => SEG_DECODE := "1001111";
				when 4 => SEG_DECODE := "1100110";
				when 5 => SEG_DECODE := "1101101";
				when 6 => SEG_DECODE := "1111101";
				when 7 => SEG_DECODE := "0100111";
				when 8 => SEG_DECODE := "1111111";
				when 9 => SEG_DECODE := "1100111";
				when others => SEG_DECODE := "0000000";
			end case;
		return (0 & SEG_DECODE);
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


