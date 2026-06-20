#!/bin/bash
DIR="/home/ollie/decentralized strength pod"
cd "$DIR"
python3 server.py &
sleep 2
google-chrome-stable --app=http://localhost:8080
