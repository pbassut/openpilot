# OpenPilot CAN CLI Tool v2 - Message Injection

This version injects CAN messages through the running OpenPilot system via the `sendcan` service.

## Key Differences from v1

- **No Direct Panda Access**: Works with running OpenPilot system
- **Message Injection**: Publishes to `sendcan` service like car controllers
- **System Integration**: Messages go through same path as control messages
- **Panda Safety Active**: Hardware safety model still applies

## Requirements

⚠️ **OpenPilot must be running** for this tool to work!

## Architecture

```
can_cli_v2.py
     ↓
PubMaster(['sendcan'])
     ↓
Cap'n Proto Message
     ↓
pandad (subscribes to sendcan)
     ↓
Panda Hardware (with safety checks)
     ↓
CAN Bus
```

## Usage Examples

### Basic Message Sending

```bash
# Send a simple message
./can_cli_v2.py send 0x123 "01 02 03 04" --bus 0

# Send in testing mode
./can_cli_v2.py --mode testing send 0x200 "FF 00" --bus 1
```

### Batch Sending

```bash
# Send multiple messages in one sendcan message
./can_cli_v2.py send-batch '[
  {"address": "0x123", "data": "01 02", "bus": 0},
  {"address": "0x456", "data": "AA BB CC", "bus": 1}
]'
```

### Continuous Sending

```bash
# Send at 10 Hz for 5 seconds
./can_cli_v2.py --mode testing send-continuous 0x100 "55 AA" --rate 10 --duration 5

# Send at 50 Hz for 10 seconds
./can_cli_v2.py --mode development send-continuous 0x200 "01 02 03" --rate 50 --duration 10
```

### Monitor CAN Traffic

```bash
# Monitor all buses through OpenPilot's can service
./can_cli_v2.py monitor --timeout 30

# Monitor specific bus
./can_cli_v2.py monitor --bus 0 --timeout 60
```

### Using DBC Files

```bash
# Send using DBC definitions
./can_cli_v2.py --mode testing send-dbc toyota "STEERING_LKA" "STEER_REQUEST=1,STEER_TORQUE_CMD=50"
```

## Safety Features

### 1. Software Safety (can_cli_v2)
- Mode-based restrictions (LOCKED, PRODUCTION, TESTING, DEVELOPMENT)
- Critical address protection
- Rate limiting
- Confirmation prompts

### 2. Hardware Safety (Panda)
- **Still Active!** Even in DEVELOPMENT mode
- Car-specific safety models
- Torque/acceleration limits
- Message validation

### 3. What This Means
- Some messages may be blocked by Panda even if can_cli allows them
- Critical control messages require appropriate Panda safety mode
- Test non-critical messages first

## Message Flow Timing

```
Your Script → sendcan → pandad → Panda → CAN Bus
    0ms        ~1ms      ~2ms     ~3ms     ~4ms
```

Messages typically reach the CAN bus within 5ms of sending.

## Integration with OpenPilot

This tool integrates seamlessly with running OpenPilot:

1. **Same Message Path**: Uses identical infrastructure as car controllers
2. **Proper Timestamps**: Messages timestamped correctly for pandad
3. **Service Integration**: Appears as another sendcan publisher
4. **Monitoring**: Can see your messages mixed with system messages

## Advanced Usage

### Custom Control Loop

```python
#!/usr/bin/env python3
import time
from can_cli_v2 import CANInjector, CANMessage, SafetyMode

# Create injector
injector = CANInjector(SafetyMode.TESTING)
injector.connect()

# Control loop at 20 Hz
rate = 20.0
period = 1.0 / rate

for i in range(100):
    # Create dynamic message
    data = bytes([i & 0xFF, (i >> 8) & 0xFF])
    msg = CANMessage(0x123, data, 0)
    
    # Send through OpenPilot
    injector.send_message(msg)
    
    time.sleep(period)

injector.disconnect()
```

### Synchronized Sending

```python
# Send messages synchronized with OpenPilot's control loop
import cereal.messaging as messaging

sm = messaging.SubMaster(['controlsState'])
injector = CANInjector(SafetyMode.TESTING)
injector.connect()

while True:
    sm.update()
    
    if sm.updated['controlsState']:
        # Send message synchronized with controls
        msg = CANMessage(0x100, b'\x01\x02', 0)
        injector.send_message(msg)
```

## Troubleshooting

### "Failed to connect to messaging system"
- Ensure OpenPilot is running: `tmux a`
- Check if managerd is running: `pgrep -f managerd`
- Verify no errors in tmux sessions

### "Message sent but no effect"
- Check Panda safety mode: may be blocking your message
- Monitor pandad logs: `tail -f /data/log/pandad.log`
- Use `monitor` command to verify message on bus

### "Rate limit exceeded"
- OpenPilot's sendcan runs at 100Hz max
- Reduce your sending rate
- Use batch sending for efficiency

## Comparison with Direct Panda Access

| Feature | Direct Panda (v1) | Via OpenPilot (v2) |
|---------|-------------------|-------------------|
| Requires OP running | No | Yes |
| Hardware safety | Configurable | Always active |
| Message latency | ~1ms | ~4ms |
| Integration | Standalone | Full integration |
| Best for | Testing/Debug | Production use |

## Best Practices

1. **Start with Monitoring**: Understand existing traffic first
2. **Test Non-Critical**: Begin with diagnostic messages (0x7XX)
3. **Respect Safety**: Panda will block dangerous messages
4. **Use DBC Files**: Ensures correct message format
5. **Log Everything**: Enable logging for debugging

## Example: Safe Testing Sequence

```bash
# 1. Monitor existing traffic
./can_cli_v2.py monitor --timeout 30

# 2. Send diagnostic query (safe)
./can_cli_v2.py send 0x7DF "02 01 00"

# 3. Try DBC-based message
./can_cli_v2.py --mode testing send-dbc toyota "ACC_CONTROL" "MINI_CAR=1"

# 4. Continuous sending test
./can_cli_v2.py --mode testing send-continuous 0x100 "AA BB" --rate 5 --duration 10
```

Remember: This tool respects OpenPilot's architecture and safety systems while providing powerful CAN injection capabilities.