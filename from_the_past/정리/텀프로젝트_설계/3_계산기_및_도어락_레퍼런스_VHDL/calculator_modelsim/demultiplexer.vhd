library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity demultiplexer is

port
(

	addr	: in std_logic_vector(2 downto 0);
	indata	: in std_logic_vector(3 downto 0);
	we		: in std_logic;
	outdata0: out std_logic_vector(3 downto 0);
	outdata1: out std_logic_vector(3 downto 0);
	outdata2: out std_logic_vector(3 downto 0);
	outdata3: out std_logic_vector(3 downto 0);
	outdata4: out std_logic_vector(3 downto 0);
	outdata5: out std_logic_vector(3 downto 0);	
	we0		: out std_logic;
	we1		: out std_logic;
	we2		: out std_logic;
	we3		: out std_logic;
	we4		: out std_logic;
	we5		: out std_logic

);
end demultiplexer;

architecture Behavioral of demultiplexer is

begin
	process(addr,indata,we)
	begin
		case addr is
		when "000" =>
						outdata0<=indata;
						outdata1<="----";
						outdata2<="----";
						outdata3<="----";
						outdata4<="----";
						outdata5<="----";						
						we0		<=we;
						we1		<='0';
						we2		<='0';
						we3		<='0';
						we4		<='0';
						we5		<='0';										
		when "001" =>
						outdata0<="----";
		                outdata1<=indata;
		                outdata2<="----";
		                outdata3<="----";
		                outdata4<="----";
		                outdata5<="----";
		                we0		<='0';   
		                we1		<=we;   
		                we2		<='0';   
		                we3		<='0';   
		                we4		<='0';   		
						we5		<='0';   		
		when "010" =>	
						outdata0<="----";
		                outdata1<="----";
		                outdata2<=indata;
		                outdata3<="----";
		                outdata4<="----";
		                outdata5<="----";
		                we0		<='0';   
		                we1		<='0';
		                we2		<=we;   
		                we3		<='0';   
			            we4		<='0';   
			            we5		<='0';   
		when "011" =>
						outdata0<="----"; 
						outdata1<="----"; 
						outdata2<="----"; 
						outdata3<=indata;
						outdata4<="----"; 
						outdata5<="----"; 
						we0		<='0';    
						we1		<='0';    
						we2		<='0';    
						we3		<=we;    
						we4		<='0';    												
						we5		<='0'; 
						   												
		when "100" =>
						outdata0<="----"; 
		                outdata1<="----"; 
		                outdata2<="----";
		                outdata3<="----"; 
		                outdata4<=indata; 
						outdata5<="----"; 		                
		                we0		<='0';    
		                we1		<='0';    
		                we2		<='0';    
		                we3		<='0';    
		                we4		<=we;    	
						we5		<='0';  
		
		when "101" =>                       
						outdata0<="----";   
		                outdata1<="----";   
		                outdata2<="----";   
		                outdata3<="----";   
		                outdata4<="----";   
						outdata5<=indata; 	
		                we0		<='0';      
		                we1		<='0';      
		                we2		<='0';      
		                we3		<='0';      
		                we4		<='0';    	
						we5		<=we;      
						
						
						
						    
		when others =>  
						outdata0<="----";
		                outdata1<="----";
		                outdata2<="----";
		                outdata3<="----";
		                outdata4<="----";
		                outdata5<="----";
		                we0		<='0';   
		                we1		<='0';   
		                we2		<='0';   
		                we3		<='0';   
		                we4		<='0';  
						we5		<='0';  		                
		end case; 
    end process;			

end Behavioral;
