library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;


ENTITY stopwatch1 IS                                               -- TOPMODEL? ???? INPUT, OUTPUT ??
PORT (
         clk,startstop,reset              : in std_logic;
         mmsec2,sec1,sec2,min1,min2       : out std_logic_vector(3 downto 0)
        
       );
END stopwatch;

ARCHITECTURE stopwatch_arch OF stopwatch IS
  
COMPONENT mmsec                               -- SUBMODEL? mmsec, secmin ??? ? ??? ????
port (
        A    : in std_logic;
        B    : in std_logic;
        C    : out std_logic_vector(3 downto 0);
        D    : in std_logic
      );
END COMPONENT;

COMPONENT secmin
port (
        A      : in  std_logic_vector(3 downto 0);
        B      : out std_logic_vector(3 downto 0);
        C      : out std_logic_vector(3 downto 0);
        D      : in std_logic 
      );
END COMPONENT;   


SIGNAL signal1, signal2,signal3,signal4,signal5 : std_logic_vector(3 downto 0);   -- ?? ??? ???? signal ??

BEGIN                    -- SUB?? mmsec ? ???? U0, secmin? ???? U1, U2 
        U0  : mmsec PORT MAP  (clk, startstop,signal1,reset);
        U1  : secmin PORT MAP (signal1, signal2, signal3,reset);
        U2  : secmin PORT MAP (signal2, signal4, signal5,reset);
        

mmsec2 <= signal1 ;
sec1   <= signal3 ;
sec2   <= signal2 ;
min1   <= signal5 ;
min2   <= signal4 ;
END stopwatch_arch;

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;
 
entity mmsec is                                                         --  mmsec? ???? ????
 port (
        A    : in std_logic;
        B    : in std_logic;
        C    : out std_logic_vector(3 downto 0);
        D    : in std_logic
      );
end mmsec;


architecture mmsec_arch of mmsec is                        -- mmsec? ????
signal mmssec  : std_logic_vector(3 downto 0) := "0000";      -- mmsec? ?? ??? ???? ?? mmssec??
begin
  process(A, B, D, mmssec)
  begin
  if (D'EVENT AND D = '0') then                             -- mmsec? ??
  mmssec <= "0000";                                          -- RESET(?? ?? D)? 0? ???? 0000?? ?????.
  else  
    if (A = '1' AND A'EVENT) then                            -- CLK(?? ?? A)? 1? ???? ????? ????.
      if (B = '1') then                                          -- B? 1? ?? mmsec? +!???.
          mmssec <= mmssec + 1 ;
         if (mmssec = "1001") then                             -- mmsec? 9??? 0?? ???.
           mmssec <= "0000";
         end if;
       end if;
    end if;
  end if;

C <= mmssec;                                                  -- ???? ?? ???? C? ???.
end process;
end mmsec_arch;

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_arith.all;
use ieee.std_logic_unsigned.all;

entity secmin is                                                 --  secmin? ???? ????
port (
        A      : in  std_logic_vector(3 downto 0);
        B      : out std_logic_vector(3 downto 0);
        C      : out std_logic_vector(3 downto 0); 
        D      : in std_logic
      );
end secmin;


architecture secmin_arch of secmin is                         -- secmin? ????
signal ssec   : std_logic_vector(3 downto 0) := "0000";          -- secmin? ?? ??? ???? ?? ssec ssec1,
signal ssec1  : std_logic_vector(3 downto 0) := "0000";          -- sssec, sssec1 ??
signal sssec   : std_logic_vector(3 downto 0) ;
signal sssec1  : std_logic_vector(3 downto 0) ;  

begin
  process(A, D, ssec, ssec1)                                  -- secmin? ??
  begin
  if (D = '0' AND D'EVENT) then                           -- RESET(?? ?? D)? 0? ?? ?? 0000?? ?????.
  ssec <= "0000";
  ssec1 <= "0000";
  sssec  <= ssec;
  sssec1 <= ssec1;
  else
    if (A = "0000" AND A'EVENT) then                       -- ?? ?? A? 1? ???? ????? ????.
       ssec <= ssec + 1 ;
        if (ssec = "1001") then                                         --ssec? 9??? 0?? ???.
          ssec <= "0000";
        elsif (ssec = "0000") then                                      -- ssec? 0??? ssec1 +1??.
              ssec1 <= ssec1 + 1 ;
                if (ssec1 = "0101") then                                --ssec1? 5??? 0?? ???.
                   ssec1 <= "0000";
                end if;
        sssec1 <= ssec1;
        end if;
     sssec  <= ssec;
    end if;    
  end if; 
C <= sssec;                                                            -- ???? ?? ???? C ? B? ???.
B <= sssec1; 

end process ;
end secmin_arch;