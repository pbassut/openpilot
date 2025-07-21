# CAN CLI Tool

A comprehensive command-line interface tool for safely interacting with CAN bus networks. This tool prioritizes safety and correctness while providing powerful capabilities for CAN bus operations.

## Overview

The CAN CLI tool is designed with safety as the primary concern. It implements multiple layers of protection to prevent accidental damage to vehicle systems while enabling legitimate development and testing use cases.

## Key Features

### 🛡️ Safety Framework
- **Multiple Safety Modes**: LOCKED, PRODUCTION, TESTING, and DEVELOPMENT modes with different restriction levels
- **Critical Address Protection**: Prevents sending to addresses that control steering, braking, throttle, etc.
- **Rate Limiting**: Prevents CAN bus flooding with configurable limits
- **Confirmation Prompts**: Requires explicit confirmation for dangerous operations
- **Audit Trail**: Complete logging of all operations for compliance and debugging

### 📡 Core Capabilities
- Send single or batch CAN messages
- Monitor live CAN traffic with filtering
- Record and replay CAN sessions
- DBC file support for message decoding
- Message templates for common operations
- Multiple interface support (Panda, SocketCAN, Virtual)

### 🔧 Advanced Features
- Message validation with checksums and counters
- Watchdog monitoring for long operations
- Burst mode for controlled rapid sending
- CSV import/export for batch operations
- Real-time statistics and performance monitoring

## Safety Modes

1. **LOCKED Mode**: No write operations allowed (read-only)
2. **PRODUCTION Mode**: Critical messages require confirmation, strict safety rules
3. **TESTING Mode**: Some critical messages blocked, relaxed rules for testing
4. **DEVELOPMENT Mode**: Full access with warnings, intended for development only

## Quick Start

```bash
# Monitor CAN bus (safe in any mode)
can-cli monitor live --bus 0

# Send a message in production mode (will prompt for confirmation if critical)
can-cli send single --address 0x100 --data "01 02 03 04" --bus 0

# Use development mode for testing (be careful!)
can-cli --safety-mode development send single -a 0x180 -d "00 00 00 00"

# Record CAN traffic
can-cli record start --output session.json --duration 60

# Monitor with DBC decoding
can-cli monitor live --dbc honda_civic_2016.dbc --filter 0x326
```

## Architecture

The tool is built with a modular architecture:

```
can_cli/
├── cli.py              # Main CLI entry point
├── safety/            # Safety validation and rules
├── core/             # CAN interface abstraction
├── commands/         # CLI command implementations
├── utils/           # Utilities and helpers
└── config/          # Configuration management
```

## Example Usage

See `example_usage.py` for demonstrations of:
- Safety mode behavior
- Rate limiting in action
- Message validation
- Safe sending patterns

## Safety Best Practices

1. **Always start in PRODUCTION mode** - This is the safest default
2. **Use DBC files when available** - They provide message validation
3. **Test in DEVELOPMENT mode first** - Before production use
4. **Monitor before sending** - Understand bus traffic patterns
5. **Use templates for common operations** - Reduces errors
6. **Enable audit logging** - For compliance and debugging
7. **Set appropriate rate limits** - Prevent bus flooding

## Critical Addresses

The following addresses are considered critical and have special protections:

- `0x180`: Steering Control
- `0x200`: Brake Command
- `0x220`: Throttle Control
- `0x260`: Transmission Control
- `0x343`: AEB Control
- `0x394`: Airbag Control

## Implementation Status

This is a design specification and partial implementation. The core safety framework is implemented, including:

- ✅ Safety rules engine
- ✅ Rate limiting
- ✅ Message validation
- ✅ CAN interface abstraction
- ✅ Example usage demonstrations

Still to be implemented:
- CLI command structure
- DBC file integration
- Record/replay functionality
- Configuration management
- Full test suite

## Contributing

When contributing to this tool:

1. Safety is the top priority - don't compromise on safety features
2. All changes must maintain backward compatibility with safety rules
3. New features should default to the safest option
4. Add tests for any new functionality
5. Update documentation for user-facing changes

## License

This tool is part of openpilot and follows the same licensing.