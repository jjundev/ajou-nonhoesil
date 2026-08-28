library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;


entity segment_driver is
port
(
	indata : in std_logic_vector(3 downto 0);
	outdata: out std_logic_vector(6 downto 0)
);
end segment_driver;

--           (a)
--			----
--	    (b)|	|(c)
--	       |    |
--			----
--         |(d) |
--      (e)|    | (f)
--          ----
--           (g)



architecture Behavioral of segment_driver is
begin
	process(indata)
	begin
		case indata is	 		  --"abcdefg"
			when "0000"=>  outdata<="1110111"	   ;	--value 0
			when "0001"=>  outdata<="0010010"      ;	--value 1
			when "0010"=>  outdata<="1011101"      ;    --value 2
			when "0011"=>  outdata<="1011011"      ;    --value 3
			when "0100"=>  outdata<="0111010"      ;    --value 4
			when "0101"=>  outdata<="1101011"      ;    --value 5
			when "0110"=>  outdata<="1101111"      ;    --value 6 
			when "0111"=>  outdata<="1110010"      ;    --value 7
			when "1000"=>  outdata<="1111111"      ;    --value 8
			when "1001"=>  outdata<="1111010"      ;    --value 9
			when others=>  outdata<="0000000"      ;    --exception value
		end case;
	end process;
end Behavioral;
