# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitaya
from WhamRedPitaya import WhamRedPitayaGroup

import numpy as np

# Create fake data
cycles_1 = 300 # how many sine cycles
resolution_1 = 2.5e6 # how many datapoints to generate
length_1 = np.pi * 2 * cycles_1
data_in_1 = np.sin(np.arange(0, length_1, length_1 / resolution_1))

cycles_2 = 200 # how many sine cycles
resolution_2 = 2.5e6 # how many datapoints to generate
length_2 = np.pi * 2 * cycles_2
data_in_2 = np.sin(np.arange(0, length_2, length_2 / resolution_2))




# MDSplus node to write data to
DEVICE_NODE = "ECH:ECH_RAW:RP_1"
DEVICE_TREE = "ECH.ECH_RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

IP_LIST = [
    ("192.168.0.150", 5000),
    ("192.168.0.151", 5000)
]


rpg = WhamRedPitayaGroup(num_devices=2, ip_list=IP_LIST, device_tree=DEVICE_TREE, mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE)

#rpg.connect_devices()

#rpg.configure_devices()

#rpg.arm_devices() # This will finish when data is received from all devices


rpg.connected_devices_list = rpg.devices_list

rpg.connected_devices_list[0].data_in = data_in_1
rpg.connected_devices_list[1].data_in = data_in_2

rpg.store_data()