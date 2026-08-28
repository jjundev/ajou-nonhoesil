library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.STD_LOGIC_ARITH.ALL;
use IEEE.STD_LOGIC_UNSIGNED.ALL;
USE IEEE.STD_LOGIC_TEXTIO.ALL;
USE STD.TEXTIO.ALL;

ENTITY cal_test IS
END cal_test;

ARCHITECTURE testbench_arch OF cal_test IS
    FILE RESULTS: TEXT OPEN WRITE_MODE IS "results.txt";

    COMPONENT calculator_machine
        PORT (
            clk : In std_logic;
            reset : In std_logic;
            Num : In std_logic_vector (9 DownTo 0);
            Func : In std_logic_vector (4 DownTo 0);
            Display_h : Out std_logic_vector (6 DownTo 0);
            Display_m : Out std_logic_vector (6 DownTo 0);
            Display_l : Out std_logic_vector (6 DownTo 0)
        );
    END COMPONENT;

    SIGNAL clk : std_logic := '0';
    SIGNAL reset : std_logic := '1';
    SIGNAL Num : std_logic_vector (9 DownTo 0) := "0000000000";
    SIGNAL Func : std_logic_vector (4 DownTo 0) := "00000";
    SIGNAL Display_h : std_logic_vector (6 DownTo 0) := "0000000";
    SIGNAL Display_m : std_logic_vector (6 DownTo 0) := "0000000";
    SIGNAL Display_l : std_logic_vector (6 DownTo 0) := "0000000";

    SHARED VARIABLE TX_ERROR : INTEGER := 0;
    SHARED VARIABLE TX_OUT : LINE;

    constant PERIOD : time := 200 ns;
    constant DUTY_CYCLE : real := 0.5;
    constant OFFSET : time := 0 ns;

    BEGIN
        UUT : calculator_machine
        PORT MAP (
            clk => clk,
            reset => reset,
            Num => Num,
            Func => Func,
            Display_h => Display_h,
            Display_m => Display_m,
            Display_l => Display_l
        );

        PROCESS    -- clock process for clk
        BEGIN
            WAIT for OFFSET;
            CLOCK_LOOP : LOOP
                clk <= '0';
                WAIT FOR (PERIOD - (PERIOD * DUTY_CYCLE));
                clk <= '1';
                WAIT FOR (PERIOD * DUTY_CYCLE);
            END LOOP CLOCK_LOOP;
        END PROCESS;

        PROCESS
            PROCEDURE CHECK_Display_h(
                next_Display_h : std_logic_vector (6 DownTo 0);
                TX_TIME : INTEGER
            ) IS
                VARIABLE TX_STR : String(1 to 4096);
                VARIABLE TX_LOC : LINE;
                BEGIN
                IF (Display_h /= next_Display_h) THEN
                    STD.TEXTIO.write(TX_LOC, string'("Error at time="));
                    STD.TEXTIO.write(TX_LOC, TX_TIME);
                    STD.TEXTIO.write(TX_LOC, string'("ns Display_h="));
                    IEEE.STD_LOGIC_TEXTIO.write(TX_LOC, Display_h);
                    STD.TEXTIO.write(TX_LOC, string'(", Expected = "));
                    IEEE.STD_LOGIC_TEXTIO.write(TX_LOC, next_Display_h);
                    STD.TEXTIO.write(TX_LOC, string'(" "));
                    TX_STR(TX_LOC.all'range) := TX_LOC.all;
                    STD.TEXTIO.writeline(RESULTS, TX_LOC);
                    STD.TEXTIO.Deallocate(TX_LOC);
                    ASSERT (FALSE) REPORT TX_STR SEVERITY ERROR;
                    TX_ERROR := TX_ERROR + 1;
                END IF;
            END;
            PROCEDURE CHECK_Display_l(
                next_Display_l : std_logic_vector (6 DownTo 0);
                TX_TIME : INTEGER
            ) IS
                VARIABLE TX_STR : String(1 to 4096);
                VARIABLE TX_LOC : LINE;
                BEGIN
                IF (Display_l /= next_Display_l) THEN
                    STD.TEXTIO.write(TX_LOC, string'("Error at time="));
                    STD.TEXTIO.write(TX_LOC, TX_TIME);
                    STD.TEXTIO.write(TX_LOC, string'("ns Display_l="));
                    IEEE.STD_LOGIC_TEXTIO.write(TX_LOC, Display_l);
                    STD.TEXTIO.write(TX_LOC, string'(", Expected = "));
                    IEEE.STD_LOGIC_TEXTIO.write(TX_LOC, next_Display_l);
                    STD.TEXTIO.write(TX_LOC, string'(" "));
                    TX_STR(TX_LOC.all'range) := TX_LOC.all;
                    STD.TEXTIO.writeline(RESULTS, TX_LOC);
                    STD.TEXTIO.Deallocate(TX_LOC);
                    ASSERT (FALSE) REPORT TX_STR SEVERITY ERROR;
                    TX_ERROR := TX_ERROR + 1;
                END IF;
            END;
            PROCEDURE CHECK_Display_m(
                next_Display_m : std_logic_vector (6 DownTo 0);
                TX_TIME : INTEGER
            ) IS
                VARIABLE TX_STR : String(1 to 4096);
                VARIABLE TX_LOC : LINE;
                BEGIN
                IF (Display_m /= next_Display_m) THEN
                    STD.TEXTIO.write(TX_LOC, string'("Error at time="));
                    STD.TEXTIO.write(TX_LOC, TX_TIME);
                    STD.TEXTIO.write(TX_LOC, string'("ns Display_m="));
                    IEEE.STD_LOGIC_TEXTIO.write(TX_LOC, Display_m);
                    STD.TEXTIO.write(TX_LOC, string'(", Expected = "));
                    IEEE.STD_LOGIC_TEXTIO.write(TX_LOC, next_Display_m);
                    STD.TEXTIO.write(TX_LOC, string'(" "));
                    TX_STR(TX_LOC.all'range) := TX_LOC.all;
                    STD.TEXTIO.writeline(RESULTS, TX_LOC);
                    STD.TEXTIO.Deallocate(TX_LOC);
                    ASSERT (FALSE) REPORT TX_STR SEVERITY ERROR;
                    TX_ERROR := TX_ERROR + 1;
                END IF;
            END;
            BEGIN
                -- -------------  Current Time:  85ns
                WAIT FOR 85 ns;
                reset <= '0';
                -- -------------------------------------
                -- -------------  Current Time:  285ns
                WAIT FOR 200 ns;
                reset <= '1';
                -- -------------------------------------
                -- -------------  Current Time:  485ns
                WAIT FOR 200 ns;
                Num <= "0000000010";
                -- -------------------------------------
                -- -------------  Current Time:  685ns
                WAIT FOR 200 ns;
                Num <= "0000000000";
                -- -------------------------------------
                -- -------------  Current Time:  885ns
                WAIT FOR 200 ns;
                Num <= "0000001000";
                -- -------------------------------------
                -- -------------  Current Time:  1085ns
                WAIT FOR 200 ns;
                Num <= "0000000000";
                -- -------------------------------------
                -- -------------  Current Time:  1285ns
                WAIT FOR 200 ns;
                Func <= "01000";
                -- -------------------------------------
                -- -------------  Current Time:  1485ns
                WAIT FOR 200 ns;
                Num <= "0000000100";
                Func <= "00000";
                -- -------------------------------------
                -- -------------  Current Time:  1685ns
                WAIT FOR 200 ns;
                Num <= "0000000000";
                -- -------------------------------------
                -- -------------  Current Time:  1885ns
                WAIT FOR 200 ns;
                Num <= "0000001000";
                -- -------------------------------------
                -- -------------  Current Time:  2085ns
                WAIT FOR 200 ns;
                Num <= "0000000000";
                Func <= "00001";
                -- -------------------------------------
                WAIT FOR 8115 ns;

                IF (TX_ERROR = 0) THEN
                    STD.TEXTIO.write(TX_OUT, string'("No errors or warnings"));
                    STD.TEXTIO.writeline(RESULTS, TX_OUT);
                    ASSERT (FALSE) REPORT
                      "Simulation successful (not a failure).  No problems detected."
                      SEVERITY FAILURE;
                ELSE
                    STD.TEXTIO.write(TX_OUT, TX_ERROR);
                    STD.TEXTIO.write(TX_OUT,
                        string'(" errors found in simulation"));
                    STD.TEXTIO.writeline(RESULTS, TX_OUT);
                    ASSERT (FALSE) REPORT "Errors found during simulation"
                         SEVERITY FAILURE;
                END IF;
            END PROCESS;

    END testbench_arch;

