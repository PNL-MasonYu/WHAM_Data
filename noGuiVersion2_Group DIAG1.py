 # %%
"""
Script to run the Red Pitaya digitizers on the diagnostics rack
Arms, set up and store data from the red pitayas in that rack on external trigger
This should be called by the master control program on Andrew and run ~30 seconds before the shot
Running this script manually will interfere with this
"""
from WhamRedPitaya import WhamRedPitayaGroup
import contextlib
import signal
import time
import logging
import os
start_time = time.localtime()
MAX_RUNTIME_SECONDS = 110
ARM_TIMEOUT_SECONDS = 40
CONNECT_TIMEOUT_SECONDS = 1
log_dir = "/home/whamdata/WHAM_Data/logs/DIAG1_logs"
os.makedirs(log_dir, exist_ok=True)
err_file = os.path.join(log_dir, "DIAG1_log.csv")
logging.getLogger().handlers.clear()
logging.basicConfig(filename=err_file, level=logging.INFO, filemode='w')

# MDSplus node to write data to
DEVICE_TREE = "RAW.DIAG_RP_01"

MDSPLUS_SERVER = "andrew.psl.wisc.edu"
MDSPLUS_TREE = "wham"

# The two commented red pitayas are currently used for logging purposes
# f0bd65 for the NBI ion gauge data log
# f0952f for the WISP gauge and the chiller alert
IP_LIST = [("rp-f0bd5d.local", 5000), #no ping
            ("rp-f09303.local", 5000),
            ("rp-f0952f.local", 5000),
            ("rp-f0be68.local", 5000),
            ("rp-f0bd72.local", 5000), # no ping
            ("rp-f0bd65.local", 5000), # possibly bad?
            ("rp-f0be2d.local", 5000), #no ping
            ("rp-f0bd99.local", 5000)] # possibly bad?

device_nodes = ["RP_01", "RP_02", "RP_03", "RP_04", "RP_05", "RP_06", "RP_07", "RP_08"]

if __name__ == '__main__':
    rpg = WhamRedPitayaGroup(num_devices=len(IP_LIST), ip_list=IP_LIST, device_tree=DEVICE_TREE, device_nodes=device_nodes,
                                 mdsplus_server=MDSPLUS_SERVER, mdsplus_tree=MDSPLUS_TREE, Trig="EXT_NE", shot_num=None)
    script_deadline = time.monotonic() + MAX_RUNTIME_SECONDS

    def _runtime_limit_handler(signum, frame):
        logging.error("DIAG1 forced exit after {} seconds".format(MAX_RUNTIME_SECONDS))
        raise SystemExit(1)

    signal.signal(signal.SIGALRM, _runtime_limit_handler)
    signal.alarm(MAX_RUNTIME_SECONDS)
    
    # Keep console output quiet; rely on the file logger in DIAG1_logs.
    try:
        with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            # Repeat until device connection
            while time.monotonic() < script_deadline:
                rpg.connect_devices(connect_timeout=CONNECT_TIMEOUT_SECONDS)

                if not all(device is None for device in rpg.connected_devices_list):
                    break

            else:
                logging.error("DIAG1 aborted before connection completed: exceeded {} seconds".format(MAX_RUNTIME_SECONDS))
                raise SystemExit(1)


            for device in rpg.connected_devices_list:
                if device is None:
                    continue
                device.verbosity = 0
                device.n_pts = 5e6 + 1
                device.downsample_value = 1
                device.bMDS = 1
                device.bPlot = 0
                device.channel = 3
                #device.trig_level = 0.3
                #device.trig = "CH2_PE"
                """
                if device.ip == "rp-f0be68.local" or device.ip == "rp-f09303.local":
                    device.n_pts = 5e5 + 1 
                    device.downsample_value = 1024
                if device.ip == "rp-f0952f.local":
                    device.n_pts = 5e5 + 1
                    device.downsample_value = 1
                """
            rpg.configure_devices()
            rpg.arm_devices(timeout=ARM_TIMEOUT_SECONDS) # This will finish when data is received from all devices
            rpg.store_data()
            logging.info("DIAG1 run complete: arm/store sequence exited")
    finally:
        signal.alarm(0)

# %%
