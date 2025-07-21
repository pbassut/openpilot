"""Rate limiting for CAN message sending"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    global_limit: int = 1000          # Total messages per second
    per_address_limit: int = 100      # Messages per second per address
    burst_size: int = 10              # Allow burst of messages
    window_size: float = 1.0          # Time window in seconds
    critical_address_limit: int = 10  # Lower limit for critical addresses


class RateLimiter:
    """Rate limiter for CAN message sending"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.global_timestamps: deque = deque()
        self.address_timestamps: Dict[int, deque] = defaultdict(deque)
        self.burst_tokens: Dict[int, int] = defaultdict(lambda: self.config.burst_size)
        self.last_clean = time.time()
        
        # Critical addresses get lower limits
        self.critical_addresses = {
            0x180, 0x200, 0x220, 0x260,  # Core control
            0x343, 0x394,                 # Safety systems
        }
        
    def check_and_update(self, address: int) -> Tuple[bool, Optional[str]]:
        """
        Check if message can be sent and update counters
        
        Returns:
            Tuple of (allowed, error_message)
        """
        current_time = time.time()
        
        # Clean old timestamps periodically
        if current_time - self.last_clean > 0.1:  # Clean every 100ms
            self._clean_old_timestamps(current_time)
            self.last_clean = current_time
        
        # Check global rate
        if len(self.global_timestamps) >= self.config.global_limit:
            return False, f"Global rate limit exceeded ({self.config.global_limit} msg/s)"
        
        # Determine limit for this address
        if address in self.critical_addresses:
            limit = self.config.critical_address_limit
        else:
            limit = self.config.per_address_limit
        
        # Check per-address rate
        address_count = len(self.address_timestamps[address])
        if address_count >= limit:
            # Check if we can use burst tokens
            if self.burst_tokens[address] > 0:
                self.burst_tokens[address] -= 1
            else:
                return False, f"Rate limit exceeded for 0x{address:03X} ({limit} msg/s)"
        
        # Update timestamps
        self.global_timestamps.append(current_time)
        self.address_timestamps[address].append(current_time)
        
        # Regenerate burst tokens slowly
        if address_count < limit / 2:  # If under 50% of limit
            self.burst_tokens[address] = min(
                self.burst_tokens[address] + 1,
                self.config.burst_size
            )
        
        return True, None
    
    def _clean_old_timestamps(self, current_time: float):
        """Remove timestamps outside the window"""
        cutoff = current_time - self.config.window_size
        
        # Clean global timestamps
        while self.global_timestamps and self.global_timestamps[0] < cutoff:
            self.global_timestamps.popleft()
        
        # Clean per-address timestamps
        empty_addresses = []
        for address, timestamps in self.address_timestamps.items():
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            
            # Mark empty deques for removal
            if not timestamps:
                empty_addresses.append(address)
        
        # Remove empty entries to prevent memory growth
        for address in empty_addresses:
            del self.address_timestamps[address]
    
    def get_current_rate(self, address: Optional[int] = None) -> float:
        """Get current message rate (messages per second)"""
        if address is not None:
            return len(self.address_timestamps.get(address, []))
        else:
            return len(self.global_timestamps)
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            "global_rate": self.get_current_rate(),
            "global_limit": self.config.global_limit,
            "active_addresses": len(self.address_timestamps),
            "address_rates": {
                f"0x{addr:03X}": len(timestamps)
                for addr, timestamps in self.address_timestamps.items()
            },
            "burst_tokens": {
                f"0x{addr:03X}": tokens
                for addr, tokens in self.burst_tokens.items()
                if tokens < self.config.burst_size
            }
        }
    
    def reset(self):
        """Reset all rate limiting counters"""
        self.global_timestamps.clear()
        self.address_timestamps.clear()
        self.burst_tokens.clear()
        self.last_clean = time.time()