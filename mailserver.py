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
    import datetime
    import ipaddress
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    
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
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName(socket.gethostname()),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
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


def get_external_ip():
    """Get the external IP address of this machine"""
    import urllib.request
    import json
    
    # Try multiple services in case one is down
    services = [
        ('https://ifconfig.co/json', 'ip'),
        ('https://api.ipify.org?format=json', 'ip'),
        ('https://ipinfo.io/json', 'ip'),
    ]
    
    for url, field in services:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                return data.get(field)
        except:
            continue
    
    # Fallback to text-based service
    try:
        with urllib.request.urlopen('https://ifconfig.co/ip', timeout=5) as response:
            return response.read().decode().strip()
    except:
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
            print(f"  swaks --to test@localhost --from sender@example.com \\")
            print(f"    --server 127.0.0.1:{port} --tls \\")
            print(f"    --header 'Subject: Test Email' \\")
            print(f"    --body 'This is a test email body'")
            print(f"  openssl s_client -starttls smtp -connect 127.0.0.1:{port}")
        else:
            print(f"  telnet 127.0.0.1 {port}")
            print(f"  swaks --to test@localhost --from sender@example.com \\")
            print(f"    --server 127.0.0.1:{port} \\")
            print(f"    --header 'Subject: Test Email' \\")
            print(f"    --body 'This is a test email body'")
        print(f"  python test_email.py  # If you have a test script")
    else:
        print("Local testing:")
        if port == 587:
            print(f"  # For port 587 with STARTTLS:")
            print(f"  swaks --to test@localhost --from sender@example.com \\")
            print(f"    --server {hostname}:{port} --tls \\")
            print(f"    --header 'Subject: Test Email' \\")
            print(f"    --body 'This is a test email body'")
            print(f"  openssl s_client -starttls smtp -connect {hostname}:{port}")
        else:
            print(f"  telnet {hostname} {port}")
            print(f"  swaks --to test@localhost --from sender@example.com \\")
            print(f"    --server {hostname}:{port} \\")
            print(f"    --header 'Subject: Test Email' \\")
            print(f"    --body 'This is a test email body'")
        
        # Get external IP for testing commands
        external_ip = get_external_ip()
        test_ip = external_ip if external_ip else local_ip
        
        if test_ip:
            print(f"\nExternal testing (from another machine):")
            if external_ip:
                print(f"  # From internet (using external IP):")
            else:
                print(f"  # From local network (external IP unavailable):")
            
            if port == 587:
                print(f"  swaks --to test@localhost --from sender@example.com \\")
                print(f"    --server {test_ip}:{port} --tls \\")
                print(f"    --header 'Subject: Test Email' \\")
                print(f"    --body 'This is a test email body'")
                print(f"  openssl s_client -starttls smtp -connect {test_ip}:{port}")
            else:
                print(f"  telnet {test_ip} {port}")
                print(f"  swaks --to test@localhost --from sender@example.com \\")
                print(f"    --server {test_ip}:{port} \\")
                print(f"    --header 'Subject: Test Email' \\")
                print(f"    --body 'This is a test email body'")
            
            if local_ip and local_ip != test_ip:
                print(f"\n  # From local network:")
                if port == 587:
                    print(f"  swaks --to test@localhost --from sender@example.com \\")
                    print(f"    --server {local_ip}:{port} --tls \\")
                    print(f"    --header 'Subject: Test Email' \\")
                    print(f"    --body 'This is a test email body'")
                    print(f"  openssl s_client -starttls smtp -connect {local_ip}:{port}")
                else:
                    print(f"  telnet {local_ip} {port}")
                    print(f"  swaks --to test@localhost --from sender@example.com \\")
                    print(f"    --server {local_ip}:{port} \\")
                    print(f"    --header 'Subject: Test Email' \\")
                    print(f"    --body 'This is a test email body'")
            
            print(f"\n⚠️  External access requires:")
            print(f"  1. Port {port} open in firewall")
            print(f"  2. No NAT/router blocking if testing from internet")
            print(f"  3. ISP not blocking port {port}")
            if port == 587:
                print(f"  4. Email clients must support STARTTLS")
    
    print("-" * 60)
    return True


def find_letsencrypt_cert():
    """Try to find Let's Encrypt certificates automatically"""
    hostname = socket.getfqdn()
    
    # Common Let's Encrypt paths to check
    possible_paths = [
        (f'/etc/letsencrypt/live/{hostname}/fullchain.pem', 
         f'/etc/letsencrypt/live/{hostname}/privkey.pem'),
        # Also check domain without subdomain
        (f'/etc/letsencrypt/live/{".".join(hostname.split(".")[-2:])}/fullchain.pem',
         f'/etc/letsencrypt/live/{".".join(hostname.split(".")[-2:])}/privkey.pem') if '.' in hostname else (None, None),
        # Check for any cert in Let's Encrypt directory
        ('/etc/letsencrypt/live/*/fullchain.pem', '/etc/letsencrypt/live/*/privkey.pem'),
    ]
    
    for cert_path, key_path in possible_paths:
        if cert_path and key_path:
            # Handle wildcards
            if '*' in cert_path:
                import glob
                certs = glob.glob(cert_path)
                keys = glob.glob(key_path)
                if certs and keys:
                    return certs[0], keys[0]
            elif os.path.exists(cert_path) and os.path.exists(key_path):
                return cert_path, key_path
    
    # Fallback to local self-signed
    return 'mailserver.crt', 'mailserver.key'


def main():
    # Auto-detect Let's Encrypt certificates
    default_cert, default_key = find_letsencrypt_cert()
    
    parser = argparse.ArgumentParser(description='Simple email server that prints emails to console')
    parser.add_argument('--host', default='0.0.0.0', 
                        help='Hostname to bind to (default: 0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=25,
                        help='Port to listen on (default: 25 for SMTP server-to-server delivery)')
    parser.add_argument('--tls', action='store_true', default=True,
                        help='Enable TLS/STARTTLS support (default: enabled)')
    parser.add_argument('--no-tls', dest='tls', action='store_false',
                        help='Disable TLS/STARTTLS support')
    parser.add_argument('--cert', default=default_cert,
                        help=f'Path to TLS certificate file (default: {default_cert})')
    parser.add_argument('--key', default=default_key,
                        help=f'Path to TLS private key file (default: {default_key})')
    parser.add_argument('--generate-cert', action='store_true',
                        help='Generate a self-signed certificate if none exists')
    
    args = parser.parse_args()
    
    hostname = args.host
    port = args.port
    
    # Setup TLS if enabled
    ssl_context = None
    if args.tls:
        # Show certificate type being used
        print("\n📋 Certificate Configuration:")
        
        # Check if Let's Encrypt certs are being used
        if '/etc/letsencrypt/' in args.cert:
            if os.path.exists(args.cert) and os.path.exists(args.key):
                print(f"   🔒 Using Let's Encrypt certificate")
                print(f"      Certificate: {args.cert}")
                print(f"      Private key: {args.key}")
            else:
                print(f"   ⚠️  Let's Encrypt path configured but certificates not found")
                print(f"      Expected: {args.cert}")
                print(f"      To obtain: sudo certbot certonly --standalone -d {socket.getfqdn()}")
                print(f"   📝 Falling back to self-signed certificate...")
                # Fall back to self-signed
                args.cert = 'mailserver.crt'
                args.key = 'mailserver.key'
                args.generate_cert = True
        elif args.cert == 'mailserver.crt':
            print(f"   🔐 Using self-signed certificate")
            print(f"      Certificate: {args.cert}")
            print(f"      Private key: {args.key}")
        else:
            print(f"   📜 Using custom certificate")
            print(f"      Certificate: {args.cert}")
            print(f"      Private key: {args.key}")
        
        # Check if we need to generate certificates
        if args.generate_cert or (not os.path.exists(args.cert) or not os.path.exists(args.key)):
            if args.cert == 'mailserver.crt':  # Only generate if using default local paths
                try:
                    print("🔒 Generating self-signed certificate for TLS...")
                    cert_file, key_file = generate_self_signed_cert(args.cert, args.key)
                    print(f"   ✅ Certificate generated: {cert_file}")
                    print(f"   ✅ Private key generated: {key_file}")
                except Exception as e:
                    print(f"\n❌ Failed to generate self-signed certificate:")
                    print(f"   Error: {str(e)}")
                    print(f"\n   Possible solutions:")
                    print(f"   1. Install cryptography: pip install cryptography")
                    print(f"   2. Check file permissions in current directory")
                    print(f"   3. Use --no-tls to run without TLS support")
                    sys.exit(1)
        
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
    
    # Skip diagnostics - too verbose
    
    # Create and start the server
    handler = EmailHandler()
    
    # Determine certificate type for display
    cert_type = None
    if ssl_context:
        if '/etc/letsencrypt/' in args.cert:
            cert_type = "Let's Encrypt"
        elif args.cert == 'mailserver.crt':
            cert_type = "self-signed"
        else:
            cert_type = "custom"
    
    # Use custom server implementation when TLS is enabled to fix greeting bug
    if ssl_context:
        # Use our custom implementation that properly sends SMTP greeting
        import asyncio
        
        class WorkingSMTPServer:
            def __init__(self, handler, hostname, port, ssl_context):
                self.handler = handler
                self.hostname = hostname
                self.port = port
                self.ssl_context = ssl_context
                self.server = None
                
            async def handle_client(self, reader, writer):
                """Handle a client connection with proper SMTP greeting"""
                client_addr = writer.get_extra_info('peername')
                
                try:
                    # Send initial greeting immediately - this fixes the bug!
                    writer.write(b"220 Mail Server Ready\r\n")
                    await writer.drain()
                    
                    envelope = type('Envelope', (), {
                        'mail_from': None,
                        'rcpt_tos': [],
                        'content': b''
                    })()
                    
                    session = type('Session', (), {'peer': client_addr})()
                    
                    while True:
                        try:
                            data = await asyncio.wait_for(reader.readline(), timeout=30.0)
                        except asyncio.TimeoutError:
                            break
                            
                        if not data:
                            break
                            
                        command = data.decode('utf-8', errors='ignore').strip()
                        parts = command.split(None, 1)
                        if not parts:
                            continue
                            
                        cmd = parts[0].upper()
                        arg = parts[1] if len(parts) > 1 else ''
                        
                        if cmd in ("EHLO", "HELO"):
                            response = f"250-{socket.getfqdn()}\r\n250-8BITMIME\r\n"
                            if self.ssl_context:
                                response += "250-STARTTLS\r\n"
                            response += "250 OK\r\n"
                            writer.write(response.encode())
                            
                        elif cmd == "STARTTLS" and self.ssl_context:
                            writer.write(b"220 Ready to start TLS\r\n")
                            await writer.drain()
                            
                            # Upgrade to TLS
                            transport = writer.transport
                            protocol = transport.get_protocol()
                            new_transport = await asyncio.get_event_loop().start_tls(
                                transport, protocol, self.ssl_context, server_side=True
                            )
                            writer._transport = new_transport
                            
                        elif cmd == "MAIL":
                            envelope.mail_from = arg.replace('FROM:', '').strip('<>')
                            writer.write(b"250 OK\r\n")
                            
                        elif cmd == "RCPT":
                            envelope.rcpt_tos.append(arg.replace('TO:', '').strip('<>'))
                            writer.write(b"250 OK\r\n")
                            
                        elif cmd == "DATA":
                            writer.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                            await writer.drain()
                            
                            # Collect email data
                            email_data = []
                            while True:
                                line = await reader.readline()
                                if line == b".\r\n":
                                    break
                                email_data.append(line)
                            
                            envelope.content = b''.join(email_data)
                            
                            # Call the handler
                            result = await self.handler.handle_DATA(None, session, envelope)
                            writer.write(f"{result}\r\n".encode())
                            
                        elif cmd == "QUIT":
                            writer.write(b"221 Bye\r\n")
                            await writer.drain()
                            break
                        else:
                            writer.write(b"500 Command not recognized\r\n")
                        
                        await writer.drain()
                        
                except Exception as e:
                    pass  # Silently handle connection errors
                finally:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except:
                        pass
            
            async def start_async(self):
                self.server = await asyncio.start_server(
                    self.handle_client, self.hostname, self.port
                )
                async with self.server:
                    await self.server.serve_forever()
                    
            def start(self):
                # Run in a new thread like Controller does
                import threading
                self.thread = threading.Thread(target=self._run)
                self.thread.daemon = True
                self.thread.start()
                # Give it a moment to start and potentially fail
                import time
                time.sleep(0.5)
                if not self.thread.is_alive():
                    raise OSError("[Errno 98] Address already in use")
                
            def _run(self):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.start_async())
                
            def stop(self):
                if self.server:
                    self.server.close()
        
        # Use working implementation for TLS
        controller = WorkingSMTPServer(handler, hostname, port, ssl_context)
    else:
        # Use standard controller for non-TLS
        controller = Controller(
            handler, 
            hostname=hostname, 
            port=port,
            auth_required=False,
            decode_data=False,
            enable_SMTPUTF8=True
        )
    
    # Try to start the server first (fail fast if port is in use)
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
    
    # Server started successfully, show minimal messages
    external_ip = get_external_ip() or "unknown"
    
    print(f"\n✅ Mail server started on port {port}")
    if hostname == '0.0.0.0':
        print(f"📧 Test: swaks --to test@localhost --from sender@example.com --server {external_ip}:{port}")
    print("Press Ctrl+C to stop\n")
    
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