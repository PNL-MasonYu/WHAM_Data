# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitaya

import numpy as np


cycles = 1000 # how many sine cycles
resolution = 2.5e6 # how many datapoints to generate
length = np.pi * 2 * cycles
data_in = np.sin(np.arange(0, length, length / resolution))




# MDSplus node to write data to
RP1_NODE = "ECH:ECH_RAW:RP_1"

rp = WhamRedPitaya(device_node=RP1_NODE, ip="192.168.0.150", port=5000)

# Change any settings here
rp.mdsplus_server = "andrew.psl.wisc.edu" # server running mdsplus
rp.mdsplus_tree = "wham" # name of top mdsplus tree (should always be "wham")

# Attempt to establish connection to the RP
#rp.connect()

# Configure the RP device
#rp.configure()

# Set the trigger on the RP and wait for data. 
#rp.arm()

rp.data_in = data_in
rp.ip = "test_message"



print(rp.data_in[1000])
print(data_in[1000])


# Store the data to MDSplus. plots, HDF5, etc...
rp.store()
