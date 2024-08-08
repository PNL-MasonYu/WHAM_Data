 # %%
from WhamRedPitaya import WhamRedPitayaGroup
import logging
import time
start_time = time.localtime()
err_file = "/mnt/n/whamdata/WHAMdata4_logs/ECH_log_" + time.strftime("%Y_%m_%d_%H-%M", start_time) + ".csv"
logging.basicConfig(filename=err_file, level=logging.INFO)

# MDSplus node to write data to
DEVICE_TREE = "ECH.ECH_RAW"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"


ECH_IP_LIST = [("192.168.130.224", 5000),
               ("192.168.130.223", 5000),
#               ("192.168.130.225", 5000),
               ("192.168.130.226", 5000)]

ECH_device_nodes = ["ECH_RP_01", "ECH_RP_02", "ECH_RP_04"]

if __name__ == '__main__':
    rpg_ech = WhamRedPitayaGroup(num_devices=len(ECH_IP_LIST), ip_list=ECH_IP_LIST, device_tree="ECH.ECH_RAW", device_nodes=ECH_device_nodes,
                                 mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, Trig="EXT_NE", shot_num=None)
    
    # Repeat until device connection
    while True:
        rpg_ech.connect_devices()
    
        if not all(device is None for device in rpg_ech.connected_devices_list):
            break


    for device in rpg_ech.connected_devices_list:
        device.verbosity=1
        device.n_pts = 2e6
        device.downsample_value = 2
        device.bMDS = 1
        device.bPlot = 1
        device.channel = 3
        #device.trig_level = 0.3
        #device.trig = "CH2_PE"
        

    rpg_ech.configure_devices()
    rpg_ech.arm_devices() # This will finish when data is received from all devices
    rpg_ech.store_data()
