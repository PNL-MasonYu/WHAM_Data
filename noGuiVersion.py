# %%
from __future__ import print_function
import sys
import numpy as np
import matplotlib.pyplot as plt
from MDSplus import * #Connection

import time
import h5py, datetime
import RP_PLL

##############################################################################
# Warning : For this code to work, the correct FPGA firmware and CPU software must have been updated.
IP = "192.168.0.150"
PORT = 5000 #5000 by default

#### User selection
data_addr = 0x0800_0000 # Min : 0x0800_0000

bUseTrig = 1
bSave = 0
bPlot = 1
bContinuous = 1
bMDS = 1

downsample_value = 1 # change from 125 MHz

n_pts = 5e6 # if both channel, this is n_pts1 + n_pts2 ##If you want max, just put a large number
channel = 3 # 1 or 2 or 3 for both
fileName = 'data_saving/8-08-23/shot.bin'
shot_num = 0
trig_delay = 10e-3  #trigger delay in seconds

ADC1_counter = 0 # 0 for ADC, 1 for counter (ADC 1 is connected to 16 MSBs of the 32 bits counter)
ADC2_counter = 0 # 0 for ADC, 1 for counter (ADC 2 is connected to 16 LSBs of the 32 bits counter)
###########################################################################
fs = 125e6 # clock speed, use downsample_value to change sample rate

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

dev = RP_PLL.RP_PLL_device(None)

dev.OpenTCPConnection(IP, PORT)


# make sure n_pts is < MAXPOINTS
n_pts = min(MAXPOINTS,n_pts)

# make sure downsample_value is between 1 and 2^32
downsample_value = min(2**32,downsample_value)
downsample_value = max(1,downsample_value)

dev.write_Zynq_AXI_register_uint32(DOWNSAMPLE_REG, downsample_value-1)
fs = fs/downsample_value
while bContinuous:
    
    #Reset DMA FSM (active low)
    dev.write_Zynq_AXI_register_uint32(RESET_DMA_REG, 0)
    dev.write_Zynq_AXI_register_uint32(RESET_DMA_REG, 1)

    # set MUX
    dev.write_Zynq_AXI_register_uint32(MUX_ADC_1_REG, ADC1_counter)
    dev.write_Zynq_AXI_register_uint32(MUX_ADC_2_REG, ADC2_counter)

    #set addr
    dev.write_Zynq_AXI_register_uint32(START_ADDR_REG, data_addr)

    # set n_bytes
    n_bytes = int(2*n_pts)
    n_bytes = max(n_bytes, 512) # at least 1 tx
    dev.write_Zynq_AXI_register_uint32(N_BYTES_REG, n_bytes)

    # set chan
    dev.write_Zynq_AXI_register_uint32(CHANNEL_REG, channel)

    # set start
    if bUseTrig == 0:
        dev.write_Zynq_AXI_register_uint32(START_REG, 1)
        dev.write_Zynq_AXI_register_uint32(START_REG, 0)
    else:
        dev.write_Zynq_AXI_register_uint32(TRIG_REG, 0) # 0 before to make sure we have a rising edge
        dev.write_Zynq_AXI_register_uint32(TRIG_REG, 1) # Start with trig need to stay high to register external trig
        dev.write_Zynq_AXI_register_uint32(TRIG_REG, 0)

    time.sleep(n_pts/fs) 

    # read status (0b10 = error // 0b01 = data_valid // 0b00 = not_ready)
    status = 0

    while status == 0:
        status = dev.read_Zynq_AXI_register_uint32(STATUS_REG)
        time.sleep(1e-1)
        
    print("Start receiving data")
    timeStart = time.time()
    data_in = dev.read_Zynq_ddr(data_addr-START_ADDR, int(2*n_pts))
    print('Elapsed time for receiving= {}'.format(time.time() - timeStart))

    timeStart = time.time()
    # data_in = np.fromstring(data_in, dtype=np.uint32) # Uncomment this line if you want to read data as 32 bits (useful if both ADCs are connected to counter)
    data_in = np.fromstring(data_in, dtype=np.int16) # Uncomment this line if you want to read data as 16 bits
    print('Elapsed time for conversion = {}'.format(time.time() - timeStart))

    timeStart = time.time()
    if bSave == 1:
        fNames = fileName.split(".")
        fNames[0] += str(shot_num)
        shot_num += 1
        shot_name = fNames[0] + time.strftime("(%m-%d-%y;%H-%M-%S)") + "." + fNames[1]
        hdf5_name = fNames[0] + ".hdf5"
        print(shot_name)
        if channel == 3 and not(ADC1_counter == 1 and ADC2_counter == 1):
            
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

    if bMDS == 1:
        
        conn = connection.Connection('andrew')      #Connect to Andrew
        #tree_name = 230731000 + shot_num
        
        conn.openTree('wham', 0)
        
        #result = conn.get("(RAW:ACQ196_370:CH_01)")
        #print(result)

        if channel == 3 and not(ADC1_counter == 1 and ADC2_counter == 1):
            conn.put("RAW:RP_F0918A:CH_01", "$", np.int16(data_in[1::2]))
            conn.put("RAW:RP_F0918A:CH_02", "$", np.int16(data_in[::2]))
            conn.put("RAW:RP_F0918A:FREQ", "$", fs)

            conn.put("ECH:ECH_RAW:RP_1:CH_01", "$", np.int16(data_in[1::2]))
            conn.put("ECH:ECH_RAW:RP_1:CH_02", "$", np.int16(data_in[::2]))
            conn.put("ECH:ECH_RAW:RP_1:FREQ", "$", fs)

            conn.put("ECH:ECH_RAW:RP_2:CH_01", "$", np.int16(data_in[1::2]))
            conn.put("ECH:ECH_RAW:RP_2:CH_02", "$", np.int16(data_in[::2]))
            conn.put("ECH:ECH_RAW:RP_2:FREQ", "$", fs)

            conn.closeTree('wham', 0)
            #result = conn.get("(RAW:ACQ196_370:CH_01)")
            #print(result)
        

    if bPlot == 1: 
        if channel == 3:
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

