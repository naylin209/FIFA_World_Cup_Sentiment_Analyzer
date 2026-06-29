#!/bin/bash
# FIFA World Cup Sentiment Tracker — one-shot server setup
# Run as: bash setup.sh <your-github-repo-url>
# Example: bash setup.sh https://github.com/yourname/FIFA_World_Cup_Sentiment_Analyzer
set -e

REPO_URL="${1:-}"
APP_DIR="/home/ubuntu/app"
DB_NAME="fifa_sentiment"
DB_USER="postgres"
SERVICE_NAME="fifa-sentiment"

if [ -z "$REPO_URL" ]; then
    echo "Usage: bash setup.sh <github-repo-url>"
    exit 1
fi

echo "===> [1/8] System update"
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

echo "===> [2/8] Install Python 3.12, git, build tools"
sudo apt-get install -y -qq python3.12 python3.12-venv python3-pip git build-essential

echo "===> [3/8] Install PostgreSQL"
sudo apt-get install -y -qq postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

echo "===> [4/8] Create database"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "  database already exists, skipping"
sudo -u postgres psql -c "ALTER USER $DB_USER PASSWORD 'changeme';"

echo "===> [5/8] Create 2 GB swap (needed for HuggingFace model on t2.micro)"
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "  swap created"
else
    echo "  swap already exists, skipping"
fi

echo "===> [6/8] Clone repo and install Python dependencies"
if [ -d "$APP_DIR" ]; then
    echo "  $APP_DIR exists — pulling latest"
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

python3.12 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "===> [7/8] Create .env (you must fill in your real values)"
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" <<EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=changeme
BLUESKY_HANDLE=your.handle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
FOOTBALL_API_KEY=your_key_here
EOF
    echo ""
    echo "  *** IMPORTANT: edit $APP_DIR/.env with your real credentials ***"
    echo "  Run: nano $APP_DIR/.env"
    echo ""
else
    echo "  .env already exists, skipping"
fi

echo "===> [8/8] Install systemd service"
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=FIFA World Cup Sentiment Tracker
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$APP_DIR/venv/bin/python src/dashboard/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

echo ""
echo "============================================"
echo " Setup complete!"
echo " App status : sudo systemctl status $SERVICE_NAME"
echo " Live logs  : sudo journalctl -u $SERVICE_NAME -f"
echo " Restart    : sudo systemctl restart $SERVICE_NAME"
echo "============================================"
echo " Don't forget to fill in .env:"
echo "   nano $APP_DIR/.env"
echo " Then restart: sudo systemctl restart $SERVICE_NAME"
echo "============================================"
