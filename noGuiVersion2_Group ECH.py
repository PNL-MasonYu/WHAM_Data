# %%
from WhamRedPitaya import WhamRedPitayaGroup, WhamRedPitaya

import numpy as np

# MDSplus node to write data to
DEVICE_TREE = "ECH.ECH_RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"


ECH_IP_LIST = [("rp-f0939a.local", 5000),
               ("rp-f0bd7d.local", 5000),
               ("rp-f0bda7.local", 5000)] #

ECH_device_nodes = ["ECH_RP_01", "ECH_RP_02", "ECH_RP_03"]

if __name__ == '__main__':
    rpg_ech = WhamRedPitayaGroup(num_devices=len(ECH_IP_LIST), ip_list=ECH_IP_LIST, device_tree="ECH.ECH_RAW", device_nodes=ECH_device_nodes,
                                 mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, Trig="EXT_NE", shot_num=None)
    
    # Repeat until device connection
    while True:
        rpg_ech.connect_devices()
    
        if not all(device is None for device in rpg_ech.connected_devices_list):
            break

    while 1:
        for device in rpg_ech.connected_devices_list:
            device.verbosity=0
            device.n_pts = 1e7
            device.downsample_value = 8
            device.bMDS = 1
            device.bPlot = 1
            device.channel = 3
            #device.trig_level = 0.5
            device.trig = "NOW"
            

        rpg_ech.configure_devices()
        rpg_ech.arm_devices() # This will finish when data is received from all devices
        rpg_ech.store_data()
