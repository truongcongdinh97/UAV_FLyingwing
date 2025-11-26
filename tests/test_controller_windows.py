import pygame
import time
import os
import sys

def main():
    # Khởi tạo Pygame
    pygame.init()
    pygame.joystick.init()

    # Kiểm tra số lượng tay cầm
    joystick_count = pygame.joystick.get_count()
    
    if joystick_count == 0:
        print("❌ KHÔNG TÌM THẤY TAY CẦM NÀO!")
        print("Hãy đảm bảo bạn đã cắm RadioMaster Pocket vào và chọn chế độ 'USB Joystick (HID)' trên tay cầm.")
        input("Nhấn Enter để thoát...")
        return

    # Chọn tay cầm đầu tiên
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print(f"✅ Đã kết nối: {joystick.get_name()}")
    print(f"🆔 ID: {joystick.get_id()}")
    print(f"🕹️  Số trục (Axes): {joystick.get_numaxes()}")
    print(f"🔘 Số nút (Buttons): {joystick.get_numbuttons()}")
    print(f"🎩 Số Hat (D-pad): {joystick.get_numhats()}")
    print("-" * 50)
    print("Đang đọc dữ liệu... Nhấn Ctrl+C để dừng.")
    time.sleep(2)

    try:
        while True:
            # Cập nhật sự kiện từ hệ thống
            pygame.event.pump()

            # Xóa màn hình console để hiển thị mượt (Windows dùng 'cls')
            os.system('cls' if os.name == 'nt' else 'clear')

            print(f"🎮 CONTROLLER: {joystick.get_name()}")
            print("=" * 50)

            # --- HIỂN THỊ TRỤC (STICKS / POTS) ---
            print(f"📊 AXES (Thường là 4 kênh chính AETR + Sliders):")
            num_axes = joystick.get_numaxes()
            for i in range(num_axes):
                val = joystick.get_axis(i)
                # Vẽ thanh trạng thái đơn giản
                # Giá trị từ -1.0 đến 1.0
                bar_len = int((val + 1) * 10)  # Quy đổi ra 0-20 ký tự
                bar = "█" * bar_len + "-" * (20 - bar_len)
                print(f"  Axis {i:02d}: {val:>6.3f} |{bar}|")

            print("-" * 50)

            # --- HIỂN THỊ NÚT (SWITCHES / AUX CHANNELS) ---
            # RadioMaster thường map các công tắc (SA, SB, SC...) thành các nút bấm
            print(f"🔘 BUTTONS (Thường là các công tắc AUX):")
            num_buttons = joystick.get_numbuttons()
            
            # In theo hàng, mỗi hàng 8 nút
            for i in range(0, num_buttons, 8):
                chunk = []
                for j in range(i, min(i + 8, num_buttons)):
                    state = joystick.get_button(j)
                    # Hiển thị nút đang nhấn bằng màu hoặc ký tự đậm
                    char = "ON " if state else "---"
                    chunk.append(f"B{j:02d}:{char}")
                print("  " + " | ".join(chunk))

            print("-" * 50)
            print("Di chuyển cần gạt và bấm công tắc để kiểm tra.")
            
            # Tốc độ làm mới
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nĐã dừng kiểm tra.")
        pygame.quit()

if __name__ == "__main__":
    main()
