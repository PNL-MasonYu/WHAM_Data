import time
import matplotlib.pyplot as plt
import numpy as np

import redpitaya_scpi as scpi

IP = '192.168.130.224'          # local IP of Red Pitaya
rp_s = scpi.scpi(IP)            # open socket connection with Red Pitaya


## size in samples 16Bit
DATA_SIZE = 1e5          # ((1024 * 1024 * 128) / 2)        ## for 128 MB ##
READ_DATA_SIZE = 1024*128     # (1024 * 256)                     ## for 128 MB ##

dec = 1
trig_lvl = 0.0


## Reset Acquisition
rp_s.tx_txt('ACQ:RST')

# Get Memory region
start_address = int(rp_s.txrx_txt('ACQ:AXI:START?'))
size = int(rp_s.txrx_txt('ACQ:AXI:SIZE?'))
start_address2 = round(start_address + size/2)

print(f"Reserved memory Start: {start_address:x} Size: {size:x}\n")

# Set decimation
rp_s.tx_txt(f"ACQ:AXI:DEC {dec}")

# Set units
rp_s.tx_txt('ACQ:AXI:DATA:UNITS VOLTS')

# Set trigger delay for both channels
rp_s.tx_txt(f"ACQ:AXI:SOUR1:Trig:Dly {DATA_SIZE}")
rp_s.tx_txt(f"ACQ:AXI:SOUR2:Trig:Dly {DATA_SIZE}")

# Set-up the Channel 1 and channel 2 buffers to each work with half the available memory space.
rp_s.tx_txt(f"ACQ:AXI:SOUR1:SET:Buffer {start_address},{size/2}")
rp_s.tx_txt(f"ACQ:AXI:SOUR2:SET:Buffer {start_address2},{size/2}")

# Enable DMA
rp_s.tx_txt('ACQ:AXI:SOUR1:ENable ON')
rp_s.tx_txt('ACQ:AXI:SOUR2:ENable ON')
print('Enable CHA and CHB\n')

# Specify the acquisition trigger
rp_s.tx_txt(f"ACQ:TRig:LEV {trig_lvl}")

rp_s.tx_txt('ACQ:TRig:EXT:DEBouncerUs 500')

## ACQUISITION

rp_s.tx_txt('ACQ:START')
rp_s.tx_txt('ACQ:TRig CH1_PE')

# Wait for trigger
while 1:
    rp_s.tx_txt("ACQ:TRig:STAT?")
    if rp_s.rx_txt() == 'TD':
        print("Triggered")
        time.sleep(1)
        break

# wait for fill adc buffer
while 1:
    rp_s.tx_txt('ACQ:AXI:SOUR1:TRIG:FILL?')
    if rp_s.rx_txt() == '1':
        print('DMA buffer full\n')
        break

# Stop Acquisition
rp_s.tx_txt('ACQ:STOP')

## Get write pointer at trigger location
posChA = int(rp_s.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?'))
posChB = int(rp_s.txrx_txt('ACQ:AXI:SOUR2:Trig:Pos?'))

## Read & plot

rp_s.tx_txt(f"ACQ:AXI:SOUR1:DATA:Start:N? {posChA},{READ_DATA_SIZE}")
signal_str = rp_s.rx_txt()
#rp_s.tx_txt(f"ACQ:AXI:SOUR2:DATA:Start:N? {posChB},{READ_DATA_SIZE}")
#signal_str2 = rp_s.rx_txt()

print("Data Acquired\n")

signal_num  = signal_str.strip('{}\n\r').replace("  ", "").split(',')
#signal_num2 = signal_str2.strip('{}\n\r').replace("  ", "").split(',')


# Writing data into a text file
with open("./out.txt", "w", encoding="ascii") as fp:
    read_size = 0

    while read_size < DATA_SIZE:
        size1 = READ_DATA_SIZE
        size2 = READ_DATA_SIZE
        rp_s.tx_txt(f"ACQ:AXI:SOUR1:DATA:Start:N? {posChA},{size1}")
        signal_str = rp_s.rx_txt()
        #rp_s.tx_txt(f"ACQ:AXI:SOUR2:DATA:Start:N? {posChB},{size2}")
        #signal_str2 = rp_s.rx_txt()

        buff1 = list(map(float, signal_str.strip('{}\n\r').replace("  ", "").split(',')))
        #buff2 = list(map(float, signal_str2.strip('{}\n\r').replace("  ", "").split(',')))

        for i in range(0, READ_DATA_SIZE):
            fp.write(f"{i+1:6d}:  {buff1[i]:6f}\t\n") #{buff2[i]:6f}\n")

        posChA += size1
        posChB += size2
        read_size += READ_DATA_SIZE
        print(f"Saved data size {read_size}\n")

plt.plot(buff1)
plt.show()
## Close connection with Red Pitaya
rp_s.tx_txt('ACQ:AXI:SOUR1:ENable OFF')
rp_s.tx_txt('ACQ:AXI:SOUR2:ENable OFF')
print('Releasing resources\n')
rp_s.close()