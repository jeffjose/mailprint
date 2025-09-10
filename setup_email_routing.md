# Email Server Setup Guide

## Option 1: Port Forwarding with iptables (Recommended)
Redirect port 25 to 1025 so you don't need root for the Python server:

```bash
# Add iptables rule (requires sudo)
sudo iptables -t nat -A PREROUTING -p tcp --dport 25 -j REDIRECT --to-port 1025

# Save the rule (Ubuntu/Debian)
sudo iptables-save | sudo tee /etc/iptables/rules.v4

# Or for RedHat/CentOS
sudo service iptables save
```

## Option 2: Use Postfix as a Relay
Install and configure Postfix to forward emails to your Python server:

```bash
# Install Postfix
sudo apt-get install postfix  # Debian/Ubuntu
# or
sudo yum install postfix       # RedHat/CentOS

# Edit /etc/postfix/main.cf
sudo nano /etc/postfix/main.cf
```

Add these lines to main.cf:
```
# Forward all mail to local Python server
relayhost = [127.0.0.1]:1025
inet_interfaces = all
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain

# Disable local delivery
local_transport = error:local delivery is disabled
```

Restart Postfix:
```bash
sudo systemctl restart postfix
```

## Option 3: Direct Port 25 Binding (Requires Root)
Modify mailserver.py to use port 25:
```python
port = 25  # Instead of 1025
```

Run with sudo:
```bash
sudo uv run mailserver.py
```

## Testing External Email Reception

1. **Check firewall allows port 25:**
```bash
sudo ufw allow 25/tcp  # Ubuntu
# or
sudo firewall-cmd --permanent --add-port=25/tcp  # CentOS/RHEL
sudo firewall-cmd --reload
```

2. **Test with telnet:**
```bash
telnet localhost 25
# Type:
HELO test
MAIL FROM: <test@example.com>
RCPT TO: <user@yourdomain.com>
DATA
Subject: Test
This is a test message.
.
QUIT
```

3. **For Internet emails, you need:**
- A domain name pointing to your server's IP
- MX records in DNS pointing to your domain
- Open port 25 on your router/firewall
- No ISP blocking (many ISPs block port 25)

## Quick Local Test
```bash
# Install swaks for testing
sudo apt-get install swaks

# Send test email
swaks --to test@localhost --server localhost:1025
```

## Security Notes
- Running on port 25 exposes you to spam/abuse
- Consider using authentication
- Implement rate limiting
- Use fail2ban for protection
- Consider using established solutions like Postfix/Exim for production