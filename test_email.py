#!/usr/bin/env python3
"""Test script to send an email to the local server"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_email():
    # Email configuration
    smtp_server = "127.0.0.1"
    smtp_port = 1025
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = "sender@example.com"
    msg['To'] = "recipient@example.com"
    msg['Subject'] = "Test Email - Hello from Python!"
    
    # Email body
    body = """This is a test email message.
    
It contains multiple lines to demonstrate
that the email server correctly handles
and displays the email body.

Best regards,
Test Sender"""
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.send_message(msg)
        print("✅ Test email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        print("Make sure the email server is running on port 1025")

if __name__ == "__main__":
    send_test_email()