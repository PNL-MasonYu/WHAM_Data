from MDSplus import connection
import numpy as np
conn = connection.Connection("andrew.psl.wisc.edu")
conn.openTree("wham", 0)
data = np.array([1.0, 2.0, 3.0])
conn.put("RAW.PICOSCOPE_01:CH_01", "$", data)
conn.put("RAW.PICOSCOPE_01:FREQ", "$", 123.0)
conn.closeTree('wham', 0)


