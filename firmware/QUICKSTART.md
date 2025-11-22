# iNav Firmware Build - Quick Start Guide

## WSL Setup Complete ✓

Ubuntu 22.04 đã được cài đặt. Bây giờ làm theo các bước sau:

---

## Bước 1: Mở Ubuntu Terminal

Có 3 cách:
1. **Start Menu** → tìm "Ubuntu 22.04"
2. **Windows Terminal** → New tab → chọn Ubuntu
3. **PowerShell** → gõ `wsl`

---

## Bước 2: Setup Build Environment

Trong Ubuntu terminal, chạy:

```bash
# Download setup script từ Windows
cp /mnt/h/VSCode/Flying_Wing_UAV/firmware/scripts/setup_wsl.sh ~/
chmod +x ~/setup_wsl.sh

# Run setup (mất ~5-10 phút)
~/setup_wsl.sh
```

**Hoặc manual:**

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install tools
sudo apt install -y git build-essential cmake gcc-arm-none-eabi

# Verify
arm-none-eabi-gcc --version
```

---

## Bước 3: Clone iNav

```bash
# Tạo workspace
mkdir -p ~/inav_workspace
cd ~/inav_workspace

# Clone iNav
git clone https://github.com/iNavFlight/inav.git
cd inav

# Checkout stable version
git checkout 7.1.2
git submodule update --init --recursive
```

---

## Bước 4: Build Stock Firmware (Test)

```bash
# Clean build
make clean

# Build (2-5 phút)
make TARGET=MATEKF722
```

**Kết quả:**
```
obj/inav_7.1.2_MATEKF722.hex
```

---

## Bước 5: Copy Firmware sang Windows

```bash
# Copy hex file sang Windows
cp obj/inav_7.1.2_MATEKF722.hex /mnt/h/VSCode/Flying_Wing_UAV/firmware/

# Verify
ls -lh /mnt/h/VSCode/Flying_Wing_UAV/firmware/*.hex
```

---

## Bước 6: Flash Firmware

### Method A: iNav Configurator (Recommended)

1. Download **iNav Configurator**:
   - https://github.com/iNavFlight/inav-configurator/releases
   - Chọn file `.exe` cho Windows

2. Cài đặt và mở

3. Connect FC qua USB

4. Go to **Firmware Flasher** tab

5. **Load Firmware [Local]** → chọn file `.hex`

6. Click **Flash Firmware**

7. Chờ ~30 giây

### Method B: DFU Mode (Advanced)

```bash
# Trong WSL, cài dfu-util
sudo apt install dfu-util

# Put FC in DFU mode:
# 1. Disconnect USB
# 2. Hold BOOT button
# 3. Connect USB
# 4. Release BOOT button

# Check DFU device
lsusb | grep DFU

# Flash
dfu-util -a 0 -s 0x08000000:leave -D obj/inav_7.1.2_MATEKF722.hex
```

---

## Bước 7: Configure via CLI

1. Mở iNav Configurator
2. Connect FC
3. Go to **CLI** tab
4. Copy nội dung từ `firmware/config/inav_cli_config.txt`
5. Paste vào CLI
6. Gõ `save` và Enter

---

## Troubleshooting

### "Permission denied" khi flash trong WSL

```bash
# Add udev rules
sudo nano /etc/udev/rules.d/45-dfu.rules

# Add line:
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="df11", MODE="0666"

# Reload
sudo udevadm control --reload-rules
```

### Build error "arm-none-eabi-gcc not found"

```bash
sudo apt install gcc-arm-none-eabi
which arm-none-eabi-gcc  # Should show path
```

### Access Windows files from WSL

```bash
# Windows H:\ drive
cd /mnt/h/VSCode/Flying_Wing_UAV

# Windows C:\ drive
cd /mnt/c/Users/YourName/
```

---

## Quick Build Script

Hoặc dùng script tự động:

```bash
# Copy build script
cp /mnt/h/VSCode/Flying_Wing_UAV/firmware/scripts/build_firmware.sh ~/
chmod +x ~/build_firmware.sh

# Run
~/build_firmware.sh
```

---

## Next Steps After Flash

1. ✅ Flash firmware
2. ⚙️ Configure via CLI
3. 🔧 Calibrate sensors (accelerometer, magnetometer)
4. 📡 Test RC receiver
5. 🚁 Bench test (props off!)
6. ✈️ First flight (manual mode)

---

## Files Location

**Windows side:**
```
H:\VSCode\Flying_Wing_UAV\firmware\
├── *.hex               # Built firmware
├── config/
│   └── inav_cli_config.txt
└── scripts/
    ├── setup_wsl.sh
    └── build_firmware.sh
```

**WSL side:**
```
~/inav_workspace/
└── inav/
    ├── obj/*.hex       # Build output
    └── src/            # Source code
```

---

## Useful Commands

```bash
# Check WSL version
wsl --version

# Enter WSL
wsl

# Access from PowerShell
wsl ls -la ~/inav_workspace

# Copy file WSL → Windows
wsl cp ~/file.txt /mnt/h/destination/

# Copy file Windows → WSL
wsl cp /mnt/h/source/file.txt ~/destination/
```

---

**Ready to build! 🚀**

Bây giờ mở Ubuntu terminal và chạy setup script!
