#!/usr/bin/python3
# %%
import sys
import redpitaya_scpi as scpi
import matplotlib.pyplot as plot

rp_s = scpi.scpi("rp-f0bd40.local", timeout=30)

rp_s.tx_txt('ACQ:RST')
rp_s.tx_txt('ACQ:DATA:FORMAT ASCII')

rp_s.tx_txt('ACQ:AXI:DATA:UNITS VOLTS')
print('ACQ:AXI:DATA:UNITS?: ',rp_s.txrx_txt('ACQ:AXI:DATA:UNITS?'))
rp_s.check_error()

rp_s.tx_txt('ACQ:AXI:DEC 1')
print('ACQ:AXI:DEC?: ',rp_s.txrx_txt('ACQ:AXI:DEC?'))
rp_s.check_error()

start = int(rp_s.txrx_txt('ACQ:AXI:START?'))
size = int(rp_s.txrx_txt('ACQ:AXI:SIZE?'))
print('ACQ:AXI:START?: ' + str(start))
print('ACQ:AXI:SIZE?: ' + str(size))
samples = 262
rp_s.check_error()

print("Start address ",start," size of aviable memory ",size)
print("Number of samples to capture per channel " + str(samples))

# Specify the buffer sizes in bytes for the first and second channels
add_str_ch1 = 'ACQ:AXI:SOUR1:SET:Buffer ' + str(start) + ',' + str(size//2)
add_str_ch2 = 'ACQ:AXI:SOUR2:SET:Buffer ' + str(start + size // 2) + ',' + str(size//2)
print(add_str_ch1)
print(add_str_ch2)

rp_s.tx_txt(add_str_ch1)
rp_s.tx_txt(add_str_ch2)
rp_s.check_error()

# You need to specify the number of samples after the trigger
rp_s.tx_txt('ACQ:AXI:SOUR1:Trig:Dly '+ str(samples))
rp_s.tx_txt('ACQ:AXI:SOUR2:Trig:Dly '+ str(samples))
rp_s.check_error()

rp_s.tx_txt('ACQ:AXI:SOUR1:ENable ON')
rp_s.tx_txt('ACQ:AXI:SOUR2:ENable ON')
rp_s.check_error()

rp_s.tx_txt('ACQ:START')
rp_s.tx_txt('ACQ:TRIG NOW')
rp_s.check_error()

while 1:
    rp_s.tx_txt('ACQ:AXI:SOUR1:TRIG:FILL?')
    if rp_s.rx_txt() == '1':
        break

while 1:
    rp_s.tx_txt('ACQ:AXI:SOUR2:TRIG:FILL?')
    if rp_s.rx_txt() == '1':
        break

print("All data captured")
rp_s.tx_txt('ACQ:STOP')

trig_ch1 = rp_s.txrx_txt('ACQ:AXI:SOUR1:Trig:Pos?')
trig_ch2 = rp_s.txrx_txt('ACQ:AXI:SOUR2:Trig:Pos?')

print("receiving ASCII data from Ch1 from :" + str(trig_ch1))
rp_s.tx_txt('ACQ:AXI:SOUR1:DATA:Start:N? ' + str(trig_ch1)+',' + str(samples))
buff_string = rp_s.rx_txt()
print("receiving ASCII data from Ch2 from :" + str(trig_ch2))
rp_s.tx_txt('ACQ:AXI:SOUR2:DATA:Start:N? ' + str(trig_ch2)+',' + str(samples))
buff_string2 = rp_s.rx_txt()

buff_string = buff_string.strip('{}\n\r').replace("  ", "").split(',')
buff = list(map(float, buff_string))

buff_string2 = buff_string2.strip('{}\n\r').replace("  ", "").split(',')
buff2 = list(map(float, buff_string2))

print("Buffer 1 last 100 samples",buff[-100:])
print("Buffer 2 last 100 samples",buff2[-100:])


fig, axs = plot.subplots(2)
fig.suptitle('ADC data')
axs[0].plot(buff)
axs[1].plot(buff2)
plot.show()
# %%