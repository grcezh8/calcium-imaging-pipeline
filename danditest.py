from dandi.dandiapi import DandiAPIClient

import os

os.makedirs("data/sample", exist_ok=True)

dandiset_id = "001425"

# #print all entities in this dandi dataset
# with DandiAPIClient() as client:
#     dandiset = client.get_dandiset(dandiset_id)

#     for asset in dandiset.get_assets():
#         if asset.path.endswith(".nwb"):
#             print(asset.path)


#print all entities in specific file
file_path = "sub-VG1-GC#48/sub-VG1-GC#48_ses-2023-08-21-task-day1_widefield+behavior.nwb"

# with DandiAPIClient() as client:
#     dandiset = client.get_dandiset(dandiset_id)
#     asset = dandiset.get_asset_by_path(file_path)

#     print(asset)

# get remote url
with DandiAPIClient() as client:
    dandiset = client.get_dandiset(dandiset_id)
    asset2 = dandiset.get_asset_by_path(file_path)

    url = asset2.get_content_url(
        follow_redirects=1,
        strip_query=True
    )

# read file
import remfile
import h5py
from pynwb import NWBHDF5IO

remote_file = remfile.File(url)

h5_file = h5py.File(remote_file, "r")

io = NWBHDF5IO(
    file=h5_file,
    mode="r"
)

nwb = io.read()

#explore the nwb file
# print(nwb.session_description)
# print(nwb.acquisition)
# print(nwb.processing)

# for name in ["body_video", "face_video", "eye_video"]:
#     video = nwb.acquisition[name]

#     print("\n", name)
#     print(video.external_file[:])

video_path = (
    "sub-VG1-GC#48_ses-2023-08-21-task-day1_widefield+behavior/"
    "sub-VG1-GC#48_ses-2023-08-21-task-day1_body-camera.mp4"
)

# with DandiAPIClient() as client:
#     dandiset = client.get_dandiset(dandiset_id)

#     asset = dandiset.get_asset_by_path(video_path)

#     print("Asset:", asset)
#     print("Size:", asset.size)

# with DandiAPIClient() as client:
#     dandiset = client.get_dandiset(dandiset_id)

#     for asset in dandiset.get_assets():
#         if "VG1-GC#48" in asset.path:
#             print(asset.path)

video_path = (
    "sub-VG1-GC#48/"
    "sub-VG1-GC#48_ses-2023-08-21-task-day1_widefield+behavior/"
    "sub-VG1-GC#48_ses-2023-08-21-task-day1_body-camera.mp4"
)

with DandiAPIClient() as client:
    dandiset = client.get_dandiset(dandiset_id)

    asset = dandiset.get_asset_by_path(video_path)

    url = asset.get_content_url(
        follow_redirects=1,
        strip_query=True
    )

import requests

url = "https://dandiarchive.s3.amazonaws.com/blobs/a3e/fe8/a3efe8c5-0d2e-4be7-bdb1-3f0a32cbb62d"

headers = {
    "Range": "bytes=0-999999"
}

response = requests.get(url, headers=headers)

ophys = nwb.processing["ophys"]
dff = ophys["DfOverF"]

video = nwb.acquisition["body_video"]

timestamps = video.timestamps[:]

import numpy as np

START = 100
END = 110

dff_series = nwb.processing["ophys"]["DfOverF"]["dFF"]
dff_b_series = nwb.processing["ophys"]["DfOverF"]["dFF_B"]
dff_v_series = nwb.processing["ophys"]["DfOverF"]["dFF_V"]

timestamps = dff_series.timestamps[:]

# Find the calcium samples inside 100–110 seconds
mask = (timestamps >= START) & (timestamps < END)

calcium_dff = dff_series.data[mask, :]
calcium_dff_b = dff_b_series.data[mask, :]
calcium_dff_v = dff_v_series.data[mask, :]
calcium_times = timestamps[mask]

np.savez(
    "data/sample/calcium_100_110.npz",
    timestamps=calcium_times,
    dff=calcium_dff,
    dff_B=calcium_dff_b,
    dff_V=calcium_dff_v
)

body = nwb.acquisition["body_video"]

body_times = body.timestamps[:]

mask = (body_times >= START) & (body_times < END)

import numpy as np
import matplotlib.pyplot as plt

data = np.load("data/sample/calcium_100_110.npz")

timestamps = data["timestamps"]
dff = data["dff"]

# print("Shape:", dff.shape)

# plt.figure(figsize=(12, 4))

# plt.plot(timestamps, dff[:, 0])

# plt.xlabel("Time (seconds)")
# plt.ylabel("dF/F")
# plt.title("ROI 0 — Calcium Activity")

# plt.show()

# print("min:", np.min(dff))
# print("max:", np.max(dff))
# print("mean:", np.mean(dff))
# print("std:", np.std(dff))

# print("\nFirst 10 values of ROI 0:")
# print(dff[:10, 0])

# print("\nStd of each ROI:")
# print(np.std(dff, axis=0))

import numpy as np
import matplotlib.pyplot as plt

data = np.load("data/sample/calcium_100_110.npz")

timestamps = data["timestamps"]
dff = data["dff"]

plt.figure(figsize=(12, 7))

plt.imshow(
    dff.T,
    aspect="auto",
    extent=[timestamps[0], timestamps[-1], 0, dff.shape[1]],
    origin="lower"
)

plt.xlabel("Time (seconds)")
plt.ylabel("ROI")
plt.title("Calcium Activity — 100–110 seconds")
plt.colorbar(label="dF/F")

plt.show()