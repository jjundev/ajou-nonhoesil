--------------------------------------------------------------------------------
-- Copyright (c) 2011 Wedu Solution Co., Ltd.
-- This work may not be copied, modified, re-published, uploaded, executed, or
-- distributed in any way, in any medium, whether in whole or in part, without
-- prior written permission from Wedu Solution Co., Ltd.
--------------------------------------------------------------------------------
-- Title   : stopwatch
--------------------------------------------------------------------------------
-- Project    : Training
-- File       : stopwatch.vhd
-- Author     : lebits 
-- Created    : July 11, 2011
--------------------------------------------------------------------------------
-- Description : Implements the stopwatch
--------------------------------------------------------------------------------
-- $Revision: 0.001 $
--------------------------------------------------------------------------------
-- Rev 0.001 July 11, 2011
--		First Release
---------------------------------------------------------------------------------------

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use ieee.std_logic_unsigned.all;
use ieee.std_logic_arith.all;


-- Uncomment the following library declaration if using
-- arithmetic functions with Signed or Unsigned values
--use IEEE.NUMERIC_STD.ALL;

-- Uncomment the following library declaration if instantiating
-- any Xilinx primitives in this code.
--library UNISIM;
--use UNISIM.VComponents.all;

entity stopwatch is
    Port ( RST : in  STD_LOGIC;
           CLK : in  STD_LOGIC;		-- 50 Mhz reference clock
           START : in  STD_LOGIC;
           STOP : in  STD_LOGIC;
			  LED : out  STD_LOGIC;
           DIGIT : out  STD_LOGIC_VECTOR (7 downto 0);
           AN : out  STD_LOGIC_VECTOR (3 downto 0));
end stopwatch;

architecture Behavioral of stopwatch is
------------------------------------------------------
--			COMPONENTS
------------------------------------------------------  

------------------------------------------------------
--			SIGNALS & CONSTANT
------------------------------------------------------  

	type DIGIT_ARRAY is array (0 to 9) of std_logic_vector ( 7 downto 0);
	constant DIGIT_VAL : DIGIT_ARRAY := (
						0 => X"03",
						1 => X"9F",
						2 => X"25",
						3 => X"0D",
						4 => X"99",
						5 => X"49",
						6 => X"41",
						7 => X"1F",
						8 => X"01",
						9 => X"09");
	
	constant Khz1_VAL : std_logic_vector(15 downto 0) := CONV_STD_LOGIC_VECTOR(49999,16);
							-- 50Mhz clock
	signal en : std_logic;
	signal clk_cnt : std_logic_vector(15 downto 0);
	signal khz_tick : std_logic;
	signal msec_cnt : std_logic_vector(9 downto 0);
	signal sec_tick : std_logic;
	signal sec_cnt : std_logic_vector(3 downto 0);
	signal sec10_tick : std_logic;
	signal sec10_cnt : std_logic_vector(2 downto 0);

	signal min_tick : std_logic;
	signal min_cnt : std_logic_vector(3 downto 0);
	signal min10_tick : std_logic;
	signal min10_cnt : std_logic_vector(2 downto 0);

	signal an_sel : std_logic_vector(1 downto 0);

	signal digi_sec : std_logic_vector(7 downto 0);
	signal digi10_sec : std_logic_vector(7 downto 0);
	signal digi_min : std_logic_vector(7 downto 0);
	signal digi10_min : std_logic_vector(7 downto 0);
	
	signal led_int : std_logic;

------------------------------------------------------
--			IMPLEMENTATION
------------------------------------------------------ 

begin

	process (CLK) begin
		if rising_edge(CLK) then
			if (RST = '1') then
				en <= '0';
			else
				if (START = '1') then
					en <= '1';
				else
					if (STOP = '1') then
						en <= '0';
					end if;
				end if;
			end if;
		end if;
	end process;
					

	process (CLK) begin
		if rising_edge(CLK) then
			if (RST = '1') then
				clk_cnt <= (others => '0');
				khz_tick <= '0';
			else
				clk_cnt <= clk_cnt + 1;
				khz_tick <= '0';
				if(clk_cnt = Khz1_VAL) then
					clk_cnt <= (others => '0');
					khz_tick <= '1';
				end if;
			end if;
		end if;
	end process;

	process (CLK) begin
		if rising_edge(CLK) then
			if (RST = '1') then
				msec_cnt <= (others => '0');
				sec_tick <= '0';
			else
				if (en = '1') then
					sec_tick <= '0';
					if (khz_tick = '1') then
						msec_cnt <= msec_cnt + 1;
						sec_tick <= '0';
						if(msec_cnt = 999) then
							msec_cnt <= (others => '0');
							sec_tick <= '1';
						end if;
					end if;
				end if;
			end if;
		end if;
	end process;

	process (CLK) begin
		if rising_edge(CLK) then
			if(RST = '1') then
				sec_cnt <= (others => '0');
				sec10_tick <= '0';
			else
				sec10_tick <= '0';
				if(sec_tick = '1') then
					sec_cnt <= sec_cnt + 1;
					sec10_tick <= '0';
					if(sec_cnt = 9) then
						sec_cnt <= (others => '0');
						sec10_tick <= '1';
					end if;
				end if;
			end if;
		end if;
	end process;

	process (CLK) begin
		if rising_edge(CLK) then
			if(RST = '1') then
				sec10_cnt <= (others => '0');
				min_tick <= '0';
			else
				min_tick <= '0';
				if(sec10_tick = '1') then
					sec10_cnt <= sec10_cnt + 1;
					min_tick <= '0';
					if(sec10_cnt = 5) then
						sec10_cnt <= (others => '0');
						min_tick <= '1';
					end if;
				end if;
			end if;
		end if;
	end process;
	
	process (CLK) begin
		if rising_edge(CLK) then
			if(RST = '1') then
				min_cnt <= (others => '0');
				min10_tick <= '0';
			else
				min10_tick <= '0';
				if(min_tick = '1') then
					min_cnt <= min_cnt + 1;
					min10_tick <= '0';
					if(min_cnt = 9) then
						min_cnt <= (others => '0');
						min10_tick <= '1';
					end if;
				end if;
			end if;
		end if;
	end process;

	process (CLK) begin
		if rising_edge(CLK) then
			if(RST = '1') then
				min10_cnt <= (others => '0');
			else
				if(min10_tick = '1') then
					min10_cnt <= min10_cnt + 1;
					if(min10_cnt = 5) then
						min10_cnt <= (others => '0');
					end if;
				end if;
			end if;
		end if;
	end process;



	process (CLK) begin
		if rising_edge(CLK) then
			if(RST = '1') then
				an_sel <= (others => '0');
			else
				if (khz_tick = '1')  then
					an_sel <= an_sel + 1;
				end if;
			end if;
		end if;
	end process;

	digi_sec <= DIGIT_VAL(conv_integer(sec_cnt));
	digi10_sec <= DIGIT_VAL(conv_integer(sec10_cnt));
	digi_min <= DIGIT_VAL(conv_integer(min_cnt));
	digi10_min <= DIGIT_VAL(conv_integer(min10_cnt));
	
	process (an_sel) begin
		case (an_sel) is
			when "00" => AN <= "1110";
							DIGIT <= digi_sec;
			when "01" => AN <= "1101";
							DIGIT <= digi10_sec;
			when "10" => AN <= "1011";
							DIGIT <= digi_min;
			when "11" => AN <= "0111";
							DIGIT <= digi10_min;
			when others =>  AN <= "1110";
							DIGIT <= digi_sec;
		end case;
	end process;
	
	process (CLK) begin
		if rising_edge (CLK) then
			if (sec_tick = '1') then
				led_int <= not (led_int);
			end if;
		end if;
	end process;

	LED <= led_int;

end Behavioral;

