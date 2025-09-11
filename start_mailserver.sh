#!/bin/bash
# Script to properly start the mail server

# Kill any existing mailserver processes
echo "Stopping any existing mailserver processes..."
sudo pkill -9 -f 'python.*mailserver' 2>/dev/null
sleep 2

# Check which port to use
PORT=${1:-2525}
echo "Starting mailserver on port $PORT..."

# Add firewall rule if needed
sudo iptables -C INPUT -p tcp --dport $PORT -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT 10 -p tcp --dport $PORT -j ACCEPT

# Start the server
cd ~/mailprint
sudo ./mailserver --port $PORT --no-tls