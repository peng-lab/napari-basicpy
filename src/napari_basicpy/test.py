import matplotlib.pyplot as plt
import numpy as np

m = 2048
n = 2048

# plt.figure(figsize=(7, 3), tight_layout=True)
fig, (ax1, ax2) = plt.subplots(1, 2)
# fig.tight_layout()
# fig.set_size_inches(n / 300, m / 300)
baseline_before = np.random.rand(100) * 200
baseline_after = np.random.rand(100) * 200
baseline_max = 1.01 * max(baseline_after.max(), baseline_before.max())
baseline_min = 0.99 * min(baseline_after.min(), baseline_before.min())
ax1.plot(baseline_before)
ax2.plot(baseline_after)
ax1.tick_params(labelsize=10)
ax2.tick_params(labelsize=10)
ax1.set_title("before BaSiCPy")
ax2.set_title("after BaSiCPy")
ax1.set_xlabel("slices")
ax2.set_xlabel("slices")
ax1.set_ylabel("baseline value")
# ax2.set_ylabel("baseline value")
ax1.set_ylim([baseline_min, baseline_max])
ax2.set_ylim([baseline_min, baseline_max])

plt.show()
