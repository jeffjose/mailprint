#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "fastapi",
#     "uvicorn",
# ]
# ///
"""HTTP/HTTPS server that receives emails via POST and prints them to console"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import argparse
import sys
import os
import ssl

app = FastAPI(title="Email Receiver", version="1.0.0")

class Email(BaseModel):
    from_: Optional[str] = None
    to: Optional[str | List[str]] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    text: Optional[str] = None
    html: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    
    class Config:
        fields = {'from_': 'from'}

@app.get("/")
async def root():
    return {"message": "Email receiver is running. POST to /email to submit emails."}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "email-receiver"}

@app.get("/email")
async def email_info():
    return {"message": "Email endpoint ready. Use POST to submit emails.", "status": "ready"}

@app.post("/email")
async def receive_email(email: Email):
    """Receive and print email"""
    # Extract email fields
    sender = email.from_ or '(unknown)'
    recipients = email.to or '(unknown)'
    subject = email.subject or '(no subject)'
    body = email.body or email.text or ''
    html = email.html or ''
    headers = email.headers or {}
    
    # Print email in same format as mailserver
    print("\n" + "="*60)
    print("📧 NEW EMAIL RECEIVED")
    print("-"*60)
    print(f"From: {sender}")
    print(f"To: {recipients if isinstance(recipients, str) else ', '.join(recipients)}")
    print(f"Subject: {subject}")
    
    # Print any additional headers
    if headers:
        for key, value in headers.items():
            if key.lower() not in ['from', 'to', 'subject']:
                print(f"{key}: {value}")
    
    print("-"*60)
    print("Body:")
    if body:
        print(body)
    elif html:
        print("[HTML content received]")
        print(html[:500] + "..." if len(html) > 500 else html)
    else:
        print("(empty body)")
    print("="*60 + "\n")
    
    return {"status": "success", "message": "Email received"}

# Backward compatibility - also accept at /mail
@app.post("/mail")
async def receive_email_alt(email: Email):
    return await receive_email(email)


def main():
    parser = argparse.ArgumentParser(description='HTTP/HTTPS server that receives and prints emails')
    parser.add_argument('--port', type=int, default=443,
                        help='Port to listen on (default: 443 for HTTPS)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--no-tls', action='store_true',
                        help='Disable HTTPS/TLS and use plain HTTP')
    parser.add_argument('--cert', default='/etc/letsencrypt/live/telemetry.fyi/fullchain.pem',
                        help='Path to SSL certificate (default: /etc/letsencrypt/live/telemetry.fyi/fullchain.pem)')
    parser.add_argument('--key', default='/etc/letsencrypt/live/telemetry.fyi/privkey.pem',
                        help='Path to SSL private key (default: /etc/letsencrypt/live/telemetry.fyi/privkey.pem)')
    args = parser.parse_args()
    
    # If no-tls is specified and port is still 443, switch to 80
    if args.no_tls and args.port == 443:
        args.port = 80
    
    # Check if we need root for port < 1024
    if args.port < 1024 and sys.platform != 'win32':
        import os
        if os.geteuid() != 0:
            print(f"❌ Port {args.port} requires root privileges.")
            print(f"   Run with: sudo {' '.join(sys.argv)}")
            sys.exit(1)
    
    # Setup SSL by default (unless --no-tls is specified)
    ssl_context = None
    if not args.no_tls:
        if not os.path.exists(args.cert) or not os.path.exists(args.key):
            print(f"❌ Certificate files not found:")
            print(f"   Cert: {args.cert}")
            print(f"   Key: {args.key}")
            print(f"\nRun without --tls for HTTP, or provide valid certificates.")
            sys.exit(1)
        
        # Create SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(args.cert, args.key)
        
        print(f"✅ HTTPS Email Receiver starting on {args.host}:{args.port}")
        print(f"🔒 Using certificates from {os.path.dirname(args.cert)}")
        print(f"📧 POST emails to https://{args.host}:{args.port}/email")
    else:
        print(f"✅ HTTP Email Receiver starting on {args.host}:{args.port}")
        print(f"📧 POST emails to http://{args.host}:{args.port}/email")
    
    print("Press Ctrl+C to stop\n")
    
    try:
        if ssl_context:
            uvicorn.run(app, host=args.host, port=args.port, log_level="error",
                       ssl_keyfile=args.key, ssl_certfile=args.cert)
        else:
            uvicorn.run(app, host=args.host, port=args.port, log_level="error")
    except KeyboardInterrupt:
        print("\n✋ Server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {args.port} is already in use")
            print(f"   Check what's using it: lsof -i :{args.port}")
        elif "Permission denied" in str(e):
            print(f"❌ Permission denied for port {args.port}")
            print(f"   Run with: sudo {' '.join(sys.argv)}")
        else:
            print(f"❌ Failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()