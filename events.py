class EventManager:
    def __init__(self):
        self.events = {}

    def create_label(self, label):
        label = label.strip()

        if label and label not in self.events:
            self.events[label] = []

    def add_event(self, label, time):
        if label in self.events:
            self.events[label].append(float(time))
            self.events[label].sort()

    def get_events(self, label):
        return self.events.get(label, [])

    def get_all_events(self):
        return self.events