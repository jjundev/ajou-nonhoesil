library IEEE;                                                               
use IEEE.STD_LOGIC_1164.ALL;                                                
use IEEE.STD_LOGIC_ARITH.ALL;                                               
use IEEE.STD_LOGIC_UNSIGNED.ALL;                                            
                                                                            
                                               
                                                                            
entity func_encoder is                                                           
port                                                                        
(                                                                           
	indata: in std_logic_vector(4 downto 0);                                
	outdata: out std_logic_vector(3 downto 0)                               
);                                                                          
end func_encoder;                                                                
                                                                            
architecture Behavioral of func_encoder is                                       
                                                                            
begin                                                                       
	process(indata)                                                         
	begin                                                                   
		case indata is                     
		
		                                 
		when "00000" =>                                                
						outdata<="0000";                                    
		-- '=' 연산
		when "00001" =>                                                
        				outdata<="0001";                                    
        -- '+' 연산
        when "00010" =>                                                
        				outdata<="0010";                                    
		-- '-' 연산        				
        when "00100" =>                                                
        				outdata<="0011";                                    
        -- '*' 연산
        when "01000" =>                                                
        				outdata<="0100";  
        
		when others  =>                                                
						outdata<="0000";	                                
		end case;                                                           
	end process;														    
end Behavioral;                                                             