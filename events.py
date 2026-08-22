import json

class EventManager:
    def __init__(self):
        self.events = []

    def create_label(self, label, start_time, end_time):
        self.events.append({
            "label": label,
            "start_time": float(start_time),
            "end_time": float(end_time),
        })

    def get_all_events(self):
        return self.events

    def delete_event(self, index):
        if 0 <= index < len(self.events):
            self.events.pop(index)

    def save(self, filepath, experiment_name):
        data = {
            "experiment": experiment_name,
            "annotations": self.events,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)

        self.events = data["annotations"]