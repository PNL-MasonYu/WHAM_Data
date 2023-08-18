
from MDSmonkey import get_tree
from matplotlib import pyplot as plt


#shot_num = 230818110
shot_num = 0

tree = get_tree(shot_num,"wham","andrew.psl.wisc.edu")

#d = tree.ech.ech_raw.rp_01.ch_01.data
#d = tree.raw.acq196_370.ch_01.data
d = tree.raw.rp_f0918a.ch_01.data

d = d.to_numpy()
plt.figure()
plt.plot(d)
plt.savefig("test.png")