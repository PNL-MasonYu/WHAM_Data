# %%
from __future__ import print_function
import sys
import numpy as np
import matplotlib.pyplot as plt
#from MDSplus import * #Connection
from MDSplus import connection

import time
import h5py, datetime
import RP_PLL


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


    def __init__(self, DEVICE_NODE="RP", IP="192.168.0.150", PORT=5000):

        # Instance variables:

        ##############################################################################
        # Warning : For this code to work, the correct FPGA firmware and CPU software must have been updated.

        self.DEVICE_NODE = DEVICE_NODE # The name of the node to write data to. Should be something like "ECH:ECH_RAW:RP_1"

        self.IP = IP
        self.PORT = PORT #5000 by default

        self.mdsplus_server = "andrew" # server running mdsplus
        self.mdsplus_tree = "wham" # name of top mdsplus tree (should always be "wham")


        #### User selection
        self.data_addr = 0x0800_0000 # Min : 0x0800_0000

        self.bUseTrig = 1
        self.bSave = 0
        self.bPlot = 0
        self.bContinuous = 1
        self.bMDS = 1

        self.downsample_value = 1 # change from 125 MHz

        self.n_pts = 5e6 # if both channel, this is n_pts1 + n_pts2 ##If you want max, just put a large number
        self.channel = 3 # 1 or 2 or 3 for both
        self.fileName = 'data_saving/8-08-23/shot.bin'
        self.shot_num = 0
        self.trig_delay = 10e-3  #trigger delay in seconds

        self.ADC1_counter = 0 # 0 for ADC, 1 for counter (ADC 1 is connected to 16 MSBs of the 32 bits counter)
        self.ADC2_counter = 0 # 0 for ADC, 1 for counter (ADC 2 is connected to 16 LSBs of the 32 bits counter)
        ###########################################################################


        self.fs = 125e6 # clock speed, use downsample_value to change sample rate


    def connect(self):

        print("Connecting to device at " + self.IP + " on port " + str(self.PORT))
        dev = RP_PLL.RP_PLL_device(None)
        dev.OpenTCPConnection(self.IP, self.PORT)


        # make sure n_pts is < MAXPOINTS
        n_pts = min(self.MAXPOINTS,self.n_pts)

        # make sure downsample_value is between 1 and 2^32
        downsample_value = min(2**32,downsample_value)
        downsample_value = max(1,downsample_value)

        dev.write_Zynq_AXI_register_uint32(self.DOWNSAMPLE_REG, downsample_value-1)
        fs = fs/downsample_value

        while self.bContinuous:
            
            #Reset DMA FSM (active low)
            dev.write_Zynq_AXI_register_uint32(self.RESET_DMA_REG, 0)
            dev.write_Zynq_AXI_register_uint32(self.RESET_DMA_REG, 1)

            # set MUX
            dev.write_Zynq_AXI_register_uint32(self.MUX_ADC_1_REG, self.ADC1_counter)
            dev.write_Zynq_AXI_register_uint32(self.MUX_ADC_2_REG, self.ADC2_counter)

            #set addr
            dev.write_Zynq_AXI_register_uint32(self.START_ADDR_REG, self.data_addr)

            # set n_bytes
            n_bytes = int(2*n_pts)
            n_bytes = max(n_bytes, 512) # at least 1 tx
            dev.write_Zynq_AXI_register_uint32(self.N_BYTES_REG, n_bytes)

            # set chan
            dev.write_Zynq_AXI_register_uint32(self.CHANNEL_REG, self.channel)

            # set start
            if self.bUseTrig == 0:
                dev.write_Zynq_AXI_register_uint32(self.START_REG, 1)
                dev.write_Zynq_AXI_register_uint32(self.START_REG, 0)
            else:
                dev.write_Zynq_AXI_register_uint32(self.TRIG_REG, 0) # 0 before to make sure we have a rising edge
                dev.write_Zynq_AXI_register_uint32(self.TRIG_REG, 1) # Start with trig need to stay high to register external trig
                dev.write_Zynq_AXI_register_uint32(self.TRIG_REG, 0)

            time.sleep(n_pts/fs) 

            # read status (0b10 = error // 0b01 = data_valid // 0b00 = not_ready)
            status = 0

            while status == 0:
                status = dev.read_Zynq_AXI_register_uint32(self.STATUS_REG)
                time.sleep(1e-1)
                
            print("Start receiving data")
            timeStart = time.time()
            data_in = dev.read_Zynq_ddr(self.data_addr-self.START_ADDR, int(2*n_pts))
            print('Elapsed time for receiving= {}'.format(time.time() - timeStart))

            timeStart = time.time()
            # data_in = np.fromstring(data_in, dtype=np.uint32) # Uncomment this line if you want to read data as 32 bits (useful if both ADCs are connected to counter)
            data_in = np.fromstring(data_in, dtype=np.int16) # Uncomment this line if you want to read data as 16 bits
            print('Elapsed time for conversion = {}'.format(time.time() - timeStart))

            timeStart = time.time()
            if self.bSave == 1:
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
                        f.create_dataset("IN1", data=data_in[1::2].tobytes())
                        f.create_dataset("IN2", data=data_in[::2].tobytes())
                    """
                    file_output = open(fileName_split[0] + fileName_split[1] +  'IN1_' + fileName_split[2], 'wb')
                    file_output.write(data_in[1::2].tobytes())
                    file_output.close()
                    
                    file_output = open(fileName_split[0] + fileName_split[1] +  'IN2_' + fileName_split[2], 'wb')
                    file_output.write(data_in[::2].tobytes())
                    file_output.close()
                else:
                    file_output = open(shot_name, 'wb')
                    file_output.write(data_in.tobytes())
                    file_output.close()

            if self.bMDS == 1:
                
                conn = connection.Connection(self.mdsplus_server)      #Connect to Andrew
                #tree_name = 230731000 + shot_num
                
                conn.openTree(self.mdsplus_tree, 0)

                shot_num = conn.get('$shot') # Get current shot number using TDI expression
                print("Writing data to shot number: " + shot_num)
                
                #result = conn.get("(RAW:ACQ196_370:CH_01)")
                #print(result)

                if self.channel == 3 and not(self.ADC1_counter == 1 and self.ADC2_counter == 1):
                    
                    #conn.put("RAW:RP_F0918A:CH_01", "$", np.int16(data_in[1::2]))
                    #conn.put("RAW:RP_F0918A:CH_02", "$", np.int16(data_in[::2]))
                    #conn.put("RAW:RP_F0918A:FREQ", "$", fs)

                    conn.put(self.DEVICE_NODE+":CH_01", "$", np.int16(data_in[1::2]))
                    conn.put(self.DEVICE_NODE+":CH_02", "$", np.int16(data_in[::2]))
                    conn.put(self.DEVICE_NODE+":FREQ", "$", fs)
                    conn.put(self.DEVICE_NODE+":NAME", "$", self.IP) # TODO: need to change this to IP


                    #conn.put("ECH:ECH_RAW:RP_1:CH_01", "$", np.int16(data_in[1::2]))
                    #conn.put("ECH:ECH_RAW:RP_1:CH_02", "$", np.int16(data_in[::2]))
                    #conn.put("ECH:ECH_RAW:RP_1:FREQ", "$", fs)
                    #conn.put("ECH:ECH_RAW:RP_1:NAME", "$", self.IP) # need to change this to IP


                    conn.closeTree(self.mdsplus_tree, 0)
                    #result = conn.get("(RAW:ACQ196_370:CH_01)")
                    #print(result)
                

            if self.bPlot == 1: 
                if self.channel == 3:
                    time_scale = np.linspace(0, 1/fs*len(data_in[::2]), len(data_in[::2]))
                    plt.plot(time_scale, data_in[::2])
                    plt.plot(time_scale, data_in[1::2])
                    plt.show()
                else:
                    plt.plot(data_in)
            #        plt.plot(np.diff(data_in))
                    plt.show()

            
            print('Elapsed time for writing = {}'.format(time.time() - timeStart))
            print('Done')

