# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitayaGroup, WhamRedPitaya

import numpy as np


# Create fake data
#cycles_1 = 300 # how many sine cycles
#resolution_1 = 2.5e6 # how many datapoints to generate
#length_1 = np.pi * 2 * cycles_1
#data_1 = np.sin(np.arange(0, length_1, length_1 / resolution_1))

#cycles_2 = 200 # how many sine cycles
#resolution_2 = 2.5e6 # how many datapoints to generate
#length_2 = np.pi * 2 * cycles_2
#data_2 = np.sin(np.arange(0, length_2, length_2 / resolution_2))




# MDSplus node to write data to
DEVICE_NODE = "ECH:ECH_RAW:RP_1"
DEVICE_TREE = "ECH.ECH_RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"


IP_LIST = [
    ("192.168.0.152", 5000),
    ("192.168.0.151", 5000)
]


NUM_DEVICES = 2

'''
IP_LIST = []
for i in range(0,NUM_DEVICES):

    ip = ("192.168.0.1" + str(50+i), 5000)
    print(ip)

    IP_LIST.append(ip)
'''




if __name__ == '__main__':
    rpg = WhamRedPitayaGroup(num_devices=NUM_DEVICES, ip_list=IP_LIST, device_tree=DEVICE_TREE, mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, useTrig=0)

    # Repeat until device connection
    while True:
        rpg.connect_devices()
    
        if not all(device is None for device in rpg.connected_devices_list):
            break

    # Continuous loop (wait for data, read, and reset)
    while True:

        rpg.configure_devices()

        rpg.arm_devices() # This will finish when data is received from all devices
        
        rpg.connected_devices_list[1].bPlot = 1
        rpg.connected_devices_list[1].bMDS = 0
        rpg.connected_devices_list[0].bMDS = 0
        
        rpg.store_data()
