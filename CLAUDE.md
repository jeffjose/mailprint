# Mailprint Server Configuration

## Remote Server Details
- **IP Address**: 192.18.136.224
- **SSH Access**: `ssh ubuntu@192.18.136.224`
- **Code Location**: `~/mailprint` on remote server

## Important Notes

### Port Configuration
- **Port 25**: BLOCKED by cloud provider (common anti-spam measure)
- **Port 587**: OPEN and working (standard SMTP submission port)
- **Port 2525**: Alternative SMTP port (needs firewall rules)

### Running the Mail Server

#### On Remote Server
```bash
# SSH to server
ssh ubuntu@192.18.136.224

# Navigate to code directory
cd ~/mailprint

# Pull latest changes
git pull

# Start mail server on port 587 (no TLS)
sudo ./mailserver --port 587 --no-tls

# Or run in background
nohup sudo ./mailserver --port 587 --no-tls > /tmp/mail.log 2>&1 &
```

### Testing the Server

#### From Internet (using swaks)
```bash
# Send test email to port 587
swaks --to test@localhost --from sender@example.com \
  --server 192.18.136.224:587 \
  --header 'Subject: Test Email' \
  --body 'This is a test email body'
```

#### Check connectivity
```bash
# Test if port is open
nc -zv -w 5 192.18.136.224 587
```

### Firewall Configuration
The server uses iptables. Ports 25, 587, and 2525 have been added to the firewall rules:
```bash
sudo iptables -I INPUT -p tcp --dport 587 -j ACCEPT
```

### Known Issues & Solutions

1. **Port 25 is blocked**: This is a cloud provider restriction for spam prevention. Use port 587 instead.

2. **STARTTLS issues**: The server has been configured to make STARTTLS optional rather than required to avoid connection issues.

3. **SSH commands hanging**: Some SSH commands may hang when running the mail server interactively. Use `nohup` or background processes.

### Code Changes Made

1. Modified `mailserver.py` to make STARTTLS optional instead of required
2. Added `auth_required=False` and `decode_data=False` parameters to the Controller
3. Created startup script `start_mailserver.sh` for easier server management

### Deployment Workflow
1. Make changes locally
2. `git add -A && git commit -m "message" && git push`
3. SSH to remote server
4. `cd ~/mailprint && git pull`
5. Restart mail server with updated code