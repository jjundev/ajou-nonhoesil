library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity ALU is
port
(
	
	indata1	: in std_logic_vector(3 downto 0);
	indata2 : in std_logic_vector(3 downto 0);
	indata3 : in std_logic_vector(3 downto 0);
	indata4 : in std_logic_vector(3 downto 0); 
	func    : in std_logic_vector(3 downto 0);
	equal	: in std_logic_vector(3 downto 0);
	segment_driver0:out std_logic_vector(3 downto 0); 
	segment_driver1:out std_logic_vector(3 downto 0);
	segment_driver2:out std_logic_vector(3 downto 0)
);
end ALU;

architecture Behavioral of ALU is

signal fir 		:std_logic_vector(6 downto 0);
signal sec 		:std_logic_vector(6 downto 0);
signal result 	:std_logic_vector(9 downto 0);
signal segment_data0: std_logic_vector(3 downto 0); 
signal segment_data1: std_logic_vector(3 downto 0); 
signal segment_data2: std_logic_vector(3 downto 0); 

begin
fir<=conv_std_logic_vector(conv_integer(indata1)*10 + conv_integer(indata2),7);     
sec<=conv_std_logic_vector(conv_integer(indata3)*10 + conv_integer(indata4),7);    


MAKE_DISPLAY_VALUE:
process(result)
variable high	: integer range 0 to 999 ;
variable medium : integer range 0 to 99  ;
variable low    : integer range 0 to 9   ;                                    
begin		                                              
	                                                      
	high:=conv_integer(result);	                               	      
	FIRST_POSITION:                                       
	for i in 0 to 9 loop                                  
		if high > 100 then 
			high:= high - 100; 
		else                                              
			segment_data0<=conv_std_logic_vector(i,4); 	
			exit FIRST_POSITION;                          
		end if;                                           
	end loop;			                                  
                                                          
                                                          
                                                          
	medium:=high ; 
	SECOND_POSITION:	                                  
	                                                      
	for j in 0 to 9 loop                                  
		if medium > 10 then 
			medium:=medium - 10; 
		else                                              
			segment_data1<=conv_std_logic_vector(j,4);  
			low:=medium;                                
			segment_data2<=conv_std_logic_vector(conv_integer(low),4);
			exit SECOND_POSITION;                         
		end if;                                           
	end loop;  
	                                          
	   
	   
	 
	                                              
end process MAKE_DISPLAY_VALUE;

process(equal)
begin
	if equal="0001" then								  						                                                            
		case func is 			 			                                                
			                                                                                			                    							     											                                                            
			-- '+' 연산                                                                     
			when "0010"=> 					 					                            
				result<=conv_std_logic_vector(conv_integer(fir) + conv_integer(sec),10);    
				                                                                            
				                                                                            
			-- '-' 연산        				                                                
			when "0011"=>     					 			                                
				result<=conv_std_logic_vector(conv_integer(fir) - conv_integer(sec),10);    
				                                                                            
				                                                                            
		    -- '*' 연산                                                                     
		    when "0100"=>                                                                   
		   		result<=conv_std_logic_vector(conv_integer(fir) * conv_integer(sec),10);    
		   			                                                                        
		    when others  =>                                                                 
		    	result<="0000000000";	        			        		            
		end case;	                                                                        	
	end if;
end process;

segment_driver0<=segment_data0;
segment_driver1<=segment_data1;
segment_driver2<=segment_data2;
     	                                
end ;
            
            
            
            
            