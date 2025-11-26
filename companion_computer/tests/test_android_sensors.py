import socket
import json
import time
import sys

def listen_sensors(host='0.0.0.0', port=5555):
    """
    Lắng nghe dữ liệu cảm biến từ Android qua UDP.
    Tương thích với các App như 'Sensor Server', 'SensorStreamer', 'IMU+GPS Stream'.
    """
    print(f"--- Android Sensor Test ---")
    print(f"Listening on UDP {host}:{port}")
    print(f"1. Cài đặt App 'Sensor Server' hoặc 'Sensor Node' trên Android.")
    print(f"2. Nhập IP của máy tính này vào App.")
    print(f"3. Nhấn Start Stream.")
    print(f"---------------------------")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(1.0) # Timeout để check Ctrl+C dễ hơn
    
    count = 0
    try:
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                count += 1
                
                # Try to decode
                try:
                    text = data.decode('utf-8').strip()
                    
                    # Try JSON
                    try:
                        json_data = json.loads(text)
                        # Clear screen or just print
                        print(f"[{count}] JSON from {addr}:")
                        # In ra một số trường quan trọng nếu có
                        if 'gps' in json_data:
                            print(f"  GPS: {json_data['gps']}")
                        elif 'accelerometer' in json_data:
                            print(f"  Accel: {json_data['accelerometer']}")
                        else:
                            print(f"  Data: {str(json_data)[:100]}...")
                            
                    except json.JSONDecodeError:
                        # CSV format?
                        print(f"[{count}] RAW from {addr}: {text[:100]}")
                        
                except UnicodeDecodeError:
                    print(f"[{count}] Binary data from {addr} ({len(data)} bytes)")
                    
            except socket.timeout:
                continue
                
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    # Cho phép nhập port từ dòng lệnh
    port = 5555
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    listen_sensors(port=port)
