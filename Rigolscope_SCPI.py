from redpitaya_scpi import scpi
import logging, datetime
from MDSplus import connection
import numpy as np
import time
import matplotlib.pyplot as plt

class rigol_scpi:
    def __init__(self, IP="192.168.130.227", port=5555) -> None:
        self.dev = scpi(IP, port=port)
        self.dev.delimiter = '\n'
        self.ip = IP
        self.shot_num = None
        self.last_shot = None
        if self.ip == "192.168.130.227":
            self.device_node = "RAW.MASON_SCOPE"
        if self.ip == "192.168.130.231":
            self.device_node = "RAW.TQ_SCOPE"
        self.mdsplus_server = "andrew.psl.wisc.edu"
        if self.ip == "192.168.130.233":
            self.device_node = "RAW.MASON_DS1000"
        self.mdsplus_server = "andrew.psl.wisc.edu"
        self.mdsplus_tree = "wham"
        self.data_ch1 = None
        self.data_ch2 = None
        self.data_ch3 = None
        self.data_ch4 = None
        self.offset = 0.0  # time base offset in seconds
        self.timescale = 10.0  # time base scale in seconds per division (10 div total)
        self.sample_rate = 1.0
        
    def get_waveform(self, ch=1):
        self.dev.tx_txt(":STOP")
        self.dev.tx_txt(":WAV:SOUR CHAN" + str(ch))
        self.dev.tx_txt(":WAV:MODE MAXimum")
        #self.dev.tx_txt(":WAV:FORM ASCii")
        self.dev.tx_txt(":WAV:STAR 1")
        self.dev.tx_txt(":WAV:FORM WORD") # 2 bytes per point
        self.dev.tx_txt(":WAV:DATA?")
        buff_byte1 = self.dev.rx_arb()
        rawdata = []
        for i in range(0, len(buff_byte1), 2):
            bit_data = int.from_bytes(bytearray(buff_byte1[i:i+2]), 'little')
            rawdata.append(bit_data)
        #plt.plot(rawdata)
        #plt.show()
        volts_per_division = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":SCALe?"))
        data = np.array(rawdata) * volts_per_division * 8.0 / 32767.0
        
        return data
    
    def get_waveform_chunks(self, ch=1, chunks=100):
        self.dev.tx_txt(":STOP")
        self.dev.tx_txt(":WAV:SOUR CHAN" + str(ch))
        self.dev.tx_txt(":WAV:MODE MAXimum")
        maximum_points = self.dev.txrx_txt("ACQuire:MDEPth?")
        chunk_bounds = np.linspace(1, int(maximum_points), chunks)
        rawdata = []
        for n in range(chunks-1):
            start = str(int(chunk_bounds[n]))
            stop = str(int(chunk_bounds[n + 1])-1)
            self.dev.tx_txt(":WAV:STAR " + start)
            self.dev.tx_txt(":WAV:STOP " + stop)
            #print(start + " - " + stop)
            self.dev.tx_txt(":WAV:FORM BYTE")
            self.dev.tx_txt(":WAV:DATA?")
            buff = self.dev.rx_arb()
            for i in range(0, len(buff)):
                bit_data = int.from_bytes(bytearray(buff[i:i+1]), 'little')
                rawdata.append(bit_data)

            # Need this extra command in here to ensure the next series of bytes starts with the proper header
            volts_per_division = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":SCALe?"))
        #plt.plot(rawdata)
        #plt.show()
        data = np.array(rawdata) * volts_per_division * 8.0 / 32767.0
        
        return data
    
    def set_up_channel(self, ch=1):
        # Sets channel to no bandwidth limit, DC coupling, zero offset, 1 meg impedance
        self.dev.tx_txt(":CHANnel" + str(ch) + ":BWLimit OFF")
        self.dev.tx_txt(":CHANnel" + str(ch) + ":COUPling DC")
        self.dev.tx_txt(":CHANnel" + str(ch) + ":OFFSet 0")
        self.dev.tx_txt(":CHANnel" + str(ch) + ":IMPedance OMEG")
        
        
    def get_all_ch_waveform(self):
        self.data_ch1 = self.get_waveform(ch=1)
        self.data_ch2 = self.get_waveform(ch=2)
        self.data_ch3 = self.get_waveform(ch=3)
        self.data_ch4 = self.get_waveform(ch=4)

    def get_all_ch_waveform_chunks(self):
        self.data_ch1 = self.get_waveform_chunks(ch=1)
        self.data_ch2 = self.get_waveform_chunks(ch=2)
        self.data_ch3 = self.get_waveform_chunks(ch=3)
        self.data_ch4 = self.get_waveform_chunks(ch=4)

    def get_time_scale(self):
        # This is not sampling rate! It's the time base on the screen
        scale = self.dev.txrx_txt(":TIMebase:MAIN:SCALe?")
        self.timescale = float(scale) 
        return float(scale)
    
    def get_sampling_rate(self):
        sample_rate = self.dev.txrx_txt(":ACQuire:SRATe?")
        self.sample_rate = float(sample_rate)
        return self.sample_rate
    
    def get_delay(self):
        delay = self.dev.txrx_txt("TIMebase:MAIN:OFFSet?")
        self.delay = float(delay)
        return self.delay
    
    def get_vertical_offset(self, ch=1):
        offset = self.dev.txrx_txt(":CHANnel" + str(ch) + ":OFFSet?")
        return float(offset)
    
    def get_vertical_scale(self, ch=1):
        volts_per_division = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":SCALe?"))
        return volts_per_division
    
    def set_vertical_scale(self, ch=1, volts_per_division = 50e-3):
        self.dev.tx_txt(":CHANnel" + str(ch) + ":SCALe " + float(volts_per_division))

    def write_mdsplus(self, conn):

        # Check that we are not writing to the same shot
        if self.shot_num == self.last_shot:

            print("Overlapping shot number " + str(self.shot_num) + "!")
            logging.error("Overlapping shot number " + str(self.shot_num) + "!")
    
        if self.last_shot == None:
            self.last_shot = self.shot_num
    
        msg1 = "Writing data to shot number: " + self.shot_num
        msg2 = "Writing data to node: " + self.device_node

        print(msg1) 
        print(msg2)
        logging.info(msg1)
        logging.info(msg2)
        # iterate through each channel and write the data
        data_chs = [self.data_ch1, self.data_ch2, self.data_ch3, self.data_ch4]
        for ch in [1,2,3,4]: 
            try:
                # Write (put) the data to the device in MDSplus
                conn.put(self.device_node+".CH_0" + str(ch) + ":SIGNAL", "$", data_chs[ch-1])
                conn.put(self.device_node+".CH_0" + str(ch) + ":FREQ", "$",  self.get_sampling_rate())
                conn.put(self.device_node+".CH_0" + str(ch) + ":OFFSET", "$", self.get_vertical_offset(ch=ch))
                conn.put(self.device_node+".CH_0" + str(ch) + ":DELAY", "$", self.get_delay())
                conn.put(self.device_node+".CH_0" + str(ch) + ":SCALE",  "$", self.get_vertical_scale(ch=ch))

                self.last_shot = self.shot_num
            except Exception as E:
                print("MDSPlus Error on " + self.ip)
                print(E)
                print("Shot number: {:}".format(self.shot_num))
                logging.error("MDSPlus Error on " + self.ip)
                logging.error(E)
                logging.error("Shot number: {:}".format(self.shot_num))

    def _write_mdsplus(self):
        # No remote connection to MDSplus is provided so create a new one

        # Establish new remote connection to MDSplus
        conn = connection.Connection(self.mdsplus_server) # Connect to MDSplus server (andrew)
        
        # Open the tree
        conn.openTree(self.mdsplus_tree, self.shot_num)

        # Get the current shot number
        self.shot_num = conn.get('$shot')

        time.sleep(1)
        # Write the data
        self.write_mdsplus(conn)

        # Close the tree and latest shot
        conn.closeTree(self.mdsplus_tree, self.shot_num)
        
    def read_csv(self, path):
        data_rows = np.loadtxt(path,delimiter=',', skiprows=1, usecols=[0,1,2,3])
        self.data_ch1 = data_rows[:, 0]
        self.data_ch2 = data_rows[:, 1]
        self.data_ch3 = data_rows[:, 2]
        self.data_ch4 = data_rows[:, 3]
        timescale_str = np.loadtxt(path, dtype=str, delimiter=',', max_rows=1)[5]
        t0_str = np.loadtxt(path, dtype=str, delimiter=',', max_rows=1)[4]
        self.timescale = float(timescale_str.split(" = ")[-1]) * len(self.data_ch1) / 10
        self.offset = float(t0_str.split(" =")[-1])

        
    def plot_all_ch(self):
        time_base = np.linspace(0, self.timescale*10, len(self.data_ch1))
        plt.plot(time_base, self.data_ch1, label="ch1")
        plt.plot(time_base, self.data_ch2, label="ch2")
        plt.plot(time_base, self.data_ch3, label="ch3")
        plt.plot(time_base, self.data_ch4, label="ch4")
        plt.legend()
        plt.show()
        
    def run(self):
        self.dev.tx_txt(":RUN")


if __name__ == "__main__":
    for IP in ["192.168.130.227", "192.168.130.231", "192.168.130.233"]:
        scope = rigol_scpi(IP)
        if IP == "192.168.130.233":
            scope.get_all_ch_waveform_chunks()
        elif IP == "192.168.130.227": 
            scope.data_ch1 = []
            scope.data_ch2 = scope.get_waveform(2)
            scope.data_ch3 = scope.get_waveform(3)
            scope.data_ch4 = scope.get_waveform(4)
        else:
            scope.get_all_ch_waveform()

        scope.get_delay()
        scope.get_vertical_offset()
        scope.get_time_scale()
        scope.get_vertical_scale()
        #scope.read_csv("data_saving/2407230490.csv")
        scope.shot_num = 0
        #scope.plot_all_ch()
        scope._write_mdsplus()
        scope.run()