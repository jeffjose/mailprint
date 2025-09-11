#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiosmtpd>=1.4.0",
# ]
# ///
"""Simplified mail server for debugging - no TLS, just basic SMTP"""

import asyncio
import socket
import sys
from aiosmtpd.controller import Controller
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

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Simple SMTP server')
    parser.add_argument('--port', type=int, default=587,
                        help='Port to listen on (default: 587)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()
    
    handler = EmailHandler()
    
    # Create controller with minimal configuration
    controller = Controller(
        handler,
        hostname=args.host,
        port=args.port,
        auth_required=False,
        require_starttls=False,
        decode_data=False
    )
    
    try:
        controller.start()
        print(f"✅ Mail server started on {args.host}:{args.port}")
        print(f"📧 Ready to receive emails")
        print(f"Test with: swaks --to test@localhost --from sender@example.com --server <ip>:{args.port}")
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