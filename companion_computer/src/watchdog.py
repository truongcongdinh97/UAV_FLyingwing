"""
Watchdog Timer for Companion Computer
Tự động reset hệ thống nếu không được "kick" trong thời gian định kỳ
"""
import threading
import time
import os
from loguru import logger

class WatchdogTimer:
    def __init__(self, timeout_s=10):
        self.timeout_s = timeout_s
        self.last_kick = time.time()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._stop_event.clear()
        self._thread.start()
        logger.info(f"Watchdog started (timeout: {self.timeout_s}s)")

    def kick(self):
        self.last_kick = time.time()

    def stop(self):
        self._stop_event.set()
        logger.info("Watchdog stopped")

    def _run(self):
        while not self._stop_event.is_set():
            if time.time() - self.last_kick > self.timeout_s:
                logger.error("Watchdog timeout! System will reset.")
                self._reset_system()
                break
            time.sleep(1)

    def _reset_system(self):
        # On Raspberry Pi, use 'sudo reboot' for real reset
        logger.error("Simulated system reset (replace with actual reboot in production)")
        # os.system('sudo reboot')

# Example usage:
if __name__ == "__main__":
    wd = WatchdogTimer(timeout_s=5)
    wd.start()
    for i in range(10):
        print(f"Tick {i}")
        wd.kick()
        time.sleep(1)
    wd.stop()
