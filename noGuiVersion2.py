# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitaya

# MDSplus node to write data to
RP1_NODE = "ECH:ECH_RAW:RP_1"

rp = WhamRedPitaya(DEVICE_NODE=RP1_NODE, IP="192.168.0.150", PORT=5000)

# Change any settings here
rp.mdsplus_server = "andrew" # server running mdsplus
rp.mdsplus_tree = "wham" # name of top mdsplus tree (should always be "wham")

# Attempt to establish connection to the RP
rp.connect()

# Configure the RP device
rp.configure()

# Set the trigger on the RP and wait for data. 
# Automatically reads and writes the data to MDSplus if it is recieved from the RP
rp.arm()


