# %%
#from MDSplus import * #Connection

from WhamRedPitaya import WhamRedPitaya


RP1_NODE = "ECH:ECH_RAW:RP_1"

rp = WhamRedPitaya(DEVICE_NODE=RP1_NODE, IP="192.168.0.150", PORT=5000)

rp.connect()


