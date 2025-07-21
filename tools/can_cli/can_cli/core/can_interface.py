"""CAN interface abstraction layer"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time
import logging
from contextlib import contextmanager

from ..safety.rules import SafetyRules, ValidationResult
from ..safety.rate_limiter import RateLimiter
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CANMessage:
    """Represents a CAN message"""
    address: int
    data: bytes
    bus: int
    timestamp: Optional[float] = field(default_factory=time.time)
    
    def __post_init__(self):
        # Validate on creation
        if not 0 <= self.address <= 0x1FFFFFFF:
            raise ValueError(f"Invalid CAN address: 0x{self.address:X}")
        if not isinstance(self.data, bytes):
            raise TypeError("Data must be bytes")
        if not 0 <= self.bus <= 2:
            raise ValueError(f"Invalid bus number: {self.bus}")
    
    def __str__(self):
        return f"[{self.bus}] 0x{self.address:03X}: {self.data.hex()}"
    
    @property
    def is_extended(self) -> bool:
        """Check if this is an extended CAN ID"""
        return self.address > 0x7FF


class BaseCANInterface(ABC):
    """Abstract base class for CAN interfaces"""
    
    def __init__(self, safety: Optional[SafetyRules] = None, 
                 rate_limiter: Optional[RateLimiter] = None):
        self.safety = safety
        self.rate_limiter = rate_limiter
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "safety_violations": 0
        }
        
    @abstractmethod
    def _send_raw(self, address: int, data: bytes, bus: int) -> None:
        """Send a raw CAN message (implementation specific)"""
        pass
        
    @abstractmethod
    def _receive_raw(self, timeout: Optional[float] = None) -> List[CANMessage]:
        """Receive raw CAN messages (implementation specific)"""
        pass
        
    @abstractmethod
    def set_safety_mode(self, mode: int) -> None:
        """Set interface safety mode (implementation specific)"""
        pass
    
    def send(self, address: int, data: bytes, bus: int, 
             force: bool = False) -> ValidationResult:
        """
        Send a CAN message with safety checks
        
        Args:
            address: CAN ID
            data: Message data
            bus: CAN bus number
            force: Skip safety checks if True
            
        Returns:
            ValidationResult with any warnings/violations
        """
        # Create message object
        msg = CANMessage(address=address, data=data, bus=bus)
        
        # Safety validation
        validation_result = ValidationResult(passed=True, violations=[], warnings=[])
        
        if self.safety and not force:
            validation_result = self.safety.validate_message(address, data, bus)
            if not validation_result.passed:
                self.stats["safety_violations"] += 1
                logger.warning(f"Safety violation for message {msg}: {validation_result.violations}")
                
                # Don't send if validation failed and can't override
                if not validation_result.can_override:
                    raise PermissionError(f"Cannot send message: {validation_result.violations[0].message}")
        
        # Rate limiting
        if self.rate_limiter:
            allowed, error_msg = self.rate_limiter.check_and_update(address)
            if not allowed:
                raise RuntimeError(f"Rate limit exceeded: {error_msg}")
        
        # Log the send attempt
        logger.info(f"Sending CAN message: {msg}")
        
        # Actually send the message
        try:
            self._send_raw(address, data, bus)
            self.stats["messages_sent"] += 1
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to send message {msg}: {e}")
            raise
            
        return validation_result
    
    def receive(self, timeout: Optional[float] = None) -> List[CANMessage]:
        """
        Receive CAN messages
        
        Args:
            timeout: Timeout in seconds (None for non-blocking)
            
        Returns:
            List of received messages
        """
        try:
            messages = self._receive_raw(timeout)
            self.stats["messages_received"] += len(messages)
            return messages
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to receive messages: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get interface statistics"""
        stats = self.stats.copy()
        if self.rate_limiter:
            stats["rate_limiter"] = self.rate_limiter.get_stats()
        return stats
    
    @contextmanager
    def batch_mode(self):
        """Context manager for batch operations"""
        # Could implement buffering here
        yield self


class PandaInterface(BaseCANInterface):
    """Panda CAN interface implementation"""
    
    def __init__(self, safety: Optional[SafetyRules] = None,
                 rate_limiter: Optional[RateLimiter] = None,
                 safety_mode: Optional[int] = None):
        super().__init__(safety, rate_limiter)
        
        # Import here to avoid dependency issues
        try:
            from panda import Panda
        except ImportError:
            raise ImportError("panda package not found. Install with: pip install pandas")
        
        self.panda = Panda()
        self._safety_mode = safety_mode
        
        # Set safety mode if specified
        if safety_mode is not None:
            self.set_safety_mode(safety_mode)
            
        logger.info(f"Initialized Panda interface, HW type: {self.panda.get_type()}")
    
    def _send_raw(self, address: int, data: bytes, bus: int) -> None:
        """Send a CAN message via Panda"""
        self.panda.can_send(address, data, bus)
    
    def _receive_raw(self, timeout: Optional[float] = None) -> List[CANMessage]:
        """Receive CAN messages from Panda"""
        messages = []
        
        # Panda doesn't support timeout directly, so we implement it
        start_time = time.time()
        
        while True:
            can_msgs = self.panda.can_recv()
            
            for address, dat, bus in can_msgs:
                messages.append(CANMessage(
                    address=address,
                    data=dat,
                    bus=bus
                ))
            
            # Break if we have messages or timeout
            if messages or (timeout and time.time() - start_time > timeout):
                break
            elif timeout is None:
                break  # Non-blocking mode
                
            # Small sleep to prevent busy waiting
            time.sleep(0.001)
        
        return messages
    
    def set_safety_mode(self, mode: int) -> None:
        """Set Panda safety mode"""
        self.panda.set_safety_mode(mode)
        self._safety_mode = mode
        logger.info(f"Set Panda safety mode to {mode}")
    
    def get_health(self) -> Dict[str, Any]:
        """Get Panda health information"""
        health = self.panda.health()
        return {
            "voltage": health['voltage'] / 1000.0,  # Convert to volts
            "current": health['current'],
            "can_rx_errs": health['can_rx_errs'], 
            "can_send_errs": health['can_send_errs'],
            "can_fwd_errs": health['can_fwd_errs'],
            "uptime": health['uptime'],
            "safety_mode": self._safety_mode
        }


class MockCANInterface(BaseCANInterface):
    """Mock CAN interface for testing"""
    
    def __init__(self, safety: Optional[SafetyRules] = None,
                 rate_limiter: Optional[RateLimiter] = None):
        super().__init__(safety, rate_limiter)
        self.sent_messages: List[CANMessage] = []
        self.receive_queue: List[CANMessage] = []
        self._safety_mode = 0
        
    def _send_raw(self, address: int, data: bytes, bus: int) -> None:
        """Store sent messages"""
        msg = CANMessage(address=address, data=data, bus=bus)
        self.sent_messages.append(msg)
        
    def _receive_raw(self, timeout: Optional[float] = None) -> List[CANMessage]:
        """Return queued messages"""
        messages = self.receive_queue[:]
        self.receive_queue.clear()
        return messages
        
    def set_safety_mode(self, mode: int) -> None:
        """Set mock safety mode"""
        self._safety_mode = mode
        
    def add_receive_message(self, address: int, data: bytes, bus: int):
        """Add a message to the receive queue for testing"""
        self.receive_queue.append(CANMessage(address, data, bus))