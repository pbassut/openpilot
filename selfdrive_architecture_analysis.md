# OpenPilot Selfdrive Architecture Analysis

## Overview

OpenPilot's selfdrive system is a sophisticated autonomous driving stack that uses a modular architecture to handle perception, planning, control, and vehicle integration. The system operates as a collection of interconnected processes communicating via a publish-subscribe messaging system.

## Core Components

### 1. Controls (`/selfdrive/controls/`)

#### controlsd.py - Main Control Loop
- **Purpose**: Central control daemon that orchestrates lateral and longitudinal vehicle control
- **Key Responsibilities**:
  - Runs at 100Hz (10ms cycle time)
  - Manages lateral control (steering) and longitudinal control (acceleration/braking)
  - Publishes control commands to the car interface
  - Handles state transitions between manual and automated driving

- **Architecture**:
  ```python
  Controls:
    - LatControl (Lateral Control):
      - PID Controller
      - Torque Controller
      - Angle Controller
    - LongControl (Longitudinal Control):
      - PID-based acceleration control
      - State machine for stopping/starting
  ```

#### Lateral Control Implementations
1. **PID Control** (`latcontrol_pid.py`):
   - Classic PID controller for steering angle
   - Uses vehicle model to compute desired steering angle from curvature
   - Includes feedforward term for improved response

2. **Torque Control** (`latcontrol_torque.py`):
   - Direct torque control for steering
   - Compensates for low-speed effects and friction
   - Uses lateral acceleration as primary control signal

3. **Angle Control** (`latcontrol_angle.py`):
   - Direct steering angle control
   - Used for vehicles with angle-based steering interfaces

#### Longitudinal Control
- **State Machine**:
  - `off`: Control disabled
  - `pid`: Active PID control
  - `stopping`: Deceleration to stop
  - `starting`: Initial acceleration from stop

- **PID Control**: Tracks desired acceleration with configurable gains per vehicle

### 2. Planning (`/selfdrive/controls/lib/`)

#### plannerd.py - Planning Daemon
- Runs longitudinal planning and lane departure warning
- Subscribes to model outputs and radar data
- Publishes longitudinal plan and driver assistance info

#### longitudinal_planner.py
- **MPC (Model Predictive Control)**: 
  - Plans optimal acceleration profile over 10-second horizon
  - Considers lead vehicles, desired speed, and comfort constraints
  - Two modes: 'acc' (adaptive cruise) and 'blended' (with vision)

- **Key Features**:
  - Forward collision warning (FCW)
  - Smooth following distance maintenance
  - Turn speed limiting
  - Personality modes (relaxed, standard, aggressive)

### 3. Model Execution (`/selfdrive/modeld/`)

#### modeld.py - Neural Network Inference
- **Purpose**: Runs the driving model for perception and path planning
- **Architecture**:
  - Supports both TinyGrad (on device) and ONNX (CPU) backends
  - Processes camera frames at 20Hz
  - Outputs lane lines, lead vehicles, and desired path

- **Inputs**:
  - Road camera images (main and wide)
  - Desire vector (lane change intentions)
  - Vehicle state (speed, steering)
  - Calibration data

- **Outputs**:
  - Lane line predictions
  - Lead vehicle detections
  - Desired path curvature
  - Pose estimation for localization

### 4. Car Abstraction Layer (`/selfdrive/car/`)

Located primarily in `opendbc/car/`:
- **Purpose**: Provides unified interface for different vehicle makes/models
- **Architecture**:
  ```
  CarInterface (Abstract Base)
    ├── CarState: Reads vehicle sensors
    ├── CarController: Sends control commands
    └── RadarInterface: Processes radar data
  ```

- **Key Features**:
  - Fingerprinting for automatic car detection
  - CAN bus communication abstraction
  - Safety parameter configuration
  - Firmware version checking

### 5. Self-Driving State Machine (`/selfdrive/selfdrived/`)

#### selfdrived.py - Main State Manager
- **Purpose**: Manages the overall system state and safety
- **Key States**:
  - `disabled`: System off
  - `preEnabled`: Preparing to engage
  - `enabled`: Active control
  - `softDisabling`: Gradual disengagement
  - `overriding`: Driver override active

- **Safety Features**:
  - Continuous system health monitoring
  - Driver monitoring integration
  - Fault detection and handling
  - Alert management

#### Alert System
- **AlertManager**: Prioritizes and displays alerts
- **Event System**: 
  - Tracks system events (warnings, errors, state changes)
  - Maps events to user-visible alerts
  - Handles alert priorities and durations

### 6. Localization (`/selfdrive/locationd/`)

#### locationd.py - Position and Orientation Estimation
- **Purpose**: Fuses sensor data for accurate vehicle pose estimation
- **Sensor Fusion**:
  - IMU data (accelerometer, gyroscope)
  - Camera odometry
  - GPS (when available)
  
- **Kalman Filter**:
  - 27-state extended Kalman filter
  - Estimates position, velocity, orientation, and sensor biases
  - Handles sensor delays and asynchronous updates

## System Integration

### Communication Flow
```
Camera → ModelD → PlannerD → ControlsD → Car
           ↓         ↓           ↓
      LocationD  SelfdriveD   AlertManager
```

### Key Design Patterns

1. **Publish-Subscribe Messaging**:
   - Uses cereal/msgq for inter-process communication
   - Enables modular, loosely-coupled architecture
   - Supports replay and simulation

2. **Separation of Concerns**:
   - Perception (ModelD)
   - Planning (PlannerD)
   - Control (ControlsD)
   - State Management (SelfdriveD)
   - Vehicle Interface (Car modules)

3. **Real-time Constraints**:
   - Hard real-time control loop (100Hz)
   - Soft real-time for perception (20Hz)
   - Priority-based process scheduling

4. **Safety Architecture**:
   - Multiple independent safety checks
   - Fail-safe state transitions
   - Driver monitoring integration
   - Hardware safety (Panda)

## Performance Considerations

1. **Computational Efficiency**:
   - TinyGrad for optimized neural network inference
   - C++ extensions for performance-critical paths
   - Careful memory management

2. **Latency Management**:
   - Predictive control to compensate for delays
   - Timestamp-based synchronization
   - Buffering strategies for sensor fusion

3. **Robustness**:
   - Graceful degradation with sensor failures
   - Extensive error handling
   - State recovery mechanisms

## Extensibility

The architecture supports:
- Adding new vehicle platforms via car abstraction
- Custom control algorithms via modular controllers
- Alternative perception models
- Different planning strategies
- Integration with external systems

This modular design allows OpenPilot to evolve while maintaining safety and reliability across diverse hardware platforms and vehicle types.