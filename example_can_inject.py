#!/usr/bin/env python3
"""
Example script showing how to properly inject CAN messages into the openpilot system.
This demonstrates publishing messages to the 'sendcan' service.
"""

import time
import cereal.messaging as messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp

def send_can_message(address, data, bus=0):
    """
    Send a single CAN message through the sendcan service.
    
    Args:
        address: CAN message ID (e.g., 0x123)
        data: Bytes data (e.g., b'\x01\x02\x03\x04\x05\x06\x07\x08')
        bus: CAN bus number (0, 1, or 2)
    """
    # Create PubMaster for sendcan service
    pm = messaging.PubMaster(['sendcan'])
    
    # Format: [(address, data, bus)]
    can_sends = [(address, data, bus)]
    
    # Convert to Cap'n Proto format and send
    pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
    
    print(f"Sent CAN message: ID=0x{address:03X}, Data={data.hex()}, Bus={bus}")


def send_multiple_can_messages():
    """Example of sending multiple CAN messages in a batch."""
    pm = messaging.PubMaster(['sendcan'])
    
    # Multiple messages in one send
    can_sends = [
        (0x123, b'\x01\x02\x03\x04\x05\x06\x07\x08', 0),
        (0x456, b'\xAA\xBB\xCC\xDD', 0),
        (0x789, b'\x11\x22\x33\x44\x55\x66', 1),
    ]
    
    # Send all at once
    pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
    
    print(f"Sent {len(can_sends)} CAN messages")


def continuous_can_sender():
    """Example of continuously sending CAN messages at a specific rate."""
    pm = messaging.PubMaster(['sendcan'])
    
    counter = 0
    try:
        while True:
            # Create a message with changing data
            data = bytes([counter & 0xFF, (counter >> 8) & 0xFF, 0, 0, 0, 0, 0, 0])
            can_sends = [(0x200, data, 0)]
            
            # Send the message
            pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
            
            print(f"Sent message {counter}: {data.hex()}")
            counter += 1
            
            # Send at 10Hz (100ms interval)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopped sending CAN messages")


if __name__ == "__main__":
    print("CAN Message Injection Examples")
    print("==============================")
    
    # Example 1: Send a single message
    print("\n1. Sending single CAN message:")
    send_can_message(0x123, b'\x01\x02\x03\x04\x05\x06\x07\x08', bus=0)
    
    # Example 2: Send multiple messages
    print("\n2. Sending multiple CAN messages:")
    send_multiple_can_messages()
    
    # Example 3: Continuous sending (uncomment to run)
    print("\n3. To start continuous sending, uncomment the line below:")
    print("   (Press Ctrl+C to stop)")
    # continuous_can_sender()
    
    print("\nIMPORTANT NOTES:")
    print("- Messages sent to 'sendcan' are forwarded to the CAN hardware by pandad")
    print("- pandad subscribes to 'sendcan' and sends messages through the Panda device")
    print("- Messages older than 1 second are dropped by pandad for safety")
    print("- Always be careful when injecting CAN messages on a real vehicle!")