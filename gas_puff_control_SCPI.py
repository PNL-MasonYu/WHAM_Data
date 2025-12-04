#!/usr/bin/python3

import time
import threading
import concurrent.futures
import numpy as np
import logging
from WhamRedPitaya import WhamRedPitaya_SCPI
from redpitaya_scpi import scpi
start_time = time.localtime()
err_file = "/mnt/n/whamdata/WHAMdata4_logs/GAS_log_" + time.strftime("%Y_%m_%d_%H-%M", start_time) + ".csv"
logging.basicConfig(filename=err_file, level=logging.INFO)

class WhamGasPuff():

    def __init__(self, IP, device_node, n_pts=5e5+1, downsample_value=32):
        """
        Configure the internal data acquisition on the RPs and sets up the RP SCPI device
        """
        self.IP = IP
        self.rp = WhamRedPitaya_SCPI(IP, device_node=device_node,
                                    mdsplus_server="andrew.psl.wisc.edu", mdsplus_tree="wham", shot_num=None, Trig="EXT_NE")
        self.rp.bMDS = 1
        self.rp.n_pts = n_pts
        self.rp.bPlot = 1
        self.rp.downsample_value = downsample_value
        self.rp.channel = 3
        self.rp.verbosity = 0
        self.dev = self.rp.dev
        self.timer_increment = 10    #Time interval in seconds at which the arb. waveform from labview is updated
        self.next_t = 0
        self.done = False
        self.iterations = 0

    def arm_square_gas_puff(self, wave_form, ampl, pulse_len_ms, ch=1):
        """
        Arm gas puff for square pulse of length pulse_len_ms
        """
        freq = 1/pulse_len_ms * 1000 / 2

        self.dev.tx_txt('GEN:RST')

        self.dev.tx_txt('SOUR{:}:FUNC '.format(ch) + str(wave_form).upper())
        self.dev.tx_txt('SOUR{:}:FREQ:FIX '.format(ch) + str(freq))
        self.dev.tx_txt('SOUR{:}:VOLT '.format(ch) + str(ampl))
        self.dev.tx_txt('SOUR{:}:BURS:STAT BURST'.format(ch))
        self.dev.tx_txt('SOUR{:}:BURS:NCYC 1'.format(ch))
        self.dev.tx_txt('SOUR{:}:BURS:NOR 1'.format(ch))
        # Force initial value to -1 to ensure valve is closed when it is armed
        self.dev.tx_txt('SOUR{:}:INITValue -1'.format(ch))
        #self.dev.tx_txt('SOUR{:}:BURS:LASTValue 0'.format(ch))
        #self.dev.tx_txt('SOUR{:}:BURS:INITValue 0'.format(ch))
        #self.dev.tx_txt('SOUR{:}:TRig:SOUR EXT_NE'.format(ch))
        #self.dev.tx_txt('SOUR:TRig:EXT:DEBouncerUs 10'.format(ch))
        self.dev.tx_txt('SOUR{:}:TRig:SOUR EXT_NE'.format(ch))
        #self.dev.tx_txt('SOUR{:}:TRIG:INT'.format(ch))


        self.dev.tx_txt('OUTPUT1:STATE ON')
        print("gas system armed")
        logging.info("gas system armed")

    def reset_gas_puff(self):
        self.dev.tx_txt('OUTPUT1:STATE OFF')
        self.dev.tx_txt('OUTPUT2:STATE OFF')
        self.dev.tx_txt('GEN:RST')
        print("gas system reset")
        logging.info("gas system reset")

    def arm_dual_pulse_waveform(self, ch=1, prefill_ms=8, delay_ms=30, prefill_lvl = 1.0, start_lvl=0.7, end_lvl=1.0, puff_ms=10):
        """
        Loads a dual puff waveform into the RP's ch and arms it
        """
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
        self.dev.tx_txt('OUTPUT{:}:STATE ON'.format(ch))
        print("gas system armed with dual puff waveform")
        logging.info("gas system armed with dual puff waveform")
        return data_array
    
    def arm_arb_waveform(self, ch=1, path='/mnt/n/whamdata/Gas Puff Waveform/gas_puff_waveform.csv'):
        """
        Load the arbitrary waveform command from the NAS and send it to the RP, arming the output channel
        ch=1 or 2
        """
        total_ms = np.loadtxt(path, delimiter=',', usecols=0)[0]
        if total_ms == 0:
            # in case operators set the gas puff duration to zero
            data_array = [0]
            frequency = 1000
        else:
            data_array = np.loadtxt(path, delimiter=',', skiprows=1)
            frequency = 1 / (total_ms / 1000)
        
        self.dev.sour_set(ch, "ARBITRARY", freq=frequency, data=data_array, burst=True, ncyc=1, nor=1, trig="EXT_NE")
        # Force initial value to -1 to ensure valve is closed when it is armed
        self.dev.tx_txt('SOUR{:}:INITValue -1'.format(ch))
        self.dev.tx_txt('SOUR{:}:TRig:SOUR EXT_NE'.format(ch))
        self.dev.tx_txt('OUTPUT{:}:STATE ON'.format(ch))
        self.dev.check_error()
        
        print("gas system armed from {:}".format(path.split("/")[-1]))
        print('OUTPUT{:}:STATE? '.format(ch) + self.dev.txrx_txt('OUTPUT{:}:STATE?'.format(ch)))
        logging.info("gas system armed with arbitrary waveform from {:}".format(path.split("/")[-1]))

        return

    def _run_arb_waveform(self):
        """
        periodically checks the waveform file and load it
        This is not typically used since the labview calls this script and it loads the waveform before arming
        """
        if self.next_t == 0:
            self.next_t = time.time()
        self.arm_arb_waveform()
        self.next_t += self.timer_increment
        if self.iterations > 12:
            self.done = True
            self.reset_gas_puff()
            logging.debug("Exceeded 2 minutes after arming gas system, resetting.")
        if not self.done:
            threading.Timer(self.next_t - time.time(), self._run_arb_waveform).start()

    def arm_for_shot(self):
        """
        This function arms both the arbitrary waveform generator and the digitizer for a shot
        After the trigger, the data is saved and the IP connection is closed.
        """
        if self.IP == "192.168.130.228": #f0:bd:40, rp_01
            self.arm_arb_waveform(ch=1, path="/mnt/n/whamdata/Gas Puff Waveform/gas_puff_waveform_n_lim.csv") #ch1: north limiter inj
            self.arm_arb_waveform(ch=2, path="/mnt/n/whamdata/Gas Puff Waveform/gas_puff_waveform_n_ext.csv") #ch3: north external inj
        else: #f0:92:cd, rp_02
            self.arm_arb_waveform(ch=1, path="/mnt/n/whamdata/Gas Puff Waveform/gas_puff_waveform_s_lim.csv") #ch2: south limiter inj
            self.arm_arb_waveform(ch=2, path="/mnt/n/whamdata/Gas Puff Waveform/gas_puff_waveform_s_ext.csv") #ch4: south external inj
        # Now arm the data acquisition
        self.rp.configure()
        self.rp.arm()
        # Wait for trigger...
        self.rp.store()
        print("Output data acquired")
        # Give some time for data transfer before disconnecting
        time.sleep(20)
        self.reset_gas_puff()
        self.dev.close()
        return

if __name__ == "__main__":

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        rp_01 = WhamGasPuff(IP = "192.168.130.228", device_node="raw.gas_puff_rp.rp_01") #f0:bd:40
        rp_02 = WhamGasPuff(IP = "192.168.130.229", device_node="raw.gas_puff_rp.rp_02") #f0:92:cd
        executor.submit(rp_01.arm_for_shot)
        # Add in a bit of a delay so we avoid any race conditions
        time.sleep(0.5)
        executor.submit(rp_02.arm_for_shot)
