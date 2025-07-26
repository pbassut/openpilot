#!/usr/bin/env python3
"""
Example usage of the CAN CLI tool
Demonstrates safe practices and common use cases
"""

import subprocess
import time
import os

# Path to the CAN CLI tool
CAN_CLI = os.path.join(os.path.dirname(__file__), "can_cli.py")


def run_command(cmd):
    """Run a CAN CLI command and print output"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run([CAN_CLI] + cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode


def example_1_monitoring():
    """Example 1: Monitor CAN bus traffic"""
    print("\n### EXAMPLE 1: Monitoring CAN Traffic ###")
    print("This is always safe - we're only reading, not sending")
    
    # Monitor all buses for 5 seconds
    run_command(['monitor', '--timeout', '5'])
    
    # Monitor specific bus
    run_command(['monitor', '--bus', '0', '--timeout', '3'])


def example_2_safe_sending():
    """Example 2: Send non-critical messages safely"""
    print("\n### EXAMPLE 2: Safe Message Sending ###")
    print("Sending to non-critical addresses in production mode")
    
    # Send a diagnostic request (typically safe)
    run_command(['send', '0x7DF', '02 01 00', '--bus', '0'])
    
    # Send with explicit safety mode
    run_command(['--mode', 'production', 'send', '0x123', 'AA BB CC'])


def example_3_dbc_usage():
    """Example 3: Using DBC files for correct message format"""
    print("\n### EXAMPLE 3: DBC-Based Sending ###")
    print("DBC files ensure correct message format")
    
    # Example: Set cruise speed (non-critical)
    run_command([
        '--mode', 'testing',
        'send-dbc', 'toyota', 'ACC_CONTROL',
        'CRUISE_SET_SPEED=65.0,CRUISE_ACTIVE=1'
    ])


def example_4_testing_mode():
    """Example 4: Testing mode for development"""
    print("\n### EXAMPLE 4: Testing Mode ###")
    print("Testing mode allows more operations but still has safety")
    
    # Send multiple test messages
    test_messages = [
        ('0x100', '11 22 33'),
        ('0x101', '44 55 66'),
        ('0x102', '77 88 99')
    ]
    
    for addr, data in test_messages:
        run_command(['--mode', 'testing', 'send', addr, data])
        time.sleep(0.1)  # Small delay between messages


def example_5_batch_operations():
    """Example 5: Batch operations with safety"""
    print("\n### EXAMPLE 5: Batch Operations ###")
    print("Sending multiple messages with rate limiting")
    
    # Create a batch script
    batch_script = """#!/bin/bash
# Batch CAN message sending with safety

CAN_CLI="{}"

# Wake up sequence (example)
$CAN_CLI --mode testing send 0x700 "00 00 00 00 00 00 00 00"
sleep 0.1

# Status queries
$CAN_CLI send 0x7DF "02 01 00"  # Mode 01 PID 00
sleep 0.1
$CAN_CLI send 0x7DF "02 01 0C"  # RPM
sleep 0.1
$CAN_CLI send 0x7DF "02 01 0D"  # Speed
""".format(CAN_CLI)
    
    # Save and run the script
    script_path = "/tmp/can_batch_example.sh"
    with open(script_path, 'w') as f:
        f.write(batch_script)
    
    os.chmod(script_path, 0o755)
    subprocess.run([script_path])


def example_6_safety_demo():
    """Example 6: Demonstrate safety features"""
    print("\n### EXAMPLE 6: Safety Features Demo ###")
    print("Showing how safety features protect against dangerous operations")
    
    # Try to send to critical address in production mode (will fail)
    print("\n1. Attempting critical address in production mode:")
    run_command(['send', '0x180', '00 00'])  # Steering - will be blocked
    
    # Show rate limiting
    print("\n2. Demonstrating rate limiting:")
    print("Sending many messages rapidly...")
    for i in range(25):
        result = run_command(['--mode', 'testing', 'send', '0x500', f'{i:02X} 00'])
        if result != 0:
            print("Rate limit hit!")
            break


def example_7_advanced_usage():
    """Example 7: Advanced usage patterns"""
    print("\n### EXAMPLE 7: Advanced Usage ###")
    
    # CAN-FD example
    print("\n1. CAN-FD message (up to 64 bytes):")
    fd_data = ' '.join([f'{i:02X}' for i in range(16)])  # 16 bytes
    run_command(['--mode', 'testing', 'send', '0x400', fd_data, '--fd'])
    
    # Different bus example
    print("\n2. Sending to different CAN buses:")
    for bus in [0, 1, 2]:
        run_command([
            '--mode', 'testing', 
            'send', '0x600', 'BUS TEST', 
            '--bus', str(bus)
        ])


def main():
    """Run all examples"""
    print("""
    CAN CLI Tool Examples
    ====================
    
    This script demonstrates safe usage of the CAN CLI tool.
    
    WARNING: These examples are for educational purposes.
    Only run on a test bench or with appropriate safety measures!
    
    Press Enter to continue or Ctrl+C to exit...
    """)
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nExiting...")
        return
    
    # Run examples
    examples = [
        example_1_monitoring,
        example_2_safe_sending,
        example_3_dbc_usage,
        example_4_testing_mode,
        example_5_batch_operations,
        example_6_safety_demo,
        example_7_advanced_usage
    ]
    
    for example in examples:
        try:
            example()
            print("\nPress Enter for next example or Ctrl+C to exit...")
            input()
        except KeyboardInterrupt:
            print("\nStopping examples...")
            break
    
    print("\n✅ Examples completed!")
    print("\nKey takeaways:")
    print("1. Always start with monitoring to understand the bus")
    print("2. Use production mode by default")
    print("3. Use DBC files when possible")
    print("4. Be aware of rate limits")
    print("5. Critical addresses require extra caution")
    print("6. Test in safe environments first")


if __name__ == "__main__":
    main()