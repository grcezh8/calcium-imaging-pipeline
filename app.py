import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

CALCIUM_FILE = "data/sample/calcium_100_110.npz"
VIDEO_FILE = "data/sample/body_100_110.mp4"

data = np.load(CALCIUM_FILE)

calcium = data["dff"]
timestamps = data["timestamps"]

#page
st.set_page_config(
    page_title="Calcium + Behavior Viewer",
    layout="wide"
)

st.title("Calcium Imaging + Behavior Viewer")

st.write(
    f"Calcium data: {calcium.shape[0]} samples × "
    f"{calcium.shape[1]} ROIs"
)

st.write(
    f"Time range: {timestamps[0]:.2f} – "
    f"{timestamps[-1]:.2f} seconds"
)

#time slider
selected_time = st.slider(
    "Time",
    min_value=float(timestamps[0]),
    max_value=float(timestamps[-1]),
    value=float(timestamps[0]),
    step=0.01
)

# Find calcium sample closest to selected time
calcium_idx = np.argmin(
    np.abs(timestamps - selected_time)
)

actual_calcium_time = timestamps[calcium_idx]

st.write(
    f"Selected time: {selected_time:.2f} s"
)

st.write(
    f"Closest calcium sample: "
    f"{actual_calcium_time:.2f} s"
)

#calcium heatmap
st.subheader("Calcium Activity")

fig, ax = plt.subplots(figsize=(10, 5))

ax.imshow(
    calcium.T,
    aspect="auto",
    extent=[
        timestamps[0],
        timestamps[-1],
        0,
        calcium.shape[1]
    ],
)

# Current time indicator
ax.axvline(
    selected_time,
    linewidth=2
)

ax.set_xlabel("Time (seconds)")
ax.set_ylabel("ROI")
ax.set_title("dF/F Activity")

st.pyplot(fig)

#current activity
st.subheader("Current Neural Activity")

current_calcium = calcium[calcium_idx]

st.bar_chart(current_calcium)

#video
st.subheader("Behavioral Video")

st.video(VIDEO_FILE)