library ieee;
use ieee.std_logic_1164.all;

entity andgate is
port ( in1 : in std_logic;
		 in2 : in std_logic;
		 and2_out : out std_logic);
end andgate;

architecture body_and_2 of andgate is
begin
	process(in1, in2)
	begin
	  and2_out <= in1 and in2;
	end process;
end body_and_2;
