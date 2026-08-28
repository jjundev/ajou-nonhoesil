library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;


entity memory_module is
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
end memory_module;

architecture Behavioral of memory_module is

component reg_sync 
generic (bit_widths:integer:=32);                            
port                                                         
(                                                            
	clk				: in std_logic;                                  
	reset   		: in std_logic;                                  
	clear   		: in std_logic;                                  
	we      		: in std_logic;                                  
	indata  		: in std_logic_vector(bit_widths-1 downto 0);    
	outdata 		: out std_logic_vector(bit_widths-1 downto 0)   
);                                                           
end component;                                                

component demultiplexer 
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
end component;
                               
signal demux_to_reg0: std_logic_vector(3 downto 0);
signal demux_to_reg1: std_logic_vector(3 downto 0);
signal demux_to_reg2: std_logic_vector(3 downto 0);
signal demux_to_reg3: std_logic_vector(3 downto 0);
signal demux_to_reg4: std_logic_vector(3 downto 0);
signal demux_to_reg5: std_logic_vector(3 downto 0);


signal reg0_we : std_logic;
signal reg1_we : std_logic;
signal reg2_we : std_logic;
signal reg3_we : std_logic;
signal reg4_we : std_logic;
signal reg5_we : std_logic;

begin
                 
MEMORY_ADDRESS_POINTER:
demultiplexer                          
port map                                             
(                                                
                                                 
	addr	=>mem_addr			,
	indata	=>encoded_code      ,
	we		=>mem_we            ,
	outdata0=>demux_to_reg0     ,
	outdata1=>demux_to_reg1     ,
	outdata2=>demux_to_reg2     ,
	outdata3=>demux_to_reg3     ,
	outdata4=>demux_to_reg4     ,
	outdata5=>demux_to_reg5     ,	
	we0		=>reg0_we           ,
	we1		=>reg1_we           ,
	we2		=>reg2_we           ,
	we3		=>reg3_we           ,
	we4		=>reg4_we           ,
	we5		=>reg5_we                                      
);                                               

MEMORY_ADDRESS0:
reg_sync 
generic map(4)                           
port map                                                        
(                                                            
	clk		=>  clk				,
	reset   =>  reset           ,
	clear   =>  clear           ,
	we      =>  reg0_we         ,
	indata  =>  demux_to_reg0   ,
	outdata =>  num_out0
);                                                           

MEMORY_ADDRESS1:                 
reg_sync                         
generic map(4)                     
port map                            
(                                
	clk		=>  clk				,
	reset   =>  reset           ,
	clear   =>  clear           ,
	we      =>  reg1_we         ,
	indata  =>  demux_to_reg1   ,
	outdata =>  num_out1         
);                               

MEMORY_ADDRESS2:                 
reg_sync                         
generic map(4)                     
port map                            
(                                
	clk		=>  clk				,
	reset   =>  reset           ,
	clear   =>  clear           ,
	we      =>  reg2_we         ,
	indata  =>  demux_to_reg2   ,
	outdata =>  func_out         
);                               

MEMORY_ADDRESS3:                 
reg_sync                         
generic map(4)                     
port map                            
(                                
	clk		=>  clk				,
	reset   =>  reset           ,
	clear   =>  clear           ,
	we      =>  reg3_we         ,
	indata  =>  demux_to_reg3   ,
	outdata =>  num_out2         
);                               

MEMORY_ADDRESS4:                 
reg_sync                         
generic map(4)                     
port map                            
(                                
	clk		=>  clk				,
	reset   =>  reset           ,
	clear   =>  clear           ,
	we      =>  reg4_we         ,
	indata  =>  demux_to_reg4   ,
	outdata =>  num_out3         
);                               
                                 
MEMORY_ADDRESS5:                                                  
reg_sync                                                          
generic map(4)                                                    
port map                                                          
(                                                                 
	clk		=>  clk				, 
	reset   =>  reset           , 
	clear   =>  clear           , 
	we      =>  reg5_we         , 
	indata  =>  demux_to_reg5   , 
	outdata =>  equal_out          
);                                
    
end Behavioral;
