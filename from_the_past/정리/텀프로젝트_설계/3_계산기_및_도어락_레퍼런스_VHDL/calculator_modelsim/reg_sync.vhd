
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;


entity reg_sync is
generic (bit_widths:integer:=32);
port
(
	clk		: in std_logic;
	reset   : in std_logic;
	clear   : in std_logic;
	we      : in std_logic;
	indata  : in std_logic_vector(bit_widths-1 downto 0);
	outdata : out std_logic_vector(bit_widths-1 downto 0)
);
end reg_sync;

architecture Behavioral of reg_sync is
signal data: std_logic_vector(bit_widths-1 downto 0);
begin
	process(clk,reset,clear,we,indata)
	begin
		if reset='0' then
			data<=(others=>'0');
		elsif rising_edge(clk) then
			if clear='1' then
				data<=(others=>'0');
			elsif we='1' then
				data<=indata;
			else
				data<=data;
			end if;
		end if;
	end process;
	outdata<=data;
end Behavioral;
