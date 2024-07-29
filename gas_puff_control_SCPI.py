#!/usr/bin/python3

import time
import threading
import numpy as np
import logging
from WhamRedPitaya import WhamRedPitaya_SCPI
start_time = time.localtime()
err_file = "/mnt/n/whamdata/WHAMdata4_logs/GAS_log_" + time.strftime("%Y_%m_%d_%H-%M", start_time) + ".csv"
logging.basicConfig(filename=err_file, level=logging.INFO)

class WhamGasPuff():

    def __init__(self, dev):
        self.dev = dev
        self.timer_increment = 10    #Time interval at which the arb. waveform from labview is updated
        self.next_t = 0
        self.done = False

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
        self.dev.tx_txt('SOUR1:TRig:SOUR EXT_NE')
        #self.dev.tx_txt('SOUR:TRig:EXT:DEBouncerUs 10')
        #self.dev.tx_txt('SOUR1:TRig:SOUR NOW')
        #self.dev.tx_txt('SOUR1:TRIG:INT')

        self.dev.tx_txt('OUTPUT1:STATE ON')
        print("gas system armed")
        logging.info("gas system armed")

    def reset_gas_puff(self):
        self.dev.tx_txt('GEN:RST')
        self.dev.tx_txt('OUTPUT1:STATE OFF')
        print("gas system reset")
        logging.info("gas system reset")

    def arm_dual_pulse_waveform(self, prefill_ms=8, delay_ms=30, prefill_lvl = 1.0, start_lvl=0.7, end_lvl=1.0, puff_ms=10):
        self.dev.tx_txt('GEN:RST')

        total_ms = prefill_ms + delay_ms + puff_ms
        frequency = 1 / (total_ms / 1000)
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
        self.dev.sour_set(1, "ARBITRARY", freq=frequency, data=data_array, burst=True, ncyc=1, nor=1, trig="EXT_NE")
        self.dev.tx_txt('OUTPUT1:STATE ON')
        print("gas system armed with arbitrary waveform")
        logging.info("gas system armed with arbitrary waveform")
        return data_array
    
    def arm_arb_waveform(self, path='/mnt/n/whamdata/Gas Puff Waveform/gas_puff_waveform.csv'):
        
        self.dev.tx_txt('GEN:RST')
        total_ms = np.loadtxt(path, delimiter=',', usecols=0)[0]
        data_array = np.loadtxt(path, delimiter=',', skiprows=1)
        frequency = 1 / (total_ms / 1000)
        self.dev.sour_set(1, "ARBITRARY", freq=frequency, data=data_array, burst=True, ncyc=1, nor=1, trig="EXT_NE")
        self.dev.tx_txt('OUTPUT1:STATE ON')
        #print("gas system armed with arbitrary waveform from LabView")
        #plt.plot(data_array)
        #plt.show()
        return

    def _run_arb_waveform(self):
        """
        periodically checks the waveform file and load it on
        """
        if self.next_t == 0:
            self.next_t = time.time()
        self.arm_arb_waveform()
        self.next_t += self.timer_increment
        if not self.done:
            threading.Timer(self.next_t - time.time(), self._run_arb_waveform).start()

if __name__ == "__main__":
    
    #gas_puff = WhamGasPuff("rp-f093a9.local")
    
    data_acq = WhamRedPitaya_SCPI("192.168.130.228", device_node="RAW.GAS_PUFF_RP.RP_01",
                                   mdsplus_server="andrew.psl.wisc.edu", mdsplus_tree="wham", shot_num=None, Trig="EXT_NE")
    gas_puff = WhamGasPuff(data_acq.dev)
    data_acq.bMDS = 1
    data_acq.n_pts = 5e6 + 1
    data_acq.bPlot = 1
    data_acq.trig_level = 0.4
    data_acq.downsample_value = 16
    data_acq.channel = 3
    data_acq.verbosity = 1
    #data_acq.dev = gas_puff.dev

    while True:
        #gas_puff.arm_gas_puff(wave_form='square', ampl=1, pulse_len_ms=6)
        #gas_puff.arm_dual_pulse_waveform(prefill_ms=3, delay_ms=195, prefill_lvl = 1.0, start_lvl=1.0, end_lvl=1.0, puff_ms=9)
        #gas_puff.arm_arb_waveform()
        gas_puff._run_arb_waveform()
        data_acq.configure()
        data_acq.arm()
        data_acq.store()
        print("Output data acquired")
        gas_puff.reset_gas_puff()

        time.sleep(10)