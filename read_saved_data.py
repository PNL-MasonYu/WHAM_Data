#%matplotlib qt
# %%
from MDSplus.connection import * #Connection
import matplotlib.pyplot as plt
import numpy as np


filename = "data_saving/7-31-23/IN1_shot12(07-31-23;15-59-42).bin"
sampling_f = 125e6
bin_to_v = 1 / 2**15 * 20# * 10**(5/2)
time_window = (0.000,0.005)


with open(filename, mode='rb') as f:
    data_arr = np.fromfile(f, np.int16) * bin_to_v
    time_arr = np.linspace(0, len(data_arr)/sampling_f, len(data_arr))
    
    plt.plot(time_arr, data_arr)
    title_str = filename.split("/")[-1].strip(".bin")
    plt.title(title_str)
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    #plt.show()

    window_t = []
    window_d = []
    for n in range(len(time_arr)):
        if time_arr[n] > time_window[0] and time_arr[n] < time_window[1]:
            window_t.append(time_arr[n])
            window_d.append(data_arr[n])
    
    fft_fig, (ax1, ax2) = plt.subplots(2, 1)
    ax1.plot(window_t, window_d)
    ax1.set_xlabel("Time (sec)")
    ax1.set_title("Windowed Data ({:.2e} to {:.2e} sec)".format(time_window[0], time_window[1]))
    fft_d = np.fft.fft(window_d, len(window_t))
    fft_freq = np.fft.fftfreq(len(window_d), 1/sampling_f)
    #ax2.plot(fft_freq, fft_d.real, 'r-')
    #ax2.plot(fft_freq, fft_d.imag, 'b--')
    ax2.plot(fft_freq, abs(fft_d))
    ax2.set_xlim(0, max(fft_freq))
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_title("Windowed FFT")
    ax2.set_yscale("log")
    #ax2.set_ylim(1e4, 1e8)
    plt.tight_layout()
    plt.show()
    
    #conn = Connection('andrew')      #Connect to Andrew
    #conn.openTree('wham', 230501006)
    #result = conn.get("(RAW:ACQ196_370:CH_01)")
    #print(result)
    #conn.put("RAW:RP_F0918A:CH_01", "$", data_arr)
    #result = conn.get("(RAW:ACQ196_370:CH_01)")
    #print(result)
    #C:\Users\WHAMuser\Desktop\RedPitaya_Acquisition-master\python\data_saving\5-01-23\IN1_shot2(05-01-23;14-37-08).bin
# %%