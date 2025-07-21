#!/usr/bin/env python3
"""
Example usage of the CAN CLI tool demonstrating safety features
"""

from can_cli.safety import SafetyMode, SafetyRules, RateLimiter
from can_cli.core import MockCANInterface, CANMessage

def demonstrate_safety_modes():
    """Demonstrate different safety modes"""
    print("=== CAN CLI Safety Demonstration ===\n")
    
    # Test different safety modes
    modes = [
        SafetyMode.LOCKED,
        SafetyMode.PRODUCTION, 
        SafetyMode.TESTING,
        SafetyMode.DEVELOPMENT
    ]
    
    # Critical steering control message
    critical_addr = 0x180
    critical_data = bytes([0x00, 0x00, 0x00, 0x00])
    
    for mode in modes:
        print(f"\n--- Testing {mode.value.upper()} mode ---")
        
        # Create safety rules for this mode
        safety = SafetyRules(mode)
        interface = MockCANInterface(safety=safety)
        
        # Try to send a critical message
        try:
            result = safety.validate_message(critical_addr, critical_data, 0)
            
            if result.passed:
                print(f"✅ Message validation PASSED")
            else:
                print(f"❌ Message validation FAILED")
                for violation in result.violations:
                    print(f"   - {violation.message}")
                    print(f"     Severity: {violation.severity}")
                    print(f"     Requires confirmation: {violation.requires_confirmation}")
                    print(f"     Can override: {violation.can_override}")
                    
            # Show warnings
            for warning in result.warnings:
                print(f"   ⚠️  {warning}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


def demonstrate_rate_limiting():
    """Demonstrate rate limiting"""
    print("\n\n=== Rate Limiting Demonstration ===\n")
    
    rate_limiter = RateLimiter()
    rate_limiter.config.per_address_limit = 5  # Low limit for demo
    rate_limiter.config.window_size = 1.0
    
    print(f"Rate limit: {rate_limiter.config.per_address_limit} messages/second")
    
    # Try to send messages rapidly
    address = 0x100
    for i in range(10):
        allowed, msg = rate_limiter.check_and_update(address)
        if allowed:
            print(f"✅ Message {i+1}: Allowed")
        else:
            print(f"❌ Message {i+1}: {msg}")
            
    print(f"\nCurrent stats: {rate_limiter.get_stats()}")


def demonstrate_message_validation():
    """Demonstrate message validation"""
    print("\n\n=== Message Validation Demonstration ===\n")
    
    safety = SafetyRules(SafetyMode.PRODUCTION)
    
    test_cases = [
        # (address, data, bus, description)
        (0x100, b'\x01\x02\x03\x04', 0, "Normal message"),
        (0x180, b'\x00' * 8, 0, "Critical steering control"),
        (0x100, b'\x00' * 16, 0, "Oversized data for CAN 2.0"),
        (0x100, b'\x00' * 8, 5, "Invalid bus number"),
        (0x326, b'\x00' * 8, 0, "Cruise control (high priority)"),
    ]
    
    for addr, data, bus, desc in test_cases:
        print(f"\nTesting: {desc}")
        print(f"  Address: 0x{addr:03X}, Data length: {len(data)}, Bus: {bus}")
        
        result = safety.validate_message(addr, data, bus)
        
        if result.passed:
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            for violation in result.violations:
                print(f"     - {violation.message}")


def demonstrate_safe_sending():
    """Demonstrate safe message sending with the interface"""
    print("\n\n=== Safe Message Sending Demonstration ===\n")
    
    # Setup
    safety = SafetyRules(SafetyMode.TESTING)
    rate_limiter = RateLimiter()
    interface = MockCANInterface(safety=safety, rate_limiter=rate_limiter)
    
    # Messages to send
    messages = [
        (0x100, b'\x01\x02\x03\x04', 0, "Normal allowed message"),
        (0x200, b'\x00\x00\x00\x00', 0, "Brake command (blocked)"),
        (0x326, b'\x00\x00\x00\x00', 0, "Cruise control (allowed in testing)"),
    ]
    
    for addr, data, bus, desc in messages:
        print(f"\nSending: {desc}")
        try:
            result = interface.send(addr, data, bus)
            print(f"  ✅ Message sent successfully")
            if result.warnings:
                for warning in result.warnings:
                    print(f"  ⚠️  {warning}")
        except PermissionError as e:
            print(f"  ❌ Permission denied: {e}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\nSent messages: {len(interface.sent_messages)}")
    for msg in interface.sent_messages:
        print(f"  - {msg}")


def main():
    """Run all demonstrations"""
    demonstrate_safety_modes()
    demonstrate_rate_limiting()
    demonstrate_message_validation()
    demonstrate_safe_sending()
    
    print("\n\n=== Key Safety Features ===")
    print("1. Multiple safety modes with different restrictions")
    print("2. Critical address protection")
    print("3. Rate limiting to prevent bus flooding")
    print("4. Message validation (structure, bus, data length)")
    print("5. Confirmation required for dangerous operations")
    print("6. Complete audit trail (with proper logging)")
    print("7. Fail-safe defaults (PRODUCTION mode)")


if __name__ == "__main__":
    main()