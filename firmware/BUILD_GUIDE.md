# iNav Firmware Build Guide - Windows

**Flying Wing UAV Custom Firmware**

---

## Build Environment Options

### Option 1: WSL2 Ubuntu (⭐ RECOMMENDED)

**Pros**: Linux native, dễ cài đặt, full compatibility  
**Cons**: Tốn ~5GB disk space

#### Setup WSL2
```powershell
# 1. Install WSL2 (PowerShell as Administrator)
wsl --install

# Reboot sau khi cài xong

# 2. Verify installation
wsl --list --verbose

# 3. Access Ubuntu
wsl
```

#### Install ARM Toolchain trong WSL
```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install build tools
sudo apt install -y git build-essential cmake ninja-build

# Install ARM toolchain
sudo apt install -y gcc-arm-none-eabi

# Verify installation
arm-none-eabi-gcc --version
# Should show: arm-none-eabi-gcc (15:10.3-2021.07-4) 10.3.1 20210621
```

---

### Option 2: Docker (Good for CI/CD)

**Pros**: Isolated environment, reproducible builds  
**Cons**: Cần Docker Desktop (tốn RAM)

#### Setup
```powershell
# 1. Install Docker Desktop
# Download: https://www.docker.com/products/docker-desktop/

# 2. Create Dockerfile
```

**Dockerfile**:
```dockerfile
FROM ubuntu:22.04

RUN apt update && apt install -y \
    git \
    build-essential \
    cmake \
    ninja-build \
    gcc-arm-none-eabi \
    python3 \
    python3-pip

WORKDIR /build
```

**Build & Run**:
```powershell
# Build image
docker build -t inav-builder .

# Run container (mount source code)
docker run -it -v ${PWD}:/build inav-builder bash
```

---

### Option 3: Native Windows với MinGW (Advanced)

**Pros**: Không cần WSL/Docker  
**Cons**: Phức tạp, dễ lỗi

#### Setup
```powershell
# Install MSYS2
# Download: https://www.msys2.org/

# Trong MSYS2 terminal:
pacman -S mingw-w64-x86_64-arm-none-eabi-gcc
pacman -S mingw-w64-x86_64-cmake
pacman -S mingw-w64-x86_64-ninja
pacman -S git make
```

---

## Build iNav Firmware

### Step 1: Clone iNav Repository

**WSL/Docker/MSYS2**:
```bash
# Clone iNav
git clone https://github.com/iNavFlight/inav.git
cd inav

# Checkout stable version
git checkout 7.1.2
git submodule update --init --recursive
```

### Step 2: Identify Your Target

**LANRC F4 V3S Plus** tương thích với target:
- **MATEKF722** (recommended - F7 chip)
- **MATEKF405** (alternative - F4 chip)

Kiểm tra chip của bạn:
```
STM32F722RET6 → Use MATEKF722
STM32F405RGT6 → Use MATEKF405
```

### Step 3: Build Firmware (Stock iNav first)

```bash
# Clean previous builds
make clean

# Build for MATEKF722 target
make TARGET=MATEKF722

# Or for F405
make TARGET=MATEKF405

# Wait 2-5 minutes...
# Output: obj/inav_7.1.2_MATEKF722.hex
```

### Step 4: Test Flash (Stock Firmware)

Trước khi custom, test flash stock firmware trước:

#### Method A: iNav Configurator (Easiest)

1. Download **iNav Configurator**: https://github.com/iNavFlight/inav-configurator/releases
2. Install và mở
3. Connect FC qua USB
4. Click **Firmware Flasher** tab
5. **Load Firmware [Local]** → chọn `.hex` file
6. Click **Flash Firmware**
7. Wait ~30 seconds

#### Method B: DFU Mode (Manual)

```bash
# Install dfu-util
# WSL:
sudo apt install dfu-util

# Windows: Download from http://dfu-util.sourceforge.net/

# Put FC in DFU mode:
# 1. Disconnect USB
# 2. Hold BOOT button
# 3. Connect USB
# 4. Release BOOT button

# Verify DFU mode
dfu-util -l
# Should show: "Found DFU: [0483:df11]"

# Flash firmware
dfu-util -a 0 -s 0x08000000:leave -D obj/inav_7.1.2_MATEKF722.hex

# Disconnect and reconnect USB
```

---

## Custom Firmware Modifications

### Step 5: Create Custom Mixer

**File**: `src/main/flight/mixer_custom_twin.c`

```c
/*
 * Custom mixer for Twin-Engine Flying Wing
 */

#include "platform.h"
#include "flight/mixer.h"

#ifdef USE_MIXER_CUSTOM_TWIN

// Custom mixer rule for twin-engine flying wing
static const mixerRule_t mixerRulesTwinEngine[] = {
    // Motor 1 (Left): Throttle + Yaw differential
    { MIXER_MOTOR,  0, INPUT_STABILIZED_THROTTLE, 1000, 0 },
    { MIXER_MOTOR,  0, INPUT_STABILIZED_YAW,      -500, 0 },
    
    // Motor 2 (Right): Throttle - Yaw differential
    { MIXER_MOTOR,  1, INPUT_STABILIZED_THROTTLE, 1000, 0 },
    { MIXER_MOTOR,  1, INPUT_STABILIZED_YAW,       500, 0 },
    
    // Elevon Left: Pitch + Roll
    { MIXER_SERVO,  0, INPUT_STABILIZED_PITCH,     500, 0 },
    { MIXER_SERVO,  0, INPUT_STABILIZED_ROLL,     -500, 0 },
    
    // Elevon Right: Pitch - Roll
    { MIXER_SERVO,  1, INPUT_STABILIZED_PITCH,     500, 0 },
    { MIXER_SERVO,  1, INPUT_STABILIZED_ROLL,      500, 0 },
};

const mixer_t mixerTwinEngine = {
    .motorCount = 2,
    .servoCount = 2,
    .rules = mixerRulesTwinEngine,
    .ruleCount = sizeof(mixerRulesTwinEngine) / sizeof(mixerRule_t),
};

#endif // USE_MIXER_CUSTOM_TWIN
```

### Step 6: Register Custom Mixer

**Edit**: `src/main/flight/mixer.c`

Find the mixer array và add:
```c
// Around line 50-100, find:
const mixer_t *mixers[] = {
    &mixerQuadX,
    &mixerQuadP,
    &mixerTricopter,
    // ... other mixers ...
    &mixerTwinEngine,  // ADD THIS
    NULL
};
```

**Edit**: `src/main/flight/mixer.h`

Add declaration:
```c
// Around line 20-30:
extern const mixer_t mixerTwinEngine;  // ADD THIS
```

### Step 7: Enable in Build System

**Edit**: `src/main/target/MATEKF722/target.h`

Add near top:
```c
#define USE_MIXER_CUSTOM_TWIN  // ADD THIS
```

### Step 8: Build Custom Firmware

```bash
# Clean
make clean

# Build with custom mixer
make TARGET=MATEKF722

# New file: obj/inav_7.1.2_MATEKF722.hex (with custom mixer)
```

### Step 9: Flash Custom Firmware

Same as Step 4, but với custom `.hex` file.

---

## Configuration via CLI

### Step 10: Initial Setup

1. Connect FC qua USB
2. Open iNav Configurator
3. Go to **CLI** tab
4. Type commands:

```bash
# Set mixer to custom twin-engine
set mixer = CUSTOM
mixer load 0  # Load our custom mixer

# Configure serial ports
serial 0 1 115200 115200 0 115200  # USB
serial 2 64 115200 115200 0 115200  # UART3 for MAVLink (Pi)

# Differential thrust settings
set differential_thrust_gain = 50  # 50% authority
set differential_thrust_expo = 0.3

# Failsafe
set failsafe_procedure = RTH
set failsafe_delay = 10
set failsafe_off_delay = 5

# GPS & Navigation
set gps_provider = UBLOX
set gps_auto_config = ON
set nav_rth_altitude = 50  # RTH at 50m
set nav_rth_allow_landing = ON

# Save và reboot
save
```

### Step 11: Test on Bench

⚠️ **PROPS OFF!**

1. **Motor Test**: CLI → `motor 0 1100` (left motor should spin)
2. **Motor Test**: CLI → `motor 1 1100` (right motor should spin)
3. **Yaw Test**: Move yaw stick → motors should differential
4. **Servo Test**: Move pitch/roll stick → elevons should move
5. **Arming Test**: Arm via switch → motors should arm

---

## Troubleshooting

### Build Errors

**Error**: `arm-none-eabi-gcc: command not found`
```bash
# Install toolchain
sudo apt install gcc-arm-none-eabi
```

**Error**: `submodule not initialized`
```bash
git submodule update --init --recursive
```

**Error**: `make: *** No rule to make target`
```bash
make clean
make TARGET=MATEKF722
```

### Flash Errors

**Error**: `No DFU capable device found`
- FC không ở DFU mode
- Giữ BOOT button khi cắm USB

**Error**: `Permission denied (WSL)`
```bash
# Add udev rules
sudo nano /etc/udev/rules.d/45-dfu.rules

# Add line:
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="df11", MODE="0666"

# Reload
sudo udevadm control --reload-rules
```

**Error**: `Hex file not found`
- Check build output: `ls obj/*.hex`
- Build lại nếu cần

### CLI Errors

**Error**: `Command not found: differential_thrust_gain`
- Chức năng này custom, chưa có trong iNav stock
- Cần implement thêm hoặc dùng workaround với mixer gain

---

## Next Steps

✅ Firmware built & flashed  
→ **Configure FC**: Calibrate sensors, set failsafe  
→ **Test MAVLink**: Connect Pi và test communication  
→ **Bench test**: All functions với props off  
→ **First flight**: Manual mode first, then test autonomous  

---

## Resources

- **iNav GitHub**: https://github.com/iNavFlight/inav
- **iNav Docs**: https://github.com/iNavFlight/inav/wiki
- **iNav Configurator**: https://github.com/iNavFlight/inav-configurator
- **FC Pinout**: Check LANRC F4 V3S Plus manual
