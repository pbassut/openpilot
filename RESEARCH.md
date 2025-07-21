# OpenPilot Codebase Research Document

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Directory Structure](#directory-structure)
4. [Core Components](#core-components)
5. [Hardware and Sensors](#hardware-and-sensors)
6. [Control Algorithms](#control-algorithms)
7. [Communication System](#communication-system)
8. [Data Flow](#data-flow)
9. [Safety Systems](#safety-systems)
10. [Development and Build System](#development-and-build-system)

## Project Overview

OpenPilot is an open-source operating system for robotics, currently focused on upgrading the driver assistance system in 275+ supported cars. It's developed by comma.ai and is distributed under the MIT license.

### Key Features
- **Adaptive Cruise Control (ACC)**: Maintains safe following distance
- **Automated Lane Centering (ALC)**: Keeps vehicle centered in lane
- **Forward Collision Warning (FCW)**: Alerts driver to potential collisions
- **Lane Departure Warning (LDW)**: Warns when vehicle drifts from lane
- **Driver Monitoring**: Ensures driver attention using camera

### Design Philosophy
1. **Safety First**: Multiple layers of safety checks and fail-safe mechanisms
2. **Stability**: Robust system design with graceful degradation
3. **Quality**: Extensive testing and validation
4. **Modularity**: Clean separation of concerns between components

## Architecture Overview

OpenPilot uses a modular microservice architecture with the following characteristics:

### Key Architectural Patterns
- **Process-Based Design**: Each major function runs in its own process
- **Publisher-Subscriber Pattern**: Components communicate via message passing
- **Real-Time Constraints**: Hard real-time control loop at 100Hz
- **Hardware Abstraction**: Platform-independent interfaces
- **Sensor Fusion**: Multiple data sources combined for robust perception

### System Layers
1. **Hardware Layer**: Cameras, sensors, CAN interface
2. **System Services**: Low-level drivers and data collection
3. **Perception Layer**: Neural networks and sensor processing
4. **Planning Layer**: Path planning and decision making
5. **Control Layer**: Vehicle actuation and safety monitoring
6. **UI Layer**: Driver interface and alerts

## Directory Structure

```
openpilot/
├── selfdrive/          # Core self-driving functionality
│   ├── car/            # Car-specific implementations (moved to opendbc/)
│   ├── controls/       # Control algorithms (lateral/longitudinal)
│   ├── locationd/      # Localization and positioning
│   ├── modeld/         # ML model execution
│   ├── monitoring/     # Driver monitoring system
│   ├── pandad/         # Panda hardware interface
│   ├── selfdrived/     # Main state machine
│   └── ui/             # User interface (Qt-based)
├── system/             # System-level services
│   ├── athena/         # Cloud connectivity
│   ├── camerad/        # Camera drivers
│   ├── hardware/       # Hardware abstraction layer
│   ├── loggerd/        # Data logging
│   ├── manager/        # Process management
│   ├── sensord/        # Sensor data collection
│   └── updated/        # OTA updates
├── common/             # Shared utilities
├── tools/              # Development tools
├── cereal/             # Message definitions (Cap'n Proto)
└── [submodules]        # External dependencies
    ├── panda/          # CAN interface firmware
    ├── opendbc/        # CAN database definitions
    ├── rednose/        # Kalman filter library
    ├── tinygrad/       # Neural network inference
    ├── msgq/           # Message queue implementation
    └── teleoprtc/      # WebRTC for remote operation
```

## Core Components

### 1. Controls System (`selfdrive/controls/`)

The heart of OpenPilot, responsible for vehicle control:

#### **controlsd.py** - Main Control Loop
- Runs at 100Hz (hard real-time requirement)
- Coordinates lateral and longitudinal control
- Manages state transitions and safety checks
- Integrates vehicle model and calibration
- Publishes control commands to car interface

#### **Lateral Control** - Steering Control
Multiple controller implementations:
- **PID Controller**: Classic control with speed-scheduled gains
- **Torque Controller**: Direct torque control with dynamics compensation
- **Angle Controller**: Simple angle-based control
- **LQR Controller**: Optimal control for supported vehicles
- **MPC Controller**: Model Predictive Control using ACADOS

#### **Longitudinal Control** - Speed/Acceleration Control
- **PID Mode**: Speed and acceleration control
- **MPC Mode**: Sophisticated planning with constraints
- State machine: off, starting, stopping, pid/mpc modes
- Handles following distance and cruise control

### 2. Planning System (`selfdrive/controls/plannerd.py`)

Responsible for trajectory planning and decision making:

#### **Longitudinal Planner**
- Model Predictive Control (MPC) with 10-second horizon
- Handles:
  - Following distance maintenance
  - Cruise speed tracking
  - Lead vehicle prediction
  - Comfort optimization (jerk minimization)
- Safety features:
  - Forward Collision Warning (FCW)
  - Automatic Emergency Braking (AEB) preparation
  - Dynamic following distance

#### **Lateral Planner**
- Path prediction from neural network
- Lane change assistance
- Curve speed adaptation

### 3. Perception System (`selfdrive/modeld/`)

Neural network-based perception:

#### **Model Execution**
- Runs at 20Hz on dedicated hardware
- Processes dual camera streams
- Supports multiple backends:
  - TinyGrad (on-device optimization)
  - ONNX Runtime (CPU fallback)

#### **SuperCombo Model**
Multi-task neural network providing:
- **Path Prediction**: Desired driving path
- **Lane Lines**: Lane boundary detection
- **Lead Vehicles**: Detection and tracking
- **Road Edges**: Driveable area detection
- **Desire/Intent**: Turn signals and lane change predictions

### 4. Localization System (`selfdrive/locationd/`)

Precise vehicle positioning through sensor fusion:

#### **Sensor Fusion**
- Extended Kalman Filter (EKF) implementation
- Fuses:
  - IMU data (accelerometer, gyroscope)
  - Visual odometry from cameras
  - GPS measurements (dual system)
  - Vehicle odometry (wheel speeds)

#### **Calibration**
- Online calibration of sensors
- Bias estimation for IMU
- Camera-to-vehicle alignment

### 5. State Management (`selfdrive/selfdrived/`)

Central state machine managing system operation:

#### **States**
- **Disabled**: System off, monitoring only
- **PreEnabled**: Preparing to engage
- **Enabled**: Active control
- **SoftDisabling**: Graceful disengagement

#### **Event System**
- Comprehensive alert management
- Priority-based event handling
- User notifications (visual, auditory, haptic)

#### **Safety Monitoring**
- Driver attention monitoring
- System health checks
- Environmental condition validation

### 6. Car Interface (`opendbc/car/`)

Abstraction layer for vehicle diversity:

#### **Fingerprinting**
- Automatic vehicle detection via CAN messages
- Database of supported vehicles

#### **Platform Interface**
Each car platform implements:
- `CarState`: Reading vehicle sensors
- `CarController`: Sending control commands
- `CarInterface`: High-level abstraction
- `RadarInterface`: Radar data processing

#### **Safety Parameters**
- Maximum steering torque
- Acceleration limits
- Platform-specific constraints

## Hardware and Sensors

### Comma Device Hardware (TICI Platform)

#### **Compute Platform**
- Qualcomm Snapdragon 845 SoC
- Hexagon DSP for neural network acceleration
- 6GB RAM, 128GB storage
- Passive cooling with thermal management

#### **Camera System**
Three cameras via Qualcomm Spectra ISP:
1. **Driver Camera**: OV2312, 1936x1464 @ 30fps
2. **Road Camera**: AR0231, OX03C10, or OS04C10, 1928x1208 @ 20fps
3. **Wide Camera**: OV8865, 1636x1228 @ 20fps

#### **IMU Sensors**
- **BMX055**: 9-axis sensor (accel, gyro, magnetometer)
- **LSM6DS3**: 6-axis backup IMU
- **MMC5603NJ**: Additional magnetometer
- Sampling rate: 100+ Hz via interrupts

#### **GPS Systems**
1. **UBLOX M8**: External high-precision module
   - GPS + GLONASS support
   - Assisted GPS capability
   - Raw measurements for RTK

2. **Qualcomm Modem**: Integrated GPS
   - Backup positioning
   - Network time synchronization

#### **CAN Interface (Panda)**
- STM32F4-based hardware
- Supports 3 CAN buses + CAN-FD
- Hardware safety features:
  - Voltage monitoring
  - Watchdog timer
  - Fail-safe relay control
- Communication:
  - Internal: SPI interface
  - External: USB interface

### Sensor Processing

#### **Camera Pipeline** (`system/camerad/`)
- Zero-copy frame capture
- Hardware ISP processing
- Auto-exposure control
- Frame synchronization

#### **IMU Processing** (`system/sensord/`)
- Interrupt-driven data collection
- Temperature compensation
- Timestamp alignment
- Pre-filtering

## Control Algorithms

### 1. Vehicle Model (`common/vehicle_model.py`)

Based on "The Science of Vehicle Dynamics" (Guiggiani):

#### **Dynamic Bicycle Model**
```
States: [lateral velocity (y'), yaw rate (psi')]
Inputs: [steering angle (delta), velocity (v)]

Equations:
ẏ' = (F_f + F_r) / m - v * psi'
ψ̈' = (l_f * F_f - l_r * F_r) / I

Where:
F_f = C_f * (delta - atan((y' + l_f * psi') / v))  # Front tire force
F_r = C_r * (-atan((y' - l_r * psi') / v))         # Rear tire force
```

#### **Model Switching**
- Low speed (<0.1 m/s): Kinematic model
- High speed: Full dynamic model
- Smooth transition between models

### 2. Lateral Control Algorithms

#### **PID Controller**
```python
error = desired_curvature - actual_curvature
steering_angle = Kp * error + Ki * ∫error + Kd * d(error)/dt + feedforward
```
- Speed-scheduled gains
- Anti-windup on integrator
- Feedforward from desired path

#### **Torque Controller**
```python
# Account for vehicle dynamics
lateral_accel = v² * curvature
# Include gravity compensation for road roll
torque = K_torque * (lateral_accel + g * sin(roll)) * vehicle_mass
# Apply friction compensation at low speeds
torque += friction_compensation(v)
```

#### **Model Predictive Control (MPC)**
```
Minimize over horizon T:
J = Σ(x_error² + y_error² + psi_error² + control_cost * u²)

Subject to:
- Vehicle dynamics constraints
- Actuator limits
- State boundaries
```

### 3. Longitudinal Control Algorithms

#### **PID Controller**
```python
# Velocity control
v_error = v_target - v_ego
accel_cmd = Kp * v_error + Ki * ∫v_error

# Following distance control
distance_error = distance_desired - distance_actual
v_target = v_lead + Kp_follow * distance_error
```

#### **Model Predictive Control (MPC)**
```
State: [position, velocity, acceleration]
Control: jerk

Cost function:
J = Σ(w_distance * (x_ego - x_lead - d_desired)² +
     w_velocity * (v_ego - v_cruise)² +
     w_accel * a_ego² +
     w_jerk * j_ego²)

Constraints:
- Maximum acceleration/deceleration
- Jerk limits for comfort
- Safety distance constraints
```

### 4. Kalman Filtering

Used throughout for state estimation:

#### **Simple Kalman Filter** (`common/simple_kalman.py`)
```python
# Prediction
x_pred = A * x + B * u
P_pred = A * P * A' + Q

# Update
K = P_pred * C' / (C * P_pred * C' + R)
x = x_pred + K * (z - C * x_pred)
P = (I - K * C) * P_pred
```

#### **Extended Kalman Filter** (locationd)
- Non-linear vehicle dynamics
- Multi-sensor fusion
- Online calibration

## Communication System

### Message Protocol (Cap'n Proto)

#### **Event Structure**
```capnp
struct Event {
  logMonoTime @0: UInt64;  # Nanoseconds since boot
  valid @1: Bool;          # Message validity
  union {
    carState @2: CarState;
    carControl @3: CarControl;
    modelV2 @4: ModelDataV2;
    # ... 100+ message types
  }
}
```

### Message Queue Implementation

#### **Shared Memory (msgq)**
- Lock-free circular buffer
- Memory-mapped files for IPC
- Single writer, multiple readers
- Reader tracking and cleanup

#### **Network Mode (ZMQ)**
- TCP sockets for distributed operation
- Dynamic port assignment
- Optional message conflation
- Automatic reconnection

### Pub-Sub API

#### **Publisher**
```python
pm = messaging.PubMaster(['carControl'])
msg = messaging.new_message('carControl')
msg.carControl.actuators.steer = 0.1
pm.send('carControl', msg)
```

#### **Subscriber**
```python
sm = messaging.SubMaster(['carState', 'modelV2'])
while True:
    sm.update()
    if sm.updated['carState']:
        speed = sm['carState'].vEgo
```

## Data Flow

### Sensor to Actuator Pipeline

```
1. Sensors → Raw Data Collection
   - Cameras → camerad → roadCameraState (20Hz)
   - IMU → sensord → sensorEvents (100Hz)
   - GPS → ubloxd → gpsLocation (1Hz)
   - CAN → pandad → carState (100Hz)

2. Perception → Scene Understanding
   - Camera frames → modeld → modelV2 (path, objects)
   - Radar → radard → radarState (lead vehicles)

3. Localization → Vehicle State
   - All sensors → locationd → liveLocationKalman
   - Calibration → liveCalibration

4. Planning → Desired Trajectory
   - Model output + radar → plannerd → longitudinalPlan
   - Path prediction → lateralPlan

5. Control → Actuator Commands
   - Plans + state → controlsd → carControl
   - Safety checks → sendcan → CAN bus

6. Feedback → System Monitoring
   - Driver camera → dmonitoringd → driverState
   - System health → selfdrived → alerts
```

### Real-Time Requirements

#### **Hard Real-Time (must meet deadline)**
- controlsd: 100Hz control loop
- pandad: CAN message handling
- camerad: Frame capture timing

#### **Soft Real-Time (best effort)**
- modeld: 20Hz inference
- plannerd: 20Hz planning
- UI updates: 30Hz

## Safety Systems

### Multi-Layer Safety Architecture

#### **1. Hardware Safety (Panda)**
- Independent safety MCU
- Checks torque/accel limits
- Monitors driver override
- Hardware watchdog timer
- Fail-safe relay control

#### **2. Software Safety (selfdrived)**
- State machine validation
- Sensor sanity checks
- Control authority limits
- Graceful degradation

#### **3. Driver Monitoring**
- Face detection and tracking
- Eye state detection
- Attention metrics
- Graduated alerts

#### **4. System Monitoring**
- Process health checks
- CPU/memory monitoring
- Thermal management
- Disk space management

### Safety Features

#### **Operational Limits**
- Maximum steering torque
- Speed-dependent control authority
- Acceleration/deceleration limits
- Minimum following distance

#### **Fault Detection**
- Sensor failure detection
- Communication timeouts
- Model uncertainty monitoring
- Hardware fault detection

#### **Emergency Procedures**
- Immediate disengagement triggers
- Gradual handoff protocols
- Emergency braking preparation
- Driver takeover assistance

## Development and Build System

### Build System (SCons)

#### **Key Features**
- Cross-compilation support
- Dependency management
- Parallel builds
- Cache system

#### **Build Targets**
- PC (Linux x86_64): Development
- Device (Linux aarch64): Production
- Mac (Darwin): Limited development

### Development Tools

#### **Replay System** (`tools/replay/`)
- Replay logged drives
- Debug control algorithms
- Test perception changes
- Performance profiling

#### **Cabana** (`tools/cabana/`)
- CAN bus analyzer
- Signal plotting
- DBC editing
- Real-time monitoring

#### **Testing**
- Unit tests (pytest)
- Integration tests
- Hardware-in-loop testing
- Simulation environments

### Code Quality

#### **Static Analysis**
- Type checking (mypy)
- Linting (ruff)
- Code formatting
- Security scanning

#### **Continuous Integration**
- GitHub Actions
- Automated testing
- Build verification
- Performance regression tests

## Summary

OpenPilot represents a sophisticated autonomous driving system with:

1. **Robust Architecture**: Modular design with clear separation of concerns
2. **Advanced Algorithms**: State-of-the-art control and perception
3. **Safety Focus**: Multiple independent safety layers
4. **Hardware Integration**: Efficient use of embedded hardware
5. **Extensibility**: Easy to add new vehicles and features
6. **Development Tools**: Comprehensive tooling for development and debugging

The system demonstrates how modern robotics principles can be applied to create a practical, safety-critical autonomous system that operates in real-world conditions across hundreds of vehicle models.