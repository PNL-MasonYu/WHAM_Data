#!/usr/bin/env python3

import sys
import redpitaya_scpi as scpi

IP = 'rp-f0bd72.local'

rp_s = scpi.scpi(IP)

for i in range(4):
    rp_s.tx_txt('ANALOG:PIN? AIN' + str(i))
    value = float(rp_s.rx_txt())
    print ("Measured voltage on AI["+str(i)+"] = "+str(value)+"V")

rp_s.close()
