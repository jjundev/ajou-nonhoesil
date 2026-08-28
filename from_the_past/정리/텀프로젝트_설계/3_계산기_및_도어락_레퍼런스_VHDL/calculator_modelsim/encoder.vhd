library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;



entity encoder is
port
(
	indata: in std_logic_vector(9 downto 0);
	outdata: out std_logic_vector(3 downto 0)
);
end encoder;

architecture Behavioral of encoder is

begin
	process(indata)
	begin
		case indata is
		-- no input
		when "0000000000" =>
						outdata<="0000";
		-- num 1 
		when "0000000001" =>            
        				outdata<="0001";
        -- num 2 
        when "0000000010" =>            
        				outdata<="0010";
        -- num 3
        when "0000000100" =>            
        				outdata<="0011";
        -- num 4
        when "0000001000" =>            
        				outdata<="0100";
        -- num 5
        when "0000010000" =>            
						outdata<="0101";				
		-- num 6
		when "0000100000" =>            
						outdata<="0110";				
		-- num 7
		when "0001000000" =>            
						outdata<="0111";				
		-- num 8
		when "0010000000" =>            
						outdata<="1000";
		-- num 9
		when "0100000000" =>            				
						outdata<="1001";
		-- num 0
		when "1000000000" =>            				
						outdata<="0000";                										
		when others 	  =>
						outdata<="0000";	
		end case;
	end process;														
end Behavioral;
