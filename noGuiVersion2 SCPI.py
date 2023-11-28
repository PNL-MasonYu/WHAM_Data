# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitaya_SCPI

import numpy as np
from datetime import datetime

# MDSplus node to write data to
DEVICE_NODE = "NBI.NBI_RAW:NBI_RP_01"
DEVICE_TREE = "NBI.NBI_RAW"
#DEVICE_NODE = "RAW.RP_F0918A"
#DEVICE_TREE = "RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

#rpg = WhamRedPitayaGroup(num_device=2, ip_list=IP_LIST, device_tree=DEVICE_TREE, mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE)

rp = WhamRedPitaya_SCPI(ip="rp-f0bd40.local", port=5000, device_node=DEVICE_NODE,
                        mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE,
                        Trig="EXT_PE", shot_num="231115029")

# Change any settings here
rp.mdsplus_server = MDSPLUS_SERVER # server running mdsplus
rp.mdsplus_tree = MDSPLUS_TREE # name of top mdsplus tree (should always be "wham")
rp.n_pts = 400000
rp.downsample_value = 1
rp.bPlot = 1

# Attempt to establish connection to the RP
rp.connect()

# Configure the RP device
rp.configure()

# Set the trigger on the RP and wait for data. 
rp.arm()

# Store the data to MDSplus. plots, HDF5, etc...
rp.store()
rp.close()

# %%
