# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitaya
from WhamRedPitaya import WhamRedPitayaGroup

import numpy as np
from datetime import datetime

# Create fake data
cycles_1 = 1000 # how many sine cycles
resolution_1 = 2.5e6 # how many datapoints to generate
length_1 = np.pi * 2 * cycles_1
#data_in_1 = np.sin(np.arange(0, length_1, length_1 / resolution_1))


# MDSplus node to write data to
DEVICE_NODE = "ECH:ECH_RAW:RP_01"
DEVICE_TREE = "ECH.ECH_RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

#rpg = WhamRedPitayaGroup(num_device=2, ip_list=IP_LIST, device_tree=DEVICE_TREE, mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE)


rp = WhamRedPitaya(ip="192.168.0.150", port=5000, device_node=DEVICE_NODE, mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, useTrig=False)

# Change any settings here
rp.mdsplus_server = MDSPLUS_SERVER # server running mdsplus
rp.mdsplus_tree = MDSPLUS_TREE # name of top mdsplus tree (should always be "wham")

# Attempt to establish connection to the RP
rp.connect()

# Configure the RP device
rp.configure()

# Set the trigger on the RP and wait for data. 

while True:
    rp.bPlot = 1
    rp.bMDS = 0
    rp.arm()
    #rp.data_in = data_in_1
    #rp.ip = str(datetime.now())
    
    # Store the data to MDSplus. plots, HDF5, etc...
    rp.store()
