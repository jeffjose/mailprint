#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "aiosmtpd>=1.4.0",
# ]
# ///

import asyncio
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


def main():
    # Server configuration
    hostname = '127.0.0.1'
    port = 1025  # Use port 1025 to avoid needing root privileges
    
    # Create and start the server
    handler = EmailHandler()
    controller = Controller(handler, hostname=hostname, port=port)
    
    print(f"🚀 Email server starting on {hostname}:{port}")
    print(f"📮 Send test emails to: test@localhost:{port}")
    print("Press Ctrl+C to stop the server\n")
    
    controller.start()
    
    try:
        # Keep the server running
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Shutting down email server...")
    finally:
        controller.stop()
        print("Server stopped.")


if __name__ == "__main__":
    main()