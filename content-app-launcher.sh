#!/bin/bash
DIR="/home/ollie/decentralized strength pod"
cd "$DIR"
python3 server.py &
sleep 1.5
firefox --new-window "http://localhost:8080" 2>/dev/null &
