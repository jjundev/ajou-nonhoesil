create_clock -name clock_50m -period 20.000 [get_ports clock_50m]
derive_clock_uncertainty
# Keypad is asynchronous (2-FF synchronizer) and the display is for human eyes.
set_false_path -from [get_ports {pb[*]}]
set_false_path -to [get_ports {fnd_s[*] fnd_d[*]}]
