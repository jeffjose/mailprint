#!/usr/bin/env python3

import socket
import sys
import time

def test_smtp_connection(host, port=25):
    """Test basic SMTP connection and commands"""
    print(f"Testing SMTP connection to {host}:{port}")
    print("-" * 60)
    
    try:
        # Create socket
        print(f"1. Creating socket connection to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        
        # Connect
        print(f"2. Connecting...")
        sock.connect((host, port))
        print("   ✓ Connected successfully")
        
        # Read initial banner
        print("3. Reading server banner...")
        data = sock.recv(1024)
        banner = data.decode('utf-8', errors='ignore')
        print(f"   Banner: {banner.strip()}")
        
        # Send EHLO
        print("4. Sending EHLO command...")
        sock.send(b"EHLO testclient\r\n")
        time.sleep(0.5)
        
        # Read EHLO response
        print("5. Reading EHLO response...")
        data = sock.recv(1024)
        response = data.decode('utf-8', errors='ignore')
        print(f"   Response: {response.strip()}")
        
        # Send MAIL FROM
        print("6. Sending MAIL FROM...")
        sock.send(b"MAIL FROM:<test@example.com>\r\n")
        time.sleep(0.5)
        
        # Read response
        data = sock.recv(1024)
        response = data.decode('utf-8', errors='ignore')
        print(f"   Response: {response.strip()}")
        
        # Send RCPT TO
        print("7. Sending RCPT TO...")
        sock.send(b"RCPT TO:<test@localhost>\r\n")
        time.sleep(0.5)
        
        # Read response
        data = sock.recv(1024)
        response = data.decode('utf-8', errors='ignore')
        print(f"   Response: {response.strip()}")
        
        # Send DATA
        print("8. Sending DATA command...")
        sock.send(b"DATA\r\n")
        time.sleep(0.5)
        
        # Read response
        data = sock.recv(1024)
        response = data.decode('utf-8', errors='ignore')
        print(f"   Response: {response.strip()}")
        
        # Send email content
        print("9. Sending email content...")
        email_data = b"""Subject: Test Email
From: test@example.com
To: test@localhost

This is a test email.
.\r\n"""
        sock.send(email_data)
        time.sleep(0.5)
        
        # Read final response
        data = sock.recv(1024)
        response = data.decode('utf-8', errors='ignore')
        print(f"   Response: {response.strip()}")
        
        # Send QUIT
        print("10. Sending QUIT...")
        sock.send(b"QUIT\r\n")
        time.sleep(0.5)
        
        # Read QUIT response
        data = sock.recv(1024)
        response = data.decode('utf-8', errors='ignore')
        print(f"   Response: {response.strip()}")
        
        # Close connection
        sock.close()
        print("\n✅ Test completed successfully!")
        
    except socket.timeout:
        print(f"\n❌ Connection timed out after 10 seconds")
        print("   Possible causes:")
        print("   - Server not running")
        print("   - Firewall blocking connection")
        print("   - Wrong IP/port")
    except ConnectionRefused:
        print(f"\n❌ Connection refused")
        print("   The server is not listening on port {port}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"   Type: {type(e).__name__}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_mail.py <host> [port]")
        print("Example: python debug_mail.py 192.18.136.224 25")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    
    test_smtp_connection(host, port)