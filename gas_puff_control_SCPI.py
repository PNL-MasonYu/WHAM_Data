#!/usr/bin/python3

import time, struct
import redpitaya_scpi as scpi
import numpy as np
import matplotlib.pyplot as plt
from WhamRedPitaya import WhamRedPitaya_SCPI


class WhamGasPuff():

    def __init__(self, ip):
        self.ip = ip
        self.dev = scpi.scpi(ip)

    def arm_gas_puff(self, wave_form, ampl, pulse_len_ms):
        freq = 1/pulse_len_ms * 1000

        self.dev.tx_txt('GEN:RST')

        self.dev.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
        self.dev.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
        self.dev.tx_txt('SOUR1:VOLT ' + str(ampl))
        self.dev.tx_txt('SOUR1:BURS:STAT BURST')
        self.dev.tx_txt('SOUR1:BURS:NCYC 1')
        self.dev.tx_txt('SOUR1:BURS:NOR 1')
        self.dev.tx_txt('SOUR1:BURS:LASTValue 0')
        #self.dev.tx_txt('SOUR1:BURS:INITValue 0')
        self.dev.tx_txt('SOUR1:TRig:SOUR EXT_PE')
        #self.dev.tx_txt('SOUR1:TRig:EXT:DEBouncerUs 10000000')
        #dev.tx_txt('SOUR1:TRIG:INT')

        self.dev.tx_txt('OUTPUT1:STATE ON')
        print("gas system armed")

    def reset_gas_puff(self):
        self.dev.tx_txt('GEN:RST')
        self.dev.tx_txt('OUTPUT1:STATE OFF')
        print("gas system reset")

if __name__ == "__main__":

    gas_puff = WhamGasPuff("rp-f093a9.local")
    data_acq = WhamRedPitaya_SCPI("rp-f093a9.local", device_node="RAW.GAS_PUFF_RP", mdsplus_server="andrew.psl.wisc.edu", mdsplus_tree="wham", shot_num=None)
    data_acq.bMDS = 1
    data_acq.n_pts = 400000
    data_acq.bPlot = 1
    data_acq.trig = "EXT_PE"
    #data_acq.trig_level = 0.5
    data_acq.downsample_value = 16
    data_acq.channel = 3
    data_acq.dev = gas_puff.dev

    while True:
        gas_puff.arm_gas_puff(wave_form='square', ampl=1, pulse_len_ms=20)

        data_acq.configure()
        data_acq.arm()
        data_acq.store()
        print("Output data acquired")
        gas_puff.reset_gas_puff()

        time.sleep(5)