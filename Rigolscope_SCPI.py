from redpitaya_scpi import scpi
import logging, datetime
from MDSplus import connection
import numpy as np
import time
import matplotlib.pyplot as plt
import concurrent.futures
import matplotlib
import os
import gc
from Siglentscope_SCPI import put_all_data_siglent
matplotlib.use('agg')


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

class rigol_scpi:
    def __init__(self, IP="192.168.130.227", port=5555) -> None:
        
        self.dev = scpi(IP, port=port)
        self.dev.delimiter = '\n'
        self.ip = IP
        self.shot_num = None
        self.last_shot = None

        if self.ip == "192.168.140.227":
            self.device_node = "RAW.MASON_SCOPE"
        if self.ip == "192.168.130.231":
            self.device_node = "RAW.TQ_SCOPE"
        if self.ip == "192.168.140.225":
            self.device_node = "RAW.MASON_DS1000"
        if self.ip == "192.168.130.78":
            self.device_node = "RAW.GAS_SCOPE" 
        if self.ip == "192.168.130.80":
            self.device_node = "RAW.MEZZ_SCOPE"
        if self.ip == "192.168.130.81":
            self.device_node = "RAW.SCOPE_1074"
        if self.ip == "192.168.140.228":
            self.device_node = "RAW.DIAG_SCOPE_1"
        if self.ip == "192.168.140.229":
            self.device_node = "RAW.DIAG_SCOPE_2"
        if self.ip == "192.168.140.230":
            self.device_node = "RAW.DIAG_SCOPE_3"
        if self.ip == "192.168.140.150":
            self.device_node = "RAW.NEUTRONSCOPE"
        if self.ip == "192.168.140.238":
            self.device_node = "RAW.BDUMP_SCOPE"
        
                    
        
        self.mdsplus_server = "andrew.psl.wisc.edu"
        #self.mdsplus_server = "192.168.130.236" #jack
        self.mdsplus_tree = "wham"
        self.data_ch1 = None
        self.data_ch2 = None
        self.data_ch3 = None
        self.data_ch4 = None
        self.offset = 0.0  # time base offset in seconds
        self.timescale = 10.0  # time base scale in seconds per division (10 div total)
        self.delay = 0.0  # This is number of ms from trigger edge to start of pulse
        self.sample_rate = 1.05
        
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
        del buff_byte1
        volts_per_division = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":SCALe?"))
        vertical_position = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":POSition?"))
        vertical_offset = self.get_vertical_offset(ch=ch)
        data = np.array(rawdata) / 65535.0 * volts_per_division * 9.0
        data = data - volts_per_division * 4.5 - vertical_offset
        del rawdata
        gc.collect()
        print(str(self.ip) + ": volts per division of ch {:} : {:}".format(ch, volts_per_division))
        print(str(self.ip) + ": vertical position of ch {:} : {:}".format(ch, vertical_position))
        print(str(self.ip) + ": vertical offset of ch {:} : {:}".format(ch, vertical_offset))
        return data

    def get_waveform_chunks(self, ch=1, chunks=1000):
        """
        Transfer the waveform data on the scope back to the computer, but done in discrete chunks
        Used for older rigol scopes that does not have sufficient memory, like the DS1000
        """
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
        volts_per_division = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":SCALe?"))
        #vertical_position = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":POSition?"))
        #vertical_offset = self.get_vertical_offset(ch=ch)
        data = np.array(rawdata) / 65535.0 * volts_per_division * 8.0 - volts_per_division * 4.0
        print(str(self.ip) + " volts per division of ch {:} : {:}".format(ch, volts_per_division))
        #print("vertical position of ch {:} : {:}".format(ch, vertical_position))
        #print("vertical offset of ch {:} : {:}".format(ch, vertical_offset))
        
        return data
    
    def set_up_channel(self, ch=1):
        self.dev.tx_txt(":ACQuire:MDEPth 50M")
        self.dev.tx_txt(":ACQuire:TYPE NORMal")
        # Sets channel to no bandwidth limit, DC coupling, zero offset, 1 meg impedance
        self.dev.tx_txt(":CHANnel" + str(ch) + ":BWLimit OFF")
        self.dev.tx_txt(":CHANnel" + str(ch) + ":COUPling DC")
        self.dev.tx_txt(":CHANnel" + str(ch) + ":OFFSet 0")
        self.dev.tx_txt(":CHANnel" + str(ch) + ":IMPedance OMEG")
        """
        if self.ip == "192.168.140.225" and ch == 2:
            self.dev.tx_txt(":CHANnel" + str(ch) + ":SCALe 0.3")
            self.dev.tx_txt(":TIMebase:MAIN:SCALe 0.1")
            self.dev.tx_txt(":TIMebase:MAIN:OFFSet -0.5")
            self.dev.tx_txt(":CHANnel" + str(ch) + ":OFFSet -0.7")       
        """     
        
        
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
        # This is the delay from start of data to trigger position in seconds
        #trig_pos = self.dev.txrx_txt(":TRIGger:POSition?")
        #print("Trigger position: " + trig_pos)
        #timebase_offset = self.dev.txrx_txt(":TIMebase:MAIN:OFFSet?")
        #print("Timebase offset: " + timebase_offset)
        x_origin = self.dev.txrx_txt(":WAVeform:XORigin?")
        #print("X origin: " + x_origin)
        self.delay = float(x_origin)
        return self.delay
    
    def get_vertical_offset(self, ch=1):
        offset = self.dev.txrx_txt(":CHANnel" + str(ch) + ":OFFSet?")
        return float(offset)
    
    def get_vertical_scale(self, ch=1):
        volts_per_division = float(self.dev.txrx_txt(":CHANnel" + str(ch) + ":SCALe?"))
        return volts_per_division
    
    def set_vertical_scale(self, ch=1, volts_per_division = 50e-3):
        self.dev.tx_txt(":CHANnel" + str(ch) + ":SCALe " + float(volts_per_division))

    def write_mdsplus(self, conn, logger):

        # Check that we are not writing to the same shot
        if self.shot_num == self.last_shot:

            print("Overlapping shot number " + str(self.shot_num) + "!")
            logger.error("Overlapping shot number " + str(self.shot_num) + "!")
    
        if self.last_shot == None:
            self.last_shot = self.shot_num
    
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
                start_time = time.time()
                # Write (put) the data to the device in MDSplus
                conn.put(self.device_node+".CH_0" + str(ch) + ":SIGNAL", "$", data_chs[ch-1])
                conn.put(self.device_node+".CH_0" + str(ch) + ":FREQ", "$",  self.get_sampling_rate())
                conn.put(self.device_node+".CH_0" + str(ch) + ":OFFSET", "$", self.get_vertical_offset(ch=ch))
                conn.put(self.device_node+".CH_0" + str(ch) + ":DELAY", "$", self.get_delay())
                conn.put(self.device_node+".CH_0" + str(ch) + ":SCALE",  "$", self.get_vertical_scale(ch=ch))
                #print(f"Put data from {self.ip}:CH{ch} to MDSPlus, took {time.time()-start_time} s")
                logger.info(f"Put data from {self.ip}:CH{ch} to MDSPlus, took {time.time()-start_time} s")
                self.last_shot = self.shot_num
            except Exception as E:
                print("MDSPlus Error on " + self.ip)
                print(E)
                print("Shot number: {:}".format(self.shot_num))
                logger.error("MDSPlus Error on " + self.ip)
                logger.error(E)
                logger.error("Shot number: {:}".format(self.shot_num))

    def _write_mdsplus(self, logger):
        # No remote connection to MDSplus is provided so create a new one
        start_time = time.time()
        # Establish new remote connection to MDSplus
        conn = connection.Connection(self.mdsplus_server) # Connect to MDSplus server (andrew)
        
        # Open the tree
        conn.openTree(self.mdsplus_tree, self.shot_num)
        logger.info(f"Took {time.time()-start_time} to open connection and tree")
        # Get the current shot number
        self.shot_num = conn.get('$shot')
        logger.info(f"Current shot number {self.shot_num}")

        time.sleep(0.1)
        # Write the data
        self.write_mdsplus(conn, logger)

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

    def store_data_local(self, path):
        time_base = np.linspace(0, len(self.data_ch1)/self.get_sampling_rate(), len(self.data_ch1)) - self.get_delay()

    def plot_all_ch(self):
        
        time_base = np.linspace(0, len(self.data_ch1)/self.get_sampling_rate(), len(self.data_ch1)) - self.get_delay()
        fig = plt.figure(figsize=(10, 8))
        plt.plot(time_base, self.data_ch1, label="ch1")
        plt.plot(time_base, self.data_ch2, label="ch2")
        plt.plot(time_base, self.data_ch3, label="ch3")
        plt.plot(time_base, self.data_ch4, label="ch4")
        
        plt.legend()
        
        plt.title(self.ip)
        
        plt.savefig("/home/whamdata/WHAM_Data/data_saving/" + str(self.device_node) + ".png")
        plt.close(fig)
        print("Made all channel plots for " + self.ip)
        
    def run(self):
        self.dev.tx_txt(":RUN")
        
    def force_trig(self):
        self.dev.tx_txt(":TFORce")

    def write_waveform(self, path):
        """
        Write the waveform locally to path as a compressed npz file
        Just write the channels that has meaningful data for now
        """
        np.savez_compressed(path, 
                            ch2 = self.data_ch2.astype(np.float16),
                            ch3 = self.data_ch3.astype(np.float16),
                            ch4 = self.data_ch4.astype(np.float16),
                            )


def put_all_data(IP):
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
    logger = initialize_logger("/home/whamdata/WHAM_Data/logs/rigol_scope.log", IP)
    try:
        start_time = time.time()
        print(f"Starting {IP}")
        scope = rigol_scpi(IP)
    except Exception as error:
        logger.error(f"{IP} is not connected")
        print(error)
        print(f"{IP} is not connected")
        return
        
    if IP == "192.168.130.233":
            scope.get_all_ch_waveform_chunks()
    else:
        #scope.get_waveform(2)
        scope.get_all_ch_waveform()

    logger.info(f"Got raw data from {IP}")

    scope.get_time_scale()
    logger.info(f"Got time scale from {IP}")
    scope.get_vertical_scale()
    logger.info(f"Got vertical scale from {IP}")
    scope.shot_num = 0
    
    scope._write_mdsplus(logger)
    logger.info(f"Wrote to MDSPlus from {IP}")
    scope.run()
    logger.info(f"{IP} running")
    scope.plot_all_ch()
    #scope.write_waveform(cal_file)
    time_taken = time.time() - start_time
    logger.info(f"Completed {IP}, took {time_taken} s\n")
    return
    
if __name__ == "__main__":
    '''
    140.227 - Mason_Scope
    130.231 - TQ_SCOPE
    140.225 - Mason-DS1000 
    130.80 - Mezzanine scope for scintillator and REM ball
    130.81 - DHO1074
    140.228 - DIAG_SCOPE_1
    '''
    try:
        os.remove("/home/whamdata/WHAM_Data/logs/rigol_scope.log")
        os.remove("/home/whamdata/WHAM_Data/logs/siglent_scope.log")
        os.remove("/home/whamdata/WHAM_Data/logs/rigol_continuous.log")
    except:
        pass
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:

        # RIGOL Scopes
        for IP in ["192.168.130.231", 
                   "192.168.130.78", 
                   "192.168.130.80", 
                   "192.168.130.81", 
                   "192.168.140.225", 
                   "192.168.140.228", 
                   "192.168.140.229", 
                   "192.168.140.230", 
                   "192.168.140.227"]:
            executor.submit(put_all_data, IP)

        # Siglent Scopes
        for IP in ["192.168.140.227", 
                   "192.168.140.238"]:
            executor.submit(put_all_data_siglent, IP)
