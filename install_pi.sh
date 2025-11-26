#!/bin/bash

# Kích hoạt lỗi nếu có lệnh nào thất bại
set -e

echo "=================================================="
echo "   BẮT ĐẦU CÀI ĐẶT MÔI TRƯỜNG CHO RASPBERRY PI"
echo "=================================================="

# 1. Cập nhật hệ thống và cài đặt thư viện hệ thống cần thiết
echo "[1/4] Cài đặt thư viện hệ thống (System Dependencies)..."
sudo apt update
# Thay thế libatlas-base-dev bằng libopenblas-dev (phổ biến hơn trên OS mới)
sudo apt install -y python3-pip python3-venv libopenblas-dev libopencv-dev

# 2. Cập nhật pip trong môi trường ảo (nếu đang chạy trong venv)
echo "[2/4] Cập nhật pip..."
pip install --upgrade pip

# 3. Cài đặt TensorFlow Lite Runtime (Xử lý riêng vì khó cài qua pip thường)
echo "[3/4] Cài đặt TensorFlow Lite Runtime..."
# Tắt chế độ dừng khi lỗi (set +e) để đoạn này không làm chết script dù cài thất bại
set +e 

# Thử cài tflite_runtime
pip install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime
if [ $? -eq 0 ]; then
    echo "-> Cài đặt tflite_runtime thành công!"
else
    echo "-> tflite_runtime thất bại. Đang thử cài 'tensorflow' thay thế..."
    # Thử cài tensorflow
    pip install tensorflow
    if [ $? -eq 0 ]; then
        echo "-> Cài đặt tensorflow thành công!"
    else
        echo "----------------------------------------------------------------"
        echo "CẢNH BÁO: KHÔNG CÀI ĐƯỢC THƯ VIỆN AI (TENSORFLOW/TFLITE)"
        echo "Nguyên nhân: Python 3.13 quá mới, chưa được hỗ trợ."
        echo "Hậu quả: Tính năng nhận diện hình ảnh sẽ không hoạt động."
        echo "GIẢI PHÁP: Script sẽ BỎ QUA và tiếp tục cài đặt các phần khác."
        echo "----------------------------------------------------------------"
    fi
fi

# Bật lại chế độ dừng khi lỗi cho các phần quan trọng sau
set -e

# 4. Cài đặt các thư viện chính cho Companion Computer
echo "[4/4] Cài đặt thư viện chính (Companion Computer)..."
if [ -f "companion_computer/requirements.txt" ]; then
    pip install -r companion_computer/requirements.txt || echo "Cảnh báo: Một số thư viện trong requirements.txt không cài được."
else
    echo "LỖI: Không tìm thấy file companion_computer/requirements.txt"
fi

# 5. Cài đặt thư viện Geofence (Cài trực tiếp để tránh lỗi file)
echo "[Phụ] Cài đặt thư viện Geofence..."
pip install shapely>=2.0.0 folium>=0.14.0 loguru>=0.7.0 pymavlink>=2.4.37 numpy>=1.24.0 geopandas>=0.14.0 requests>=2.31.0 pillow>=10.0.0

# Lưu ý: Không cài requirements_windows.txt vì đây là Linux
# Lưu ý: Không cài ground_station/requirements_web.txt vì cái đó chạy trên Laptop

echo "=================================================="
echo "   CÀI ĐẶT HOÀN TẤT! SẴN SÀNG CHẠY CODE."
echo "=================================================="
