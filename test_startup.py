#!/usr/bin/env python3
"""Test script to simulate mailserver startup and port binding"""

import socket
import sys
import time

def test_port_binding(port):
    """Test if we can bind to a port quickly"""
    start_time = time.time()
    
    try:
        # Try to bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.listen(5)
        
        bind_time = time.time() - start_time
        print(f"✅ Successfully bound to port {port} in {bind_time:.3f} seconds")
        
        # Keep it open for a moment
        time.sleep(1)
        sock.close()
        return True
        
    except OSError as e:
        bind_time = time.time() - start_time
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use (detected in {bind_time:.3f} seconds)")
        else:
            print(f"❌ Failed to bind to port {port}: {e} (in {bind_time:.3f} seconds)")
        return False

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8025
    
    print(f"Testing port binding on port {port}...")
    
    # First attempt
    if test_port_binding(port):
        print("\nTesting what happens when port is already in use...")
        
        # Start a server on the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.listen(5)
        
        # Try to bind again (should fail immediately)
        test_port_binding(port)
        
        sock.close()