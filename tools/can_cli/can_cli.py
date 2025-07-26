#!/usr/bin/env python3
"""
OpenPilot CAN CLI Tool
A safe, comprehensive command-line interface for CAN bus operations
"""

import argparse
import sys
import time
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
import json
import os
from pathlib import Path
from datetime import datetime

try:
    from panda import Panda
    PANDA_AVAILABLE = True
except ImportError:
    print("Warning: panda not available. Running in simulation mode.")
    PANDA_AVAILABLE = False

from opendbc.can.packer import CANPacker
from opendbc.can.parser import CANParser
import cereal.messaging as messaging
from cereal.services import SERVICE_LIST


class SafetyMode(Enum):
    """Safety operation modes"""
    LOCKED = "locked"           # Read-only, no sending allowed
    PRODUCTION = "production"   # High safety, confirmations required
    TESTING = "testing"         # Moderate safety for testing
    DEVELOPMENT = "development" # Low safety for development


class CANMessage:
    """Represents a CAN message"""
    def __init__(self, address: int, data: bytes, bus: int, fd: bool = False):
        self.address = address
        self.data = data
        self.bus = bus
        self.fd = fd
        self.timestamp = time.time()
    
    def __repr__(self):
        return f"CAN(0x{self.address:03X}, {self.data.hex()}, bus={self.bus})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'address': f"0x{self.address:03X}",
            'data': self.data.hex(),
            'bus': self.bus,
            'fd': self.fd,
            'timestamp': self.timestamp
        }


class SafetyRules:
    """Implements safety validation for CAN messages"""
    
    CRITICAL_ADDRESSES = {
        0x180: "STEERING",
        0x200: "BRAKE",
        0x220: "THROTTLE",
        0x2E4: "TRANSMISSION",
        0x191: "CRUISE_CONTROL",
        0x1D2: "PCM_CRUISE",
        0x1FA: "CRUISE_BUTTONS"
    }
    
    @staticmethod
    def validate_message(msg: CANMessage, mode: SafetyMode) -> Tuple[bool, str]:
        """Validate if a message can be sent in the current safety mode"""
        
        # LOCKED mode - no sending allowed
        if mode == SafetyMode.LOCKED:
            return False, "Cannot send messages in LOCKED mode"
        
        # Check for critical addresses
        if msg.address in SafetyRules.CRITICAL_ADDRESSES:
            critical_type = SafetyRules.CRITICAL_ADDRESSES[msg.address]
            
            if mode == SafetyMode.PRODUCTION:
                return False, f"Cannot send to critical address {critical_type} in PRODUCTION mode"
            
            if mode == SafetyMode.TESTING:
                # Additional validation for testing mode
                if critical_type in ["STEERING", "BRAKE", "THROTTLE"]:
                    return False, f"Cannot send to {critical_type} even in TESTING mode"
        
        # Validate message structure
        if msg.fd and len(msg.data) > 64:
            return False, "CAN-FD data cannot exceed 64 bytes"
        elif not msg.fd and len(msg.data) > 8:
            return False, "Standard CAN data cannot exceed 8 bytes"
        
        # Validate bus number
        if msg.bus not in [0, 1, 2]:
            return False, f"Invalid bus number: {msg.bus}"
        
        return True, "Message validated"


class RateLimiter:
    """Implements rate limiting for CAN messages"""
    
    def __init__(self):
        self.message_times: Dict[int, List[float]] = {}
        self.global_times: List[float] = []
        
        # Configurable limits
        self.global_limit = 100  # messages per second
        self.per_address_limit = 20  # messages per second per address
        self.window_size = 1.0  # 1 second window
    
    def check_rate(self, address: int) -> Tuple[bool, str]:
        """Check if sending is within rate limits"""
        current_time = time.time()
        
        # Clean old entries
        self._clean_old_entries(current_time)
        
        # Check global rate
        if len(self.global_times) >= self.global_limit:
            return False, f"Global rate limit exceeded ({self.global_limit} msg/s)"
        
        # Check per-address rate
        if address in self.message_times:
            if len(self.message_times[address]) >= self.per_address_limit:
                return False, f"Per-address rate limit exceeded ({self.per_address_limit} msg/s)"
        
        return True, "Within rate limits"
    
    def record_message(self, address: int):
        """Record a message send event"""
        current_time = time.time()
        
        self.global_times.append(current_time)
        
        if address not in self.message_times:
            self.message_times[address] = []
        self.message_times[address].append(current_time)
    
    def _clean_old_entries(self, current_time: float):
        """Remove entries outside the time window"""
        cutoff_time = current_time - self.window_size
        
        self.global_times = [t for t in self.global_times if t > cutoff_time]
        
        for address in list(self.message_times.keys()):
            self.message_times[address] = [
                t for t in self.message_times[address] if t > cutoff_time
            ]
            if not self.message_times[address]:
                del self.message_times[address]


class CANInterface:
    """Main interface for CAN operations"""
    
    def __init__(self, safety_mode: SafetyMode = SafetyMode.PRODUCTION):
        self.safety_mode = safety_mode
        self.safety_rules = SafetyRules()
        self.rate_limiter = RateLimiter()
        self.panda = None
        self.connected = False
        
        # Logging
        self.log_file = None
        self.enable_logging = True
        
        # Initialize logging
        self._init_logging()
    
    def _init_logging(self):
        """Initialize logging directory and file"""
        log_dir = Path.home() / ".openpilot" / "can_cli" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = log_dir / f"can_cli_{timestamp}.log"
    
    def _log_operation(self, operation: str, details: Dict[str, Any]):
        """Log operations for audit trail"""
        if not self.enable_logging:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'safety_mode': self.safety_mode.value,
            'details': details
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def connect(self) -> bool:
        """Connect to Panda device"""
        if not PANDA_AVAILABLE:
            print("Running in simulation mode - no Panda connection")
            self.connected = False
            return False
        
        try:
            self.panda = Panda()
            
            # Set appropriate safety mode based on our safety level
            if self.safety_mode == SafetyMode.LOCKED:
                self.panda.set_safety_mode(Panda.SAFETY_SILENT)
            elif self.safety_mode == SafetyMode.PRODUCTION:
                # Use car-specific safety mode if available
                self.panda.set_safety_mode(Panda.SAFETY_TOYOTA)
            else:
                # Testing/Development modes
                print("\n⚠️  WARNING: Using ALLOUTPUT safety mode!")
                print("This bypasses hardware safety checks. Use with extreme caution!")
                response = input("Continue? (yes/no): ")
                if response.lower() != 'yes':
                    return False
                self.panda.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
            
            self.connected = True
            print(f"Connected to Panda in {self.safety_mode.value} mode")
            
            self._log_operation("connect", {
                'success': True,
                'safety_mode': self.safety_mode.value
            })
            
            return True
            
        except Exception as e:
            print(f"Failed to connect to Panda: {e}")
            self._log_operation("connect", {
                'success': False,
                'error': str(e)
            })
            return False
    
    def send_message(self, msg: CANMessage) -> Tuple[bool, str]:
        """Send a single CAN message with safety checks"""
        
        # Validate message
        valid, reason = self.safety_rules.validate_message(msg, self.safety_mode)
        if not valid:
            self._log_operation("send_rejected", {
                'message': msg.to_dict(),
                'reason': reason
            })
            return False, reason
        
        # Check rate limits
        rate_ok, rate_reason = self.rate_limiter.check_rate(msg.address)
        if not rate_ok:
            self._log_operation("send_rate_limited", {
                'message': msg.to_dict(),
                'reason': rate_reason
            })
            return False, rate_reason
        
        # Require confirmation for critical messages
        if msg.address in SafetyRules.CRITICAL_ADDRESSES:
            critical_type = SafetyRules.CRITICAL_ADDRESSES[msg.address]
            print(f"\n⚠️  WARNING: Sending to CRITICAL address: {critical_type}")
            print(f"Message: {msg}")
            response = input("Are you sure? (yes/no): ")
            if response.lower() != 'yes':
                return False, "User cancelled"
        
        # Send the message
        try:
            if self.connected and self.panda:
                self.panda.can_send(msg.address, msg.data, msg.bus)
                self.rate_limiter.record_message(msg.address)
                
                self._log_operation("send_success", {
                    'message': msg.to_dict()
                })
                
                return True, "Message sent successfully"
            else:
                # Simulation mode
                print(f"[SIMULATION] Would send: {msg}")
                return True, "Message sent (simulation)"
                
        except Exception as e:
            error = f"Failed to send message: {e}"
            self._log_operation("send_error", {
                'message': msg.to_dict(),
                'error': str(e)
            })
            return False, error
    
    def monitor_bus(self, bus: int = -1, timeout: float = 10.0):
        """Monitor CAN bus traffic"""
        if not self.connected or not self.panda:
            print("Not connected to Panda")
            return
        
        print(f"Monitoring CAN bus {'all' if bus == -1 else bus} for {timeout}s...")
        print("Press Ctrl+C to stop\n")
        
        start_time = time.time()
        message_count = 0
        
        try:
            while time.time() - start_time < timeout:
                messages = self.panda.can_recv()
                
                for msg in messages:
                    addr, data, msg_bus = msg
                    if bus == -1 or msg_bus == bus:
                        timestamp = time.time() - start_time
                        print(f"[{timestamp:7.3f}] Bus {msg_bus}: 0x{addr:03X} {data.hex()}")
                        message_count += 1
                
                time.sleep(0.001)  # Small delay to prevent CPU spinning
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        
        print(f"\nReceived {message_count} messages")
    
    def disconnect(self):
        """Disconnect from Panda"""
        if self.panda:
            self.panda.close()
            self.panda = None
        self.connected = False
        print("Disconnected from Panda")


class CANCLIApp:
    """Main CLI application"""
    
    def __init__(self):
        self.interface = None
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description="OpenPilot CAN CLI Tool - Safe CAN bus operations",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Send a message in testing mode
  can_cli --mode testing send 0x123 "01 02 03 04" --bus 0
  
  # Monitor all CAN buses
  can_cli monitor --timeout 30
  
  # Send using DBC file
  can_cli --mode development send-dbc toyota "STEERING_LKA" "STEER_REQUEST=1,STEER_TORQUE_CMD=100"
            """
        )
        
        # Global options
        parser.add_argument(
            '--mode', 
            type=str,
            choices=[m.value for m in SafetyMode],
            default=SafetyMode.PRODUCTION.value,
            help='Safety mode (default: production)'
        )
        
        parser.add_argument(
            '--no-log',
            action='store_true',
            help='Disable logging'
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # Send command
        send_parser = subparsers.add_parser('send', help='Send a CAN message')
        send_parser.add_argument('address', type=lambda x: int(x, 0), help='CAN ID (hex or dec)')
        send_parser.add_argument('data', type=str, help='Data bytes (hex string)')
        send_parser.add_argument('--bus', type=int, default=0, help='CAN bus number')
        send_parser.add_argument('--fd', action='store_true', help='CAN-FD message')
        
        # Monitor command
        monitor_parser = subparsers.add_parser('monitor', help='Monitor CAN bus')
        monitor_parser.add_argument('--bus', type=int, default=-1, help='Bus to monitor (-1 for all)')
        monitor_parser.add_argument('--timeout', type=float, default=10.0, help='Monitor duration')
        
        # Send DBC command
        dbc_parser = subparsers.add_parser('send-dbc', help='Send using DBC file')
        dbc_parser.add_argument('dbc', type=str, help='DBC name (e.g., toyota)')
        dbc_parser.add_argument('signal', type=str, help='Signal name')
        dbc_parser.add_argument('values', type=str, help='Signal values (key=value,key2=value2)')
        dbc_parser.add_argument('--bus', type=int, default=0, help='CAN bus number')
        
        return parser
    
    def _parse_hex_data(self, data_str: str) -> bytes:
        """Parse hex string to bytes"""
        # Remove spaces and convert to bytes
        data_str = data_str.replace(' ', '').replace('0x', '')
        return bytes.fromhex(data_str)
    
    def run(self, args):
        """Run the CLI application"""
        # Parse arguments
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return 1
        
        # Create interface with specified safety mode
        safety_mode = SafetyMode(parsed_args.mode)
        self.interface = CANInterface(safety_mode)
        self.interface.enable_logging = not parsed_args.no_log
        
        # Connect to Panda
        if not self.interface.connect():
            return 1
        
        try:
            # Execute command
            if parsed_args.command == 'send':
                return self._cmd_send(parsed_args)
            elif parsed_args.command == 'monitor':
                return self._cmd_monitor(parsed_args)
            elif parsed_args.command == 'send-dbc':
                return self._cmd_send_dbc(parsed_args)
            
        finally:
            self.interface.disconnect()
        
        return 0
    
    def _cmd_send(self, args) -> int:
        """Execute send command"""
        try:
            data = self._parse_hex_data(args.data)
            msg = CANMessage(args.address, data, args.bus, args.fd)
            
            print(f"Sending: {msg}")
            success, reason = self.interface.send_message(msg)
            
            if success:
                print(f"✓ {reason}")
                return 0
            else:
                print(f"✗ {reason}")
                return 1
                
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def _cmd_monitor(self, args) -> int:
        """Execute monitor command"""
        self.interface.monitor_bus(args.bus, args.timeout)
        return 0
    
    def _cmd_send_dbc(self, args) -> int:
        """Execute send-dbc command"""
        try:
            # Parse signal values
            values = {}
            for pair in args.values.split(','):
                key, value = pair.split('=')
                # Try to convert to number if possible
                try:
                    values[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    values[key] = value
            
            # Create message using CANPacker
            dbc_name = f"{args.dbc}_generated"
            packer = CANPacker(dbc_name)
            addr, data, bus = packer.make_can_msg(args.signal, args.bus, values)
            
            # Send the message
            msg = CANMessage(addr, data, bus)
            print(f"Sending DBC message: {msg}")
            print(f"Signal values: {values}")
            
            success, reason = self.interface.send_message(msg)
            
            if success:
                print(f"✓ {reason}")
                return 0
            else:
                print(f"✗ {reason}")
                return 1
                
        except Exception as e:
            print(f"Error: {e}")
            return 1


def main():
    """Main entry point"""
    app = CANCLIApp()
    sys.exit(app.run(sys.argv[1:]))


if __name__ == "__main__":
    main()