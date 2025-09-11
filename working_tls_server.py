#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""Working SMTP server that properly handles STARTTLS"""

import asyncio
import ssl
import socket
import sys
from pathlib import Path

class SimpleSMTPServer:
    def __init__(self, host='0.0.0.0', port=587, ssl_context=None):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.server = None
        
    async def handle_client(self, reader, writer):
        """Handle a client connection"""
        client_addr = writer.get_extra_info('peername')
        print(f"New connection from {client_addr}")
        
        try:
            # Send initial greeting immediately
            writer.write(b"220 Mail Server Ready\r\n")
            await writer.drain()
            
            while True:
                # Read command from client
                try:
                    data = await asyncio.wait_for(reader.readline(), timeout=30.0)
                except asyncio.TimeoutError:
                    break
                    
                if not data:
                    break
                    
                command = data.decode('utf-8', errors='ignore').strip()
                print(f"< {command}")
                
                # Parse command
                parts = command.split(None, 1)
                if not parts:
                    continue
                    
                cmd = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ''
                
                # Handle SMTP commands
                if cmd == "EHLO" or cmd == "HELO":
                    response = f"250-{socket.getfqdn()}\r\n"
                    response += "250-8BITMIME\r\n"
                    if self.ssl_context:
                        response += "250-STARTTLS\r\n"
                    response += "250 OK\r\n"
                    writer.write(response.encode())
                    
                elif cmd == "STARTTLS":
                    if self.ssl_context:
                        writer.write(b"220 Ready to start TLS\r\n")
                        await writer.drain()
                        
                        # Upgrade to TLS
                        transport = writer.transport
                        protocol = transport.get_protocol()
                        
                        new_transport = await asyncio.get_event_loop().start_tls(
                            transport,
                            protocol,
                            self.ssl_context,
                            server_side=True
                        )
                        
                        # Update reader/writer with new transport
                        writer._transport = new_transport
                        
                    else:
                        writer.write(b"454 TLS not available\r\n")
                        
                elif cmd == "MAIL":
                    self.mail_from = arg
                    writer.write(b"250 OK\r\n")
                    
                elif cmd == "RCPT":
                    self.rcpt_to = arg
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
                        email_data.append(line.decode('utf-8', errors='ignore'))
                    
                    # Print received email
                    print("\n" + "="*60)
                    print("📧 NEW EMAIL RECEIVED")
                    print("-"*60)
                    print(''.join(email_data))
                    print("="*60 + "\n")
                    
                    writer.write(b"250 Message accepted\r\n")
                    
                elif cmd == "QUIT":
                    writer.write(b"221 Bye\r\n")
                    await writer.drain()
                    break
                    
                else:
                    writer.write(b"500 Command not recognized\r\n")
                
                await writer.drain()
                
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"Connection closed from {client_addr}")
    
    async def start(self):
        """Start the SMTP server"""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        addr = self.server.sockets[0].getsockname()
        print(f"✅ SMTP Server listening on {addr[0]}:{addr[1]}")
        print(f"📧 Test: swaks --to test@localhost --from test@example.com --server <ip>:{addr[1]} --tls")
        print("Press Ctrl+C to stop\n")
        
        async with self.server:
            await self.server.serve_forever()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Working SMTP server with STARTTLS')
    parser.add_argument('--port', type=int, default=587, help='Port to listen on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--cert', default='/etc/letsencrypt/live/telemetry.fyi/fullchain.pem',
                        help='Certificate file')
    parser.add_argument('--key', default='/etc/letsencrypt/live/telemetry.fyi/privkey.pem',
                        help='Private key file')
    parser.add_argument('--no-tls', action='store_true', help='Disable TLS')
    args = parser.parse_args()
    
    # Setup SSL context if certificates exist and TLS is enabled
    ssl_context = None
    if not args.no_tls and Path(args.cert).exists() and Path(args.key).exists():
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(args.cert, args.key)
        print(f"🔒 TLS enabled using: {args.cert}")
    elif not args.no_tls:
        print("⚠️  Certificates not found, running without TLS")
    else:
        print("⚠️  TLS disabled by --no-tls flag")
    
    # Create and start server
    server = SimpleSMTPServer(args.host, args.port, ssl_context)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n✋ Server stopped")

if __name__ == "__main__":
    main()