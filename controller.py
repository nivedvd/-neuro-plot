import threading
import time

class PlotterController:
    def __init__(self):
        self.paused = False
        self.stopped = False
        self.lock = threading.Lock()

    def pause(self):
        with self.lock:
            self.paused = True

    def resume(self):
        # Resume should clear both paused and stopped so a new job can run
        with self.lock:
            self.paused = False
            self.stopped = False

    def stop(self):
        with self.lock:
            self.stopped = True

    def wait_if_paused(self):
        while True:
            with self.lock:
                if self.stopped:
                    return False
                if not self.paused:
                    return True
            time.sleep(0.1)
