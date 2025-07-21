# OpenPilot System Architecture and Data Flow

## Overview

OpenPilot is a sophisticated autonomous driving system built on a modular, process-based architecture. The system uses a publish-subscribe messaging pattern (via cereal/msgq) to enable loose coupling between components while maintaining real-time performance requirements.

## Core Architecture Principles

### 1. Process-Based Architecture
- **Manager Process**: Central orchestrator (`system/manager/manager.py`)
  - Starts/stops all child processes based on driving state
  - Monitors process health
  - Handles state transitions (onroad/offroad)
  - Configuration via `process_config.py`

### 2. Messaging System (Cereal)
- **Protocol**: Cap'n Proto for serialization
- **Transport**: msgq (shared memory) for IPC
- **Pattern**: Publish-Subscribe with topic-based routing
- **Key Components**:
  - `SubMaster`: Subscribe to multiple topics
  - `PubMaster`: Publish to topics
  - All messages defined in `cereal/log.capnp`

### 3. Service Configuration
- Services defined in `cereal/services.py`
- Each service has:
  - Logging flag
  - Update frequency
  - Decimation factor (for downsampling)

## Data Flow Architecture

### 1. Sensor Input Flow

```
Physical Sensors → Hardware Interface → Processing → Control
```

#### Camera Data Flow:
1. **Camera Hardware** → `camerad` (native process)
   - Captures frames from road/driver/wide cameras
   - Publishes: `roadCameraState`, `driverCameraState`, `wideRoadCameraState`
   - Frame rate: 20 Hz

2. **Vision Processing** → `modeld` (neural network inference)
   - Consumes camera frames
   - Runs driving model (TinyGrad on device, ONNX on PC)
   - Outputs:
     - Lane lines
     - Lead vehicles
     - Desired path curvature
   - Publishes: `modelV2` at 20 Hz

#### Radar Data Flow:
1. **Radar Hardware** → Car Interface → `radard`
   - Processes radar points from vehicle
   - Kalman filtering for lead vehicle tracking
   - Fusion with vision-based detection
   - Publishes: `radarState` at 20 Hz

#### Vehicle State Flow:
1. **CAN Bus** → `pandad` → Car Interface
   - Reads vehicle sensors (speed, steering angle, etc.)
   - Handles actuator commands
   - Safety enforcement via Panda hardware
   - Publishes: `carState` at 100 Hz

### 2. Control Flow

```
Perception → Planning → Control → Actuation
```

#### Planning Pipeline:
1. **Longitudinal Planning** (`plannerd`):
   - Model Predictive Control (MPC)
   - Plans acceleration over 10-second horizon
   - Considers lead vehicles, desired speed, comfort
   - Publishes: `longitudinalPlan` at 20 Hz

2. **Lateral Planning** (integrated in model):
   - Neural network outputs desired path
   - Curvature-based representation

#### Control Pipeline (`controlsd`):
1. **State Management**:
   - Runs at 100 Hz (hard real-time)
   - Subscribes to multiple inputs:
     - `modelV2` (desired path)
     - `carState` (vehicle state)
     - `longitudinalPlan` (target acceleration)
     - `selfdriveState` (system state)

2. **Lateral Control**:
   - Multiple implementations:
     - PID control
     - Torque control
     - Angle control
   - Outputs steering commands

3. **Longitudinal Control**:
   - PID controller for acceleration
   - State machine for stop/start
   - Outputs throttle/brake commands

4. **Command Publishing**:
   - Publishes: `carControl` with actuator commands
   - Car interface translates to vehicle-specific CAN messages

### 3. State Management Flow

#### System State (`selfdrived`):
- Manages overall system state:
  - `disabled`: System off
  - `preEnabled`: Preparing to engage
  - `enabled`: Active control
  - `softDisabling`: Gradual disengagement
  
- Safety monitoring:
  - Driver monitoring integration
  - System health checks
  - Alert management
  - Event tracking

#### Localization (`locationd`):
- Sensor fusion for vehicle pose:
  - IMU data (100 Hz)
  - Visual odometry (20 Hz)
  - GPS when available
- 27-state Extended Kalman Filter
- Publishes: `liveLocationKalman`

### 4. Key Data Flows

#### Primary Control Loop:
```
Camera (20Hz) → ModelD → Desired Path
                          ↓
Vehicle Sensors (100Hz) → ControlsD → Actuator Commands → Vehicle
                          ↑
Radar (20Hz) → PlannerD → Longitudinal Plan
```

#### State Synchronization:
```
All Processes → Event Messages → Manager/Selfdrived
                                  ↓
                            System State
                                  ↓
                            UI/Alerts
```

## Message Types and Topics

### High-Frequency Topics (100Hz):
- `carState`: Vehicle sensor data
- `carControl`: Actuator commands
- `controlsState`: Control system state
- `sendcan`: CAN messages to vehicle

### Medium-Frequency Topics (20Hz):
- `modelV2`: Neural network outputs
- `radarState`: Radar tracking
- `longitudinalPlan`: Speed/acceleration plan
- `cameraOdometry`: Visual position tracking

### Low-Frequency Topics:
- `carParams`: Vehicle configuration
- `liveParameters`: Calibrated vehicle model
- `managerState`: Process health
- `deviceState`: Hardware status

## Performance Characteristics

### Real-Time Constraints:
- **Hard Real-Time**: Control loop (100Hz, 10ms deadline)
- **Soft Real-Time**: Perception (20Hz, 50ms deadline)
- **Priority Scheduling**: RT processes get CPU priority

### Latency Management:
- Timestamp-based synchronization
- Predictive control compensates for delays
- Buffering for asynchronous sensor fusion

### Resource Management:
- Separate processes for isolation
- Shared memory for efficient IPC
- GPU acceleration for neural networks
- Careful memory management

## Safety Architecture

### Multiple Layers:
1. **Hardware Safety** (Panda):
   - Independent safety MCU
   - Enforces limits on commands
   - Watchdog monitoring

2. **Software Safety**:
   - State machine ensures safe transitions
   - Multiple independent checks
   - Graceful degradation

3. **Driver Monitoring**:
   - Attention tracking
   - Hands-on-wheel detection
   - Override detection

## Extensibility

The architecture supports:
- New vehicle platforms via car abstraction layer
- Custom control algorithms
- Alternative perception models
- Different planning strategies
- External integrations

This modular design enables continuous improvement while maintaining safety and reliability across diverse hardware and vehicles.