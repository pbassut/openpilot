"""Safety rules for CAN message validation"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
import yaml
import os
from pathlib import Path


class SafetyMode(Enum):
    """Operating modes with different safety levels"""
    DEVELOPMENT = "development"  # Full access with warnings
    TESTING = "testing"         # Limited access, no critical messages
    PRODUCTION = "production"   # Read-only by default, confirmations required
    LOCKED = "locked"          # No write operations allowed


@dataclass
class SafetyViolation:
    """Represents a safety rule violation"""
    rule: str
    message: str
    severity: str  # low, medium, high, critical
    requires_confirmation: bool = False
    can_override: bool = True


@dataclass
class ValidationResult:
    """Result of safety validation"""
    passed: bool
    violations: List[SafetyViolation]
    warnings: List[str]
    
    @property
    def requires_confirmation(self) -> bool:
        """Check if any violation requires confirmation"""
        return any(v.requires_confirmation for v in self.violations)
    
    @property
    def can_override(self) -> bool:
        """Check if violations can be overridden"""
        return all(v.can_override for v in self.violations)


class SafetyRules:
    """Safety rules engine for CAN message validation"""
    
    # Critical addresses that control vehicle behavior
    # These are common across many vehicles but should be customized
    CRITICAL_ADDRESSES = {
        # Steering control
        0x180: {"name": "Steering Control", "severity": "critical", "description": "Direct steering torque command"},
        0x2E4: {"name": "Steering Assist", "severity": "critical", "description": "Lane keeping assist command"},
        
        # Brake control
        0x200: {"name": "Brake Command", "severity": "critical", "description": "Direct brake actuation"},
        0x343: {"name": "AEB Control", "severity": "critical", "description": "Automatic emergency braking"},
        0x1FA: {"name": "Brake Pressure", "severity": "critical", "description": "Brake pressure request"},
        
        # Throttle/Engine control
        0x220: {"name": "Throttle Control", "severity": "critical", "description": "Throttle position command"},
        0x2C1: {"name": "Engine Torque", "severity": "critical", "description": "Engine torque request"},
        
        # Transmission control
        0x260: {"name": "Transmission Control", "severity": "critical", "description": "Gear selection command"},
        0x1D2: {"name": "Shift Request", "severity": "critical", "description": "Transmission shift request"},
        
        # Safety systems
        0x326: {"name": "Cruise Control", "severity": "high", "description": "ACC/Cruise commands"},
        0x394: {"name": "Airbag Control", "severity": "critical", "description": "Airbag deployment control"},
        
        # Other critical systems
        0x3B7: {"name": "Power Steering", "severity": "high", "description": "EPS control"},
        0x451: {"name": "Stability Control", "severity": "high", "description": "ESC/VSC commands"},
    }
    
    # Default blocked addresses per mode
    DEFAULT_BLOCKED = {
        SafetyMode.LOCKED: set(CRITICAL_ADDRESSES.keys()),  # Block all critical
        SafetyMode.PRODUCTION: {0x180, 0x200, 0x220, 0x260, 0x343, 0x394},  # Most critical
        SafetyMode.TESTING: {0x180, 0x200, 0x394},  # Only most dangerous
        SafetyMode.DEVELOPMENT: set(),  # Nothing blocked, but warnings shown
    }
    
    def __init__(self, mode: SafetyMode, config_file: Optional[str] = None):
        self.mode = mode
        self.config = self._load_config(config_file)
        self.blocked_addresses = self._get_blocked_addresses()
        self.rate_limits = self._get_rate_limits()
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        
        # Load default config
        default_config_path = Path(__file__).parent.parent / "config" / "defaults.yaml"
        if default_config_path.exists():
            with open(default_config_path, 'r') as f:
                return yaml.safe_load(f)
                
        return {}
    
    def _get_blocked_addresses(self) -> Set[int]:
        """Get blocked addresses for current mode"""
        # Check config first
        if self.config and 'safety' in self.config:
            mode_config = self.config['safety'].get('modes', {}).get(self.mode.value, {})
            if 'blocked_addresses' in mode_config:
                return set(mode_config['blocked_addresses'])
        
        # Use defaults
        return self.DEFAULT_BLOCKED.get(self.mode, set())
    
    def _get_rate_limits(self) -> Dict[int, int]:
        """Get per-address rate limits"""
        if self.config and 'safety' in self.config:
            return self.config['safety'].get('rate_limits', {})
        return {}
    
    def validate_message(self, address: int, data: bytes, bus: int) -> ValidationResult:
        """Validate a CAN message against safety rules"""
        violations = []
        warnings = []
        
        # Check if in LOCKED mode
        if self.mode == SafetyMode.LOCKED:
            violations.append(SafetyViolation(
                rule="locked_mode",
                message="Write operations are not allowed in LOCKED mode",
                severity="critical",
                requires_confirmation=False,
                can_override=False
            ))
        
        # Check if address is completely blocked
        elif address in self.blocked_addresses:
            addr_info = self.CRITICAL_ADDRESSES.get(address, {"name": f"0x{address:03X}"})
            violations.append(SafetyViolation(
                rule="blocked_address",
                message=f"Address {addr_info['name']} (0x{address:03X}) is blocked in {self.mode.value} mode",
                severity="critical",
                requires_confirmation=False,
                can_override=self.mode == SafetyMode.DEVELOPMENT
            ))
        
        # Check if it's a critical message (warning in non-blocked modes)
        elif address in self.CRITICAL_ADDRESSES:
            addr_info = self.CRITICAL_ADDRESSES[address]
            
            if self.mode == SafetyMode.PRODUCTION:
                violations.append(SafetyViolation(
                    rule="critical_message",
                    message=f"Critical message: {addr_info['name']} - {addr_info['description']}",
                    severity=addr_info['severity'],
                    requires_confirmation=True,
                    can_override=True
                ))
            else:
                warnings.append(
                    f"⚠️  CRITICAL: Sending to {addr_info['name']} (0x{address:03X}) - {addr_info['description']}"
                )
        
        # Validate data length based on bus type
        if bus < 3:  # CAN 2.0
            if len(data) > 8:
                violations.append(SafetyViolation(
                    rule="invalid_data_length",
                    message=f"Data length {len(data)} exceeds CAN 2.0 limit of 8 bytes",
                    severity="high",
                    requires_confirmation=False,
                    can_override=False
                ))
        else:  # CAN FD
            if len(data) > 64:
                violations.append(SafetyViolation(
                    rule="invalid_data_length", 
                    message=f"Data length {len(data)} exceeds CAN FD limit of 64 bytes",
                    severity="high",
                    requires_confirmation=False,
                    can_override=False
                ))
        
        # Check bus validity
        if bus not in [0, 1, 2]:
            violations.append(SafetyViolation(
                rule="invalid_bus",
                message=f"Invalid bus number: {bus} (valid: 0, 1, 2)",
                severity="high",
                requires_confirmation=False,
                can_override=False
            ))
        
        # Add general warnings based on mode
        if self.mode == SafetyMode.DEVELOPMENT and not violations:
            warnings.append("⚠️  Development mode active - Safety checks reduced")
        elif self.mode == SafetyMode.PRODUCTION and not violations and not warnings:
            if len(data) == 0:
                warnings.append("⚠️  Sending empty data payload")
        
        return ValidationResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings
        )
    
    def get_info(self) -> Dict:
        """Get information about current safety configuration"""
        return {
            "mode": self.mode.value,
            "blocked_addresses": sorted(list(self.blocked_addresses)),
            "critical_addresses": len(self.CRITICAL_ADDRESSES),
            "total_rules": 5,  # Number of validation checks
            "config_loaded": bool(self.config)
        }