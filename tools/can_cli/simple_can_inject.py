#!/usr/bin/env python3
"""
Simple CAN injection example for OpenPilot
Shows the minimal code needed to inject CAN messages
"""

import time
import cereal.messaging as messaging
from openpilot.selfdrive.pandad import can_list_to_can_capnp

def send_can_message(address, data, bus=0):
    """Send a single CAN message through OpenPilot"""
    
    # Create publisher
    pm = messaging.PubMaster(['sendcan'])
    
    # Prepare message (address, data_bytes, bus)
    can_sends = [(address, data, bus)]
    
    # Convert to Cap'n Proto format and send
    pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
    
    print(f"Sent CAN message: 0x{address:03X} {data.hex()} on bus {bus}")

def main():
    """Example usage"""
    
    print("Simple CAN Injection Example")
    print("============================")
    print("WARNING: OpenPilot must be running!")
    print("WARNING: Messages subject to Panda safety checks!")
    print()
    
    # Example 1: Send a single diagnostic message (usually safe)
    print("Example 1: Sending diagnostic query...")
    send_can_message(0x7DF, b'\x02\x01\x00', bus=0)
    time.sleep(0.5)
    
    # Example 2: Send multiple messages
    print("\nExample 2: Sending multiple messages...")
    pm = messaging.PubMaster(['sendcan'])
    
    can_sends = [
        (0x100, b'\x11\x22\x33', 0),
        (0x101, b'\x44\x55\x66', 0),
        (0x102, b'\x77\x88\x99', 0),
    ]
    
    pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
    print(f"Sent batch of {len(can_sends)} messages")
    time.sleep(0.5)
    
    # Example 3: Send messages at specific rate (10 Hz)
    print("\nExample 3: Sending at 10 Hz for 3 seconds...")
    pm = messaging.PubMaster(['sendcan'])
    
    start_time = time.time()
    count = 0
    
    while time.time() - start_time < 3.0:
        # Create message with changing data
        data = bytes([count & 0xFF, (count >> 8) & 0xFF, 0x00])
        can_sends = [(0x200, data, 0)]
        
        pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
        count += 1
        
        time.sleep(0.1)  # 10 Hz
    
    print(f"Sent {count} messages at ~10 Hz")
    
    # Example 4: Using DBC packer
    print("\nExample 4: Using DBC packer...")
    try:
        from opendbc.can.packer import CANPacker
        
        # Create packer for Toyota DBC
        packer = CANPacker("toyota_nodsu_pt_generated")
        
        # Create ACC control message
        values = {
            "MINI_CAR": 1,
            "ACC_TYPE": 1,
        }
        
        # Pack the message
        addr, dat, bus = packer.make_can_msg("ACC_CONTROL", 0, values)
        
        # Send via sendcan
        can_sends = [(addr, dat, bus)]
        pm.send('sendcan', can_list_to_can_capnp(can_sends, msgtype='sendcan'))
        
        print(f"Sent DBC message: 0x{addr:03X} {dat.hex()}")
        
    except Exception as e:
        print(f"DBC example failed: {e}")
    
    print("\nDone! Check pandad logs to verify messages were sent.")

if __name__ == "__main__":
    main()