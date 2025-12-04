from WhamRedPitaya import WhamRedPitaya_SCPI

rp = WhamRedPitaya_SCPI("rp-f093a9.local")
#rp = WhamRedPitaya_SCPI("rp-f0918a.local")

rp.bMDS = False
rp.bPlot = True
rp.downsample_value = 1
rp.n_pts = 10e6
rp.channel = 3
rp.trig = "NOW"
rp.verbosity = 1

rp.connect()
rp.configure()
rp.arm()
rp.store()

rp.close()
