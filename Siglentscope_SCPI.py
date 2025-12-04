from redpitaya_scpi import scpi
import logging, datetime, MDSplus
import mdsthin # MDSthin doesn't like being run in a thread
from MDSplus import connection
import numpy as np
import time
import matplotlib.pyplot as plt
import os
import matplotlib
import math
import struct
import gc
matplotlib.use('agg')
HORI_NUM = 10 #number of horizontal divisions
tdiv_enum = [200e-12,500e-12, 1e-9,\
2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9, \
1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6, \
1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3, \
1, 2, 5, 10, 20, 50, 100, 200, 500, 1000] #enumerated second per division values

######################################################

def initialize_logger(path, IP):

# Create a logger for this file.
    logger = logging.getLogger(IP)
    logger.setLevel(logging.DEBUG)
# Capture other warnings
    logging.captureWarnings(True)
# Create a file handler to write to.
    #file_handler = logging.FileHandler("/home/dtacqAdmin/procScripts/logs/postproc_shinethru.log", "w")
    file_handler = logging.FileHandler(path, "a")

    file_handler.setLevel(logging.DEBUG)
# Create a formatter to make the logging look nice.
    formatter = logging.Formatter('%(asctime)s, %(name)s - %(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)
# Add the file handler to the logger.
    logger.addHandler(file_handler)

    logger.info('Logger file created')
    return logger

######################################################

class siglent_scpi:
    def __init__(self, IP="192.168.140.227", port=5025) -> None:
        self.dev = scpi(IP, timeout=100, port=port)
        self.dev.delimiter = '\n'
        self.ip = IP
        self.shot_num = None
        self.last_shot = None
        if self.ip == "192.168.140.227":
            self.device_node = "RAW.MASON_SCOPE"
        if self.ip == "192.168.140.238":
            self.device_node = "RAW.BDUMP_SCOPE"

        self.mdsplus_server = "andrew.psl.wisc.edu"
        self.mdsplus_tree = "wham"
        self.time_base = None
        self.data_ch1 = None
        self.data_ch2 = None
        self.data_ch3 = None
        self.data_ch4 = None
        self.offset = 0.0  # time base offset in seconds
        self.timescale = 10.0  # time base scale in seconds per division (10 div total)
        self.delay = 0.0  # This is number of ms from trigger edge to start of pulse
        self.sample_rate = 1.0
        self.vdiv = 1.0

    def main_desc(self, recv):
        """
        Unpack the Siglent waveform preamble block to extract the data required
        to convert the raw data to floating point values
        """
        WAVE_ARRAY_1 = recv[0x3c:0x3f + 1]
        wave_array_count = recv[0x74:0x77 + 1]
        first_point = recv[0x84:0x87 + 1]
        sp = recv[0x88:0x8b + 1]
        v_scale = recv[0x9c:0x9f + 1]
        v_offset = recv[0xa0:0xa3 + 1]
        interval = recv[0xb0:0xb3 + 1]
        code_per_div = recv[0xa4:0Xa7 + 1]
        adc_bit = recv[0xac:0Xad + 1]
        delay = recv[0xb4:0xbb + 1]
        tdiv = recv[0x144:0x145 + 1]
        probe = recv[0x148:0x14b + 1]
        data_bytes = struct.unpack('i', WAVE_ARRAY_1)[0]
        point_num = struct.unpack('i', wave_array_count)[0]
        fp = struct.unpack('i', first_point)[0]
        sp = struct.unpack('i', sp)[0]
        interval = struct.unpack('f', interval)[0]
        delay = struct.unpack('d', delay)[0]
        tdiv_index = struct.unpack('h', tdiv)[0]
        probe = struct.unpack('f', probe)[0]
        vdiv = struct.unpack('f', v_scale)[0] * probe
        offset = struct.unpack('f', v_offset)[0] * probe
        code = struct.unpack('f', code_per_div)[0]
        adc_bit = struct.unpack('h', adc_bit)[0]
        tdiv = tdiv_enum[tdiv_index]
        return vdiv, offset, interval, delay, tdiv, code, adc_bit

    def get_waveform(self, logger, ch=1, time_return=False):
        """
        Transfer the data from ch on the scope to the host computer
        """
        start_t = time.time()
        self.dev.tx_txt(":TRIG:STOP")
        self.dev.tx_txt(f":WAVeform:SOURce C{ch}")
        #self.dev.tx_txt(":WAV:FORM ASCii")
        self.dev.tx_txt(":WAV:STAR 0")
        one_piece_num = float(self.dev.txrx_txt(":WAVeform:MAXPoint?").strip())
        points = float(self.dev.txrx_txt(":ACQuire:POINts?").strip())
        print(f"maximum points read by a single slice {one_piece_num}")
        print(f"total number of points in waveform {points}")
        read_times = math.ceil(points / one_piece_num)
        print(f"Need to read data in {read_times} chunks")
        if points > one_piece_num:
            self.dev.tx_txt(":WAVeform:POINt {}".format(one_piece_num))
        # We use 12 bit scopes, so the data must be transferred as 2 byte words
        self.dev.tx_txt("WAVeform:WIDTh WORD")
        
        # Read the raw data from the scope in chunks
        recv_chunks = []
        transfer_start_t = time.time()
        for i in range(0, read_times):
            start = i * one_piece_num
            #Set the starting point of each slice
            self.dev.tx_txt(":WAVeform:STARt {}".format(start))
            #Get the waveform data of each slice
            self.dev.tx_txt("WAV:DATA?")
            try:
                recv_rtn = self.dev.rx_arb()
            except ValueError:
                logger.error(f"Unable to transfer binary data from scope ch {ch} at {self.ip}. Check trigger and channel enable")
                return [], []
            #Splice each waveform data 
            recv_chunks.append(recv_rtn)
        recv_byte = b''.join(recv_chunks)
        print(len(recv_byte))
        logger.info(f"CH {ch} binary data transfer took {time.time() - transfer_start_t:.4f} s")
        # Read the data preamble:
        self.dev.tx_txt(":WAVeform:PREamble?")
        preamble = self.dev.rx_arb()
        # Extract the waveform description from the preamble:
        vdiv, ofst, interval, trdl, tdiv, vcode_per, adc_bit = self.main_desc(preamble)
        self.sample_rate = 1/interval
        self.offset = ofst
        self.delay = -(float(tdiv) * HORI_NUM / 2)+trdl #sign to maintain consistency with previous rigol scopes
        self.vdiv = vdiv
        # Unpack signed byte data.
        conversion_start_t = time.time()
        if adc_bit > 8:
            convert_data = struct.unpack("%dh"%points, recv_byte)
        
        else:
            convert_data = struct.unpack("%db"%points, recv_byte)
        del recv_byte
        gc.collect()

        #Calculate the voltage value and time value
        time_start = - (float(tdiv) * HORI_NUM / 2) + float(trdl)
        
        if time_return:
            volt_value = np.array(convert_data) / vcode_per * float(vdiv) - float(ofst)
            logger.info(f"CH {ch} data conversion took {time.time() - conversion_start_t:.4f} s")
            #for idx in range(0, len(convert_data)):
            #    time_data = - (float(tdiv) * HORI_NUM / 2) + idx * interval + float(trdl)
            #    time_value.append(time_data)
            time_value = np.linspace(time_start, time_start+len(convert_data)*interval, len(convert_data))
            print(f"transfer for ch {ch} took {time.time()-start_t} s")
            return np.array(time_value).astype(np.float32), np.array(volt_value).astype(np.float32)
        else:
            volt_value = np.array(convert_data) / vcode_per * float(vdiv) - float(ofst)
            logger.info(f"CH {ch} data conversion took {time.time() - conversion_start_t:.4f} s")
            print(f"transfer for ch {ch} took {time.time()-start_t} s")
            return volt_value.astype(np.float32)
        #print(str(self.ip) + ": volts per division of ch {:} : {:}".format(ch, vdiv))
        #print(str(self.ip) + ": vertical offset of ch {:} : {:}".format(ch, ofst))
        

    def get_all_ch_waveform(self, logger):
        self.time_base, self.data_ch1 = self.get_waveform(logger, ch=1, time_return=True)
        self.data_ch2 = self.get_waveform(logger, ch=2)
        self.data_ch3 = self.get_waveform(logger, ch=3)
        self.data_ch4 = self.get_waveform(logger, ch=4)
    
    def plot_all_ch(self):
        
        fig = plt.figure(figsize=(10, 8))
        plt.plot(self.time_base, self.data_ch1, label="ch1")
        plt.plot(self.time_base, self.data_ch2, label="ch2")
        plt.plot(self.time_base, self.data_ch3, label="ch3")
        plt.plot(self.time_base, self.data_ch4, label="ch4")
        
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1), frameon=False)
        
        plt.title(self.ip)
        
        plt.savefig("/home/whamdata/WHAM_Data/data_saving/" + str(self.device_node) + ".png")
        plt.close(fig)
        print("Made all channel plots for " + self.ip)

    def write_mdsplus(self, logger):
        # No remote connection to MDSplus is provided so create a new one

        # Establish new remote connection to MDSplus
        conn = connection.Connection(self.mdsplus_server) # Connect to MDSplus server (andrew)
        
        # Open the tree
        conn.openTree(self.mdsplus_tree, self.shot_num)

        # Get the current shot number
        self.shot_num = conn.get('$shot')
        logger.info(f"Current shot number {self.shot_num}")

        time.sleep(0.1)
        # Write the data
        msg1 = "Writing data to shot number: " + self.shot_num
        msg2 = "Writing data to node: " + self.device_node

        print(msg1) 
        print(msg2)
        logger.info(msg1)
        logger.info(msg2)
        # iterate through each channel and write the data
        data_chs = [self.data_ch1, self.data_ch2, self.data_ch3, self.data_ch4]
        for ch in [1,2,3,4]: 
            try:
                start_t = time.time()
                # Write (put) the data to the device in MDSplus
                conn.put(self.device_node+".CH_0" + str(ch) + ":SIGNAL", "$", data_chs[ch-1])
                conn.put(self.device_node+".CH_0" + str(ch) + ":FREQ", "$",  self.sample_rate)
                conn.put(self.device_node+".CH_0" + str(ch) + ":OFFSET", "$", self.offset)
                conn.put(self.device_node+".CH_0" + str(ch) + ":DELAY", "$", self.delay)
                conn.put(self.device_node+".CH_0" + str(ch) + ":SCALE",  "$", self.vdiv)
                logger.info(f"Finished putting ch{ch} data to MDSPlus from {self.ip}, took {time.time()-start_t} secs")
                self.last_shot = self.shot_num
            except Exception as E:
                print("MDSPlus Error on " + self.ip)
                print(E)
                print("Shot number: {:}".format(self.shot_num))
                logger.error("MDSPlus Error on " + self.ip)
                logger.error(E)
                logger.error("Shot number: {:}".format(self.shot_num))

        # Close the tree and latest shot
        conn.closeTree(self.mdsplus_tree, self.shot_num)

    def write_mdsplusthin(self, logger):
        # Establish new remote connection to MDSplus
        with mdsthin.Connection(self.mdsplus_server) as conn:
            logger.info(f"Connected to {self.mdsplus_server}")
            if self.shot_num == None:
                self.shot_num = 0
            # Open the tree
            conn.openTree(self.mdsplus_tree, self.shot_num)
            # Get the current shot number
            time.sleep(0.1)
            # Write the data
            logger.info(f"Writing to shot number {self.shot_num} from {IP}")
            # iterate through each channel and write the data
            data_chs = [self.data_ch1, self.data_ch2, self.data_ch3, self.data_ch4]
            for ch in [1,2,3,4]: 
                try:
                    start_t = time.time()
                    # Write (put) the data to the device in MDSplus
                    pm = conn.putMany()
                    pm.append(self.device_node+".CH_0" + str(ch) + ":SIGNAL", "$", mdsthin.Float32Array(data_chs[ch-1]))
                    pm.append(self.device_node+".CH_0" + str(ch) + ":FREQ", "$",  self.sample_rate)
                    pm.append(self.device_node+".CH_0" + str(ch) + ":OFFSET", "$", self.offset)
                    pm.append(self.device_node+".CH_0" + str(ch) + ":DELAY", "$", self.delay)
                    pm.append(self.device_node+".CH_0" + str(ch) + ":SCALE",  "$", self.vdiv)
                    pm.execute()
                    logger.info(f"Finished putting ch{ch} data to MDSPlus from {IP}, took {time.time()-start_t} secs")
                    self.last_shot = self.shot_num
                except Exception as E:
                    print("MDSPlus Error on " + self.ip)
                    print(E)
                    print("Shot number: {:}".format(self.shot_num))
                    logger.error("MDSPlus Error on " + self.ip)
                    logger.error(E)
                    logger.error("Shot number: {:}".format(self.shot_num))



    def run(self):
        self.dev.tx_txt("TRIG:RUN")

def put_all_data_siglent(IP, logger=None):
    # Function to read all data from the given scope at IP
    # and then put the data to MDSPlus
    # Meant to be run from an threadpool executor
    #cal_file = "/mnt/n/whamdata/x-ray_cal/Radium_and_co60_240927/" + str(int(time.time())) + "_" + str(n) + ".gz"
    '''
    140.227 - Mason_Scope
    130.231 - TQ_SCOPE
    140.225 - Mason-DS1000 
    130.80 - Mezzanine scope for scintillator and REM ball
    130.81 - DHO1074
    '''
    if logger == None:
        logger = initialize_logger("/home/whamdata/WHAM_Data/logs/siglent_scope.log", IP)
    start_time = time.time()
    print(f"Starting {IP}")
    try:
        scope = siglent_scpi(IP)
    except:
        print(f"{IP} is not connected")
        logger.error(f"{IP} is not connected")
        return
        
    scope.get_all_ch_waveform(logger)
    logger.info(f"Got all channel data from {IP}, took {time.time()-start_time} secs")
    gc.collect()
    scope.shot_num = 0
    scope.write_mdsplus(logger)
    
    scope.run()
    logger.info(f"Scope set to run at {IP}")
    scope.plot_all_ch()
    time_taken = time.time() - start_time
    print(f"Completed {IP}, took {time_taken} s\n")
    logger.info(f"Completed {IP}, took {time_taken} s\n")
    return
        
if __name__ == "__main__":
    IP = "192.168.140.238"
    try:
        os.remove("/home/whamdata/WHAM_Data/logs/siglent_scope_test.log")
    except:
        pass
    logger = initialize_logger("/home/whamdata/WHAM_Data/logs/siglent_scope_test.log", IP)
    put_all_data_siglent(IP, logger)