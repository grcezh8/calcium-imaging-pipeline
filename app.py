import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from sync import Synchronizer
from events import EventManager

CALCIUM_FILE = "data/sample/calcium_100_110.npz"
VIDEO_FILE = "data/sample/body_100_110.mp4"

data = np.load(CALCIUM_FILE)

calcium = data["dff"]
timestamps = data["timestamps"]

#synchronize timestamps
sync = Synchronizer(calcium_timestamps = timestamps, video_path = VIDEO_FILE)

#event annotation manager
if "event_manager" not in st.session_state:
    st.session_state.event_manager = EventManager()

event_manager = st.session_state.event_manager

#track whether an event is currently being created
if "event_start_time" not in st.session_state:
    st.session_state.event_start_time = None

#labels the user has defined (separate from marked event instances)
if "event_labels" not in st.session_state:
    st.session_state.event_labels = []

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
    "Experiment Time",
    min_value=float(timestamps[0]),
    max_value=float(timestamps[-1]),
    value=float(timestamps[0]),
    step=0.01
)

sync_data = sync.get_synchronized_data(selected_time)

# find calcium sample closest to selected time
calcium_idx = sync_data["calcium_index"]
calcium_time = sync_data["calcium_time"]

st.write(
    f"Selected time: {selected_time:.2f} s"
)

st.write(
    f"Closest calcium sample: "
    f"{calcium_time:.2f} s"
)

#calcium heatmap
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Calcium Activity")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.imshow(
        calcium.T,
        aspect = "auto",
        extent = (
            float(timestamps[0]),
            float(timestamps[-1]),
            0.0,
            float(calcium.shape[1])
        ),
    )
    #current time indicator
    ax.axvline(
        selected_time,
        linewidth=2
    )

    #behavioral events on timeline
    for event in event_manager.get_all_events():
        ax.axvline(
            event["start_time"],
            linestyle="--",
            linewidth=1
        )

        ax.text(
            event["start_time"],
            calcium.shape[1] + 1,
            event["label"],
            rotation=90,
            verticalalignment="bottom"
        )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ROI")
    ax.set_title("dF/F Activity")

    st.pyplot(fig, use_container_width=True)

    st.subheader("Marked Events")
    events_by_label = {}
    for event in event_manager.get_all_events():
        events_by_label.setdefault(event["label"], []).append(event["start_time"])

    for label, event_times in events_by_label.items():
        st.write(
            f"**{label}**: "
            + ", ".join(
                f"{time:.2f}s"
                for time in sorted(event_times)
            )
        )

with col2:
    st.subheader("Current Neural Activity")

    current_calcium = calcium[calcium_idx, :]

    fig2, ax2 = plt.subplots(figsize=(6, 4))

    ax2.bar(
        np.arange(calcium.shape[1]),
        current_calcium
    )

    ax2.set_xlabel("ROI")
    ax2.set_ylabel("dF/F")
    ax2.set_title(
        f"At {calcium_time:.2f} s"
    )

    st.pyplot(fig2, use_container_width=True)

with col3:
    st.subheader("Behavior")

    frame = sync_data["frame"]

    if frame is not None:
        st.image(
            frame,
            use_container_width=True
        )

#event annotation
st.subheader("Behavioral Annotation")

col1, col2 = st.columns(2)

with col1:
    new_event_label = st.text_input(
        "Create a new event label",
        placeholder="e.g. lever press"
    )
    if st.button("Create Event Label"):
        label = new_event_label.strip()
        if label:
            if label not in st.session_state.event_labels:
                st.session_state.event_labels.append(label)
            st.success(f'Created event label: "{label}"')
        else:
            st.warning("Please enter an event name")

with col2:
    if st.session_state.event_labels:
        selected_event = st.selectbox(
            "Event to mark",
            st.session_state.event_labels
        )
        if st.button("Mark Event At Current Time"):
            event_manager.create_label(
                selected_event,
                selected_time,
                selected_time
            )
            st.success(
                f'Marked "{selected_event}" at '
                f'{selected_time:.2f} seconds'
            )
    else:
        st.info("Create an event label first")