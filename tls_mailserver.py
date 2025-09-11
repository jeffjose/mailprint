#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiosmtpd>=1.4.0",
# ]
# ///
"""Mail server with proper STARTTLS support for Gmail"""

import asyncio
import ssl
import sys
from pathlib import Path
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer
from email import message_from_bytes
from email.policy import default

class EmailHandler:
    async def handle_DATA(self, server, session, envelope):
        """Handle incoming email data"""
        try:
            msg = message_from_bytes(envelope.content, policy=default)
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


class CustomSMTP(SMTPServer):
    """Custom SMTP server that properly handles STARTTLS"""
    
    async def smtp_STARTTLS(self, arg):
        """Handle STARTTLS command"""
        if not self.tls_context:
            await self.push('454 TLS not available')
            return
        
        if self.transport.get_extra_info('sslcontext'):
            await self.push('554 TLS already active')
            return
            
        await self.push('220 Ready to start TLS')
        
        # Upgrade connection to TLS
        try:
            new_transport = await self.loop.start_tls(
                self.transport,
                self.protocol,
                self.tls_context,
                server_side=True
            )
            self.transport = new_transport
        except Exception as e:
            print(f"TLS upgrade failed: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='SMTP server with STARTTLS')
    parser.add_argument('--port', type=int, default=587,
                        help='Port to listen on (default: 587)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--cert', default='/etc/letsencrypt/live/telemetry.fyi/fullchain.pem',
                        help='Certificate file path')
    parser.add_argument('--key', default='/etc/letsencrypt/live/telemetry.fyi/privkey.pem',
                        help='Private key file path')
    args = parser.parse_args()
    
    handler = EmailHandler()
    
    # Create SSL context for STARTTLS
    ssl_context = None
    if Path(args.cert).exists() and Path(args.key).exists():
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(args.cert, args.key)
        print(f"🔒 TLS enabled using certificate: {args.cert}")
    else:
        print(f"⚠️  Certificate not found, running without TLS")
    
    # Create controller
    controller = Controller(
        handler,
        hostname=args.host,
        port=args.port,
        ssl_context=ssl_context,
        auth_required=False,
        require_starttls=False,  # Make STARTTLS optional
        decode_data=False,
        smtp_class=CustomSMTP
    )
    
    try:
        controller.start()
        print(f"✅ Mail server started on port {args.port}")
        print(f"📧 Test: swaks --to test@localhost --from sender@example.com --server <ip>:{args.port} --tls")
        print("Press Ctrl+C to stop\n")
        
        # Keep running
        asyncio.get_event_loop().run_forever()
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {args.port} is already in use")
        else:
            print(f"❌ Failed to start: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✋ Shutting down...")
    finally:
        controller.stop()

if __name__ == "__main__":
    main()