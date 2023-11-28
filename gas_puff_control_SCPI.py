#!/usr/bin/python3

import time
import redpitaya_scpi as scpi

rp_s = scpi.scpi("rp-f093a9.local")

def arm_gas_system(wave_form, ampl, pulse_len_ms):
    freq = 1/pulse_len_ms * 1000

    rp_s.tx_txt('GEN:RST')

    rp_s.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
    rp_s.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
    rp_s.tx_txt('SOUR1:VOLT ' + str(ampl))
    rp_s.tx_txt('SOUR1:BURS:STAT BURST')
    rp_s.tx_txt('SOUR1:BURS:NCYC 1')
    rp_s.tx_txt('SOUR1:BURS:NOR 1')
    rp_s.tx_txt('SOUR1:BURS:LASTValue 0')
    rp_s.tx_txt('SOUR1:BURS:INITValue 0')
    rp_s.tx_txt('SOUR1:TRig:SOUR EXT_NE')
    rp_s.tx_txt('SOUR1:TRig:EXT:DEBouncerUs 10000000')
    #rp_s.tx_txt('SOUR1:TRIG:INT')

    rp_s.tx_txt('OUTPUT1:STATE ON')

def reset_gas_system():
    rp_s.tx_txt('GEN:RST')
    rp_s.tx_txt('OUTPUT1:STATE OFF')

if __name__ == "__main__":
    arm_gas_system(wave_form='square', ampl=0.5, pulse_len_ms=50)
    