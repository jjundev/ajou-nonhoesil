library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;


entity calculator_machine is
port
(

	clk		:in std_logic;
	reset	:in std_logic;
	Num		:in std_logic_vector(9 downto 0);
	Func	:in std_logic_vector(4 downto 0);
	
	
	Display_h: out std_logic_vector(6 downto 0);
	Display_m: out std_logic_vector(6 downto 0);	
	Display_l: out std_logic_vector(6 downto 0)
	
);
end calculator_machine;

architecture Behavioral of calculator_machine is

component ALU 
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
end component;

component Controller 
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
end component;

component memory_module 
port
(
	clk				: in std_logic;
	reset			: in std_logic;
	clear			: in std_logic;
	        		
	mem_we			: in std_logic;
	mem_addr		: in std_logic_vector(2 downto 0);
	encoded_code	: in std_logic_vector(3 downto 0);
	
	num_out0		: out std_logic_vector(3 downto 0);
	num_out1		: out std_logic_vector(3 downto 0);	
	num_out2		: out std_logic_vector(3 downto 0);
	num_out3		: out std_logic_vector(3 downto 0);
	func_out 		: out std_logic_vector(3 downto 0);
	equal_out		: out std_logic_vector(3 downto 0)
);
end component;

component segment_driver 
port
(
	indata : in std_logic_vector(3 downto 0);
	outdata: out std_logic_vector(6 downto 0)
);
end component;


signal mem_we			: std_logic;
signal mem_addr			: std_logic_vector(2 downto 0);
signal endcoded_code	: std_logic_vector(3 downto 0);
signal mem_clear		: std_logic;
signal num_out0			: std_logic_vector(3 downto 0);
signal num_out1         : std_logic_vector(3 downto 0);
signal num_out2         : std_logic_vector(3 downto 0);
signal num_out3         : std_logic_vector(3 downto 0);
signal func_out         : std_logic_vector(3 downto 0);
signal segment_driver0	: std_logic_vector(3 downto 0);
signal segment_driver1  : std_logic_vector(3 downto 0);
signal segment_driver2  : std_logic_vector(3 downto 0);

signal equal_out		: std_logic_vector(3 downto 0); 
begin

CONTROLER_UNIT:
Controller 
port map
(
	clk			=>clk			,
	reset   	=>reset         ,
	num			=>num           ,
	func    	=>func          ,
	        	                
	mem_we		=>mem_we		,    
	mem_addr	=>mem_addr		,
	encoded_code=>endcoded_code ,  
	mem_clear	=>mem_clear		
	
	
);
MEMORY_UNIT:
memory_module 
port map
(
	clk				=>clk			,
	reset			=>reset         ,
	clear			=>mem_clear     ,
	        		                
	mem_we			=>mem_we		,    
	mem_addr		=>mem_addr		,
	encoded_code	=>endcoded_code ,  
	                                
	num_out0		=>num_out0      ,
	num_out1		=>num_out1	    ,
	num_out2		=>num_out2      ,
	num_out3		=>num_out3      ,
	func_out 		=>func_out		,
	equal_out		=>equal_out
);

ALU_UNIT:
ALU 
port map
(
	
	indata1			=>num_out0			,
	indata2         =>num_out1          ,
	indata3         =>num_out2          ,
	indata4         =>num_out3          ,
	func            =>func_out          ,
	equal			=>equal_out			,                                    
	segment_driver0 =>segment_driver0   ,
	segment_driver1 =>segment_driver1   ,
	segment_driver2 =>segment_driver2
);

DISPLAY_SEVEN_SEGMENT_HIGH:
segment_driver                         
port map 
(                                                
	indata 	=>segment_driver0	,
	outdata =>display_h
);                                               

DISPLAY_SEVEN_SEGMENT_MEDIUM:
segment_driver                         
port map 
(                                                
	indata  =>segment_driver1	,
	outdata =>display_m          
);                                               

DISPLAY_SEVEN_SEGMENT_LOW:
segment_driver                         
port map 
(                                                
	indata =>segment_driver2	,
	outdata=>display_l          
);                                               





end Behavioral;
