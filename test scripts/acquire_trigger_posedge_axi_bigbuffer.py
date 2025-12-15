#!/usr/bin/python3

import sys
import redpitaya_scpi as scpi
import matplotlib.pyplot as plot
import struct
import numpy as np 
from time import time

rp_s = scpi.scpi("rp-f0bd7d.local")

rp_s.tx_txt('ACQ:RST')
rp_s.tx_txt('ACQ:DATA:FORMAT BIN')

rp_s.tx_txt('ACQ:AXI:DATA:UNITS VOLTS')
print('ACQ:AXI:DATA:UNITS?: ',rp_s.txrx_txt('ACQ:AXI:DATA:UNITS?'))
rp_s.check_error()

rp_s.tx_txt('ACQ:AXI:DEC 1')
print('ACQ:AXI:DEC?: ',rp_s.txrx_txt('ACQ:AXI:DEC?'))
rp_s.check_error()

start = int(rp_s.txrx_txt('ACQ:AXI:START?'))
size = int(rp_s.txrx_txt('ACQ:AXI:SIZE?'))
samples = int(400000) # 1 sample = 16 Bit
rp_s.check_error()

print("Start address ",start," size of aviable memory ",size)
print("Number of samples to capture per channel " + str(samples))

# Specify the buffer sizes in bytes for the first and second channels
add_str_ch1 = 'ACQ:AXI:SOUR1:SET:Buffer ' + str(start) + ',' + str(size)

rp_s.tx_txt(add_str_ch1)
rp_s.check_error()

# You need to specify the number of samples after the trigger
rp_s.tx_txt('ACQ:AXI:SOUR1:Trig:Dly '+ str(samples))
rp_s.check_error()

rp_s.tx_txt('ACQ:AXI:SOUR1:ENable ON')
rp_s.check_error()

rp_s.tx_txt('ACQ:START')
rp_s.tx_txt('ACQ:TRIG NOW')
rp_s.check_error()

while 1:
    rp_s.tx_txt('ACQ:AXI:SOUR1:TRIG:FILL?')
    if rp_s.rx_txt() == '1':
        break

print("All data captured")
rp_s.tx_txt('ACQ:STOP')

trig = int(rp_s.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?'))

# It is quite difficult for the server to transfer a large amount of data at once, and there may not be enough memory with a very large capture buffer. 
# Therefore, we request data from the server in parts

received_size = 0
block_size = 2**18
buff_all = []

while received_size < samples:
    if (received_size + block_size) > samples:
        block_size = samples - received_size
    start = time()
    rp_s.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig)+',' + str(block_size))
    stop = time()
    print('elasped time 1 = ' + str(stop-start))
    start = time()
    buff_byte = rp_s.rx_arb()
    stop = time()
    print('elasped time 2 = ' + str(stop-start))

    start = time()
    buff = [struct.unpack('!f',bytearray(buff_byte[i:i+4]))[0] for i in range(0, len(buff_byte), 4)]
    #buff = [struct.unpack('!h',bytearray(buff_byte[i:i+2]))[0] for i in range(0, len(buff_byte), 2)]
    #buff = np.frombuffer(buff_byte, dtype=np.int16)
    
    buff_all = np.append(buff_all, buff)
    trig += block_size
    trig = trig % samples
    received_size += block_size
    stop = time()
    print('elasped time 3 = ' + str(stop-start))
    print("progress: {:.2f} %".format(received_size/samples*100))

print("Size of data array: " + str(len(buff_all)))
print("Buffer last 100 samples",buff_all[-100:])


plot.plot(buff_all)
plot.ylabel('Voltage')
plot.show()