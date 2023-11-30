import ctypes
from picosdk.ps5000a import ps5000a as ps
from picosdk.discover import find_unit
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from MDSplus import connection



class picoscope5000():

    def __init__(self, device_node="RAW.PICOSCOPE_01", mdsplus_server="andrew.psl.wisc.edu", mdsplus_tree="wham", shot_num=None,
                resolution="PS5000A_DR_12BIT", coupling=("PS5000A_DC", "PS5000A_DC", "PS5000A_DC", "PS5000A_DC"), 
                range=("PS5000A_2V", "PS5000A_2V", "PS5000A_2V", "PS5000A_2V"), trig_src="PS5000A_CHANNEL_A", trig_dir="PS5000A_RISING", trig_level = 0,
                analog_offset = 0, sample_interval=8e-9, samples_pretrig = 1e5, samples_posttrig=1e6) -> None:
        self.mdsplus_server = mdsplus_server # server running mdsplus
        self.mdsplus_tree = mdsplus_tree # name of top mdsplus tree (should always be "wham")
        self.device_node = device_node
        if not shot_num == None:
            self.shot_num = str(shot_num)
        

        self.coupling = coupling
        self.range = range
        self.trig_src = trig_src
        self.trig_dir = trig_dir
        self.trig_level = trig_level # in V
        self.resolution = resolution
        self.analog_offset = analog_offset
        self.samples_pretrig = int(samples_pretrig)
        self.samples_posttrig = int(samples_posttrig)
        if samples_posttrig + samples_pretrig > 6e6:
            print("too many samples! Max 6M samples per channel")
            self.maxSamples = int(6e6)
        else:
            self.maxSamples = int(self.samples_posttrig + self.samples_pretrig)

        if sample_interval > 34.36:
            sample_interval = 34.36
            print("maximum sample interval is 34.36 seconds")

        # calculate timebase using the sampling interval specified in nanoseconds, p22 of programmers manual
        if self.resolution == "PS5000A_DR_12BIT":
            if sample_interval <= 4e-9:
                self.time_base = 3
                self.sample_interval = 2e-9
            elif sample_interval <= 8e-9:
                self.time_base = int(np.log2(sample_interval * 500e6)) + 1
                self.sample_interval = np.power(2, self.time_base - 1) / 500e6
            else:
                self.time_base = int(sample_interval * 62.5e6 + 3)
                self.sample_interval = np.power(2, self.time_base - 3) / 62.5e6
            
        elif self.resolution == "PS5000A_DR_8BIT":
            if sample_interval <= 4e-9:
                self.time_base = 2
                self.sample_interval = np.power(2, self.time_base) / 1e9
            else:
                self.time_base = int(sample_interval * 125e6 + 2)
                self.sample_interval = np.power(2, self.time_base - 2) / 125e6

        elif self.resolution == "PS5000A_DR_14BIT":
            if sample_interval < 16e-9:
                self.time_base = 3
                self.sample_interval = 8e-9
            else:
                self.time_base == int(sample_interval * 125e6 + 2)
                self.sample_interval = np.power(2, self.time_base - 2) / 125e6
        else:
            print("Resolution not implemented")
            self.resolution = "PS5000A_DR_8BIT"
            self.time_base = 8
            self.sample_interval = np.power(2, self.time_base - 2) / 125e6

        print("actual sample interval: " + str(self.sample_interval) + " seconds, time_base: " + str(self.time_base))
        print("sample length: " + str(self.sample_interval*self.maxSamples) + " seconds, sample_freq: " + str(1e-6/self.sample_interval) + " MHz")

        # Create chandle and status ready for use
        self.status = {}
        self.chandle = ctypes.c_int16()

        self.bPlot = True
        self.bMDS = True

        with find_unit() as device:
            print("found PicoScope: %s" % (device.info,))
            self.info = device.info

    def connect(self):
        # Open 5000 series PicoScope
        # Set resolution
        resolution =ps.PS5000A_DEVICE_RESOLUTION[self.resolution]
        # Returns handle to chandle for use in future API functions
        self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, resolution)

        try:
            assert_pico_ok(self.status["openunit"])
        except: # PicoNotOkError:

            powerStatus = self.status["openunit"]

            if powerStatus == 286:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
            elif powerStatus == 282:
                self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, powerStatus)
            else:
                raise

            assert_pico_ok(self.status["changePowerSource"])
        

    def close(self):
        # Stop the scope
        self.status["stop"] = ps.ps5000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])
        # Close unit Disconnect the scope
        # handle = chandle
        self.status["close"]=ps.ps5000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

        # display status returns
        print(self.status)

    def configure(self):
        # Set up channel A
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        coupling_type = ps.PS5000A_COUPLING[self.coupling[0]]
        chARange = ps.PS5000A_RANGE[self.range[0]]
        self.status["setChA"] = ps.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chARange, self.analog_offset)
        assert_pico_ok(self.status["setChA"])

        # Set up channel B
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        coupling_type = ps.PS5000A_COUPLING[self.coupling[1]]
        chBRange = ps.PS5000A_RANGE[self.range[1]]
        self.status["setChB"] = ps.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chBRange, self.analog_offset)
        assert_pico_ok(self.status["setChB"])

        # Set up channel C
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_C"]
        coupling_type = ps.PS5000A_COUPLING[self.coupling[2]]
        chCRange = ps.PS5000A_RANGE[self.range[2]]
        self.status["setChC"] = ps.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chCRange, self.analog_offset)
        assert_pico_ok(self.status["setChC"])

        # Set up channel D
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_D"]
        coupling_type = ps.PS5000A_COUPLING[self.coupling[3]]
        chDRange = ps.PS5000A_RANGE[self.range[3]]
        self.status["setChD"] = ps.ps5000aSetChannel(self.chandle, channel, 1, coupling_type, chDRange, self.analog_offset)
        assert_pico_ok(self.status["setChD"])

        # find maximum ADC count value
        # pointer to value = ctypes.byref(maxADC)
        self.maxADC = ctypes.c_int16()
        self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))
        assert_pico_ok(self.status["maximumValue"])

        # Set up an advanced trigger
        match self.trig_src:
            case "PS5000A_CHANNEL_A":
                adcTriggerLevel = mV2adc(self.trig_level * 1000, chARange, self.maxADC)
                TriggerChannel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
            case "PS5000A_CHANNEL_B":
                adcTriggerLevel = mV2adc(self.trig_level * 1000, chBRange, self.maxADC)
                TriggerChannel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
            case "PS5000A_CHANNEL_C":
                adcTriggerLevel = mV2adc(self.trig_level * 1000, chCRange, self.maxADC)
                TriggerChannel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_C"]
            case "PS5000A_CHANNEL_D":
                adcTriggerLevel = mV2adc(self.trig_level * 1000, chDRange, self.maxADC)
                TriggerChannel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_D"]

        triggerProperties = ps.PS5000A_TRIGGER_CHANNEL_PROPERTIES_V2(adcTriggerLevel,
                                                                    10,
                                                                    0,
                                                                    10,
                                                                    TriggerChannel)
        
        self.status["setTriggerChannelPropertiesV2"] = ps.ps5000aSetTriggerChannelPropertiesV2(self.chandle, ctypes.byref(triggerProperties), 1, 0)
        triggerConditions = ps.PS5000A_CONDITION(TriggerChannel,ps.PS5000A_TRIGGER_STATE["PS5000A_CONDITION_TRUE"])

        clear = 1
        add = 2
        self.status["setTriggerChannelConditionsV2"] = ps.ps5000aSetTriggerChannelConditionsV2(self.chandle, ctypes.byref(triggerConditions), 1, (clear + add))

        # Set up trigger direction
        triggerDirections = ps.PS5000A_DIRECTION(TriggerChannel, ps.PS5000A_THRESHOLD_DIRECTION[self.trig_dir], ps.PS5000A_THRESHOLD_MODE["PS5000A_LEVEL"])

        self.status["setTriggerChannelDirections"] = ps.ps5000aSetTriggerChannelDirectionsV2(self.chandle, ctypes.byref(triggerDirections), 1)

    def arm(self):
        # Get timebase information
        # handle = chandle
        # noSamples = maxSamples
        # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
        # pointer to maxSamples = ctypes.byref(returnedMaxSamples)
        # segment index = 0
        self.timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32()
        self.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.chandle, self.time_base, self.maxSamples, ctypes.byref(self.timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
        assert_pico_ok(self.status["getTimebase2"])

        # Run block capture
        # handle = chandle
        # time indisposed ms = None 
        # segment index = 0
        # lpReady = None (using ps5000aIsReady rather than ps5000aBlockReady)
        # pParameter = None
        self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, self.samples_pretrig, self.samples_posttrig, self.time_base, None, 0, None, None)
        assert_pico_ok(self.status["runBlock"])

        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        print("trigger armed")
        while ready.value == check.value:
            self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))


        # Create buffers ready for assigning pointers for data collection
        bufferAMax = (ctypes.c_int16 * self.maxSamples)()
        bufferAMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling 
        bufferBMax = (ctypes.c_int16 * self.maxSamples)()
        bufferBMin = (ctypes.c_int16 * self.maxSamples)()
        bufferCMax = (ctypes.c_int16 * self.maxSamples)()
        bufferCMin = (ctypes.c_int16 * self.maxSamples)()
        bufferDMax = (ctypes.c_int16 * self.maxSamples)()
        bufferDMin = (ctypes.c_int16 * self.maxSamples)()
                
        # Set data buffer location for data collection from channel A
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        self.status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersA"])
        # Set data buffer location for data collection from channel B
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        self.status["setDataBuffersB"] = ps.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferBMax), ctypes.byref(bufferBMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersB"])
        # Set data buffer location for data collection from channel C
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_C"]
        self.status["setDataBuffersC"] = ps.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferCMax), ctypes.byref(bufferCMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersC"])
        # Set data buffer location for data collection from channel D
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_D"]
        self.status["setDataBuffersD"] = ps.ps5000aSetDataBuffers(self.chandle, source, ctypes.byref(bufferDMax), ctypes.byref(bufferDMin), self.maxSamples, 0, 0)
        assert_pico_ok(self.status["setDataBuffersD"])

        # create overflow loaction
        overflow = ctypes.c_int16()        
        cmaxSamples = ctypes.c_int32(self.maxSamples)

        # Retried data from scope to buffers assigned above
        # handle = chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(cmaxSamples)
        # downsample ratio = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))
        self.status["getValues"] = ps.ps5000aGetValues(self.chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
        assert_pico_ok(self.status["getValues"])

        # convert ADC counts data to mV
        print("Converting raw ADC data into mV")
        chARange = ps.PS5000A_RANGE[self.range[0]]
        chBRange = ps.PS5000A_RANGE[self.range[1]]
        chCRange = ps.PS5000A_RANGE[self.range[2]]
        chDRange = ps.PS5000A_RANGE[self.range[3]]
        #print(bufferAMax[:100])
        self.mVChA =  np.array(adc2mV(bufferAMax, chARange, self.maxADC))
        self.mVChB =  np.array(adc2mV(bufferBMax, chBRange, self.maxADC))
        self.mVChC =  np.array(adc2mV(bufferCMax, chCRange, self.maxADC))
        self.mVChD =  np.array(adc2mV(bufferDMax, chDRange, self.maxADC))

    def _write_mdsplus(self):
        
        # No remote connection to MDSplus is provided so create a new one

        # Establish new remote connection to MDSplus
        conn = connection.Connection(self.mdsplus_server) # Connect to MDSplus server (andrew)
        
        # Open the tree and latest shot
        conn.openTree(self.mdsplus_tree, 0)

        # Write the data
        self.write_mdsplus(conn)

        # Close the tree and latest shot
        conn.closeTree(self.mdsplus_tree, 0)

    def write_mdsplus(self, conn):
        if self.shot_num == None:
            # Get current shot number using TDI expression
            self.shot_num = conn.get('$shot') 

        msg1 = "Writing data to shot number: " + self.shot_num
        msg2 = "Writing data to node: " + self.device_node
        print(msg1) 
        print(msg2)
        # Write (put) the data to the device in MDSplus
        # TODO: make channels 1 and 2 individually work as well
        conn.put(self.device_node+":CH_01", "$", self.mVChA[:] * 1000)
        #print("Ch1 written")
        conn.put(self.device_node+":CH_02", "$", self.mVChB[:] * 1000)
        #print("Ch2 written")
        conn.put(self.device_node+":CH_03", "$", self.mVChC[:] * 1000)
        #print("Ch3 written")
        conn.put(self.device_node+":CH_04", "$", self.mVChD[:] * 1000)
        #print("Ch4 written")
        conn.put(self.device_node+":DELAY", "$", np.float64(self.sample_interval*self.samples_pretrig))
        conn.put(self.device_node+":FREQ", "$", np.float64(1/self.sample_interval))
        conn.put(self.device_node+":NAME", "$", "model: " + str(self.info.variant) + " serial:" + str(self.info.serial) + " time:" + str(datetime.now()))

    def store(self):
        # Create time data
        time = np.linspace(0, (self.maxSamples - 1) * self.sample_interval, self.maxSamples)

        if self.bPlot:
            # plot data
            fig, axs = plt.subplots(4)
            fig.set_size_inches(4, 8)
            fig.suptitle(str(self.info.variant) + " serial:" + str(self.info.serial))
            
            trig_time = self.sample_interval*self.samples_pretrig
            axs[0].plot(time, self.mVChA[:], linewidth=0.5)
            axs[0].axvline(trig_time, linestyle="--")
            axs[0].set_title("Channel A")
            axs[1].plot(time, self.mVChB[:], linewidth=0.2)
            axs[1].axvline(trig_time)
            axs[1].set_title("Channel B")
            axs[2].plot(time, self.mVChC[:])
            axs[2].axvline(trig_time)
            axs[2].set_title("Channel C")
            axs[3].plot(time, self.mVChD[:])
            axs[3].axvline(trig_time)
            axs[3].set_title("Channel D")

            plt.xlabel('Time (ms)')
            plt.ylabel('Voltage (mV)')
            plt.tight_layout()
            #plt.show()
            strFile = "/home/whamdata/WHAM_Data/data_saving/" + self.device_node.split(".")[-1] + ".png"
            plt.savefig(strFile)

        if self.bMDS:
            self._write_mdsplus()

    def awg_sine(self, freq, ampl, duration):
        # send out a sine wave on the AWG
        # handle = chandle
        # offsetVoltage = 0
        # pkToPk = ampl in microvolts
        # waveType = ctypes.c_int16(0) = PS5000A_SINE
        # startFrequency = freq in Hz
        # stopFrequency = freq in Hz
        # increment = 0
        # dwellTime = duration in seconds
        # sweepType = ctypes.c_int16(1) = PS5000A_UP
        # operation = 0
        # shots = 0
        # sweeps = 0
        # triggerType = ctypes.c_int16(0) = PS5000a_SIGGEN_RISING
        # triggerSource = ctypes.c_int16(0) = P5000a_SIGGEN_NONE
        # extInThreshold = 1
        wavetype = ctypes.c_int32(0)
        sweepType = ctypes.c_int32(0)
        triggertype = ctypes.c_int32(0)
        triggerSource = ctypes.c_int32(0)
        self.status["setSigGenBuiltInV2"] = ps.ps5000aSetSigGenBuiltInV2(self.chandle, 0, int(ampl * 1e6), wavetype, freq, freq, 0, duration, sweepType, 0, 0, 0, triggertype, triggerSource, 0)
        assert_pico_ok(self.status["setSigGenBuiltInV2"])

if __name__ == "__main__":
    pico = picoscope5000(sample_interval=4e-9, samples_posttrig=6e5, samples_pretrig=1e6, trig_level=0.5, shot_num="231130009")
    pico.connect()
    pico.configure()
    pico.awg_sine(1e3, 1, 10000)
    pico.arm()
    pico.store()
    pico.close()