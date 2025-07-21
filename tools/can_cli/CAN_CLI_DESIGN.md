# CAN CLI Tool - Technical Specification

## Overview
A comprehensive command-line interface tool for safely interacting with CAN bus networks. This tool prioritizes safety, correctness, and user protection while providing powerful capabilities for CAN bus operations.

## Core Principles
1. **Safety First**: Every operation must be validated against safety rules
2. **Explicit Confirmation**: Dangerous operations require explicit user confirmation
3. **Audit Trail**: All operations are logged with timestamps and context
4. **Fail-Safe Defaults**: Conservative defaults that prevent accidental damage
5. **Clear Documentation**: Every command includes warnings and best practices

## Architecture Design

### 1. Modular Structure

```
can_cli/
├── __init__.py
├── cli.py                  # Main CLI entry point
├── core/
│   ├── __init__.py
│   ├── safety.py          # Safety validation layer
│   ├── can_interface.py   # CAN bus abstraction
│   ├── message_builder.py # Message construction
│   └── validator.py       # Message validation
├── commands/
│   ├── __init__.py
│   ├── send.py           # Send commands
│   ├── monitor.py        # Monitor commands
│   ├── record.py         # Record/replay commands
│   └── config.py         # Configuration commands
├── safety/
│   ├── __init__.py
│   ├── rules.py          # Safety rule definitions
│   ├── profiles.py       # Safety profiles (dev, test, prod)
│   └── watchdog.py       # Rate limiting and monitoring
├── utils/
│   ├── __init__.py
│   ├── dbc_handler.py    # DBC file parsing
│   ├── logger.py         # Audit logging
│   └── templates.py      # Message templates
└── config/
    ├── __init__.py
    └── defaults.yaml     # Default configuration
```

### 2. Safety Framework

#### Safety Modes
```python
class SafetyMode(Enum):
    DEVELOPMENT = "development"    # Full access with warnings
    TESTING = "testing"           # Limited access, no critical messages
    PRODUCTION = "production"     # Read-only by default
    LOCKED = "locked"            # No write operations allowed
```

#### Safety Rules Engine
```python
class SafetyRules:
    def __init__(self, mode: SafetyMode):
        self.mode = mode
        self.rules = self._load_rules()
        
    def validate_message(self, msg: CANMessage) -> ValidationResult:
        """Validate a CAN message against safety rules"""
        checks = [
            self._check_address_allowed(msg),
            self._check_data_range(msg),
            self._check_rate_limit(msg),
            self._check_bus_allowed(msg),
            self._check_critical_message(msg)
        ]
        return ValidationResult(checks)
        
    def _check_critical_message(self, msg: CANMessage) -> CheckResult:
        """Check if message is in critical list requiring confirmation"""
        critical_addresses = {
            0x180: "Steering Control",
            0x200: "Brake Command",
            0x220: "Throttle Control",
            0x260: "Transmission Control"
        }
        if msg.address in critical_addresses:
            return CheckResult(
                passed=False,
                reason=f"Critical message: {critical_addresses[msg.address]}",
                requires_confirmation=True
            )
```

#### Rate Limiting
```python
class RateLimiter:
    def __init__(self):
        self.message_counts = defaultdict(int)
        self.time_windows = defaultdict(list)
        
    def check_rate(self, address: int, max_rate: float) -> bool:
        """Check if sending rate is within limits"""
        current_time = time.time()
        self.time_windows[address].append(current_time)
        
        # Clean old entries
        cutoff = current_time - 1.0  # 1 second window
        self.time_windows[address] = [
            t for t in self.time_windows[address] if t > cutoff
        ]
        
        return len(self.time_windows[address]) <= max_rate
```

### 3. Core Components

#### CAN Interface Abstraction
```python
class CANInterface:
    def __init__(self, interface_type: str = "panda"):
        self.interface = self._init_interface(interface_type)
        self.watchdog = Watchdog()
        self.logger = AuditLogger()
        
    def send_message(self, msg: CANMessage, safety_check: bool = True):
        """Send a CAN message with safety checks"""
        if safety_check:
            validation = self.safety.validate_message(msg)
            if not validation.passed:
                if validation.requires_confirmation:
                    if not self._get_user_confirmation(validation):
                        raise SafetyViolation(validation.reason)
                else:
                    raise SafetyViolation(validation.reason)
        
        # Log the attempt
        self.logger.log_send_attempt(msg, validation)
        
        # Send with watchdog monitoring
        with self.watchdog.monitor(msg):
            self.interface.can_send(msg.address, msg.data, msg.bus)
```

#### Message Builder with DBC Support
```python
class MessageBuilder:
    def __init__(self, dbc_file: Optional[str] = None):
        self.packer = CANPacker(dbc_file) if dbc_file else None
        self.templates = MessageTemplates()
        
    def build_message(self, 
                     name: str = None,
                     address: int = None,
                     data: dict = None,
                     template: str = None) -> CANMessage:
        """Build a CAN message from various inputs"""
        if template:
            return self.templates.get(template).with_data(data)
        elif name and self.packer:
            return self._build_from_dbc(name, data)
        else:
            return CANMessage(address=address, data=self._pack_data(data))
```

### 4. Command Structure

#### Main CLI Entry
```python
@click.group()
@click.option('--safety-mode', type=click.Choice(['development', 'testing', 'production', 'locked']),
              default='production', help='Safety mode for operations')
@click.option('--config', type=click.Path(), help='Configuration file path')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              default='INFO', help='Logging level')
@click.pass_context
def cli(ctx, safety_mode, config, log_level):
    """CAN CLI - Safe CAN bus interaction tool"""
    ctx.ensure_object(dict)
    ctx.obj['safety'] = SafetyRules(SafetyMode(safety_mode))
    ctx.obj['config'] = load_config(config)
    setup_logging(log_level)
```

#### Send Commands
```python
@cli.group()
@click.pass_context
def send(ctx):
    """Send CAN messages"""
    pass

@send.command()
@click.option('--address', '-a', type=str, required=True, help='CAN address (hex)')
@click.option('--data', '-d', type=str, required=True, help='Data bytes (hex)')
@click.option('--bus', '-b', type=int, default=0, help='CAN bus number')
@click.option('--repeat', '-r', type=int, default=1, help='Number of times to send')
@click.option('--interval', '-i', type=float, default=0.1, help='Interval between sends')
@click.option('--force', '-f', is_flag=True, help='Skip safety confirmation')
@click.pass_context
def single(ctx, address, data, bus, repeat, interval, force):
    """Send a single CAN message"""
    interface = CANInterface()
    
    # Parse inputs
    addr = int(address, 16)
    data_bytes = bytes.fromhex(data.replace(' ', ''))
    
    # Build message
    msg = CANMessage(address=addr, data=data_bytes, bus=bus)
    
    # Safety check
    if not force:
        validation = ctx.obj['safety'].validate_message(msg)
        if not validation.passed:
            click.echo(f"Safety check failed: {validation.reason}", err=True)
            if validation.requires_confirmation:
                if not click.confirm("Do you want to proceed?"):
                    return
    
    # Send message(s)
    for i in range(repeat):
        if i > 0:
            time.sleep(interval)
        interface.send_message(msg, safety_check=not force)
        click.echo(f"Sent: 0x{addr:03X} [{bus}] {data_bytes.hex()}")
```

#### Monitor Commands
```python
@cli.group()
def monitor():
    """Monitor CAN bus traffic"""
    pass

@monitor.command()
@click.option('--bus', '-b', type=int, help='CAN bus to monitor (all if not specified)')
@click.option('--filter', '-f', type=str, multiple=True, help='Address filter (hex)')
@click.option('--dbc', type=click.Path(exists=True), help='DBC file for decoding')
@click.option('--output', '-o', type=click.Path(), help='Output file (CSV format)')
def live(bus, filter, dbc, output):
    """Monitor live CAN traffic"""
    interface = CANInterface()
    parser = CANParser(dbc) if dbc else None
    filters = [int(f, 16) for f in filter]
    
    with OutputWriter(output) as writer:
        try:
            while True:
                messages = interface.receive_messages()
                for msg in messages:
                    if bus is not None and msg.bus != bus:
                        continue
                    if filters and msg.address not in filters:
                        continue
                    
                    # Display message
                    display_msg = format_message(msg, parser)
                    click.echo(display_msg)
                    
                    if writer:
                        writer.write(msg)
                        
        except KeyboardInterrupt:
            click.echo("\nMonitoring stopped.")
```

### 5. Configuration Management

#### Configuration Structure
```yaml
# config/defaults.yaml
safety:
  default_mode: production
  rate_limits:
    global: 1000  # messages per second
    per_address: 100  # messages per second per address
  
  blocked_addresses:
    production: [0x180, 0x200, 0x220, 0x260]  # Critical control messages
    testing: [0x180, 0x200]  # Only most critical
    development: []  # None blocked, but warnings shown
  
  require_confirmation:
    - 0x180  # Steering
    - 0x200  # Brake
    - 0x220  # Throttle
    - 0x260  # Transmission

interface:
  type: panda
  timeout_ms: 10
  
logging:
  audit_file: "~/.can_cli/audit.log"
  rotate_size: "10MB"
  keep_files: 5
  
templates:
  directory: "~/.can_cli/templates"
```

### 6. Message Templates

#### Template System
```python
class MessageTemplate:
    def __init__(self, name: str, config: dict):
        self.name = name
        self.address = config['address']
        self.default_data = config.get('data', {})
        self.description = config.get('description', '')
        self.warnings = config.get('warnings', [])
        
    def build(self, **kwargs) -> CANMessage:
        """Build message from template with overrides"""
        data = self.default_data.copy()
        data.update(kwargs)
        return CANMessage(
            address=self.address,
            data=self._pack_data(data),
            metadata={'template': self.name, 'warnings': self.warnings}
        )
```

#### Example Templates
```yaml
# templates/honda_civic.yaml
templates:
  enable_acc:
    address: 0x326
    description: "Enable Adaptive Cruise Control"
    data:
      CRUISE_ACTIVE: 1
      SET_SPEED: 0
    warnings:
      - "Ensure vehicle is in appropriate driving mode"
      
  set_speed:
    address: 0x326
    description: "Set cruise control speed"
    data:
      CRUISE_ACTIVE: 1
      SET_SPEED: 65  # mph
    warnings:
      - "Speed will be set immediately upon sending"
```

### 7. Record and Replay

#### Recording Functionality
```python
class CANRecorder:
    def __init__(self, output_file: str, filters: List[int] = None):
        self.output_file = output_file
        self.filters = filters
        self.start_time = None
        
    def record(self, interface: CANInterface, duration: Optional[float] = None):
        """Record CAN traffic to file"""
        self.start_time = time.time()
        messages = []
        
        try:
            while True:
                if duration and (time.time() - self.start_time) > duration:
                    break
                    
                batch = interface.receive_messages()
                for msg in batch:
                    if self.filters and msg.address not in self.filters:
                        continue
                    
                    messages.append({
                        'timestamp': time.time() - self.start_time,
                        'address': msg.address,
                        'data': msg.data.hex(),
                        'bus': msg.bus
                    })
                    
        except KeyboardInterrupt:
            pass
            
        # Save to file
        with open(self.output_file, 'w') as f:
            json.dump({
                'metadata': {
                    'start_time': self.start_time,
                    'duration': time.time() - self.start_time,
                    'message_count': len(messages)
                },
                'messages': messages
            }, f, indent=2)
```

#### Replay Functionality
```python
class CANReplayer:
    def __init__(self, input_file: str, safety_override: bool = False):
        self.input_file = input_file
        self.safety_override = safety_override
        
    def replay(self, interface: CANInterface, speed_factor: float = 1.0):
        """Replay recorded CAN traffic"""
        with open(self.input_file, 'r') as f:
            data = json.load(f)
            
        messages = data['messages']
        click.echo(f"Replaying {len(messages)} messages...")
        
        if not self.safety_override:
            # Check all messages for safety
            for msg_data in messages:
                msg = CANMessage(
                    address=msg_data['address'],
                    data=bytes.fromhex(msg_data['data']),
                    bus=msg_data['bus']
                )
                validation = interface.safety.validate_message(msg)
                if not validation.passed:
                    click.echo(f"Safety check failed: {validation.reason}", err=True)
                    if not click.confirm("Continue anyway?"):
                        return
                        
        # Replay messages
        start_time = time.time()
        for msg_data in messages:
            # Wait for correct timing
            target_time = start_time + (msg_data['timestamp'] / speed_factor)
            wait_time = target_time - time.time()
            if wait_time > 0:
                time.sleep(wait_time)
                
            # Send message
            msg = CANMessage(
                address=msg_data['address'],
                data=bytes.fromhex(msg_data['data']),
                bus=msg_data['bus']
            )
            interface.send_message(msg, safety_check=not self.safety_override)
```

### 8. Error Handling Strategy

```python
class CANError(Exception):
    """Base exception for CAN CLI"""
    pass

class SafetyViolation(CANError):
    """Raised when safety rules are violated"""
    pass

class InterfaceError(CANError):
    """Raised when CAN interface has issues"""
    pass

class ValidationError(CANError):
    """Raised when message validation fails"""
    pass

def safe_command(func):
    """Decorator for safe command execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SafetyViolation as e:
            click.echo(f"Safety violation: {e}", err=True)
            sys.exit(1)
        except InterfaceError as e:
            click.echo(f"Interface error: {e}", err=True)
            sys.exit(2)
        except ValidationError as e:
            click.echo(f"Validation error: {e}", err=True)
            sys.exit(3)
        except Exception as e:
            click.echo(f"Unexpected error: {e}", err=True)
            logger.exception("Unexpected error in command")
            sys.exit(255)
    return wrapper
```

### 9. Testing Approach

#### Unit Tests
```python
def test_safety_rules():
    """Test safety rule validation"""
    rules = SafetyRules(SafetyMode.PRODUCTION)
    
    # Test blocked address
    msg = CANMessage(address=0x180, data=b'\x00' * 8, bus=0)
    result = rules.validate_message(msg)
    assert not result.passed
    assert result.requires_confirmation
    
    # Test allowed address
    msg = CANMessage(address=0x300, data=b'\x00' * 8, bus=0)
    result = rules.validate_message(msg)
    assert result.passed

def test_rate_limiter():
    """Test rate limiting"""
    limiter = RateLimiter()
    
    # Send within limit
    for _ in range(10):
        assert limiter.check_rate(0x100, max_rate=100)
        
    # Exceed limit
    for _ in range(100):
        limiter.check_rate(0x100, max_rate=100)
    assert not limiter.check_rate(0x100, max_rate=100)
```

#### Integration Tests
```python
def test_send_with_safety():
    """Test sending message with safety checks"""
    interface = MockCANInterface()
    safety = SafetyRules(SafetyMode.TESTING)
    
    # Try to send critical message
    msg = CANMessage(address=0x180, data=b'\x00' * 8, bus=0)
    
    with pytest.raises(SafetyViolation):
        interface.send_message(msg, safety_check=True)
```

### 10. Example Usage

#### Basic Operations
```bash
# Monitor CAN bus 0
can-cli monitor live --bus 0

# Send a single message (will prompt for confirmation if critical)
can-cli send single --address 0x326 --data "00 00 00 00 00 00 00 00" --bus 0

# Send with DBC file
can-cli send dbc --dbc honda_civic_2016.dbc --message STEERING_CONTROL --data "STEER_TORQUE:100"

# Record CAN traffic
can-cli record start --output session.json --duration 60

# Replay recorded traffic
can-cli record replay --input session.json --speed 0.5  # Half speed
```

#### Advanced Usage
```bash
# Use development mode for testing (less restrictions)
can-cli --safety-mode development send single -a 0x180 -d "01 02 03 04" --force

# Monitor with filters and DBC decoding
can-cli monitor live --bus 0 --filter 0x326 --filter 0x330 --dbc honda.dbc

# Send from template
can-cli send template --name enable_acc --template-dir ./templates/honda/

# Batch send from file
can-cli send batch --input messages.csv --interval 0.1
```

#### Safety Warnings

Each command includes appropriate warnings:

```
$ can-cli send single --address 0x180 --data "00 00 00 00"

⚠️  WARNING: Address 0x180 is a critical control message (Steering Control)
⚠️  Sending this message could affect vehicle behavior
⚠️  Current safety mode: PRODUCTION

Safety check failed: Critical message: Steering Control
Do you want to proceed? [y/N]: 
```

### 11. Best Practices Documentation

#### Safety Guidelines
1. **Always start in PRODUCTION mode** - This is the safest default
2. **Use DBC files when available** - They provide message validation
3. **Test in DEVELOPMENT mode first** - Before production use
4. **Monitor before sending** - Understand bus traffic patterns
5. **Use templates for common operations** - Reduces errors
6. **Enable audit logging** - For compliance and debugging
7. **Set appropriate rate limits** - Prevent bus flooding
8. **Regularly review safety rules** - Keep them up to date

#### Common Pitfalls
1. **Sending on wrong bus** - Always verify bus number
2. **Incorrect byte order** - Check endianness in DBC
3. **Missing counter/checksum** - Some messages require these
4. **Flooding the bus** - Use rate limiting
5. **Ignoring safety warnings** - They exist for good reasons

This design prioritizes safety while providing powerful capabilities for CAN bus interaction. The modular architecture allows for easy extension and customization while maintaining strong safety guarantees.