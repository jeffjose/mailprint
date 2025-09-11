#!/bin/bash

# Test script to run on remote server
echo "=== Remote Server Mail Test Script ==="
echo

echo "1. Checking network interfaces:"
ip addr show | grep -E "inet |UP"
echo

echo "2. Checking firewall rules (ufw):"
sudo ufw status numbered
echo

echo "3. Checking iptables:"
sudo iptables -L INPUT -n -v | head -20
echo

echo "4. Testing if port 25 is listening:"
sudo netstat -tlnp | grep :25
echo

echo "5. Testing if port 587 is listening:"
sudo netstat -tlnp | grep :587
echo

echo "6. Checking for any SMTP processes:"
ps aux | grep -E "mail|smtp" | grep -v grep
echo

echo "7. Testing local connection to port 25:"
timeout 2 telnet localhost 25 2>&1 | head -5
echo

echo "8. External IP address:"
curl -s ifconfig.co
echo

echo "9. Starting mailserver on port 25 without TLS..."
echo "Run: sudo ./mailserver --port 25 --no-tls"