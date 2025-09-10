#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiosmtpd>=1.4.0",
#     "cryptography>=41.0.0",
# ]
# ///

import argparse
import asyncio
import socket
import subprocess
import sys
import ssl
import os
from pathlib import Path
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer, AuthResult
from email import message_from_bytes
from email.policy import default
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime


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



def generate_self_signed_cert(cert_file='mailserver.crt', key_file='mailserver.key'):
    """Generate a self-signed certificate for TLS"""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MailServer"),
        x509.NameAttribute(NameOID.COMMON_NAME, socket.gethostname()),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName(socket.gethostname()),
            x509.IPAddress(socket.inet_aton("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Write private key
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    return cert_file, key_file


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
        if port == 587:
            print(f"  # For port 587 with STARTTLS:")
            print(f"  swaks --to test@localhost --server 127.0.0.1:{port} --tls")
            print(f"  openssl s_client -starttls smtp -connect 127.0.0.1:{port}")
        else:
            print(f"  telnet 127.0.0.1 {port}")
            print(f"  swaks --to test@localhost --server 127.0.0.1:{port}")
        print(f"  python test_email.py  # If you have a test script")
    else:
        print("Local testing:")
        if port == 587:
            print(f"  # For port 587 with STARTTLS:")
            print(f"  swaks --to test@localhost --server {hostname}:{port} --tls")
            print(f"  openssl s_client -starttls smtp -connect {hostname}:{port}")
        else:
            print(f"  telnet {hostname} {port}")
            print(f"  swaks --to test@localhost --server {hostname}:{port}")
        
        if local_ip:
            print(f"\nExternal testing (from another machine):")
            if port == 587:
                print(f"  swaks --to test@localhost --server {local_ip}:{port} --tls")
                print(f"  openssl s_client -starttls smtp -connect {local_ip}:{port}")
            else:
                print(f"  telnet {local_ip} {port}")
                print(f"  swaks --to test@localhost --server {local_ip}:{port}")
            print(f"\n⚠️  External access requires:")
            print(f"  1. Port {port} open in firewall")
            print(f"  2. No NAT/router blocking if testing from internet")
            print(f"  3. ISP not blocking port {port}")
            if port == 587:
                print(f"  4. Email clients must support STARTTLS")
    
    print("-" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description='Simple email server that prints emails to console')
    parser.add_argument('--host', default='0.0.0.0', 
                        help='Hostname to bind to (default: 0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=587,
                        help='Port to listen on (default: 587 for SMTP submission with STARTTLS)')
    parser.add_argument('--tls', action='store_true', default=True,
                        help='Enable TLS/STARTTLS support (default: enabled for port 587)')
    parser.add_argument('--no-tls', dest='tls', action='store_false',
                        help='Disable TLS/STARTTLS support')
    parser.add_argument('--cert', default='mailserver.crt',
                        help='Path to TLS certificate file (default: mailserver.crt)')
    parser.add_argument('--key', default='mailserver.key',
                        help='Path to TLS private key file (default: mailserver.key)')
    parser.add_argument('--generate-cert', action='store_true',
                        help='Generate a self-signed certificate if none exists')
    
    args = parser.parse_args()
    
    hostname = args.host
    port = args.port
    
    # Setup TLS if enabled
    ssl_context = None
    if args.tls:
        # Check if we need to generate certificates
        if args.generate_cert or (not os.path.exists(args.cert) or not os.path.exists(args.key)):
            print("🔒 Generating self-signed certificate for TLS...")
            cert_file, key_file = generate_self_signed_cert(args.cert, args.key)
            print(f"   ✅ Certificate generated: {cert_file}")
            print(f"   ✅ Private key generated: {key_file}")
        
        # Check if certificates exist
        if not os.path.exists(args.cert) or not os.path.exists(args.key):
            print(f"\n❌ TLS enabled but certificate files not found:")
            print(f"   Certificate: {args.cert}")
            print(f"   Private key: {args.key}")
            print(f"\n   Use --generate-cert to generate a self-signed certificate")
            print(f"   Or use --no-tls to disable TLS")
            sys.exit(1)
        
        # Create SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(args.cert, args.key)
        print(f"🔒 TLS enabled using certificate: {args.cert}")
    
    # Run diagnostics first
    if not run_diagnostics(hostname, port):
        print("\n❌ Diagnostics failed. Please fix the issues above before starting the server.")
        sys.exit(1)
    
    # Create and start the server
    handler = EmailHandler()
    
    # Configure controller based on TLS settings
    if ssl_context:
        # For STARTTLS, we need to configure it properly
        controller = Controller(
            handler, 
            hostname=hostname, 
            port=port,
            require_starttls=True,
            ssl_context=ssl_context
        )
    else:
        controller = Controller(handler, hostname=hostname, port=port)
    
    print(f"\n🚀 Email server starting on {hostname}:{port}")
    if ssl_context:
        print(f"🔒 STARTTLS enabled - clients must use STARTTLS to send emails")
    else:
        print(f"⚠️  TLS disabled - connections will be unencrypted")
    
    if hostname == '0.0.0.0':
        local_ip = get_local_ip()
        if local_ip:
            print(f"📮 Accepting emails from all interfaces")
            print(f"📮 External access: {local_ip}:{port}")
    else:
        print(f"📮 Send test emails to: test@localhost:{port}")
    
    if port == 587:
        print(f"📝 Port 587 is the standard SMTP submission port (with STARTTLS)")
    elif port == 25:
        print(f"📝 Port 25 is the standard SMTP port (usually for server-to-server)")
    
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