from threading import Timer
import time
import datetime

class Wakeup(Timer):
    def __init__(self, alarm_time, type, backend, delay=180):
        self.wakeup_time = alarm_time
        self.wakeup_type = type
        self.delay = delay
        
        #now = datetime.now(self.utc)
        now = int(time.time())
        t = int((self.wakeup_time-now)-delay)
        if t < 0:
            t = 0
        super().__init__(t, backend)
    
    def cancel(self):
        return super().cancel()
    
    def join(self, timeout = None):
        return super().join(timeout)