"""
Watchdog Timer cho Companion Computer trên Raspberry Pi

Chức năng:
- Giám sát hệ thống bằng cách kiểm tra periodic "kick" từ main thread
- Tự động reset hệ thống nếu không nhận được "kick" trong thời gian timeout
- Ngăn chặn hệ thống bị treo hoặc deadlock

Nguyên lý hoạt động:
1. Main thread phải gọi `kick()` định kỳ (ví dụ: mỗi giây)
2. Watchdog thread kiểm tra thời gian kể từ lần kick cuối cùng
3. Nếu vượt quá timeout, watchdog sẽ thực hiện system reset

Ứng dụng:
- Đảm bảo companion computer luôn responsive
- Tự động recover khi hệ thống bị treo
- Critical cho các ứng dụng UAV cần độ tin cậy cao

Lưu ý:
- Trong production, sử dụng `sudo reboot` để reset Raspberry Pi
- Trong development/simulation, chỉ log warning để tránh reset không mong muốn

Tác giả: Trương Công Định & Đặng Duy Long
Ngày: 2025-12-01
"""
import threading
import time
import os
from loguru import logger

class WatchdogTimer:
    """
    Watchdog Timer cho hệ thống Companion Computer
    
    Attributes:
        timeout_s: Thời gian timeout tính bằng giây
        last_kick: Timestamp của lần kick cuối cùng
        _stop_event: Event để dừng watchdog thread
        _thread: Watchdog thread chạy background
    
    Usage:
        wd = WatchdogTimer(timeout_s=10)
        wd.start()
        
        # Trong main loop:
        while True:
            # Do work...
            wd.kick()  # Reset watchdog timer
    """
    
    def __init__(self, timeout_s=10):
        """
        Khởi tạo Watchdog Timer
        
        Args:
            timeout_s: Thời gian timeout tính bằng giây (mặc định: 10s)
        """
        self.timeout_s = timeout_s
        self.last_kick = time.time()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """
        Khởi động watchdog thread
        
        Thread sẽ chạy background và kiểm tra timeout mỗi giây
        """
        self._stop_event.clear()
        self._thread.start()
        logger.info(f"Watchdog started (timeout: {self.timeout_s}s)")

    def kick(self):
        """
        Reset watchdog timer
        
        Gọi hàm này định kỳ từ main thread để chứng minh hệ thống vẫn hoạt động
        Nếu không gọi trong thời gian timeout, watchdog sẽ reset hệ thống
        """
        self.last_kick = time.time()

    def stop(self):
        """
        Dừng watchdog thread
        
        Gọi khi shutdown hệ thống để tránh reset không mong muốn
        """
        self._stop_event.set()
        logger.info("Watchdog stopped")

    def _run(self):
        """
        Main watchdog loop chạy trong background thread
        
        Kiểm tra mỗi giây xem thời gian kể từ lần kick cuối cùng có vượt quá timeout không
        Nếu vượt quá, thực hiện system reset
        """
        while not self._stop_event.is_set():
            if time.time() - self.last_kick > self.timeout_s:
                logger.error("Watchdog timeout! System will reset.")
                self._reset_system()
                break
            time.sleep(1)

    def _reset_system(self):
        """
        Thực hiện system reset
        
        Trong production (Raspberry Pi):
        - Sử dụng `sudo reboot` để reset hệ thống
        - Hoặc `sudo systemctl restart companion-computer.service` để restart service
        
        Trong development/simulation:
        - Chỉ log warning để tránh reset không mong muốn
        - Có thể implement graceful shutdown trước khi reset
        """
        # On Raspberry Pi, use 'sudo reboot' for real reset
        logger.error("Simulated system reset (replace with actual reboot in production)")
        # os.system('sudo reboot')
        
        # Production code:
        # try:
        #     logger.critical("WATCHDOG: System reset triggered")
        #     os.system('sudo reboot')
        # except Exception as e:
        #     logger.error(f"Failed to reset system: {e}")

# Example usage:
if __name__ == "__main__":
    """
    Test watchdog timer
    
    Demo:
    1. Khởi động watchdog với timeout 5 giây
    2. Kick mỗi giây trong 10 lần
    3. Dừng watchdog
    
    Test timeout scenario:
    - Comment dòng `wd.kick()` để test timeout behavior
    - Watchdog sẽ log error sau 5 giây
    """
    print("=== Testing Watchdog Timer ===")
    
    wd = WatchdogTimer(timeout_s=5)
    wd.start()
    
    try:
        for i in range(10):
            print(f"Tick {i} - Kicking watchdog")
            wd.kick()  # Comment this line to test timeout
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        wd.stop()
        print("Watchdog test completed")
