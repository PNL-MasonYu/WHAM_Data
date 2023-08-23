# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitayaGroup, WhamRedPitaya

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
    ("192.168.0.150", 5000)
]

'''
IP_LIST = [
    ("192.168.0.150", 5000),
    ("192.168.0.151", 5000),
    ("192.168.0.152", 5000),
    ("192.168.0.153", 5000),
    ("192.168.0.154", 5000),
    ("192.168.0.155", 5000),
    ("192.168.0.156", 5000),
    ("192.168.0.157", 5000),
    ("192.168.0.158", 5000),
    ("192.168.0.159", 5000),

    ("192.168.0.150", 5000),
    ("192.168.0.151", 5000),
    ("192.168.0.152", 5000),
    ("192.168.0.153", 5000),
    ("192.168.0.154", 5000),
    ("192.168.0.155", 5000),
    ("192.168.0.156", 5000),
    ("192.168.0.157", 5000),
    ("192.168.0.158", 5000),
    ("192.168.0.159", 5000),

    ("192.168.0.150", 5000),
    ("192.168.0.151", 5000),
    ("192.168.0.152", 5000),
    ("192.168.0.153", 5000),
    ("192.168.0.154", 5000),
    ("192.168.0.155", 5000),
    ("192.168.0.156", 5000),
    ("192.168.0.157", 5000),
    ("192.168.0.158", 5000),
    ("192.168.0.159", 5000),

    ("192.168.0.150", 5000),
    ("192.168.0.151", 5000),
    ("192.168.0.152", 5000),
    ("192.168.0.153", 5000),
    ("192.168.0.154", 5000),
    ("192.168.0.155", 5000),
    ("192.168.0.156", 5000),
    ("192.168.0.157", 5000),
    ("192.168.0.158", 5000),
    ("192.168.0.159", 5000)
    ("192.168.0.150", 5000)
]
'''

if __name__ == '__main__':
    rpg = WhamRedPitayaGroup(num_devices=40, ip_list=IP_LIST, device_tree=DEVICE_TREE, mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, useTrig=1)

    rpg.connect_devices()

    while True:

        rpg.configure_devices()

        rpg.arm_devices() # This will finish when data is received from all devices

        '''
        rpg.connected_devices_list = rpg.devices_list

        rpg.connected_devices_list[0].data_in = data_in_1
        rpg.connected_devices_list[1].data_in = data_in_2
        rpg.connected_devices_list[2].data_in = data_in_1
        rpg.connected_devices_list[3].data_in = data_in_2
        rpg.connected_devices_list[4].data_in = data_in_1
        rpg.connected_devices_list[5].data_in = data_in_2
        rpg.connected_devices_list[6].data_in = data_in_1
        rpg.connected_devices_list[7].data_in = data_in_2
        rpg.connected_devices_list[8].data_in = data_in_1
        rpg.connected_devices_list[9].data_in = data_in_2

        rpg.connected_devices_list[10].data_in = data_in_1
        rpg.connected_devices_list[11].data_in = data_in_2
        rpg.connected_devices_list[12].data_in = data_in_1
        rpg.connected_devices_list[13].data_in = data_in_2
        rpg.connected_devices_list[14].data_in = data_in_1
        rpg.connected_devices_list[15].data_in = data_in_2
        rpg.connected_devices_list[16].data_in = data_in_1
        rpg.connected_devices_list[17].data_in = data_in_2
        rpg.connected_devices_list[18].data_in = data_in_1
        rpg.connected_devices_list[19].data_in = data_in_2

        rpg.connected_devices_list[20].data_in = data_in_1
        rpg.connected_devices_list[21].data_in = data_in_2
        rpg.connected_devices_list[22].data_in = data_in_1
        rpg.connected_devices_list[23].data_in = data_in_2
        rpg.connected_devices_list[24].data_in = data_in_1
        rpg.connected_devices_list[25].data_in = data_in_2
        rpg.connected_devices_list[26].data_in = data_in_1
        rpg.connected_devices_list[27].data_in = data_in_2
        rpg.connected_devices_list[28].data_in = data_in_1
        rpg.connected_devices_list[29].data_in = data_in_2

        rpg.connected_devices_list[30].data_in = data_in_1
        rpg.connected_devices_list[31].data_in = data_in_2
        rpg.connected_devices_list[32].data_in = data_in_1
        rpg.connected_devices_list[33].data_in = data_in_2
        rpg.connected_devices_list[34].data_in = data_in_1
        rpg.connected_devices_list[35].data_in = data_in_2
        rpg.connected_devices_list[36].data_in = data_in_1
        rpg.connected_devices_list[37].data_in = data_in_2
        rpg.connected_devices_list[38].data_in = data_in_1
        rpg.connected_devices_list[39].data_in = data_in_2
        '''

        rpg.store_data()
