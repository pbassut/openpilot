# CAN Message Injection in OpenPilot

This guide explains how CAN messages flow through the OpenPilot system and how to properly inject messages.

## CAN Message Flow Overview

1. **CarController** → Creates CAN messages based on control commands
2. **Card (card.py)** → Publishes messages to 'sendcan' service
3. **Pandad** → Subscribes to 'sendcan' and forwards to hardware
4. **Panda Hardware** → Sends messages on physical CAN bus

## Key Components

### 1. CarController (car-specific implementation)
Each car has its own `carcontroller.py` that:
- Receives control commands (steering, throttle, brake)
- Converts them to car-specific CAN messages
- Returns a list of CAN messages in format: `[(address, data, bus)]`

### 2. Card Service (selfdrive/car/card.py)
- Manages the car interface
- Calls CarController's `update()` method
- Publishes CAN messages to 'sendcan' service using:
  ```python
  self.pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
  ```

### 3. Pandad (selfdrive/pandad/pandad.cc)
- Runs a dedicated thread `can_send_thread`
- Subscribes to 'sendcan' service
- Validates message timestamps (rejects messages older than 1 second)
- Forwards messages to Panda hardware via USB

### 4. Services Definition (cereal/services.py)
- Defines 'sendcan' service: `(True, 100., 139)`
- Should log: True
- Frequency: 100 Hz
- Decimation: 139 (for logging)

## Message Format

CAN messages are tuples with three elements:
```python
(address, data, bus)
```
- **address**: CAN ID (11-bit or 29-bit integer)
- **data**: Bytes data (up to 8 bytes for standard CAN)
- **bus**: CAN bus number (0, 1, or 2)

## Proper Injection Method

To inject CAN messages into the running OpenPilot system:

```python
import cereal.messaging as messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp

# Create publisher for sendcan service
pm = messaging.PubMaster(['sendcan'])

# Create your CAN messages
can_sends = [
    (0x123, b'\x01\x02\x03\x04\x05\x06\x07\x08', 0),  # Message on bus 0
    (0x456, b'\xAA\xBB\xCC\xDD', 1),                  # Message on bus 1
]

# Convert to Cap'n Proto format and send
pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
```

## Safety Considerations

1. **Timestamp Validation**: Pandad drops messages older than 1 second
2. **Safety Model**: The Panda safety model may block certain messages
3. **Bus Assignment**: Ensure you're sending to the correct CAN bus
4. **Message Rate**: Don't overwhelm the CAN bus with too many messages

## Example Use Cases

### 1. Testing Specific CAN Messages
```python
# Send a test message every 100ms
while True:
    pm.send('sendcan', can_list_to_can_capnp([(0x200, data, 0)], msgtype='sendcan'))
    time.sleep(0.1)
```

### 2. Replaying Logged CAN Data
```python
# Read logged CAN messages and replay them
for msg in logged_messages:
    can_sends = [(msg.address, msg.data, msg.bus)]
    pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
```

### 3. Custom Control Commands
```python
# Send custom steering command (example only - be careful!)
steering_msg = create_steering_command(angle=5.0)  # Your custom function
pm.send('sendcan', can_list_to_can_capnp([steering_msg], msgtype='sendcan'))
```

## Important Notes

- Always test in a safe environment first
- Understand your car's CAN protocol before sending messages
- Monitor the CAN bus to verify your messages are being sent
- Check pandad logs for any errors or dropped messages
- Remember that the car's safety systems may override your commands