library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;

entity Controller is
port
(
	clk			: in std_logic;
	reset   	: in std_logic;
	num			: in std_logic_vector(9 downto 0);
	func    	: in std_logic_vector(4 downto 0);
	        	
	mem_we		 : out std_logic;
	mem_addr	 : out std_logic_vector(2 downto 0);
	encoded_code : out std_logic_vector(3 downto 0);
	mem_clear	 : out std_logic
	
	
);
end Controller;

architecture Behavioral of Controller is

component encoder                              
port                                           
(                                              
	indata: in std_logic_vector(9 downto 0);   
	outdata: out std_logic_vector(3 downto 0)  
);                                             
end component; 
component func_encoder 
port                                           
(                                              
	indata: in std_logic_vector(4 downto 0);   
	outdata: out std_logic_vector(3 downto 0)  
);                                             
end component;                              

component multiplxer 
port                                                
(                                                   
	sel			: in std_logic;                     
	indata1     : in std_logic_vector(3 downto 0);  
	indata2     : in std_logic_vector(3 downto 0);  
	outdata     : out std_logic_vector(3 downto 0)  
);                                                  
end component;                                     

                              
type state is ( init, input_1 , input_2,wait_func,input_3,input_4,wait_equal,result);

signal present_state , next_state	: state;
signal encoded_num	: std_logic_vector(3 downto 0);
signal encoded_func : std_logic_vector(3 downto 0);
signal select_signal: std_logic;
begin   


STATE_MACHINE:
process(present_state,num,func)
begin

	case present_state is	
		
		when input_1 =>
			--숫자 입력이 들어오면 그 값을 메모리에 저장하고 스태이트를 바꾼다. 
			if num >"0000000000"  then				
				select_signal 	<='0';
				mem_we 			<='1';       
				mem_addr		<="000";
				mem_clear		<='0';
				next_state		<=input_2;
				
			else			
				select_signal 	<='-';
				mem_we 			<='0';
				mem_addr		<="---";
				mem_clear		<='0';
				next_state		<=input_1;
				
			end if;	
			
		when input_2 =>
			--숫자 입력이 들어오면 그 값을 메모리에 저장하고 스태이트를 바꾼다. 
			if num >"0000000000"  then				
				select_signal 	<='0';  
		    	mem_we 			<='1';         
		    	mem_addr		<="001"; 
		    	mem_clear		<='0';
		    	next_state		<=wait_func;
		    	
			else                      
				select_signal 	<='-';  
				mem_we 			<='0';         
				mem_addr		<="---";
				mem_clear		<='0';
				next_state		<=input_2;
				
    	    end if;	 
    	                     
		when wait_func =>
			--연산자 입력이 들어오면 그 값을 메모리에 저장하고 스태이트를 바꾼다. 
			if func >"00001"  then		    
		    	select_signal 	<='1';
		    	mem_we 			<='1';       
		    	mem_addr		<="010";
		    	mem_clear		<='0';
		    	next_state		<=input_3;  
		    	
		    else                      
		    	select_signal 	<='-';  
		    	mem_we 			<='0';         
		    	mem_addr		<="---";
		    	mem_clear		<='0';
		    	next_state		<=wait_func;      
		    	
		    end if;	 
		                     
		when input_3 =>
			--숫자 입력이 들어오면 그 값을 메모리에 저장하고 스태이트를 바꾼다.            
			if num >"0000000000"  then
				select_signal 	<='0';
		    	mem_we 			<='1';       
		    	mem_addr		<="011"; 
		    	mem_clear		<='0'; 				
		    	next_state		<=input_4;
		    	
		    else                    
		    	select_signal 	<='-';
		    	mem_we 			<='0';       
		    	mem_addr		<="---";
		    	mem_clear		<='0';
		    	next_state		<=input_3;    
		    	
		    end if;	 
		                   
		when input_4 => 
			--숫자 입력이 들어오면 그 값을 메모리에 저장하고 스태이트를 바꾼다.                        
			if num >"0000000000"  then  
		    	next_state<=wait_equal;
		    	select_signal 	<='0';
		    	mem_we 			<='1';       
		    	mem_addr		<="100";
		    	mem_clear		<='0';
		    	
		    else                    
		    	select_signal 	<='-';
		    	mem_we 			<='0';       
		    	mem_addr		<="---"; 
		    	mem_clear		<='0';
		    	next_state		<=input_4;   
		    	
		    end if;	
		                    
		when wait_equal =>
			-- '=' 연산자 입력이 들어오면 메모리에 값을 저장하고 스태이트를 바꾼다.             
			if func ="00001"  then  		    
		    	select_signal <='1';
		    	mem_we <='1';       
		    	mem_addr<="101";
		    	mem_clear<='0';
		    	next_state<=result;
		    	
		    else                    
		    	select_signal <='-';
		    	mem_we <='0';       
		    	mem_addr<="---";
		    	mem_clear<='0';
		    	next_state<=wait_equal;    
		    	
		    end if;	
		                    
		when result =>             
			if num >"0000000000"  then
			 	select_signal <='-';
		    	mem_we <='0';       
		    	mem_addr<="---";
		    	mem_clear<='1';
		    	next_state<=input_1;
		    	
		    else                    
		    	select_signal <='-';
		    	mem_we <='0';       
		    	mem_addr<="---";
		    	mem_clear<='0';
		    	next_state<=result;    
		    	
		    end if;	 
		                   
		when others =>
			select_signal <='-';	
			mem_we <='0';       	
			mem_addr<="---";    	
	        next_state<=input_1;
	        mem_clear <='0'; 
		end case;	
		
end process STATE_MACHINE;


STATE_UPDATE:
process(clk,reset)
begin  
 if rising_edge(clk) then
 	if reset='0' then          
 		present_state<=input_1;
	else 
		present_state<=next_state;
	end if;
 end if;	
end process STATE_UPDATE;


--입력된 숫자를 인코드한다.
NUM_ENCODER:               
encoder                    
port map                   
(                          
	indata 	=>num			,         
	outdata =>encoded_num  
); 
                        
--입력된 연산자를 인코드한다.
OPERATION_ENCODER:
func_encoder                          
port map
(                                            
	indata	=>func 			,
	outdata	=>encoded_func
);                                           
                                                      

--인코드된 입력을 선택
SELECT_NUM_OR_OPERATION:
multiplxer 
port map                                               
(                                                   
	sel			=>select_signal 	,
	indata1     =>encoded_num       ,
	indata2     =>encoded_func      ,
	outdata     =>encoded_code
);                                                  
                                    

end Behavioral;
