import mne

raw = mne.io.read_raw_fif("data/sample_audvis_trunc_raw.fif", preload=True)

print(raw.info)


data = raw.get_data(picks="eeg")
print(data.shape)
print(data[0, :5])
print(data[0, :5] * 1e6)


import matplotlib.pyplot as plt

times = raw.times
data_uv = data * 1e6

plt.figure(figsize=(11, 4))
plt.plot(times, data_uv[0] - data_uv[0].mean() + 0,   label="channel 0")
plt.plot(times, data_uv[10] - data_uv[10].mean() + 80, label="channel 10")
plt.plot(times, data_uv[20] - data_uv[20].mean() + 160, label="channel 20")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (uV, shifted)")
plt.legend()
plt.savefig("plot2.png", dpi=120)
print("saved plot2.png")

import numpy as np

events = mne.find_events(raw, stim_channel="STI 014")
print(events.shape)
print(events[:5])

ids, counts = np.unique(events[:, 2], return_counts=True)
print(dict(zip(ids, counts)))

print("slice starts at sample:", raw.first_samp)

first_event_sec = (events[0, 0] - raw.first_samp) / raw.info["sfreq"]
print("first event at (s):", first_event_sec)

raw_clean = raw.copy()
raw_clean.filter(l_freq=1.0, h_freq=30.0)

before = raw.get_data(picks="eeg")[0] * 1e6
after = raw_clean.get_data(picks="eeg")[0] * 1e6

plt.figure(figsize=(11, 4))
plt.plot(raw.times, before - before.mean(), label="before")
plt.plot(raw.times, after - after.mean() + 80, label="after (1-30 Hz)")
plt.xlabel("Time (s)")
plt.ylabel("Voltage (uV, shifted)")
plt.legend()
plt.savefig("plot3.png", dpi=120)
print("saved plot3.png")

print("original:", raw.info["highpass"], raw.info["lowpass"])
print("filtered:", raw_clean.info["highpass"], raw_clean.info["lowpass"])

for t in [0.5, 2.3, 3.65, 14.45]:
    w = (raw.times > t - 0.3) & (raw.times < t + 0.3)
    print(t, "before:", before[w].max() - np.median(before),
             "after:", after[w].max() - np.median(after))

raw_eeg = raw_clean.copy().pick(["eeg", "eog", "stim"])
print("bads:", raw_eeg.info["bads"])

std_before = raw_eeg.get_data(picks="eeg").std(axis=1) * 1e6
print(std_before.round(1))
print("channel 52 is", raw_eeg.copy().pick("eeg", exclude=[]).ch_names[52])

raw_fixed = raw_eeg.copy().interpolate_bads(reset_bads=True)
std_after = raw_fixed.get_data(picks="eeg").std(axis=1) * 1e6
print("std of channel 52 after fixing:", std_after[52].round(1))


sum_before = raw_fixed.get_data(picks="eeg").sum(axis=0) * 1e6
print("sum across channels before:", sum_before[:5].round(1))

raw_ref = raw_fixed.copy().set_eeg_reference("average", projection=False)

sum_after = raw_ref.get_data(picks="eeg").sum(axis=0) * 1e6
print("sum across channels after:", sum_after[:5])


event_id = {"auditory/left": 1, "auditory/right": 2,
            "visual/left": 3, "visual/right": 4}


epochs = mne.Epochs(raw_ref, events, event_id, tmin=-0.2, tmax=0.5,
                    baseline=(None, 0), picks="eeg", preload=True)
print(epochs)
print(epochs.get_data().shape)


evoked_aud = epochs["auditory"].average()
print(evoked_aud)

aud_uv = evoked_aud.data * 1e6
t_ms = evoked_aud.times * 1000

plt.figure(figsize=(8, 4))
for row in aud_uv:
    plt.plot(t_ms, row, lw=0.6, color="teal", alpha=0.6)
plt.axvline(0, color="gray")
plt.axhline(0, color="gray")
plt.xlabel("Time from sound (ms)")
plt.ylabel("Voltage (uV)")
plt.title("Auditory average, all channels")
plt.savefig("plot4.png", dpi=120)

print("biggest absolute value (uV):", np.abs(aud_uv).max())



epochs_clean = mne.Epochs(raw_ref, events, event_id, tmin=-0.2, tmax=0.5,
                          baseline=(None, 0), picks="eeg",
                          reject=dict(eeg=150e-6), preload=True)
print(epochs_clean)
print([(i, log) for i, log in enumerate(epochs_clean.drop_log) if log])

evoked_aud_clean = epochs_clean["auditory"].average()
clean_uv = evoked_aud_clean.data * 1e6
print("biggest absolute value (uV):", np.abs(clean_uv).max())

fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
axes[0].plot(t_ms, aud_uv.T, lw=0.6, color="teal", alpha=0.6)
axes[0].set_title(f"All windows (N={evoked_aud.nave})")
axes[1].plot(t_ms, clean_uv.T, lw=0.6, color="teal", alpha=0.6)
axes[1].set_title(f"Bad window removed (N={evoked_aud_clean.nave})")
for ax in axes:
    ax.axvline(0, color="gray")
    ax.axhline(0, color="gray")
    ax.set_xlabel("Time from sound (ms)")
axes[0].set_ylabel("Voltage (uV)")
plt.savefig("plot5.png", dpi=120)


evoked_vis_clean = epochs_clean["visual"].average()

gfp_aud = evoked_aud_clean.data.std(axis=0) * 1e6
gfp_vis = evoked_vis_clean.data.std(axis=0) * 1e6

plt.figure(figsize=(8, 4))
plt.plot(t_ms, gfp_aud, color="teal", label="auditory")
plt.plot(t_ms, gfp_vis, color="orange", label="visual")
plt.axvline(0, color="gray")
plt.xlabel("Time from stimulus (ms)")
plt.ylabel("GFP (uV)")
plt.legend()
plt.savefig("plot6.png", dpi=120)

window = (t_ms >= 50) & (t_ms <= 300)
for name, g in [("auditory", gfp_aud), ("visual", gfp_vis)]:
    i = np.argmax(g[window])
    print(name, "peak at", round(t_ms[window][i], 1), "ms, height", round(g[window][i], 2), "uV")



fig, axes = plt.subplots(1, 2, figsize=(9, 4))
for ax, evk, t, name in [(axes[0], evoked_aud_clean, 0.0966, "auditory"),
                         (axes[1], evoked_vis_clean, 0.1865, "visual")]:
    i = np.argmin(np.abs(evk.times - t))
    values = evk.data[:, i] * 1e6
    lim = np.abs(values).max()
    im, _ = mne.viz.plot_topomap(values, evk.info, axes=ax, show=False,
                                 cmap="RdBu_r", vlim=(-lim, lim),
                                 contours=0, sphere=0.09)
    ax.set_title(f"{name} @ {t * 1000:.0f} ms")
    fig.colorbar(im, ax=ax, shrink=0.7, label="uV")
plt.savefig("plot7.png", dpi=120)
print("saved plot7.png")



data_all = epochs_clean.get_data() * 1e6
times_all = epochs_clean.times * 1000
win = (times_all >= 150) & (times_all <= 220)
strength = data_all[:, :, win].std(axis=1).mean(axis=1)
print("strength shape:", strength.shape)

codes = epochs_clean.events[:, 2]
is_vis = np.isin(codes, [3, 4])
print("sound windows:", (~is_vis).sum(), "picture windows:", is_vis.sum())
print("mean strength, sound:", strength[~is_vis].mean().round(2),
      " picture:", strength[is_vis].mean().round(2))

real_diff = strength[is_vis].mean() - strength[~is_vis].mean()
print("real difference:", real_diff.round(3))

rng = np.random.default_rng(0)
n_shuffles = 5000
count = 0
for _ in range(n_shuffles):
    shuffled = rng.permutation(is_vis)
    diff = strength[shuffled].mean() - strength[~shuffled].mean()
    if abs(diff) >= abs(real_diff):
        count += 1

p_value = (count + 1) / (n_shuffles + 1)
print("shuffles at least as extreme:", count, " p =", round(p_value, 4))
