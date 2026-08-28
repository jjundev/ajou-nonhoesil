library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;


entity multiplxer is
port
(
	sel			: in std_logic;
	indata1     : in std_logic_vector(3 downto 0);
	indata2     : in std_logic_vector(3 downto 0);
	outdata     : out std_logic_vector(3 downto 0)
);
end multiplxer;

architecture Behavioral of multiplxer is

begin
	process(sel,indata1,indata2)
	begin
		case sel is
		when '0' =>
				outdata<=indata1;
		when '1' =>
				outdata<=indata2;
		when others =>
				outdata<=(others=>'-');
		end case;
		
	end process;


end Behavioral;
