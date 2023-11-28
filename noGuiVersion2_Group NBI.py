# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitayaGroup, WhamRedPitaya

import numpy as np


# MDSplus node to write data to
#DEVICE_NODE = "NBI:NBI_RAW:NBI_RP_01"
DEVICE_TREE = "NBI.NBI_RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

IP_LIST = [
    ("rp-f0bd64.local", 5000),
    ("rp-f0bd4d.local", 5000),
    ("rp-f0bd60.local", 5000),
    ("rp-f0bd40.local", 5000)
]


NUM_DEVICES = 4
device_nodes = ["NBI_RP_01",
                "NBI_RP_02",
                "NBI_RP_03",
                "NBI_RP_04"]

if __name__ == '__main__':
    rpg = WhamRedPitayaGroup(num_devices=NUM_DEVICES, ip_list=IP_LIST, device_tree=DEVICE_TREE, device_nodes=device_nodes,
                             mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, Trig="EXT_NE", shot_num=None)

    # Repeat until device connection
    while True:
        rpg.connect_devices()
    
        if not all(device is None for device in rpg.connected_devices_list):
            break
    while 1:
        for device in rpg.connected_devices_list:
            device.n_pts = 400000       
            device.downsample_value = 16    #Changed decimation from 8 to 16 -Kunal Sanwalka 2023/11/27
            device.bMDS = 1
            device.bPlot = 1
            device.channel = 3
        
        rpg.configure_devices()

        rpg.arm_devices() # This will finish when data is received from all devices

        rpg.store_data()