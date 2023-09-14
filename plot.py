
from MDSmonkey import get_tree
from matplotlib import pyplot as plt

shot_num = 0

tree = get_tree(shot_num, "wham", "andrew.psl.wisc.edu")

d1c1 = tree.ech.ech_raw.rp_01.ch_01.data
d2c1 = tree.ech.ech_raw.rp_01.ch_02.data

d1c1 = d1c1.to_numpy()
d2c1 = d2c1.to_numpy()

plt.figure()
plt.plot(d1c1/2**15*20)
plt.plot(d2c1/2**15*20)
plt.savefig("test.png")