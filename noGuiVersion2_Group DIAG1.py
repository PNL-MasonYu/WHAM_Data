 # %%
"""
Script to run the Red Pitaya digitizers on the diagnostics rack
Arms, set up and store data from the red pitayas in that rack on external trigger
This should be called by the master control program on Andrew and run ~30 seconds before the shot
Running this script manually will interfere with this
"""
from WhamRedPitaya import WhamRedPitayaGroup
import time
import logging
start_time = time.localtime()
err_file = "/mnt/n/whamdata/WHAMdata4_logs/DIAG1_log_" + time.strftime("%Y_%m_%d_%H-%M", start_time) + ".csv"
logging.basicConfig(filename=err_file, level=logging.INFO)

# MDSplus node to write data to
DEVICE_TREE = "RAW.DIAG_RP_01"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

# The two commented red pitayas are currently used for logging purposes
# f0bd65 for the NBI ion gauge data log
# f0952f for the WISP gauge and the chiller alert
IP_LIST = [("rp-f0bd5d.local", 5000),
            ("rp-f09303.local", 5000),
#            ("rp-f0952f.local", 5000),
            ("rp-f0be68.local", 5000),
            ("rp-f0bd72.local", 5000),
#            ("rp-f0bd65.local", 5000),
            ("rp-f0be2d.local", 5000),
            ("rp-f0bd99.local", 5000)]

device_nodes = ["RP_01", "RP_02", "RP_04", "RP_05", "RP_07", "RP_08"]

if __name__ == '__main__':
    rpg = WhamRedPitayaGroup(num_devices=len(IP_LIST), ip_list=IP_LIST, device_tree=DEVICE_TREE, device_nodes=device_nodes,
                                 mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, Trig="EXT_NE", shot_num=None)
    
    # Repeat until device connection
    while True:
        rpg.connect_devices()
    
        if not all(device is None for device in rpg.connected_devices_list):
            break


    for device in rpg.connected_devices_list:
        device.verbosity=0
        device.n_pts = 5e5 + 1
        device.downsample_value = 8
        device.bMDS = 1
        device.bPlot = 1
        device.channel = 3
        #device.trig_level = 0.3
        #device.trig = "CH2_PE"
        if device.ip == "rp-f0be68.local" or device.ip == "rp-f09303.local":
            device.n_pts = 5e5 + 1 
            device.downsample_value = 1024
        if device.ip == "rp-f0952f.local":
            device.n_pts = 5e5 + 1
            device.downsample_value = 1
        

    rpg.configure_devices()
    rpg.arm_devices() # This will finish when data is received from all devices
    rpg.store_data()

# %%
