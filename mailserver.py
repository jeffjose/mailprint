#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiosmtpd>=1.4.0",
# ]
# ///

import argparse
import asyncio
import socket
import subprocess
import sys
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer
from email import message_from_bytes
from email.policy import default


class EmailHandler:
    async def handle_DATA(self, server, session, envelope):
        """Handle incoming email data"""
        try:
            # Parse the email message
            msg = message_from_bytes(envelope.content, policy=default)
            
            # Extract subject and body
            subject = msg.get('Subject', '(no subject)')
            sender = envelope.mail_from
            recipients = ', '.join(envelope.rcpt_tos)
            
            # Get the email body
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_content()
                        break
                    elif part.get_content_type() == 'text/html' and not body:
                        body = part.get_content()
            else:
                body = msg.get_content()
            
            # Print email details
            print("\n" + "="*60)
            print(f"📧 NEW EMAIL RECEIVED")
            print("-"*60)
            print(f"From: {sender}")
            print(f"To: {recipients}")
            print(f"Subject: {subject}")
            print("-"*60)
            print("Body:")
            print(body.strip() if body else "(empty body)")
            print("="*60 + "\n")
            
            return '250 Message accepted for delivery'
            
        except Exception as e:
            print(f"Error processing email: {e}")
            return '500 Error processing message'


def check_port_availability(hostname, port):
    """Check if the port is available for binding"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return result != 0  # Port is available if connection fails
    except Exception as e:
        return False


def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def check_firewall_status():
    """Check firewall status (Linux only for now)"""
    firewall_info = []
    
    # Check ufw status
    try:
        result = subprocess.run(['ufw', 'status'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            if 'inactive' in result.stdout.lower():
                firewall_info.append("UFW: inactive")
            else:
                firewall_info.append("UFW: active (may need to allow port)")
    except:
        pass
    
    # Check iptables
    try:
        result = subprocess.run(['iptables', '-L', '-n'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            if 'ACCEPT     all' in result.stdout and 'policy ACCEPT' in result.stdout:
                firewall_info.append("iptables: permissive")
            else:
                firewall_info.append("iptables: configured (check rules)")
    except:
        pass
    
    return firewall_info if firewall_info else ["Firewall status: unknown"]


def run_diagnostics(hostname, port):
    """Run diagnostics to check if the server can receive emails"""
    print("🔍 Running diagnostics...")
    print("-" * 60)
    
    # Check port availability
    port_available = check_port_availability(hostname, port)
    if port_available:
        print(f"✅ Port {port} is available for binding")
    else:
        print(f"❌ Port {port} appears to be in use")
        print(f"   Try: lsof -i :{port} or netstat -tlnp | grep {port}")
        return False
    
    # Get local IP
    local_ip = get_local_ip()
    if local_ip:
        print(f"✅ Local IP address: {local_ip}")
        if hostname == '127.0.0.1':
            print(f"   ⚠️  Server bound to localhost only - not accessible externally")
            print(f"   💡 To accept external emails, use hostname='0.0.0.0' or '{local_ip}'")
    else:
        print("⚠️  Could not determine local IP address")
    
    # Check firewall
    firewall_status = check_firewall_status()
    print(f"🔥 Firewall status: {', '.join(firewall_status)}")
    
    # Provide testing instructions
    print("\n📧 Testing instructions:")
    print("-" * 60)
    
    if hostname == '127.0.0.1':
        print("Local testing only:")
        print(f"  telnet 127.0.0.1 {port}")
        print(f"  python test_email.py  # If you have a test script")
        print(f"  swaks --to test@localhost --server 127.0.0.1:{port}")
    else:
        print("Local testing:")
        print(f"  telnet {hostname} {port}")
        if local_ip:
            print(f"\nExternal testing (from another machine):")
            print(f"  telnet {local_ip} {port}")
            print(f"  swaks --to test@localhost --server {local_ip}:{port}")
            print(f"\n⚠️  External access requires:")
            print(f"  1. Port {port} open in firewall")
            print(f"  2. No NAT/router blocking if testing from internet")
            print(f"  3. ISP not blocking port {port}")
    
    print("-" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description='Simple email server that prints emails to console')
    parser.add_argument('--host', default='127.0.0.1', 
                        help='Hostname to bind to (default: 127.0.0.1, use 0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=1025,
                        help='Port to listen on (default: 1025)')
    parser.add_argument('--external', action='store_true',
                        help='Bind to all interfaces (equivalent to --host 0.0.0.0)')
    
    args = parser.parse_args()
    
    # Override host if --external is used
    hostname = '0.0.0.0' if args.external else args.host
    port = args.port
    
    # Run diagnostics first
    if not run_diagnostics(hostname, port):
        print("\n❌ Diagnostics failed. Please fix the issues above before starting the server.")
        sys.exit(1)
    
    # Create and start the server
    handler = EmailHandler()
    controller = Controller(handler, hostname=hostname, port=port)
    
    print(f"\n🚀 Email server starting on {hostname}:{port}")
    if hostname == '0.0.0.0':
        local_ip = get_local_ip()
        if local_ip:
            print(f"📮 Accepting emails from all interfaces")
            print(f"📮 External access: {local_ip}:{port}")
    else:
        print(f"📮 Send test emails to: test@localhost:{port}")
    print("Press Ctrl+C to stop the server\n")
    
    controller.start()
    
    try:
        # Keep the server running
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Shutting down email server...")
    finally:
        controller.stop()
        print("Server stopped.")


if __name__ == "__main__":
    main()