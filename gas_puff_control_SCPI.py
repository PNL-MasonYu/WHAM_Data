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
        freq = 1/pulse_len_ms * 1000 / 2

        self.dev.tx_txt('GEN:RST')

        self.dev.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
        self.dev.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
        self.dev.tx_txt('SOUR1:VOLT ' + str(ampl))
        self.dev.tx_txt('SOUR1:BURS:STAT BURST')
        self.dev.tx_txt('SOUR1:BURS:NCYC 1')
        self.dev.tx_txt('SOUR1:BURS:NOR 1')
        #self.dev.tx_txt('SOUR1:BURS:LASTValue 0')
        #self.dev.tx_txt('SOUR1:BURS:INITValue 0')
        self.dev.tx_txt('SOUR1:TRig:SOUR NOW')
        #self.dev.tx_txt('SOUR:TRig:EXT:DEBouncerUs 10')
        #self.dev.tx_txt('SOUR1:TRig:SOUR NOW')
        self.dev.tx_txt('SOUR1:TRIG:INT')

        self.dev.tx_txt('OUTPUT1:STATE ON')
        print("gas system armed")

    def reset_gas_puff(self):
        self.dev.tx_txt('GEN:RST')
        self.dev.tx_txt('OUTPUT1:STATE OFF')
        print("gas system reset")

    def make_arb_waveform(self, prefill_ms=200, delay_ms=10, prefill_lvl = 1.0, start_lvl=0.5, end_lvl=0.8, puff_ms=10):
        self.dev.tx_txt('GEN:RST')
        
        total_ms = prefill_ms + delay_ms + puff_ms
        frequency = 16384 / (total_ms / 1000)
        data_array = np.zeros(16384)
        prefill_end = int(16384*prefill_ms/total_ms)
        delay_end = int(16384*(prefill_ms+delay_ms)/total_ms)
        for d in range(16384):
            if d < prefill_end:
                data_array[d] = prefill_lvl
            if d >= prefill_end and d < delay_end:
                data_array[d] = 0.0
            if d >= delay_end:
                data_array[d] = start_lvl + (end_lvl-start_lvl)*(d-delay_end)/(16384-delay_end)
        #plt.plot(data_array)
        #plt.show()
        self.dev.sour_set(1, "ARBITRARY", freq=frequency, data=data_array, burst=True, ncyc=1, nor=1, trig="NOW")
        self.dev.tx_txt('OUTPUT1:STATE ON')
        print("gas system armed with arbitrary waveform")
        return data_array


if __name__ == "__main__":
    
    #gas_puff = WhamGasPuff("rp-f093a9.local")
    gas_puff = WhamGasPuff("192.168.130.228")
    gas_puff.make_arb_waveform()
    data_acq = WhamRedPitaya_SCPI("192.168.130.228", device_node="RAW.GAS_PUFF_RP",
                                   mdsplus_server="andrew.psl.wisc.edu", mdsplus_tree="wham", shot_num=None, Trig="EXT_PE")
    data_acq.bMDS = 1
    data_acq.n_pts = 6e5
    data_acq.bPlot = 1
    data_acq.trig = "NOW"
    data_acq.trig_level = 0.5
    data_acq.downsample_value = 4
    data_acq.channel = 3
    data_acq.verbosity = 1
    #data_acq.dev = gas_puff.dev

    while True:
        gas_puff.arm_gas_puff(wave_form='square', ampl=1, pulse_len_ms=100)
        data_acq.connect()
        data_acq.configure()
        data_acq.arm()
        data_acq.store()
        print("Output data acquired")
        gas_puff.reset_gas_puff()

        time.sleep(10)