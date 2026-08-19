import cv2
import numpy as np

class Synchronizer:
    def __init__(self, calcium_timestamps, video_path):
        self.calcium_timestamps = calcium_timestamps
        self.video_path = video_path

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.num_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_duration = self.num_frames / self.fps

    #find the calcium sample closest to a given experiment time
    def get_calcium_index(self, time):
        index = np.argmin(np.abs(self.calcium_timestamps - time))
        return int(index)

    #convert experiment time to video frame numbser
    def get_video_frame_index(self, time):
        video_start_time = 100.0
        frame_index = int((time-video_start_time)*self.fps)
        frame_index = max(0, min(frame_index, self.num_frames-1))
        return frame_index

    #get the video frame corresponding to an experiment timestamp
    def get_video_frame(self, time):
        frame_index = self.get_video_frame_index(time)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = self.cap.read()
        if not success:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame

    def get_synchronized_data(self, time):
        calcium_index = self.get_calcium_index(time)
        video_frame_index = self.get_video_frame_index(time)
        frame = self.get_video_frame(time)
        return {
            "time": time,
            "calcium_index": calcium_index,
            "calcium_time": self.calcium_timestamps[calcium_index],
            "video_frame": video_frame_index,
            "frame": frame
        }

    def close(self):
        self.cap.release()
