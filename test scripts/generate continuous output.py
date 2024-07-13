#!/usr/bin/env python3

import sys
import redpitaya_scpi as scpi

IP = "rp-f0bd65.local"
rp_s = scpi.scpi(IP)

wave_form = 'DC'
freq = 423
ampl = 0.2

rp_s.tx_txt('GEN:RST')

rp_s.tx_txt('SOUR2:FUNC ' + str(wave_form).upper())
rp_s.tx_txt('SOUR2:FREQ:FIX ' + str(freq))
rp_s.tx_txt('SOUR2:VOLT ' + str(ampl))

rp_s.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
rp_s.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
rp_s.tx_txt('SOUR1:VOLT ' + str(ampl))

# Enable output
rp_s.tx_txt('OUTPUT2:STATE ON')
rp_s.tx_txt('SOUR2:TRig:INT')
rp_s.tx_txt('OUTPUT1:STATE ON')
rp_s.tx_txt('SOUR1:TRig:INT')

rp_s.close()