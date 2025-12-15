#!/usr/bin/env python3

import sys
import redpitaya_scpi as scpi
import matplotlib.pyplot as plot

IP = '192.168.130.224'

rp_s = scpi.scpi(IP)

rp_s.tx_txt('ACQ:RST')

rp_s.tx_txt('ACQ:DEC 16')

# For short triggering signals set the length of internal debounce filter in us (minimum of 1 us)
rp_s.tx_txt('ACQ:TRig:EXT:DEBouncerUs 500')

rp_s.tx_txt('ACQ:START')
rp_s.tx_txt('ACQ:TRig NOW')

while 1:
    rp_s.tx_txt('ACQ:TRig:STAT?')
    if rp_s.rx_txt() == 'TD':
        break

## ! OS 2.00 or higher only ! ##
while 1:
    rp_s.tx_txt('ACQ:TRig:FILL?')
    if rp_s.rx_txt() == '1':
        break

rp_s.tx_txt('ACQ:SOUR1:DATA?')
buff_string = rp_s.rx_txt()
buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
buff = list(map(float, buff_string))

plot.plot(buff)
plot.ylabel('Voltage')
plot.show()