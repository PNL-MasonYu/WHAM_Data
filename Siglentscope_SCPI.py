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
SIGLENT_LOG_DIR = "/home/whamdata/WHAM_Data/logs"
SIGLENT_LOG_PREFIX = "siglent_scope_"
SIGLENT_LOG_SUFFIX = ".log"
SIGLENT_MAX_LOG_FILES = 10
tdiv_enum = [200e-12,500e-12, 1e-9,\
2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9, 500e-9, \
1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6, 200e-6, 500e-6, \
1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3, \
1, 2, 5, 10, 20, 50, 100, 200, 500, 1000] #enumerated second per division values

######################################################

def format_count_scientific(value):
    return f"{float(value):.6e}"

######################################################

def initialize_logger(path, IP):

# Create a logger for this file.
    logger = logging.getLogger(IP)
    logger.setLevel(logging.DEBUG)
# Capture other warnings
    logging.captureWarnings(True)
# Create a file handler to write to.
    #file_handler = logging.FileHandler("/home/dtacqAdmin/procScripts/logs/postproc_shinethru.log", "w")
    if logger.hasHandlers():
        logger.handlers.clear()
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

def get_current_shot_number(mdsplus_server="andrew.psl.wisc.edu", mdsplus_tree="wham"):
    conn = connection.Connection(mdsplus_server)
    conn.openTree(mdsplus_tree, 0)
    shot_value = conn.get('$shot')
    conn.closeTree(mdsplus_tree, 0)
    try:
        return int(shot_value)
    except (TypeError, ValueError):
        try:
            return int(shot_value.data())
        except Exception:
            return int(str(shot_value).strip())


def build_shot_log_path(shot_num):
    return os.path.join(SIGLENT_LOG_DIR, f"{SIGLENT_LOG_PREFIX}{shot_num}{SIGLENT_LOG_SUFFIX}")


def prune_old_shot_logs(max_logs=SIGLENT_MAX_LOG_FILES):
    try:
        log_files = []
        for file_name in os.listdir(SIGLENT_LOG_DIR):
            if file_name.startswith(SIGLENT_LOG_PREFIX) and file_name.endswith(SIGLENT_LOG_SUFFIX):
                shot_str = file_name[len(SIGLENT_LOG_PREFIX):-len(SIGLENT_LOG_SUFFIX)]
                if shot_str.isdigit():
                    file_path = os.path.join(SIGLENT_LOG_DIR, file_name)
                    if os.path.isfile(file_path):
                        log_files.append(file_path)

        if len(log_files) <= max_logs:
            return

        log_files.sort(key=lambda file_path: os.path.getmtime(file_path))
        for old_log in log_files[:-max_logs]:
            os.remove(old_log)
    except Exception:
        pass

######################################################

class siglent_scpi:
    def __init__(self, IP="192.168.140.227", port=5025, logger=None) -> None:
        
        
        self.ip = IP
        self.shot_num = None
        self.last_shot = None
        
        if self.ip == "192.168.140.227":
            self.device_node = "RAW.MASON_SCOPE"
        if self.ip == "192.168.130.231":
            self.device_node = "RAW.BDUMP_SCOPE" # Repurposed for end loss analyzer current on ch2, Harshaw hard x-ray scintillator on ch3
        if self.ip == "192.168.140.59":
            self.device_node = "RAW.TRIPRO_SCOPE"
        if self.ip == "192.168.130.89":
            self.device_node = "RAW.TRIPR2_SCOPE"
        if self.ip == "192.168.130.90":
            self.device_node = "RAW.DIAG_SCOPE10"
        if self.ip == "192.168.140.155":
            self.device_node = "RAW.RHODIUMSCOPE"
            for n in range(110):
                if not logger == None:
                    logger.info(f"wait {n} seconds")
                print(f"wait {n} seconds")
                time.sleep(1)
            # Use longer timeout and aggressive retries for RHODIUM scope after long acquisition
            # The scope may briefly reject TCP connections during ARM->READY transition
            # IMPORTANT: Must complete within ~25s to fit in 180s shot cycle
            timeout = 2
            connection_retries = 7  # ~15s total with exponential backoff (capped at 5s)
            retry_delay_base = 0.5
        else:
            timeout = 10
            connection_retries = 1
            retry_delay_base = 0.5

        # Retry connection logic to handle scopes that need time to be ready
        self.dev = None
        for attempt in range(connection_retries):
            try:
                self.dev = scpi(IP, timeout=timeout, port=port)
                if logger is not None:
                    logger.info(f"Successfully connected to {IP} on attempt {attempt + 1}")
                break
            except Exception as e:
                if logger is not None:
                    logger.warning(f"Connection attempt {attempt + 1} failed for {IP}: {e}")
                if attempt < connection_retries - 1:
                    # Use exponential backoff for RHODIUM, fixed delay for others
                    if self.ip == "192.168.140.155":
                        wait_time = retry_delay_base * (1.5 ** attempt)  # Exponential growth
                        # Cap at 5 seconds per retry to stay within shot cycle
                        wait_time = min(wait_time, 5)
                    else:
                        wait_time = retry_delay_base
                    if logger is not None:
                        logger.info(f"Retrying connection in {wait_time:.1f} seconds... (attempt {attempt + 1}/{connection_retries})")
                    time.sleep(wait_time)
                else:
                    if logger is not None:
                        logger.error(f"Failed to connect to {IP} after {connection_retries} attempts")
                    raise

        self.dev.delimiter = '\n'
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

    def main_desc(self, recv, logger):
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
        logger.info(
            f"Data bytes: {format_count_scientific(data_bytes)}, "
            f"Point num: {format_count_scientific(point_num)}, "
            f"First point: {format_count_scientific(fp)}, "
            f"Sample points: {format_count_scientific(sp)}, "
            f"Interval: {interval}, Delay: {delay}, tdiv index: {tdiv_index}, "
            f"Probe: {probe}, Vdiv: {vdiv}, Offset: {offset}, Code per div: {code}, ADC bit: {adc_bit}"
        )
        return vdiv, offset, interval, delay, tdiv, code, adc_bit, fp

    def wait_for_ready_and_stop(self, logger, timeout_s=5.0, poll_s=0.2):
        deadline = time.time() + timeout_s
        last_status = None

        while time.time() < deadline:
            try:
                last_status = self.dev.txrx_txt(":TRIGger:STATus?").strip()
                if last_status.lower() == "ready":
                    break
            except Exception as error:
                if logger is not None:
                    logger.debug(f"TRIGger:STATus? failed at {self.ip}: {error}")
            time.sleep(poll_s)

        if logger is not None:
            logger.info(f"Scope status before stop at {self.ip}: {last_status}")

        self.dev.tx_txt(":TRIG:STOP")

    def get_waveform(self, logger, ch=1, time_return=False):
        """
        Transfer the data from ch on the scope to the host computer
        """
        start_t = time.time()
        
        # Freeze the current acquisition before reading any channel data.
        self.wait_for_ready_and_stop(logger)

        self.dev.tx_txt(f":WAVeform:SOURce C{ch}")
        #self.dev.tx_txt(":WAV:FORM ASCii")
        self.dev.tx_txt(":WAV:STAR 0")
        one_piece_num = int(float(self.dev.txrx_txt(":WAVeform:MAXPoint?").strip())/2)
        points = int(float(self.dev.txrx_txt(":ACQuire:POINts?").strip()))
        logger.info(f"CH {ch} waveform transfer diagnostics: max points per slice {format_count_scientific(one_piece_num)}, total points {format_count_scientific(points)}")
        print(f"maximum points read by a single slice {one_piece_num}")
        print(f"total number of points in waveform {points}")
        read_times = math.ceil(points / one_piece_num)
        print(f"Need to read data in {read_times} chunks")
        if points > one_piece_num:
            self.dev.tx_txt(":WAVeform:POINt {}".format(one_piece_num))
        # We use 12 bit scopes, so the data must be transferred as 2 byte words
        self.dev.tx_txt("WAVeform:WIDTh WORD")

        # Read preamble before chunk loop so first_point is not overwritten by the final chunk start index
        self.dev.tx_txt(":WAVeform:PREamble?")
        preamble = self.dev.rx_arb_optimized()
        vdiv, ofst, interval, trdl, tdiv, vcode_per, adc_bit, first_point = self.main_desc(preamble, logger)
        self.sample_rate = 1/interval
        self.offset = ofst
        self.delay = -(float(tdiv) * HORI_NUM / 2)+trdl #sign to maintain consistency with previous rigol scopes
        self.vdiv = vdiv
        expected_trigger_index = int(round(((float(tdiv) * HORI_NUM / 2) - float(trdl)) / interval))
        logger.info(
            f"CH {ch} trigger index diagnostics: expected index {format_count_scientific(expected_trigger_index)}, "
            f"preamble first_point {format_count_scientific(first_point)}, "
            f"points {format_count_scientific(points)}"
        )
        
        # Read the raw data from the scope in chunks
        recv_chunks = []
        transfer_start_t = time.time()
        bytes_per_point = 2
        for i in range(0, read_times):
            start = i * one_piece_num
            points_this_slice = min(one_piece_num, points - start)
            stop = start + points_this_slice - 1
            #Set the start/stop point of each slice
            self.dev.tx_txt(":WAVeform:STARt {}".format(int(start)))
            self.dev.tx_txt(":WAVeform:STOP {}".format(int(stop)))
            #Get the waveform data of each slice
            self.dev.tx_txt("WAV:DATA?")
            logger.info(f"Started binary data transfer for ch {ch} slice {i+1}/{read_times} at {self.ip}")
            try:
                recv_rtn = self.dev.rx_arb_optimized()
            except ValueError:
                logger.error(f"Unable to transfer binary data from scope ch {ch} at {self.ip}. Check trigger and channel enable")
                return [], []
            expected_bytes = int(points_this_slice) * bytes_per_point
            if len(recv_rtn) != expected_bytes:
                logger.warning(
                    f"CH {ch} slice {i+1}/{read_times} expected {format_count_scientific(expected_bytes)} bytes, "
                    f"got {format_count_scientific(len(recv_rtn))} bytes"
                )
                # If we got 0 bytes, the socket/channel likely failed - abort channel
                if len(recv_rtn) == 0:
                    logger.error(f"CH {ch} slice {i+1}/{read_times} returned 0 bytes - channel transfer failed")
                    return [], []
            #Splice each waveform data 
            recv_chunks.append(recv_rtn)
        recv_byte = b''.join(recv_chunks)
        print(len(recv_byte))
        logger.info(f"CH {ch} binary data transfer took {time.time() - transfer_start_t:.4f} s")
        # Unpack signed byte data.
        conversion_start_t = time.time()
        expected_total_bytes = points * bytes_per_point
        if len(recv_byte) != expected_total_bytes:
            logger.warning(
                f"CH {ch} expected total {format_count_scientific(expected_total_bytes)} bytes, "
                f"received {format_count_scientific(len(recv_byte))} bytes"
            )
        if adc_bit > 8:
            convert_data = np.frombuffer(recv_byte, dtype=np.int16)
        else:
            convert_data = np.frombuffer(recv_byte, dtype=np.int8)

        if len(convert_data) > points:
            convert_data = convert_data[:points]
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
            time_value = time_start + np.arange(len(convert_data)) * interval
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
        ch1_result = self.get_waveform(logger, ch=1, time_return=True)
        if isinstance(ch1_result, tuple) and len(ch1_result) == 2 and len(ch1_result[0]) > 0 and len(ch1_result[1]) > 0:
            self.time_base, self.data_ch1 = ch1_result
        else:
            self.time_base, self.data_ch1 = None, None
        # Add inter-channel delay for RHODIUM scope to prevent buffer exhaustion
        if self.ip == "192.168.140.155":
            time.sleep(0.5)
        ch2_result = self.get_waveform(logger, ch=2)
        self.data_ch2 = ch2_result if np.size(ch2_result) > 0 else None
        if self.ip == "192.168.140.155":
            time.sleep(0.5)
        ch3_result = self.get_waveform(logger, ch=3)
        self.data_ch3 = ch3_result if np.size(ch3_result) > 0 else None
        if self.ip == "192.168.140.155":
            time.sleep(0.5)
        ch4_result = self.get_waveform(logger, ch=4)
        self.data_ch4 = ch4_result if np.size(ch4_result) > 0 else None
    
    def plot_all_ch(self):
        
        fig = plt.figure(figsize=(10, 8))
        if self.time_base is not None and self.data_ch1 is not None and np.size(self.time_base) == np.size(self.data_ch1):
            plt.plot(self.time_base, self.data_ch1, label="ch1")
        if self.time_base is not None and self.data_ch2 is not None and np.size(self.time_base) == np.size(self.data_ch2):
            plt.plot(self.time_base, self.data_ch2, label="ch2")
        if self.time_base is not None and self.data_ch3 is not None and np.size(self.time_base) == np.size(self.data_ch3):
            plt.plot(self.time_base, self.data_ch3, label="ch3")
        if self.time_base is not None and self.data_ch4 is not None and np.size(self.time_base) == np.size(self.data_ch4):
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
                # Skip channels that failed to acquire (None / empty)
                if data_chs[ch-1] is None or np.size(data_chs[ch-1]) == 0:
                    logger.warning(f"CH {ch} has no data, skipping MDSplus write")
                    continue

                if self.time_base is not None and np.size(self.time_base) == np.size(data_chs[ch-1]):
                    time_axis = self.time_base
                else:
                    time_axis = np.arange(np.size(data_chs[ch-1]), dtype=np.float32) / float(self.sample_rate)
                    
                start_t = time.time()
                # Write the data as a signal with a real time axis in seconds
                conn.put(
                    self.device_node+".CH_0" + str(ch) + ":SIGNAL",
                    "BUILD_SIGNAL($,*,BUILD_WITH_UNITS($,'seconds'))",
                    data_chs[ch-1],
                    time_axis,
                )
                conn.put(self.device_node+".CH_0" + str(ch) + ":FREQ", "$",  self.sample_rate)
                conn.put(self.device_node+".CH_0" + str(ch) + ":OFFSET", "$", self.offset)
                conn.put(self.device_node+".CH_0" + str(ch) + ":DELAY", "$", self.delay)
                conn.put(self.device_node+".CH_0" + str(ch) + ":SCALE",  "$", self.vdiv)
                logger.info(f"Finished putting ch{ch} data to MDSPlus from {self.ip}, took {time.time()-start_t} secs")
                self.last_shot = self.shot_num
            except Exception as E:
                self.set_normal_trigger_and_run(logger)
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
            logger.info(f"Writing to shot number {self.shot_num} from {self.ip}")
            # iterate through each channel and write the data
            data_chs = [self.data_ch1, self.data_ch2, self.data_ch3, self.data_ch4]
            for ch in [1,2,3,4]: 
                try:
                    if data_chs[ch-1] is None or np.size(data_chs[ch-1]) == 0:
                        logger.warning(f"CH {ch} has no data, skipping MDSplus write")
                        continue

                    if self.time_base is not None and np.size(self.time_base) == np.size(data_chs[ch-1]):
                        time_axis = self.time_base
                    else:
                        time_axis = np.arange(np.size(data_chs[ch-1]), dtype=np.float32) / float(self.sample_rate)

                    start_t = time.time()
                    # Write (put) the data to the device in MDSplus
                    pm = conn.putMany()
                    pm.append(
                        self.device_node+".CH_0" + str(ch) + ":SIGNAL",
                        "BUILD_SIGNAL($,*,BUILD_WITH_UNITS($,'seconds'))",
                        mdsthin.Float32Array(data_chs[ch-1]),
                        mdsthin.Float32Array(time_axis),
                    )
                    pm.append(self.device_node+".CH_0" + str(ch) + ":FREQ", "$",  self.sample_rate)
                    pm.append(self.device_node+".CH_0" + str(ch) + ":OFFSET", "$", self.offset)
                    pm.append(self.device_node+".CH_0" + str(ch) + ":DELAY", "$", self.delay)
                    pm.append(self.device_node+".CH_0" + str(ch) + ":SCALE",  "$", self.vdiv)
                    pm.execute()
                    logger.info(f"Finished putting ch{ch} data to MDSPlus from {self.ip}, took {time.time()-start_t} secs")
                    self.last_shot = self.shot_num
                except Exception as E:
                    self.set_normal_trigger_and_run(logger)
                    print("MDSPlus Error on " + self.ip)
                    print(E)
                    print("Shot number: {:}".format(self.shot_num))
                    logger.error("MDSPlus Error on " + self.ip)
                    logger.error(E)
                    logger.error("Shot number: {:}".format(self.shot_num))



    def run(self):
        self.dev.tx_txt("TRIG:RUN")

    def set_normal_trigger_and_run(self, logger=None):
        try:
            self.dev.tx_txt(":TRIGger:MODE NORMal")
            self.dev.tx_txt("TRIG:RUN")
            if logger is not None:
                logger.info(f"Scope trigger mode set to NORMal and RUN at {self.ip}")
        except Exception as error:
            if logger is not None:
                logger.error(f"Failed to set trigger mode NORMal and RUN at {self.ip}: {error}")

def put_all_data_siglent(IP, logger=None):
    # Function to read all data from the given scope at IP
    # and then put the data to MDSPlus
    # Meant to be run from an threadpool executor
    #cal_file = "/mnt/n/whamdata/x-ray_cal/Radium_and_co60_240927/" + str(int(time.time())) + "_" + str(n) + ".gz"
    '''
    140.227 - Mason_Scope
    130.231 - TQ_SCOPE
    140.225 - Mason-DS1000 
    140.238 - BDUMP_SCOPE
    130.80 - Mezzanine scope for scintillator and REM ball
    130.81 - DHO1074
    '''
    shot_num = None
    if logger == None:
        try:
            shot_num = get_current_shot_number()
        except Exception:
            shot_num = 0
        logger = initialize_logger(build_shot_log_path(shot_num), IP)
        prune_old_shot_logs()
    start_time = time.time()
    print(f"Starting {IP}")
    scope = None
    try:
        scope = siglent_scpi(IP)
    except Exception as e:
        print(f"{IP} is not connected")
        logger.error(f"{IP} is not connected")
        logger.error(e)
        return
    try:
        scope.get_all_ch_waveform(logger)
        logger.info(f"Got all channel data from {IP}, took {time.time()-start_time} secs")
        gc.collect()
        scope.shot_num = shot_num if shot_num is not None else 0
        scope.write_mdsplus(logger)
        scope.plot_all_ch()
        time_taken = time.time() - start_time
        print(f"Completed {IP}, took {time_taken} s\n")
        logger.info(f"Completed {IP}, took {time_taken} s\n")
    except Exception as e:
        logger.error(f"Error during Siglent acquisition/write for {IP}: {e}")
    finally:
        if scope is not None:
            scope.set_normal_trigger_and_run(logger)
    return
        
if __name__ == "__main__":
    IP = "192.168.130.89"
    put_all_data_siglent(IP)