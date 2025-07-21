# Openpilot Hardware Interfaces and Sensor Systems

## Overview
Openpilot runs on comma devices (TICI - comma 3/3X, and MICI) using Qualcomm Snapdragon SoCs. The system has comprehensive hardware abstraction for sensors, cameras, GPS, CAN interface, and other peripherals.

## Hardware Architecture

### 1. Hardware Abstraction Layer (`/system/hardware/`)
- **Base Classes**: 
  - `HardwareBase` - Abstract interface defining all hardware operations
  - `ThermalConfig` - Temperature monitoring for CPU, GPU, memory, etc.
  
- **TICI Implementation** (`tici/hardware.py`):
  - Qualcomm Snapdragon 845 based
  - Manages power, networking, modem, screen brightness
  - Internal panda support (CAN interface)
  - GPIO control for various peripherals

### 2. Camera System (`/system/camerad/`)
- **Architecture**:
  - Supports multiple cameras (driver, road, wide-angle)
  - Uses Qualcomm Spectra ISP
  - VisionIPC for inter-process communication
  
- **Camera Sensors**:
  - AR0231 - 2.3MP automotive sensor
  - OX03C10 - 4MP sensor
  - OS04C10 - 4MP sensor
  
- **Features**:
  - RAW frame capture
  - Auto-exposure
  - Hardware ISP processing
  - 20 FPS operation

### 3. IMU and Motion Sensors (`/system/sensord/`)
- **Sensor Types**:
  - **BMX055**: 9-axis sensor suite
    - Accelerometer (±4g range)
    - Gyroscope (±2000°/s range)
    - Magnetometer
    - Temperature sensor
  
  - **LSM6DS3**: 6-axis IMU
    - Accelerometer (±4g, 104Hz)
    - Gyroscope
    - Temperature sensor
  
  - **MMC5603NJ**: Magnetometer

- **Features**:
  - Interrupt-driven data collection
  - Hardware self-test capabilities
  - I2C interface (bus 1)
  - Real-time sensor fusion

### 4. GPS Systems
- **Dual GPS Support**:
  
  a) **UBLOX GPS** (`/system/ubloxd/`):
  - External high-precision GPS module
  - Serial interface on `/dev/ttyHS0`
  - AssistNow online assistance data
  - GPIO control for power and reset
  - Supports GPS + GLONASS
  
  b) **Qualcomm GPS** (`/system/qcomgpsd/`):
  - Integrated modem-based GPS
  - Uses Qualcomm diagnostic interface
  - XTRA assistance data support
  - Fallback when UBLOX unavailable

### 5. CAN Interface - Panda (`/panda/`)
- **Hardware**:
  - STM32F413/STM32H725 microcontrollers
  - Supports CAN and CAN-FD
  - Multiple CAN buses (up to 4 per panda)
  - Safety model enforcement
  
- **Integration** (`/selfdrive/pandad/`):
  - Multi-panda support
  - Internal panda on TICI (SPI interface)
  - External pandas via USB
  - Real-time CAN message handling

### 6. GPIO and Pin Mappings
```python
Key GPIO pins on TICI:
- GNSS_PWR_EN (34) - GPS power control
- STM_RST_N (124) - Panda reset
- BMX055_ACCEL_INT (21) - Accelerometer interrupt
- LSM_INT (84) - LSM6DS3 interrupt
- CAM0/1/2_RSTN - Camera reset pins
```

### 7. Other Hardware Interfaces
- **Power Monitoring**: Voltage/current via `/sys/class/power_supply/`
- **Thermal Zones**: Multiple temperature sensors across SoC
- **Network**: Cellular modem (Quectel), WiFi, Ethernet support
- **Audio**: Amplifier control for alerts
- **Display**: Backlight brightness control

## Process Architecture
Key hardware-related processes:
- `camerad` - Camera capture and processing
- `sensord` - IMU data collection
- `ubloxd`/`qcomgpsd` - GPS data processing
- `pandad` - CAN interface management
- `hardwared` - Hardware monitoring and control
- `locationd` - Sensor fusion for position/orientation

## Data Flow
1. **Sensors** → Raw data collection (interrupt/polling)
2. **Processing** → Kalman filtering, sensor fusion
3. **Publishing** → Cereal messaging system
4. **Consumers** → Controls, planning, logging

## Key Features
- Hardware abstraction allows portability
- Real-time sensor processing
- Comprehensive safety checks
- Redundant systems (dual GPS)
- High-frequency sensor sampling (100Hz+)
- Temperature and power management
- Automated hardware initialization