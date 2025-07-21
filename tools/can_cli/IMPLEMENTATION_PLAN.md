# CAN CLI Tool - Implementation Plan

## Phase 1: Core Safety Framework (Week 1)

### 1.1 Project Setup
```bash
tools/can_cli/
├── __init__.py
├── setup.py
├── requirements.txt
├── README.md
├── tests/
│   ├── __init__.py
│   ├── test_safety.py
│   ├── test_validator.py
│   └── test_interface.py
└── can_cli/
    ├── __init__.py
    ├── cli.py
    ├── core/
    ├── safety/
    ├── commands/
    ├── utils/
    └── config/
```

### 1.2 Core Safety Module
```python
# can_cli/safety/rules.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional
import yaml

class SafetyMode(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    LOCKED = "locked"

@dataclass
class SafetyViolation:
    rule: str
    message: str
    severity: str
    requires_confirmation: bool = False

@dataclass
class ValidationResult:
    passed: bool
    violations: List[SafetyViolation]
    warnings: List[str]

class SafetyRules:
    # Critical addresses that control vehicle behavior
    CRITICAL_ADDRESSES = {
        0x180: {"name": "Steering Control", "severity": "critical"},
        0x200: {"name": "Brake Command", "severity": "critical"},
        0x220: {"name": "Throttle Control", "severity": "critical"},
        0x260: {"name": "Transmission Control", "severity": "critical"},
        0x326: {"name": "Cruise Control", "severity": "high"},
        0x343: {"name": "AEB Control", "severity": "high"},
    }
    
    def __init__(self, mode: SafetyMode, config_file: Optional[str] = None):
        self.mode = mode
        self.config = self._load_config(config_file)
        self.blocked_addresses = self._get_blocked_addresses()
        
    def validate_message(self, address: int, data: bytes, bus: int) -> ValidationResult:
        violations = []
        warnings = []
        
        # Check if address is blocked in current mode
        if address in self.blocked_addresses:
            violations.append(SafetyViolation(
                rule="blocked_address",
                message=f"Address 0x{address:03X} is blocked in {self.mode.value} mode",
                severity="critical",
                requires_confirmation=False
            ))
        
        # Check if it's a critical message
        elif address in self.CRITICAL_ADDRESSES:
            addr_info = self.CRITICAL_ADDRESSES[address]
            if self.mode == SafetyMode.PRODUCTION:
                violations.append(SafetyViolation(
                    rule="critical_message",
                    message=f"Critical message: {addr_info['name']} (0x{address:03X})",
                    severity=addr_info['severity'],
                    requires_confirmation=True
                ))
            else:
                warnings.append(
                    f"⚠️  Sending to critical address: {addr_info['name']} (0x{address:03X})"
                )
        
        # Validate data length
        if len(data) > 8 and bus < 3:  # CAN 2.0
            violations.append(SafetyViolation(
                rule="invalid_data_length",
                message=f"Data length {len(data)} exceeds CAN 2.0 limit of 8 bytes",
                severity="high",
                requires_confirmation=False
            ))
        
        # Check bus validity
        if bus not in [0, 1, 2]:
            violations.append(SafetyViolation(
                rule="invalid_bus",
                message=f"Invalid bus number: {bus}",
                severity="high",
                requires_confirmation=False
            ))
        
        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )
```

### 1.3 Rate Limiter Implementation
```python
# can_cli/safety/rate_limiter.py
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class RateLimitConfig:
    global_limit: int = 1000  # messages per second
    per_address_limit: int = 100  # messages per second per address
    burst_size: int = 10  # allow burst of messages
    window_size: float = 1.0  # time window in seconds

class RateLimiter:
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.global_timestamps = deque()
        self.address_timestamps: Dict[int, deque] = defaultdict(deque)
        
    def check_and_update(self, address: int) -> tuple[bool, Optional[str]]:
        """Check if message can be sent and update counters"""
        current_time = time.time()
        
        # Clean old timestamps
        self._clean_old_timestamps(current_time)
        
        # Check global rate
        if len(self.global_timestamps) >= self.config.global_limit:
            return False, f"Global rate limit exceeded ({self.config.global_limit} msg/s)"
        
        # Check per-address rate
        if len(self.address_timestamps[address]) >= self.config.per_address_limit:
            return False, f"Address rate limit exceeded ({self.config.per_address_limit} msg/s for 0x{address:03X})"
        
        # Update timestamps
        self.global_timestamps.append(current_time)
        self.address_timestamps[address].append(current_time)
        
        return True, None
    
    def _clean_old_timestamps(self, current_time: float):
        """Remove timestamps outside the window"""
        cutoff = current_time - self.config.window_size
        
        # Clean global timestamps
        while self.global_timestamps and self.global_timestamps[0] < cutoff:
            self.global_timestamps.popleft()
        
        # Clean per-address timestamps
        for address_deque in self.address_timestamps.values():
            while address_deque and address_deque[0] < cutoff:
                address_deque.popleft()
```

### 1.4 Watchdog Implementation
```python
# can_cli/safety/watchdog.py
import threading
import time
from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class WatchdogConfig:
    timeout: float = 5.0  # seconds
    check_interval: float = 0.1  # seconds
    auto_stop: bool = True  # automatically stop operations on timeout

class Watchdog:
    def __init__(self, config: Optional[WatchdogConfig] = None, 
                 timeout_callback: Optional[Callable] = None):
        self.config = config or WatchdogConfig()
        self.timeout_callback = timeout_callback
        self._timer = None
        self._active = False
        self._last_activity = None
        
    def start(self):
        """Start watchdog monitoring"""
        self._active = True
        self._last_activity = time.time()
        self._timer = threading.Thread(target=self._monitor)
        self._timer.daemon = True
        self._timer.start()
        
    def stop(self):
        """Stop watchdog monitoring"""
        self._active = False
        if self._timer:
            self._timer.join()
            
    def feed(self):
        """Reset watchdog timer"""
        self._last_activity = time.time()
        
    def _monitor(self):
        """Monitor for timeout"""
        while self._active:
            if self._last_activity:
                elapsed = time.time() - self._last_activity
                if elapsed > self.config.timeout:
                    self._handle_timeout()
                    break
            time.sleep(self.config.check_interval)
            
    def _handle_timeout(self):
        """Handle timeout event"""
        if self.timeout_callback:
            self.timeout_callback()
        if self.config.auto_stop:
            self._active = False
```

## Phase 2: CAN Interface Layer (Week 1-2)

### 2.1 Abstract CAN Interface
```python
# can_cli/core/can_interface.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple
import time

@dataclass
class CANMessage:
    address: int
    data: bytes
    bus: int
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class BaseCANInterface(ABC):
    @abstractmethod
    def send(self, address: int, data: bytes, bus: int) -> None:
        """Send a CAN message"""
        pass
        
    @abstractmethod
    def receive(self, timeout: Optional[float] = None) -> List[CANMessage]:
        """Receive CAN messages"""
        pass
        
    @abstractmethod
    def set_safety_mode(self, mode: int) -> None:
        """Set interface safety mode"""
        pass

class PandaInterface(BaseCANInterface):
    def __init__(self):
        from panda import Panda
        self.panda = Panda()
        self._rx_buffer = []
        
    def send(self, address: int, data: bytes, bus: int) -> None:
        self.panda.can_send(address, data, bus)
        
    def receive(self, timeout: Optional[float] = None) -> List[CANMessage]:
        messages = []
        can_msgs = self.panda.can_recv()
        
        for address, dat, bus in can_msgs:
            messages.append(CANMessage(
                address=address,
                data=dat,
                bus=bus
            ))
            
        return messages
        
    def set_safety_mode(self, mode: int) -> None:
        self.panda.set_safety_mode(mode)
```

### 2.2 Message Validator
```python
# can_cli/core/validator.py
from typing import Dict, List, Optional, Any
import struct

class MessageValidator:
    def __init__(self, dbc_path: Optional[str] = None):
        self.dbc = None
        if dbc_path:
            from opendbc.can.parser import CANParser
            self.dbc = CANParser(dbc_path, [], 0)
            
    def validate_structure(self, address: int, data: bytes) -> List[str]:
        """Validate message structure"""
        errors = []
        
        # Basic validation
        if address < 0 or address > 0x7FF:
            if address < 0 or address > 0x1FFFFFFF:
                errors.append(f"Invalid address: 0x{address:X}")
                
        if len(data) == 0:
            errors.append("Empty data payload")
        elif len(data) > 64:
            errors.append(f"Data too long: {len(data)} bytes (max 64)")
            
        return errors
        
    def validate_checksum(self, address: int, data: bytes, 
                         checksum_func: Optional[callable] = None) -> bool:
        """Validate message checksum if applicable"""
        if checksum_func:
            expected = checksum_func(address, data[:-1])
            actual = data[-1]
            return expected == actual
        return True
        
    def validate_counter(self, address: int, data: bytes, 
                        counter_idx: int, expected: int) -> bool:
        """Validate message counter"""
        if counter_idx < len(data):
            actual = data[counter_idx]
            return actual == expected
        return False
```

## Phase 3: CLI Commands (Week 2)

### 3.1 Main CLI Structure
```python
# can_cli/cli.py
import click
import sys
from typing import Optional
from .core.can_interface import PandaInterface
from .safety.rules import SafetyMode, SafetyRules
from .utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

@click.group()
@click.option('--safety-mode', 
              type=click.Choice(['development', 'testing', 'production', 'locked']),
              default='production',
              help='Safety mode for operations')
@click.option('--config', type=click.Path(exists=True), help='Configuration file')
@click.option('--log-level', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              default='INFO')
@click.option('--interface', 
              type=click.Choice(['panda', 'socketcan', 'virtual']),
              default='panda',
              help='CAN interface to use')
@click.pass_context
def cli(ctx, safety_mode, config, log_level, interface):
    """CAN CLI - Safe CAN bus interaction tool
    
    This tool provides safe interaction with CAN buses, including message
    sending, monitoring, recording, and replay functionality.
    """
    ctx.ensure_object(dict)
    
    # Setup logging
    setup_logging(log_level)
    
    # Initialize safety rules
    mode = SafetyMode(safety_mode)
    ctx.obj['safety'] = SafetyRules(mode, config)
    
    # Initialize interface
    if interface == 'panda':
        ctx.obj['interface'] = PandaInterface()
    else:
        click.echo(f"Interface {interface} not yet implemented", err=True)
        sys.exit(1)
        
    # Log startup
    logger.info(f"CAN CLI started in {safety_mode} mode with {interface} interface")

@cli.command()
@click.pass_context
def info(ctx):
    """Display system information and current configuration"""
    safety = ctx.obj['safety']
    interface = ctx.obj['interface']
    
    click.echo("CAN CLI System Information")
    click.echo("=" * 40)
    click.echo(f"Safety Mode: {safety.mode.value}")
    click.echo(f"Interface: {type(interface).__name__}")
    click.echo(f"Blocked Addresses: {len(safety.blocked_addresses)}")
    
    if safety.blocked_addresses:
        click.echo("\nBlocked addresses in current mode:")
        for addr in sorted(safety.blocked_addresses):
            click.echo(f"  - 0x{addr:03X}")
```

### 3.2 Send Commands
```python
# can_cli/commands/send.py
import click
import time
from typing import Optional
from ..core.can_interface import CANMessage
from ..utils.formatters import parse_hex_string

@click.group()
def send():
    """Send CAN messages"""
    pass

@send.command()
@click.option('--address', '-a', required=True, help='CAN ID in hex (e.g., 0x100)')
@click.option('--data', '-d', required=True, help='Data in hex (e.g., "01 02 03")')
@click.option('--bus', '-b', type=int, default=0, help='CAN bus number')
@click.option('--count', '-c', type=int, default=1, help='Number of messages')
@click.option('--interval', '-i', type=float, default=0.0, help='Interval between messages (seconds)')
@click.option('--force', '-f', is_flag=True, help='Skip safety confirmations')
@click.pass_context
def single(ctx, address, data, bus, count, interval, force):
    """Send single or multiple CAN messages"""
    safety = ctx.obj['safety']
    interface = ctx.obj['interface']
    logger = ctx.obj.get('logger')
    
    # Parse inputs
    try:
        addr = int(address, 16)
        data_bytes = parse_hex_string(data)
    except ValueError as e:
        click.echo(f"Error parsing input: {e}", err=True)
        return
    
    # Validate message
    result = safety.validate_message(addr, data_bytes, bus)
    
    if not result.passed:
        click.echo("Safety validation failed:", err=True)
        for violation in result.violations:
            click.echo(f"  - {violation.message}", err=True)
            
        if any(v.requires_confirmation for v in result.violations) and not force:
            if not click.confirm("\nDo you want to proceed anyway?"):
                return
        elif not force:
            click.echo("\nUse --force to override safety checks", err=True)
            return
    
    # Show warnings
    for warning in result.warnings:
        click.echo(warning, err=True)
    
    # Send messages
    click.echo(f"Sending {count} message(s) to 0x{addr:03X} on bus {bus}")
    
    for i in range(count):
        try:
            interface.send(addr, data_bytes, bus)
            click.echo(f"  [{i+1}/{count}] Sent: 0x{addr:03X} <- {data_bytes.hex()}")
            
            if i < count - 1 and interval > 0:
                time.sleep(interval)
                
        except Exception as e:
            click.echo(f"  [{i+1}/{count}] Failed: {e}", err=True)
            if not force:
                break
```

## Phase 4: Monitoring and Recording (Week 2-3)

### 4.1 Monitor Command
```python
# can_cli/commands/monitor.py
import click
import time
from collections import defaultdict
from typing import Set, Optional

@click.group()
def monitor():
    """Monitor CAN bus traffic"""
    pass

@monitor.command()
@click.option('--bus', '-b', type=int, help='Specific bus to monitor')
@click.option('--filter', '-f', multiple=True, help='Filter by address (hex)')
@click.option('--exclude', '-x', multiple=True, help='Exclude addresses (hex)')
@click.option('--format', type=click.Choice(['simple', 'detailed', 'csv']), default='simple')
@click.option('--stats', is_flag=True, help='Show message statistics')
@click.pass_context
def live(ctx, bus, filter, exclude, format, stats):
    """Monitor live CAN traffic"""
    interface = ctx.obj['interface']
    
    # Parse filters
    filter_addrs = {int(f, 16) for f in filter} if filter else None
    exclude_addrs = {int(e, 16) for e in exclude} if exclude else set()
    
    # Statistics tracking
    message_counts = defaultdict(int)
    last_data = {}
    start_time = time.time()
    
    click.echo("Monitoring CAN traffic... Press Ctrl+C to stop")
    click.echo("-" * 60)
    
    try:
        while True:
            messages = interface.receive(timeout=0.1)
            
            for msg in messages:
                # Apply filters
                if bus is not None and msg.bus != bus:
                    continue
                if filter_addrs and msg.address not in filter_addrs:
                    continue
                if msg.address in exclude_addrs:
                    continue
                
                # Update statistics
                message_counts[msg.address] += 1
                last_data[msg.address] = msg.data
                
                # Format and display
                if format == 'simple':
                    click.echo(f"[{msg.bus}] 0x{msg.address:03X}: {msg.data.hex()}")
                elif format == 'detailed':
                    timestamp = msg.timestamp - start_time
                    click.echo(f"{timestamp:8.3f} [{msg.bus}] 0x{msg.address:03X} "
                             f"({len(msg.data):2d}): {msg.data.hex()}")
                elif format == 'csv':
                    click.echo(f"{msg.timestamp},{msg.bus},0x{msg.address:03X},"
                             f"{len(msg.data)},{msg.data.hex()}")
                
    except KeyboardInterrupt:
        click.echo("\n" + "-" * 60)
        
        if stats:
            click.echo("\nMessage Statistics:")
            total_msgs = sum(message_counts.values())
            duration = time.time() - start_time
            
            click.echo(f"Total messages: {total_msgs}")
            click.echo(f"Duration: {duration:.1f} seconds")
            click.echo(f"Average rate: {total_msgs/duration:.1f} msg/s")
            click.echo(f"\nTop addresses by frequency:")
            
            for addr, count in sorted(message_counts.items(), 
                                     key=lambda x: x[1], reverse=True)[:10]:
                rate = count / duration
                click.echo(f"  0x{addr:03X}: {count:6d} messages ({rate:6.1f} msg/s)")
```

## Phase 5: Testing Framework (Week 3)

### 5.1 Unit Tests for Safety
```python
# tests/test_safety.py
import pytest
from can_cli.safety.rules import SafetyRules, SafetyMode
from can_cli.safety.rate_limiter import RateLimiter

class TestSafetyRules:
    def test_production_mode_blocks_critical(self):
        """Test that production mode blocks critical addresses"""
        rules = SafetyRules(SafetyMode.PRODUCTION)
        
        # Test critical address
        result = rules.validate_message(0x180, b'\x00' * 8, 0)
        assert not result.passed
        assert any(v.rule == "critical_message" for v in result.violations)
        
    def test_development_mode_allows_with_warning(self):
        """Test that development mode allows but warns"""
        rules = SafetyRules(SafetyMode.DEVELOPMENT)
        
        # Test critical address
        result = rules.validate_message(0x180, b'\x00' * 8, 0)
        assert result.passed
        assert len(result.warnings) > 0
        
    def test_invalid_data_length(self):
        """Test data length validation"""
        rules = SafetyRules(SafetyMode.TESTING)
        
        # Test oversized data
        result = rules.validate_message(0x100, b'\x00' * 16, 0)
        assert not result.passed
        assert any(v.rule == "invalid_data_length" for v in result.violations)

class TestRateLimiter:
    def test_global_rate_limit(self):
        """Test global rate limiting"""
        limiter = RateLimiter()
        limiter.config.global_limit = 10
        limiter.config.window_size = 0.1
        
        # Send within limit
        for i in range(10):
            allowed, msg = limiter.check_and_update(0x100)
            assert allowed
            
        # Exceed limit
        allowed, msg = limiter.check_and_update(0x100)
        assert not allowed
        assert "Global rate limit" in msg
        
    def test_per_address_limit(self):
        """Test per-address rate limiting"""
        limiter = RateLimiter()
        limiter.config.per_address_limit = 5
        limiter.config.window_size = 0.1
        
        # Send to one address up to limit
        for i in range(5):
            allowed, msg = limiter.check_and_update(0x100)
            assert allowed
            
        # Exceed limit for that address
        allowed, msg = limiter.check_and_update(0x100)
        assert not allowed
        assert "Address rate limit" in msg
        
        # Other addresses should still work
        allowed, msg = limiter.check_and_update(0x200)
        assert allowed
```

## Phase 6: Configuration and Deployment (Week 3-4)

### 6.1 Default Configuration
```yaml
# can_cli/config/defaults.yaml
safety:
  modes:
    production:
      blocked_addresses: [0x180, 0x200, 0x220, 0x260]
      require_confirmation: [0x326, 0x343]
      max_data_length: 8
    testing:
      blocked_addresses: [0x180, 0x200]
      require_confirmation: []
      max_data_length: 64
    development:
      blocked_addresses: []
      require_confirmation: []
      max_data_length: 64
      
rate_limiting:
  global_limit: 1000
  per_address_limit: 100
  window_size: 1.0
  burst_size: 10
  
logging:
  audit_log: ~/.can_cli/audit.log
  level: INFO
  format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
  
interface:
  panda:
    timeout_ms: 10
    safety_mode: SAFETY_ALLOUTPUT  # For development only!
```

### 6.2 Setup Script
```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="can-cli",
    version="0.1.0",
    description="Safe CAN bus command-line interface",
    author="comma.ai",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "pyyaml>=5.4",
        "pandas>=1.3",  # For CSV operations
        "python-can>=4.0",  # For socketcan support
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.12",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ]
    },
    entry_points={
        "console_scripts": [
            "can-cli=can_cli.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
```

## Deployment Checklist

### Pre-deployment
- [ ] All unit tests passing
- [ ] Integration tests with mock interface
- [ ] Safety rules reviewed and tested
- [ ] Documentation complete
- [ ] Code review completed
- [ ] Security audit (no hardcoded values, proper input validation)

### Deployment Steps
1. Install in development environment
2. Test with virtual CAN interface
3. Test with real hardware in LOCKED mode
4. Gradual rollout with monitoring

### Post-deployment
- [ ] Monitor audit logs for issues
- [ ] Collect user feedback
- [ ] Update safety rules based on usage
- [ ] Performance optimization if needed

## Risk Mitigation

1. **Default to Safe**: Production mode by default, explicit override needed
2. **Audit Everything**: Complete audit trail of all operations
3. **Rate Limiting**: Prevent accidental bus flooding
4. **Confirmation Required**: Critical operations need explicit confirmation
5. **Rollback Plan**: Version control for safety rules, easy rollback

This implementation plan provides a structured approach to building the CAN CLI tool with safety as the primary concern throughout development.