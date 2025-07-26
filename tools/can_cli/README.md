# OpenPilot CAN CLI Tool

A safe, comprehensive command-line interface for CAN bus operations in OpenPilot.

## ⚠️ SAFETY WARNING

This tool can send messages directly to your vehicle's CAN bus. Improper use can cause:
- Loss of vehicle control
- Damage to vehicle systems
- Personal injury or death

**NEVER** use this tool on a vehicle in motion. Always test in a safe, controlled environment.

## Features

- **Multi-level Safety Modes**: Four operation modes with increasing levels of access
- **Rate Limiting**: Prevents CAN bus flooding
- **Critical Address Protection**: Special handling for safety-critical messages
- **Message Validation**: Ensures proper message format and structure
- **Audit Logging**: Complete operation history for debugging
- **DBC Support**: Send messages using signal names from DBC files
- **Bus Monitoring**: Watch CAN traffic in real-time

## Installation

```bash
cd /path/to/openpilot
pip install -e .  # Installs openpilot dependencies

# The tool is now available at:
./tools/can_cli/can_cli.py
```

## Safety Modes

### 1. LOCKED (Default for new users)
- Read-only access
- Cannot send any messages
- Safe for learning and monitoring

### 2. PRODUCTION (Default)
- High safety checks
- Blocks critical addresses
- Requires confirmations
- Recommended for normal use

### 3. TESTING
- Moderate safety for development
- Allows some critical addresses with confirmation
- Rate limiting still active

### 4. DEVELOPMENT
- Low safety restrictions
- Full access with warnings
- Use only in controlled environments

## Usage Examples

### Basic Message Sending

```bash
# Send a simple message (production mode)
./can_cli.py send 0x123 "01 02 03 04" --bus 0

# Send in testing mode
./can_cli.py --mode testing send 0x200 "FF 00" --bus 1

# Send CAN-FD message
./can_cli.py --mode development send 0x400 "01 02 03 04 05 06 07 08 09 0A" --fd
```

### Using DBC Files

```bash
# Send steering command using Toyota DBC
./can_cli.py --mode testing send-dbc toyota "STEERING_LKA" "STEER_REQUEST=1,STEER_TORQUE_CMD=50"

# Send cruise control command
./can_cli.py send-dbc honda "ACC_HUD" "CRUISE_SPEED=65,ENABLE=1"
```

### Monitoring CAN Bus

```bash
# Monitor all buses for 30 seconds
./can_cli.py monitor --timeout 30

# Monitor only bus 0
./can_cli.py monitor --bus 0 --timeout 60

# Monitor indefinitely (Ctrl+C to stop)
./can_cli.py monitor --timeout 999999
```

### Batch Operations

Create a file `messages.txt`:
```
# Format: address data bus
0x123 "01 02 03" 0
0x456 "AA BB CC DD" 1
0x789 "11 22" 0
```

Then use with shell:
```bash
while IFS= read -r line; do
    [[ $line =~ ^#.*$ ]] && continue  # Skip comments
    ./can_cli.py send $line
done < messages.txt
```

## Configuration

The tool stores configuration and logs in `~/.openpilot/can_cli/`:

```
~/.openpilot/can_cli/
├── config.json          # User configuration
├── logs/                # Audit logs
│   └── can_cli_*.log    # Timestamped log files
└── templates/           # Message templates
```

### Custom Configuration

Create `~/.openpilot/can_cli/config.json`:

```json
{
  "default_mode": "production",
  "rate_limits": {
    "global": 100,
    "per_address": 20
  },
  "critical_addresses": {
    "0x180": "CUSTOM_STEERING",
    "0x300": "CUSTOM_CRITICAL"
  },
  "templates": {
    "wake_up": {
      "address": "0x700",
      "data": "00 00 00 00 00 00 00 00",
      "bus": 0
    }
  }
}
```

## Safety Best Practices

1. **Start with LOCKED mode**: Monitor bus traffic before sending
2. **Use DBC files**: They provide correct message formats
3. **Test incrementally**: Start with non-critical messages
4. **Monitor responses**: Watch for error messages or unusual behavior
5. **Keep logs**: Enable logging for debugging issues
6. **Understand the protocol**: Know what each message does
7. **Have a kill switch**: Be ready to power off if needed

## Troubleshooting

### "Cannot find Panda"
- Ensure Panda is connected via USB
- Check permissions: `sudo chmod 666 /dev/ttyACM*`
- Try `lsusb` to verify device is detected

### "Rate limit exceeded"
- Reduce message frequency
- Check for loops in scripts
- Increase limits in config if needed

### "Invalid DBC"
- Ensure opendbc submodule is updated
- Check DBC name matches available files
- Verify signal names are correct

## Architecture

```
can_cli.py
├── SafetyMode          # Operation mode enum
├── CANMessage          # Message representation
├── SafetyRules         # Validation logic
├── RateLimiter         # Rate control
├── CANInterface        # Core CAN operations
│   ├── connect()       # Panda connection
│   ├── send_message()  # Send with safety
│   └── monitor_bus()   # Bus monitoring
└── CANCLIApp           # CLI interface
    ├── Parser          # Argument parsing
    └── Commands        # Command handlers
```

## Contributing

When adding features, ensure:
1. Safety checks are maintained
2. New critical addresses are added to `CRITICAL_ADDRESSES`
3. Rate limiting is respected
4. Operations are logged
5. Tests are added for new functionality

## License

This tool is part of OpenPilot and follows the same MIT license.

## Support

For issues or questions:
1. Check existing issues in openpilot repository
2. Review safety documentation
3. Ask in comma.ai Discord #dev channel

Remember: **Safety is not optional**. When in doubt, don't send the message.