# WSL2 Installation Guide - Complete Steps

## Issue: WSL2 Not Fully Configured

Bạn cần enable **Virtual Machine Platform** trước khi cài Ubuntu.

---

## Solution: Complete WSL2 Setup

### Step 1: Enable WSL Features (PowerShell as Admin)

**Mở PowerShell as Administrator:**
- Right-click Start menu
- Chọn "Windows PowerShell (Admin)" hoặc "Terminal (Admin)"

**Chạy commands:**

```powershell
# Enable WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# Enable Virtual Machine Platform
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Or use wsl command
wsl --install --no-distribution
```

### Step 2: Reboot

```powershell
Restart-Computer
```

### Step 3: Set WSL2 as Default (After reboot)

```powershell
wsl --set-default-version 2
```

### Step 4: Install Ubuntu

```powershell
wsl --install Ubuntu-22.04
```

### Step 5: First Launch

Mở **Ubuntu 22.04** từ Start menu:
- Tạo username và password
- Chờ setup hoàn tất

---

## Alternative: Manual Installation

Nếu `wsl --install` không hoạt động:

### 1. Download Ubuntu Manual

https://aka.ms/wslubuntu2204

- Save file `Ubuntu2204.appx`
- Double-click để cài

### 2. Enable Hyper-V (Optional, for better performance)

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

---

## Check BIOS Settings

Nếu vẫn lỗi "virtualization not enabled":

1. Reboot → Enter BIOS (F2/F10/Del key)
2. Find "Virtualization Technology" hoặc "VT-x" hoặc "AMD-V"
3. Enable it
4. Save và Exit

---

## Verify Installation

```powershell
# Check WSL version
wsl --version

# List distributions
wsl --list --verbose

# Should show:
# NAME            STATE           VERSION
# Ubuntu-22.04    Running         2
```

---

## After WSL Setup Complete

Continue với firmware build:

```bash
# In Ubuntu terminal:
cp /mnt/h/VSCode/Flying_Wing_UAV/firmware/scripts/setup_wsl.sh ~/
chmod +x ~/setup_wsl.sh
~/setup_wsl.sh
```

---

## Troubleshooting

### Error: "WSL2 requires an update to its kernel component"

Download WSL2 kernel update:
https://aka.ms/wsl2kernel

### Error: "The requested operation is successful. Changes will not be effective until the system is rebooted"

Just reboot:
```powershell
Restart-Computer
```

### Can't find Ubuntu in Start Menu

```powershell
wsl --install Ubuntu-22.04 --web-download
```

---

## Quick Commands Reference

```powershell
# Install WSL (all-in-one)
wsl --install

# Install specific distro
wsl --install -d Ubuntu-22.04

# List online distros
wsl --list --online

# List installed
wsl --list --verbose

# Set default
wsl --set-default Ubuntu-22.04

# Enter WSL
wsl

# Shutdown WSL
wsl --shutdown

# Unregister (remove) distro
wsl --unregister Ubuntu-22.04
```

---

## Next: Build Firmware

Sau khi WSL2 setup xong → xem `QUICKSTART.md`
