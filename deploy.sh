#!/bin/bash
# Pull latest code and restart the service
set -e

APP_DIR="/home/ubuntu/app"
SERVICE_NAME="fifa-sentiment"

echo "Pulling latest code..."
git -C "$APP_DIR" pull

echo "Installing any new dependencies..."
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "Restarting service..."
sudo systemctl restart "$SERVICE_NAME"

echo "Done. Logs: sudo journalctl -u $SERVICE_NAME -f"
