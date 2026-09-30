#!/bin/bash

echo "======================================"
echo "    DarkTunnel Bot Setup Script       "
echo "======================================"

read -p "Enter your Telegram BOT_TOKEN: " BOT_TOKEN
read -p "Enter your Telegram INITIAL_ADMIN_ID: " INITIAL_ADMIN_ID

echo "BOT_TOKEN=$BOT_TOKEN" > .env
echo "INITIAL_ADMIN_ID=$INITIAL_ADMIN_ID" >> .env

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installing Playwright browsers..."
playwright install --with-deps chromium

echo "Setting up systemd service..."
SERVICE_FILE="/etc/systemd/system/cloudrun-bot.service"
CURRENT_DIR=$(pwd)
CURRENT_USER=$USER

sudo bash -c "cat << 'SVC' > $SERVICE_FILE
[Unit]
Description=DarkTunnel Telegram Bot
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python $CURRENT_DIR/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
SVC"

sudo systemctl daemon-reload
sudo systemctl enable cloudrun-bot
sudo systemctl start cloudrun-bot

echo "======================================"
echo "  Setup complete! Service started.    "
echo "  Check status with:                  "
echo "  sudo systemctl status cloudrun-bot  "
echo "======================================"
