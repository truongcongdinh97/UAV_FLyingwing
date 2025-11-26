# Hướng Dẫn Chạy Giả Lập SITL (Software In The Loop)

Thư mục này chứa các file cấu hình để chạy giả lập máy bay Flying Wing trên máy tính trước khi bay thật.

## 1. Cài Đặt Môi Trường

Để chạy được SITL, bạn cần cài đặt **Mission Planner** (trên Windows) hoặc **ArduPilot SITL** (trên Linux/WSL).

### Cách 1: Dùng Mission Planner (Dễ nhất trên Windows)
1.  Mở **Mission Planner**.
2.  Vào tab **Simulation**.
3.  Chọn **Plane** (biểu tượng máy bay).
4.  Trong ô "Extra Command line", nhập: `--param="h:\VSCode\Flying_Wing_UAV\simulation\flying_wing_sitl.param"` (Sửa lại đường dẫn cho đúng với máy bạn).
5.  Bấm **Plane** để bắt đầu chạy giả lập.

### Cách 2: Dùng WSL / Linux (Cho Dev chuyên nghiệp)
1.  Cài đặt môi trường build ArduPilot.
2.  Chạy lệnh:
    ```bash
    cd ardupilot/ArduPlane
    sim_vehicle.py -v ArduPlane -f plane --console --map --param="path/to/flying_wing_sitl.param"
    ```

## 2. Kết Nối Code Python Với Giả Lập

Sau khi giả lập đã chạy (bạn sẽ thấy máy bay trên bản đồ Mission Planner), bạn có thể chạy script Python để test code điều khiển.

1.  Mở terminal trong VS Code.
2.  Chạy lệnh:
    ```powershell
    python simulation/run_sitl_test.py --connect "tcp:127.0.0.1:5760"
    ```
    *(Lưu ý: Port mặc định của Mission Planner SITL thường là 5760 cho TCP hoặc 14550 cho UDP. Nếu không được hãy thử `udp:127.0.0.1:14550`)*

## 3. Các File Trong Thư Mục Này

*   **`flying_wing_sitl.param`**: File cấu hình chứa toàn bộ thông số PID, Servo, Failsafe đã được tinh chỉnh sơ bộ cho máy bay cánh bằng 2.2m.
*   **`run_sitl_test.py`**: Script Python đơn giản để kết nối và gửi lệnh (Arm, Takeoff, Mode) tới máy bay giả lập.

## 4. Test Với Gazebo (Nâng Cao)

Nếu bạn muốn thấy hình ảnh 3D trong Gazebo:
1.  Cần cài đặt **Gazebo** và **ArduPilot Gazebo Plugin**.
2.  Copy file model máy bay (nếu có) vào thư mục models của Gazebo.
3.  Chạy SITL với flag `-f gazebo-zephyr` (Zephyr là mẫu cánh bay có sẵn gần giống nhất).
