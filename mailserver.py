#!/usr/bin/env -S uv run
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
    parser.add_argument('--host', default='0.0.0.0', 
                        help='Hostname to bind to (default: 0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=25,
                        help='Port to listen on (default: 25)')
    
    args = parser.parse_args()
    
    hostname = args.host
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
    
    try:
        controller.start()
    except PermissionError as e:
        print(f"\n❌ Permission denied: Cannot bind to {hostname}:{port}")
        if port < 1024:
            print(f"   Port {port} requires root privileges.")
            print(f"\n   Try one of these:")
            print(f"   • sudo ./mailserver")
            print(f"   • ./mailserver --port 1025  (or any port >= 1024)")
        else:
            print(f"   Another process may be using port {port}.")
            print(f"   Check with: lsof -i :{port}")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Port {port} is already in use")
            print(f"   Check what's using it: lsof -i :{port}")
            print(f"   Or try a different port: ./mailserver --port {port + 1000}")
        else:
            print(f"\n❌ Failed to start server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error starting server: {e}")
        sys.exit(1)
    
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