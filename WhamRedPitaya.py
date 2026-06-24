# %%
from __future__ import print_function
from collections import UserString
import sys, struct, os
import redpitaya_scpi as scpi
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#from MDSplus import * #Connection
from MDSplus import connection
import redpitaya_scpi as scpi

import logging
import time
#import h5py
from datetime import datetime
import RP_PLL

from threading import Thread
from multiprocessing import Process, Manager, Pool



MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

DEVICE_TREE = "NBI.NBI_RAW"
#DEVICE_TREE = "\WHAM::TOP.ECH.ECH_RAW"


IP_LIST = [
    ("rp-f0bd60.local", 5000),
    ("rp-f0bd64.local", 5000),
    ("rp-f0bd40.local", 5000),
    ("rp-f0bd4d.local", 5000)
]



class WhamRedPitayaGroup():

    def __init__(self, num_devices=2, ip_list=IP_LIST, device_tree=None, mdsplus_server=MDSPLUS_SERVER, 
                 mdsplus_tree=MDSPLUS_TREE, device_nodes = [], Trig=None, shot_num=None):

        # Instance variables

        self.num_devices = min(num_devices, len(ip_list)) # If they don't match, take smallest
        self.ip_list = ip_list
        self.device_tree = device_tree
        self.mdsplus_server = mdsplus_server
        self.mdsplus_tree = mdsplus_tree

        # Clear lists
        self.devices_list = []
        self.connected_devices_list = []
        self.threads = []
        self._stored_devices = set()

        self.Trig = Trig
        self.shot_num = shot_num #None is the latest shot

        self._create_devices(device_nodes)

    def _log_device_error(self, stage, device, err):
        ip = "unknown"
        if device is not None:
            ip = getattr(device, "ip", "unknown")
        msg = "{} failed for {}: {}".format(stage, ip, err)
        print(msg)
        logging.error(msg)


    def _get_tree(self):
        # Get list of device nodes in MDSplus tree using MDSplus.connection.Connection and TDI
        pass

    def _populate_tree(self):
        # Create device nodes in MDSplus tree using MDSplus.connection.Connection and TDI
        pass


    def _create_devices(self, device_nodes):

        # Iterate through number of devices
        for d in range(0,self.num_devices):

            # Read device IP and port
            ip = self.ip_list[d][0]
            port = self.ip_list[d][1]

            # Construct MDSplus node path
            if d >= len(device_nodes):
                device_node = ".RP_" + str(d+1).zfill(2)
            else:
                device_node = self.device_tree + ":" + device_nodes[d]

            # Create device object
            #device = WhamRedPitaya(ip=ip, port=port, device_node=device_node, mdsplus_server=self.mdsplus_server, mdsplus_tree=self.mdsplus_tree, useTrig=self.Trig)
            try:
                device = WhamRedPitaya_SCPI(ip=ip, port=port, device_node=device_node, mdsplus_server=self.mdsplus_server, mdsplus_tree=self.mdsplus_tree, Trig=self.Trig, shot_num=self.shot_num)
                self.devices_list.append(device)
            except Exception as e:
                self._log_device_error("Create", None, e)
                self.devices_list.append(None)


    def _connect_device_thread(self, d, connect_timeout):
        device = self.devices_list[d]
        if device is None:
            return
        try:
            device.connect(connect_timeout=connect_timeout)
            self.connected_devices_list[d] = device
        except Exception as e:
            self._log_device_error("Connect", device, e)

    def connect_devices(self, connect_timeout=5):

        # Attempt to establish connections to each device in parallel.
        # Pre-size list so each thread writes to a stable index.
        self.connected_devices_list = [None] * self.num_devices
        connect_threads = []

        # Spawn one connection thread per device.
        for d in range(0, self.num_devices):
            t = Thread(target=self._connect_device_thread, args=(d, connect_timeout))
            t.daemon = True
            connect_threads.append(t)
            t.start()

        # Wait for all connection attempts to complete.
        for t in connect_threads:
            t.join()


    def configure_devices(self):

        # Configure each **connected** device one by one

        # Iterate through list of connected devices
        for i, device in enumerate(self.connected_devices_list):

            if device is None:
                continue
            try:
                device.configure()
            except Exception as e:
                self._log_device_error("Configure", device, e)
                self.connected_devices_list[i] = None

    def _arm_device_thread(self, device, i, arm_results, timeout):
        try:
            ok = device.arm(timeout=timeout)
            arm_results[i] = bool(ok)
            if not ok:
                self._log_device_error("Arm", device, "timeout or trigger failure")
                return

            try:
                device.store()
                self._stored_devices.add(i)
            except Exception as e:
                self._log_device_error("Store", device, e)
        except Exception as e:
            arm_results[i] = False
            self._log_device_error("Arm", device, e)
            logging.exception("Arm traceback for {}".format(device.ip))

    def arm_devices(self, timeout=40):

        # Empty list to manage the threads
        self.threads = []
        arm_results = {}

        # Iterate through list of connected devices
        for i, device in enumerate(self.connected_devices_list):
            if device is None:
                continue
            else:
                print("Creating thread for device at " + device.ip)
                logging.info("Creating thread for device at " + device.ip)
                t = Thread(target=self._arm_device_thread, args=(device, i, arm_results, timeout))
                t.daemon = True
                self.threads.append(t)
                t.start()
                
        # Wait for the threads to complete and join them
        for t in self.threads:
            t.join()

        finished = []
        failed = []
        for i, device in enumerate(self.connected_devices_list):
            if device is None:
                continue
            if i not in arm_results or not arm_results[i]:
                failed.append(device.ip)
                self.connected_devices_list[i] = None
            else:
                finished.append(device.ip)

        summary = "Arm threads complete: {} finished, {} failed".format(len(finished), len(failed))
        print(summary)
        logging.info(summary)
        if finished:
            logging.info("Arm finished devices: {}".format(", ".join(finished)))
        if failed:
            logging.info("Arm failed devices: {}".format(", ".join(failed)))


    def store_data(self):

        timeStart = time.time()

        for i, device in enumerate(self.connected_devices_list):
            if device is None:
                continue
            if i in self._stored_devices:
                continue
            try:
                device.store()
                self._stored_devices.add(i)
            except Exception as e:
                self._log_device_error("Store", device, e)
                self.connected_devices_list[i] = None

        print('Total elapsed time for store_data threads = {}'.format(time.time() - timeStart))
        logging.info('Total elapsed time for store_data threads = {}'.format(time.time() - timeStart))
        logging.info("Store stage complete: {} devices written".format(len(self._stored_devices)))
# Wrapper function for device.store()
def store_data(device):
    if device is None:
        return None
    return device.store()
    



class WhamRedPitaya_SCPI():
    def __init__(self, ip, port=5000, device_node=DEVICE_TREE+".NBI_RP_01", mdsplus_server = MDSPLUS_SERVER, mdsplus_tree = MDSPLUS_TREE, Trig=None, shot_num=0) -> None:

        self.device_node = device_node # The name of the node to write data to. Should be something like "ECH:ECH_RAW:RP_1"

        self.ip = ip
        self.port = port #5000 by default

        self.last_shot = None

        self.mdsplus_server = mdsplus_server # server running mdsplus
        self.mdsplus_tree = mdsplus_tree # name of top mdsplus tree (should always be "wham")

        self.fs = 125e6 # clock speed, use downsample_value to change sample rate

        self.downsample_value = 1 # change from 125 MHz

        self.n_pts = 1e7 # number of samples per channel
        self.channel = 3 # 1 or 2 or 3 for both

        self.dev = None
        self.data_ch1 = None
        self.data_ch2 = None

        TRIG_SOURCES = ["DISABLED", "NOW", "CH1_PE", "CH1_NE", "CH2_PE", "CH2_NE", "EXT_PE", "EXT_NE", "AWG_PE", "AWG_NE"]

        if Trig == None:
            self.trig = "NOW"
        elif Trig not in TRIG_SOURCES:
            print(self.trig + " not in list of possible trigger sources, default to NOW")
            logging.error(self.trig + " not in list of possible trigger sources, default to NOW")
            self.trig = "NOW"
        else:
            self.trig = Trig
        self.trig_level = 0

        self.bSave = 0
        self.bPlot = 1
        self.bMDS = 1

        self.verbosity = 1

        self.shot_num = shot_num

    def connect(self, connect_timeout=5):
        if self.verbosity > 0:
            print("Connecting to device at " + self.ip + " on port " + str(self.port) + ".")
            logging.info("Connecting to device at " + self.ip + " on port " + str(self.port) + ".")
        try:
            self.dev = scpi.scpi(self.ip, timeout=connect_timeout)
            self.dev.tx_txt('ACQ:RST')
            self.dev.check_error()
        except Exception as e:
            raise WhamRedPitayaConnectionError("Unable to connect to {}:{} ({})".format(self.ip, self.port, e))
        #self.dev.tx_txt('ACQ:RST')

    def configure(self):
        self.dev.tx_txt('ACQ:RST')
        self.dev.check_error()
        
        # make sure downsample_value is between 1 and 2^32
        self.downsample_value = min(2**32,self.downsample_value)
        self.downsample_value = max(1,self.downsample_value)
        
        self.dev.tx_txt('ACQ:DATA:FORMAT BIN')
        self.dev.tx_txt('ACQ:AXI:DATA:UNITS VOLTS')
        self.dev.tx_txt('ACQ:SOUR1:GAIN HV')
        self.dev.tx_txt('ACQ:SOUR2:GAIN HV')
        if self.verbosity > 0:
            rec_str = 'ACQ:AXI:DATA:UNITS?: ',self.dev.txrx_txt('ACQ:AXI:DATA:UNITS?')
            print(rec_str)
            logging.info(rec_str)
            rec_str = 'ACQ:SOUR1:GAIN?: ',self.dev.txrx_txt('ACQ:SOUR1:GAIN?')
            print(rec_str)
            logging.info(rec_str)
            rec_str = 'ACQ:SOUR2:GAIN?: ',self.dev.txrx_txt('ACQ:SOUR2:GAIN?')
            print(rec_str)
            logging.info(rec_str)

        self.dev.check_error()
        
        # Set the decimation valueConnection
        self.dev.tx_txt('ACQ:AXI:DEC ' + str(int(self.downsample_value)))
        if self.verbosity > 0:
            rec_str = 'ACQ:AXI:DEC?: ',self.dev.txrx_txt('ACQ:AXI:DEC?')
            print(rec_str)
            logging.info(rec_str)
        self.dev.check_error()

        # Get AXI start address and size of buffer
        start = int(self.dev.txrx_txt('ACQ:AXI:START?'))
        size = int(self.dev.txrx_txt('ACQ:AXI:SIZE?'))
        if self.verbosity > 0:
            print(self.ip + ' :ACQ:AXI:START?: ' + str(start))
            logging.info(self.ip + ' :ACQ:AXI:START?: ' + str(start))
            print(self.ip + ' :ACQ:AXI:SIZE?: ' + str(size))
            logging.info(self.ip + ' :ACQ:AXI:SIZE?: ' + str(size))
        #if self.n_pts > (size // 2): #2 bytes per data point
        #    print("too many data points, truncating from {:.3e} to {:.3e} points".format(self.n_pts, (size // 2)))
        #    self.n_pts = (size // 2)
        self.dev.check_error()

        if self.verbosity > 0:
            print("Start address ",start," size of avialable memory ",size)
            logging.info("Start address "+ str(start) +" size of avialable memory "+ str(size))
            print("Number of samples to capture per channel " + str(self.n_pts))
            logging.info("Number of samples to capture per channel " + str(self.n_pts))

        # Specify the buffer sizes in bytes for the first and second channels
        add_str_ch1 = 'ACQ:AXI:SOUR1:SET:Buffer ' + str(start) + ',' + str(size//2)
        add_str_ch2 = 'ACQ:AXI:SOUR2:SET:Buffer ' + str(start + size//2) + ',' + str(size//2)
        if self.verbosity > 0:
            print("set channel 1 address: " + add_str_ch1)
            logging.info("set channel 1 address: " + add_str_ch1)
            print("set channel 2 address: " + add_str_ch2)
            logging.info("set channel 2 address: " + add_str_ch2)

        self.dev.tx_txt(add_str_ch1)
        self.dev.tx_txt(add_str_ch2)
        self.dev.check_error()

        # You need to specify the number of samples after the trigger
        self.dev.tx_txt('ACQ:AXI:SOUR1:Trig:Dly '+ str(int(self.n_pts)))
        self.dev.tx_txt('ACQ:AXI:SOUR2:Trig:Dly '+ str(int(self.n_pts)))
        self.dev.check_error()
        if self.verbosity > 0:
            rec_str = "channel 1 number of samples after trig: " + self.dev.txrx_txt('ACQ:AXI:SOUR1:Trig:Dly?')
            print(rec_str)
            logging.info(rec_str)
            rec_str = "channel 2 number of samples after trig: " + self.dev.txrx_txt('ACQ:AXI:SOUR2:Trig:Dly?')
            print(rec_str)
            logging.info(rec_str)

        self.dev.tx_txt('ACQ:AXI:SOUR1:ENable ON')
        self.dev.tx_txt('ACQ:AXI:SOUR2:ENable ON')
        self.dev.check_error()
    
    def arm(self, timeout=40):
        # set the digital trigger pin to input only
        self.dev.tx_txt('DIG:PIN:DIR IN,DIO0_P')
        acq_start_time = time.time()
        # set start
        self.dev.tx_txt('ACQ:START')

        self.dev.tx_txt('ACQ:TRIG ' + self.trig)
        if not (self.trig == "EXT_NE" or self.trig == "EXT_PE"):
            self.dev.tx_txt('ACQ:TRIG:LEV ' + str(self.trig_level))
        else:
            self.dev.tx_txt('ACQ:TRig:EXT:DEBouncer:US 200')
            #self.dev.tx_txt('ACQ:TRig:EXT:LEV 1')
        self.dev.check_error()
    
        duration = self.n_pts/(self.fs/self.downsample_value)
        acq_msg = "{} acquiring for {} ms (n_pts={}, dec={})".format(
            self.ip,
            duration*1000,
            int(self.n_pts),
            int(self.downsample_value),
        )
        print(acq_msg)
        logging.info(acq_msg)
        start_time = time.time()
        while 1:
            self.dev.tx_txt('ACQ:AXI:SOUR1:TRIG:FILL?')
            time.sleep(0.1)
            if self.dev.rx_txt() == '1':
                break
            if time.time() - start_time > timeout:
                print("Timeout reached on {} while waiting for CH1 trigger fill".format(self.ip))
                logging.info("Timeout reached on {} while waiting for CH1 trigger fill".format(self.ip))
                return False
        while 1:
            self.dev.tx_txt('ACQ:AXI:SOUR2:TRIG:FILL?')
            time.sleep(0.1)
            if self.dev.rx_txt() == '1':
                break
            if time.time() - start_time > timeout:
                print("Timeout reached on {} while waiting for CH2 trigger fill".format(self.ip))
                logging.info("Timeout reached on {} while waiting for CH2 trigger fill".format(self.ip))
                return False

        print("All data captured on " + self.ip)
        logging.info("All data captured on " + self.ip)
        logging.info(f"Waited for {time.time()-acq_start_time} seconds")
        self.dev.tx_txt('ACQ:STOP')

        self._read()
        return True


    def _read(self):

                
        print("Start receiving data")
        timeStart = time.time()
        # It is quite difficult for the server to transfer a large amount of data at once, and there may not be enough memory with a very large capture buffer. 
        # Therefore, we request data from the server in parts

        if self.channel == 1 or self.channel == 2:
            # single channel receiving, TODO: debug
            received_size = 0
            block_size = 2**18  #50000
            buff_all = []
            trig = int(self.dev.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?'))

            while received_size < self.n_pts:
                if (received_size + block_size) > self.n_pts:
                    block_size = self.n_pts - received_size

                self.dev.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig)+',' + str(block_size))
                buff_byte = self.dev.rx_arb()
                if buff_byte == False:
                    continue
                buff = [struct.unpack('!f',bytearray(buff_byte[i:i+4]))[0] for i in range(0, len(buff_byte), 4)]
                buff_all = np.append(buff_all, buff)
                trig += block_size
                trig = trig % self.n_pts
                received_size += block_size
            if self.channel == 1: self.data_ch1 = buff_all
            if self.channel == 2: self.data_ch2 = buff_all
        
        if self.channel == 3:
            # dual channel receiving, TODO: debug
            trig_ch1 = int(self.dev.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?'))
            trig_ch2 = int(self.dev.txrx_txt('ACQ:AXI:SOUR2:Trig:Pos?'))
            # Binary data receiving
            
            buff_all1 = []
            buff_all2 = []
            block_size = 2**18  #self.n_pts // 2
            received_size = 0
            while received_size < self.n_pts:
                # Check if the block size would bring us over the total number of points
                if (received_size + block_size) >= self.n_pts:
                    # minus one to get rid of one excess data point
                    block_size = self.n_pts - received_size - 1
                    received_size = self.n_pts
                else:
                    # update received data size
                    received_size += block_size
                self.dev.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig_ch1)+',' + str(block_size))
                buff_byte1 = self.dev.rx_arb()
                self.dev.tx_txt('ACQ:AXI:SOUR2:DATA:Start:N? ' + str(trig_ch2)+',' + str(block_size))
                buff_byte2 = self.dev.rx_arb()

                buff1 = [struct.unpack('!f',bytearray(buff_byte1[i:i+4]))[0] for i in range(0, len(buff_byte1), 4)]
                buff2 = [struct.unpack('!f',bytearray(buff_byte2[i:i+4]))[0] for i in range(0, len(buff_byte2), 4)]
                buff_all1 = np.append(buff_all1, buff1)
                buff_all2 = np.append(buff_all2, buff2)
                trig_ch1 += block_size
                
                trig_ch2 += block_size
                                
            self.data_ch1 = np.array(buff_all1)
            self.data_ch2 = np.array(buff_all2)
            if self.verbosity > 0:
                print("ch1 data size " + str(len(self.data_ch1)))
                logging.info("ch1 data size " + str(len(self.data_ch1)))
                print("ch2 data size " + str(len(self.data_ch2)))
                logging.info("ch2 data size " + str(len(self.data_ch2)))
            """
            # ASCII data receiving
            print(self.ip + " receiving ASCII data from Ch1 from :" + str(trig_ch1))
            self.dev.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig_ch1)+',' + str(self.n_pts))
            buff_string = self.dev.rx_txt()
            print(self.ip + " receiving ASCII data from Ch2 from :" + str(trig_ch2))
            self.dev.tx_txt('ACQ:AXI:SOUR2:DATA:Start:N? ' + str(trig_ch2)+',' + str(self.n_pts))
            buff_string2 = self.dev.rx_txt()
            
            
            buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
            self.data_ch1 = np.array(buff_string, dtype=np.float64)    #list(map(np.float64, buff_string))

            buff_string2 = buff_string2.strip('{}\n\r').replace("  ", "").split(',')
            self.data_ch2 = np.array(buff_string2, dtype=np.float64)   #list(map(np.float64, buff_string2))
            """
            print(self.ip + "done receiving")
            logging.info(self.ip + "done receiving")
            #print(self.data_ch1[:100])
            
            self.dev.tx_txt('ACQ:AXI:SOUR1:ENable OFF')
            self.dev.tx_txt('ACQ:AXI:SOUR2:ENable OFF')

        print('Elapsed time for receiving= {}'.format(time.time() - timeStart))
        logging.info('Elapsed time for receiving= {}'.format(time.time() - timeStart))

        

    def write_mdsplus(self, conn):
        
    
        msg1 = "Writing data to shot number: " + str(self.shot_num)
        msg2 = "Writing data to node: " + self.device_node

        print(msg1) 
        print(msg2)
        logging.info(msg1)
        logging.info(msg2)
        try:
            # Write (put) the data to the device in MDSplus
            conn.put(self.device_node+":CH_01", "$", self.data_ch1)
            conn.put(self.device_node+":CH_02", "$", self.data_ch2)
            conn.put(self.device_node+":FREQ", "$", self.fs/self.downsample_value)
            conn.put(self.device_node+":NAME", "$", self.ip + " " + str(datetime.now()))
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
        conn.openTree(self.mdsplus_tree, 0)

        # Get the current shot number
        self.shot_num = conn.get('$shot')
        logging.info("Latest shot is " + str(self.shot_num))
        # Write the data
        self.write_mdsplus(conn)

        # Close the tree and latest shot
        conn.closeTree(self.mdsplus_tree, self.shot_num)

    def _write_plots(self):
        if self.channel == 3:
            
            time_scale = np.linspace(0, 1/(self.fs/self.downsample_value)*len(self.data_ch1), len(self.data_ch2))
            plt.plot(time_scale, self.data_ch1, label="ch1")
            plt.plot(time_scale, self.data_ch2, label="ch2")
            plt.legend()
            plt.xlabel("Time (s)")
            plt.ylabel("Volts")
            
            strFile = "/home/whamdata/WHAM_Data/data_saving/" + self.device_node + ".png"
            if self.verbosity > 0:
                print("writing plots " + strFile)
                logging.info("writing plots " + strFile)
            if os.path.isfile(strFile):
                os.remove(strFile)
            plt.savefig(strFile)
            #plt.show()
            plt.close()
        elif self.channel == 1:
            plt.plot(self.data_ch1, label="ch1")
            plt.legend()
    #       plt.plot(np.diff(self.data_in))
            #plt.show()
        elif self.channel == 2:
            plt.plot(self.data_ch2, label="ch2")
            plt.legend()
    #       plt.plot(np.diff(self.data_in))
            #plt.show()

    def store(self):
        timeStart = time.time()

        if self.bSave == 1:
            self._write_hdf5()

        if self.bMDS == 1:
            self._write_mdsplus()

        if self.bPlot == 1: 
            self._write_plots()

        print('Elapsed time for writing = {}'.format(time.time() - timeStart))
        logging.info('Elapsed time for writing = {}'.format(time.time() - timeStart))
    
    def output(self, wave_form = 'triangle', freq=2000, ampl=1):

        # Generate a continuous waveform for testing on both outputs
        self.dev.tx_txt("GEN:RST")
        self.dev.tx_txt('SOUR1:FUNC ' + str(wave_form).upper())
        self.dev.tx_txt('SOUR1:FREQ:FIX ' + str(freq))
        self.dev.tx_txt('SOUR1:VOLT ' + str(ampl))

        self.dev.tx_txt('SOUR2:FUNC ' + str(wave_form).upper())
        self.dev.tx_txt('SOUR2:FREQ:FIX ' + str(freq))
        self.dev.tx_txt('SOUR2:VOLT ' + str(ampl))

        # Enable output
        self.dev.tx_txt('OUTPUT1:STATE ON')
        self.dev.tx_txt('SOUR1:TRig:INT')
        self.dev.tx_txt('OUTPUT2:STATE ON')
        self.dev.tx_txt('SOUR2:TRig:INT')

        
    def close(self):
        if not self.dev == None:
            self.dev.close()
            self.dev = None


class WhamRedPitayaConnectionError(Exception):

    def __init__(self, message=""):
        super(WhamRedPitayaConnectionError, self).__init__(message)
# %%
