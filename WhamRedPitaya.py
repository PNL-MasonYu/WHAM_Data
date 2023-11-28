# %%
from __future__ import print_function
from collections import UserString
import sys, struct, os
import redpitaya_scpi as scpi
import numpy as np
import matplotlib.pyplot as plt
#from MDSplus import * #Connection
from MDSplus import connection
import redpitaya_scpi as scpi

import time
#import h5py
import datetime
from datetime import datetime
import RP_PLL

from threading import Thread
from multiprocessing import Process, Manager, Pool



MDSPLUS_SERVER = "andrew"
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

        self.Trig = Trig
        self.shot_num = shot_num #None is the latest shot

        self._create_devices(device_nodes)


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
            device = WhamRedPitaya_SCPI(ip=ip, port=port, device_node=device_node, mdsplus_server=self.mdsplus_server, mdsplus_tree=self.mdsplus_tree, Trig=self.Trig, shot_num=self.shot_num)

            # Add to list of device objects
            self.devices_list.append(device)


    def connect_devices(self):

        # Attempt to establish connections to each device one by one

        # Iterate through number of devices
        for d in range(0,self.num_devices):

            # Retrieve device from list of device objects
            device = self.devices_list[d]

            try:
                # Attempt to connect to device
                device.connect()

                # If successful, add device to list of connected devices
                self.connected_devices_list.append(device)
            
            except WhamRedPitayaConnectionError as e:

                # If not successful, skip and write None to list of connected devices
                print("Skipping device at " + device.ip + ".")
                self.connected_devices_list.append(None)


    def configure_devices(self):

        # Configure each **connected** device one by one

        # Iterate through list of connected devices
        for device in self.connected_devices_list:

            if device == None:
                continue
            else:
                device.configure()

    def arm_devices(self):

        # Empty list to manage the threads
        self.threads = []

        # Iterate through list of connected devices
        for device in self.connected_devices_list:
            if device == None:
                continue
            else:
                print("Creating thread for device at " + device.ip)
                t = Thread(target=device.arm)
                self.threads.append(t)
                t.start()
                

        # Wait for the threads to complete and join them
        for t in self.threads:
            t.join()


    def store_data(self):

        timeStart = time.time()

        # Open process pool
        with Pool() as pool: 

            # Submit process jobs in parallel
            result = pool.map_async(store_data, self.connected_devices_list)

            result.wait()
            z = result.get() # Wait for processes to complete

            # Close process pool
            pool.close()
            pool.join()

        print('Total elapsed time for store_data threads = {}'.format(time.time() - timeStart))
        print('Done')

# Wrapper function for device.store()
def store_data(device):
    return device.store()
    



class WhamRedPitaya_SCPI():
    def __init__(self, ip, port=5000, device_node=DEVICE_TREE+".NBI_RP_01", mdsplus_server = MDSPLUS_SERVER, mdsplus_tree = MDSPLUS_TREE, Trig=None, shot_num=None) -> None:

        self.device_node = device_node # The name of the node to write data to. Should be something like "ECH:ECH_RAW:RP_1"

        self.ip = ip
        self.port = port #5000 by default

        self.mdsplus_server = mdsplus_server # server running mdsplus
        self.mdsplus_tree = mdsplus_tree # name of top mdsplus tree (should always be "wham")

        self.fs = 125e6 # clock speed, use downsample_value to change sample rate

        self.downsample_value = 1 # change from 125 MHz

        self.n_pts = 1e7 # if both channel, this is n_pts1 + n_pts2 ##If you want max, just put a large number
        self.channel = 3 # 1 or 2 or 3 for both

        self.dev = None
        self.data_ch1 = None
        self.data_ch2 = None

        TRIG_SOURCES = ["DISABLED", "NOW", "CH1_PE", "CH1_NE", "CH2_PE", "CH2_NE", "EXT_PE", "EXT_NE", "AWG_PE", "AWG_NE"]

        if Trig == None:
            self.trig = "NOW"
        elif Trig not in TRIG_SOURCES:
            print(self.trig + " not in list of possible trigger sources, default to NOW")
            self.trig = "NOW"
        else:
            self.trig = Trig
        self.trig_level = 0

        self.bSave = 0
        self.bPlot = 1
        self.bMDS = 1

        self.shot_num = shot_num


    def connect(self):

        print("Connecting to device at " + self.ip + " on port " + str(self.port) + ".")
        self.dev = scpi.scpi(self.ip)
        self.dev.tx_txt('ACQ:RST')


    def configure(self):

        # make sure downsample_value is between 1 and 2^32
        self.downsample_value = min(2**32,self.downsample_value)
        self.downsample_value = max(1,self.downsample_value)
        
        self.dev.tx_txt('ACQ:DATA:FORMAT ASCII')
        self.dev.tx_txt('ACQ:AXI:DATA:UNITS VOLTS')
        print('ACQ:AXI:DATA:UNITS?: ',self.dev.txrx_txt('ACQ:AXI:DATA:UNITS?'))
        self.dev.check_error()
        
        # Set the decimation value
        self.dev.tx_txt('ACQ:AXI:DEC ' + str(int(self.downsample_value)))
        print('ACQ:AXI:DEC?: ',self.dev.txrx_txt('ACQ:AXI:DEC?'))
        self.dev.check_error()

        # Get AXI start address and size of buffer
        start = int(self.dev.txrx_txt('ACQ:AXI:START?'))
        size = int(self.dev.txrx_txt('ACQ:AXI:SIZE?'))
        print('ACQ:AXI:START?: ' + str(start))
        print('ACQ:AXI:SIZE?: ' + str(size))
        if self.n_pts > (size // 2): #2 bytes per data point
            print("too many data points, truncating from {:.3e} to {:.3e} points".format(self.n_pts, (size // 2)))
            self.n_pts = (size // 2)
        self.dev.check_error()

        print("Start address ",start," size of aviable memory ",size)
        print("Number of samples to capture per channel " + str(self.n_pts))

        # Specify the buffer sizes in bytes for the first and second channels
        add_str_ch1 = 'ACQ:AXI:SOUR1:SET:Buffer ' + str(start) + ',' + str(size//2)
        add_str_ch2 = 'ACQ:AXI:SOUR2:SET:Buffer ' + str(start + size // 2) + ',' + str(size//2)
        print(add_str_ch1)
        print(add_str_ch2)

        self.dev.tx_txt(add_str_ch1)
        self.dev.tx_txt(add_str_ch2)
        self.dev.check_error()

        # You need to specify the number of samples after the trigger
        self.dev.tx_txt('ACQ:AXI:SOUR1:Trig:Dly '+ str(self.n_pts))
        self.dev.tx_txt('ACQ:AXI:SOUR2:Trig:Dly '+ str(self.n_pts))
        self.dev.check_error()

        self.dev.tx_txt('ACQ:AXI:SOUR1:ENable ON')
        self.dev.tx_txt('ACQ:AXI:SOUR2:ENable ON')
        self.dev.check_error()
    
    def arm(self):
        # set start
        self.dev.tx_txt('ACQ:START')

        self.dev.tx_txt('ACQ:TRIG ' + self.trig)
        if not (self.trig == "EXT_NE" or self.trig == "EXT_PE"):
            self.dev.tx_txt('ACQ:TRIG:LEV ' + str(self.trig_level))
        self.dev.check_error()
    
        duration = self.n_pts/(self.fs/self.downsample_value)
        print("Acquiring for " + str(duration*1000) + " ms")
        #time.sleep(duration) 
    
        while 1:
            self.dev.tx_txt('ACQ:AXI:SOUR1:TRIG:FILL?')
            if self.dev.rx_txt() == '1':
                break
        while 1:
            self.dev.tx_txt('ACQ:AXI:SOUR2:TRIG:FILL?')
            if self.dev.rx_txt() == '1':
                break
        print("All data captured")
        self.dev.tx_txt('ACQ:STOP')

        self._read()


    def _read(self):
        print("Start receiving data")
        timeStart = time.time()
        # It is quite difficult for the server to transfer a large amount of data at once, and there may not be enough memory with a very large capture buffer. 
        # Therefore, we request data from the server in parts

        if self.channel == 1 or self.channel == 2:
            # single channel receiving, TODO: debug
            received_size = 0
            block_size = self.n_pts // 2 #50000
            buff_all = []
            trig = int(self.dev.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?'))

            while received_size < self.n_pts:
                if (received_size + block_size) > self.n_pts:
                    block_size = self.n_pts - received_size

                self.dev.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig)+',' + str(block_size))
                buff_byte = self.dev.rx_arb()
                if buff_byte == False:
                    continue
                buff = [struct.unpack('!h',bytearray(buff_byte[i:i+2]))[0] for i in range(0, len(buff_byte), 2)]
                buff_all = np.append(buff_all, buff)
                trig += block_size
                trig = trig % self.n_pts
                received_size += block_size
            if self.channel == 1: self.data_ch1 = buff_all
            if self.channel == 2: self.data_ch2 = buff_all
        
        if self.channel == 3:
            # dual channel receiving, TODO: debug
            trig_ch1 = self.dev.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?')
            trig_ch2 = self.dev.txrx_txt('ACQ:AXI:SOUR2:Trig:Pos?')
            # Binary data receiving
            """
            buff_all1 = []
            buff_all2 = []
            block_size = 50000 #self.n_pts // 2
            while received_size < self.n_pts:
                if (received_size + block_size) > self.n_pts:
                    block_size = self.n_pts - received_size
                self.dev.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig_ch1)+',' + str(block_size))
                buff_byte1 = self.dev.rx_arb()
                self.dev.tx_txt('ACQ:AXI:SOUR2:DATA:Start:N? ' + str(trig_ch2)+',' + str(block_size))
                buff_byte2 = self.dev.rx_arb()

                buff1 = [struct.unpack('!h',bytearray(buff_byte1[i:i+2]))[0] for i in range(0, len(buff_byte1), 2)]
                buff2 = [struct.unpack('!h',bytearray(buff_byte2[i:i+2]))[0] for i in range(0, len(buff_byte2), 2)]
                buff_all1 = np.append(buff_all1, buff1)
                trig += block_size
                trig = trig % self.n_pts
                received_size += block_size
            """
            # ASCII data receiving
            print("receiving ASCII data from Ch1 from :" + str(trig_ch1))
            self.dev.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig_ch1)+',' + str(self.n_pts))
            buff_string = self.dev.rx_txt()
            print("receiving ASCII data from Ch2 from :" + str(trig_ch2))
            self.dev.tx_txt('ACQ:AXI:SOUR2:DATA:Start:N? ' + str(trig_ch2)+',' + str(self.n_pts))
            buff_string2 = self.dev.rx_txt()
            print("done receiving")
            
            buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
            self.data_ch1 = np.array(buff_string, dtype=np.float64) * 20#list(map(np.float64, buff_string))

            buff_string2 = buff_string2.strip('{}\n\r').replace("  ", "").split(',')
            self.data_ch2 = np.array(buff_string2, dtype=np.float64) *20#list(map(np.float64, buff_string2))

            #print(self.data_ch1[:100])
            
            self.dev.tx_txt('ACQ:AXI:SOUR1:ENable OFF')
            self.dev.tx_txt('ACQ:AXI:SOUR2:ENable OFF')

        print('Elapsed time for receiving= {}'.format(time.time() - timeStart))

        

    def write_mdsplus(self, conn):

        if self.shot_num == None:
            # Get current shot number using TDI expression
            self.shot_num = conn.get('$shot') 

        msg1 = "Writing data to shot number: " + self.shot_num
        msg2 = "Writing data to node: " + self.device_node

        print(msg1) 
        print(msg2)
        
        # Write (put) the data to the device in MDSplus
        # TODO: make channels 1 and 2 individually work as well
        conn.put(self.device_node+":CH_01", "$", self.data_ch1)
        conn.put(self.device_node+":CH_02", "$", self.data_ch2)
        conn.put(self.device_node+":FREQ", "$", self.fs/self.downsample_value)
        conn.put(self.device_node+":NAME", "$", self.ip + " " + str(datetime.now()))

        #conn.put("RAW:RP_F0918A:CH_01", "$", np.int16(self.data_in[1::2]))
        #conn.put("RAW:RP_F0918A:CH_02", "$", np.int16(self.data_in[::2]))
        #conn.put("RAW:RP_F0918A:FREQ", "$", self.fs)

        #conn.put("ECH:ECH_RAW:RP_1:CH_01", "$", np.int16(self.data_in[1::2]))
        #conn.put("ECH:ECH_RAW:RP_1:CH_02", "$", np.int16(self.data_in[::2]))
        #conn.put("ECH:ECH_RAW:RP_1:FREQ", "$", self.fs)
        #conn.put("ECH:ECH_RAW:RP_1:NAME", "$", self.IP) # need to change this to IP

    def _write_mdsplus(self):
        
        # No remote connection to MDSplus is provided so create a new one

        # Establish new remote connection to MDSplus
        conn = connection.Connection(self.mdsplus_server) # Connect to MDSplus server (andrew)
        
        # Open the tree and latest shot
        conn.openTree(self.mdsplus_tree, 0)

        # Write the data
        self.write_mdsplus(conn)

        # Close the tree and latest shot
        conn.closeTree(self.mdsplus_tree, 0)

    def _write_plots(self):
        if self.channel == 3:
            
            time_scale = np.linspace(0, 1/(self.fs/self.downsample_value)*len(self.data_ch1), len(self.data_ch2))
            plt.plot(time_scale, self.data_ch1)
            plt.plot(time_scale, self.data_ch2)
            plt.xlabel("Time (ms)")
            plt.ylabel("Volts")
            
            strFile = "/home/whamdata/WHAM_Data/data_saving/" + self.ip.split(".")[0] + ".png"
            print("writing plots " + strFile)
            if os.path.isfile(strFile):
                os.remove(strFile)
            plt.savefig(strFile)
            plt.close()
        elif self.channel == 1:
            plt.plot(self.data_ch1)
    #       plt.plot(np.diff(self.data_in))
            plt.show()
        elif self.channel == 2:
            plt.plot(self.data_ch2)
    #       plt.plot(np.diff(self.data_in))
            plt.show()

    def store(self):
        timeStart = time.time()

        if self.bSave == 1:
            self._write_hdf5()

        if self.bMDS == 1:
            self._write_mdsplus()

        if self.bPlot == 1: 
            self._write_plots()

        print('Elapsed time for writing = {}'.format(time.time() - timeStart))
        print('Done')
    
    def close(self):
        self.dev.close()



class WhamRedPitaya():

    # Class variables:

    START_ADDR        = 0x0800_0000 # Define by reserved memory in devicetree used to build Linux

    # Warning, if I put the '+1', there is an error : maybe a signal that wrap to 0 in the FPGA
    # Therefore, to keep a multiple of 32 bits, I substracted 3 bytes
    MAXPOINTS   = int((0x1FFFFFFF-START_ADDR - 3)/2) # /2 because 2 bytes per points
    xadc_base_addr    = 0x0001_0000
    DOWNSAMPLE_REG    = 0x0007_0000 #32 bits, downsample_rate-1 : 0 for 125e6, n for 125e6/n
    RESET_DMA_REG     = 0x0008_0000 # 1 bit
    MUX_ADC_1_REG     = 0x0009_0000 # 1 bit
    MUX_ADC_2_REG     = 0x0009_0008 # 1 bit
    N_BYTES_REG       = 0x000A_0000 # 32 bits
    CHANNEL_REG       = 0x000A_0008 # 2 bits
    START_REG         = 0x000B_0000 # 1 bit : start acq on rising_edge
    TRIG_REG          = 0x000B_0004 # 1 bit : allow start on rising edge of external pin
    STATUS_REG        = 0x000B_0008 # 2 bits : error_ACQ (STS =! 0x80) & data_tvalid_int ('1' when data transfer is done)
    START_ADDR_REG    = 0x000C_0000 # Min value is define by reserved memory in devicetree used to build Linux




    def __init__(self, ip="192.168.0.150", port=5000, device_node=DEVICE_TREE+".NBI_RP_01", mdsplus_server = MDSPLUS_SERVER, mdsplus_tree = MDSPLUS_TREE, useTrig=1):

        # Instance variables:

        ##############################################################################
        # Warning : For this code to work, the correct FPGA firmware and CPU software must have been updated.

        self.device_node = device_node # The name of the node to write data to. Should be something like "ECH:ECH_RAW:RP_1"

        self.ip = ip
        self.port = port #5000 by default

        self.mdsplus_server = mdsplus_server # server running mdsplus
        self.mdsplus_tree = mdsplus_tree # name of top mdsplus tree (should always be "wham")


        #### User selection
        self.data_addr = 0x0800_0000 # Min : 0x0800_0000

        self.bUseTrig = useTrig
        self.bSave = 0
        self.bPlot = 0
        self.bMDS = 1

        self.downsample_value = 1 # change from 125 MHz

        self.n_pts = 1e7 # if both channel, this is n_pts1 + n_pts2 ##If you want max, just put a large number
        self.channel = 3 # 1 or 2 or 3 for both
        self.fileName = 'data_saving/8-08-23/shot.bin'
        self.shot_num = 0
        self.trig_delay = 10e-3  #trigger delay in seconds

        self.ADC1_counter = 0 # 0 for ADC, 1 for counter (ADC 1 is connected to 16 MSBs of the 32 bits counter)
        self.ADC2_counter = 0 # 0 for ADC, 1 for counter (ADC 2 is connected to 16 LSBs of the 32 bits counter)
        ###########################################################################


        self.fs = 125e6 # clock speed, use downsample_value to change sample rate

        self.dev = None
        self.data_in = None



    def connect(self):

        print("Connecting to device at " + self.ip + " on port " + str(self.port) + ".")
        self.dev = RP_PLL.RP_PLL_device(None)
        
        self.dev.OpenTCPConnection(self.ip, self.port)

        if self.dev.valid_socket == False:
            print("Error occurred attempting to connect to device at " + self.ip + " on port " + str(self.port) + ".")
            raise WhamRedPitayaConnectionError()


    def configure(self):

        # make sure n_pts is < MAXPOINTS
        self.n_pts = min(self.MAXPOINTS,self.n_pts)

        # make sure downsample_value is between 1 and 2^32
        self.downsample_value = min(2**32,self.downsample_value)
        self.downsample_value = max(1,self.downsample_value)

        self.dev.write_Zynq_AXI_register_uint32(self.DOWNSAMPLE_REG, self.downsample_value-1)

        #Reset DMA FSM (active low)
        self.dev.write_Zynq_AXI_register_uint32(self.RESET_DMA_REG, 0)
        self.dev.write_Zynq_AXI_register_uint32(self.RESET_DMA_REG, 1)

        # set MUX
        self.dev.write_Zynq_AXI_register_uint32(self.MUX_ADC_1_REG, self.ADC1_counter)
        self.dev.write_Zynq_AXI_register_uint32(self.MUX_ADC_2_REG, self.ADC2_counter)

        #set addr
        self.dev.write_Zynq_AXI_register_uint32(self.START_ADDR_REG, self.data_addr)

        # set n_bytes
        n_bytes = int(2*self.n_pts)
        n_bytes = max(n_bytes, 512) # at least 1 tx
        self.dev.write_Zynq_AXI_register_uint32(self.N_BYTES_REG, n_bytes)

        # set chan
        self.dev.write_Zynq_AXI_register_uint32(self.CHANNEL_REG, self.channel)

    def arm(self):

        # set start
        if self.bUseTrig == 0:
            self.dev.write_Zynq_AXI_register_uint32(self.START_REG, 1)
            self.dev.write_Zynq_AXI_register_uint32(self.START_REG, 0)
        else:
            self.dev.write_Zynq_AXI_register_uint32(self.TRIG_REG, 0) # 0 before to make sure we have a rising edge
            self.dev.write_Zynq_AXI_register_uint32(self.TRIG_REG, 1) # Start with trig need to stay high to register external trig
            self.dev.write_Zynq_AXI_register_uint32(self.TRIG_REG, 0)

        duration = self.n_pts/(self.fs/self.downsample_value)
        print("Acquiring for " + str(duration) + " seconds")
        time.sleep(duration) 
        
        # read status (0b10 = error // 0b01 = data_valid // 0b00 = not_ready)
        status = 0

        # Block until data is ready
        while status == 0:
            status = self.dev.read_Zynq_AXI_register_uint32(self.STATUS_REG)
            time.sleep(1e-1)
                
        # Read data after status register changes
        self._read()



    def store(self):
            timeStart = time.time()

            if self.bSave == 1:
                self._write_hdf5()

            if self.bMDS == 1:
                self._write_mdsplus()

            if self.bPlot == 1: 
                self._write_plots()

            print('Elapsed time for writing = {}'.format(time.time() - timeStart))
            print('Done')




    def _read(self):
        print("Start receiving data")
        timeStart = time.time()
        self.data_in = self.dev.read_Zynq_ddr(self.data_addr-self.START_ADDR, int(2*self.n_pts))
        print('Elapsed time for receiving= {}'.format(time.time() - timeStart))

        timeStart = time.time()
        # self.data_in = np.fromstring(self.data_in, dtype=np.uint32) # Uncomment this line if you want to read data as 32 bits (useful if both ADCs are connected to counter)
        self.data_in = np.fromstring(self.data_in, dtype=np.int16) # Uncomment this line if you want to read data as 16 bits
        print('Elapsed time for conversion = {}'.format(time.time() - timeStart))
        
    
    def _write_mdsplus(self):
        
        # No remote connection to MDSplus is provided so create a new one

        # Establish new remote connection to MDSplus
        conn = connection.Connection(self.mdsplus_server) # Connect to MDSplus server (andrew)
        
        # Open the tree and latest shot
        conn.openTree(self.mdsplus_tree, 0)

        # Write the data
        self.write_mdsplus(conn)

        # Close the tree and latest shot
        conn.closeTree(self.mdsplus_tree, 0)



    def write_mdsplus(self, conn):

        # Get current shot number using TDI expression
        shot_num = conn.get('$shot') 

        msg1 = "Writing data to shot number: " + shot_num
        msg2 = "Writing data to node: " + self.device_node

        print(msg1) 
        print(msg2) 
        

        # Write (put) the data to the device in MDSplus
        if self.channel == 3 and not(self.ADC1_counter == 1 and self.ADC2_counter == 1):
            conn.put(self.device_node+":CH_01", "$", self.data_in[1::2])
            conn.put(self.device_node+":CH_02", "$", self.data_in[::2])
            conn.put(self.device_node+":FREQ", "$", self.fs/self.downsample_value)
            conn.put(self.device_node+":NAME", "$", self.ip + " " + str(datetime.now())) # TODO: need to change this to IP

            #conn.put("RAW:RP_F0918A:CH_01", "$", np.int16(self.data_in[1::2]))
            #conn.put("RAW:RP_F0918A:CH_02", "$", np.int16(self.data_in[::2]))
            #conn.put("RAW:RP_F0918A:FREQ", "$", self.fs)

            #conn.put("ECH:ECH_RAW:RP_1:CH_01", "$", np.int16(self.data_in[1::2]))
            #conn.put("ECH:ECH_RAW:RP_1:CH_02", "$", np.int16(self.data_in[::2]))
            #conn.put("ECH:ECH_RAW:RP_1:FREQ", "$", self.fs)
            #conn.put("ECH:ECH_RAW:RP_1:NAME", "$", self.IP) # need to change this to IP


    
    def _write_hdf5(self):
        fNames = self.fileName.split(".")
        fNames[0] += str(shot_num)
        shot_num += 1
        shot_name = fNames[0] + time.strftime("(%m-%d-%y;%H-%M-%S)") + "." + fNames[1]
        hdf5_name = fNames[0] + ".hdf5"
        print(shot_name)
        if self.channel == 3 and not(self.ADC1_counter == 1 and self.ADC2_counter == 1):
            
            fileName_split = shot_name.rpartition('/')
            # write to HDF5
            """
            with h5py.File(hdf5_name, "w") as f:
                # create a group in the HDF5 file to store metadata
                metadata = f.create_group("metadata")
                
                # save the timestamp, acquisition frequency, and delay time as attributes of the metadata group
                metadata.attrs["timestamp"] = time.strftime("%m-%d-%y;%H-%M-%S")
                metadata.attrs["acq_freq"] = fs
                metadata.attrs["trig_delay"] = trig_delay
                
                # save the two arrays as datasets in the HDF5 file
                f.create_dataset("IN1", data=self.data_in[1::2].tobytes())
                f.create_dataset("IN2", data=self.data_in[::2].tobytes())
            """
            file_output = open(fileName_split[0] + fileName_split[1] +  'IN1_' + fileName_split[2], 'wb')
            file_output.write(self.data_in[1::2].tobytes())
            file_output.close()
            
            file_output = open(fileName_split[0] + fileName_split[1] +  'IN2_' + fileName_split[2], 'wb')
            file_output.write(self.data_in[::2].tobytes())
            file_output.close()
        else:
            file_output = open(shot_name, 'wb')
            file_output.write(self.data_in.tobytes())
            file_output.close()


    def _write_plots(self):
        if self.channel == 3:
            time_scale = np.linspace(0, 1/(self.fs/self.downsample_value)*len(self.data_in[::2]), len(self.data_in[::2]))
            plt.plot(time_scale, self.data_in[::2])
            plt.plot(time_scale, self.data_in[1::2])
            plt.show()
        else:
            plt.plot(self.data_in)
    #        plt.plot(np.diff(self.data_in))
            plt.show()






class WhamRedPitayaConnectionError(Exception):

    def __init__(self):
        pass