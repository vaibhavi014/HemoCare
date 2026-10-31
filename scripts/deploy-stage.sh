#!/bin/bash
set -Eeuo pipefail
umask 077

APP_DIR="/home/ubuntu/HemoCare-stage"
APP_PATH="$APP_DIR/HemoCare"
VENV="$APP_DIR/venv"
DB="$APP_PATH/stage-bloodbank.db"
BACKUP_DIR="/home/ubuntu/hemocare-stage-backups"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

OLD_COMMIT=$(git -C "$APP_DIR" rev-parse HEAD)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="$BACKUP_DIR/stage-db-$TIMESTAMP.db"

echo "Backing up Stage database..."
"$VENV/bin/python" - "$DB" "$BACKUP" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
destination = sqlite3.connect(sys.argv[2])

try:
    source.backup(destination)
finally:
    destination.close()
    source.close()

print("SQLite backup completed successfully.")
PY

chmod 600 "$BACKUP"
rollback() {
    trap - ERR

    echo "Deployment failed. Starting rollback..."

    echo "Stopping Stage service..."
    sudo systemctl stop hemocare-stage

    echo "Restoring previous application code..."
    git -C "$APP_DIR" reset --hard "$OLD_COMMIT"

    echo "Restoring previous dependencies..."
    "$VENV/bin/pip" install -r "$APP_PATH/requirements.txt"

    echo "Restoring Stage database backup..."
    cp "$BACKUP" "$DB"
    chmod 600 "$DB"

    echo "Starting Stage service..."
    sudo systemctl start hemocare-stage

    echo "Rollback completed."
}
trap rollback ERR

echo "Fetching latest Stage code..."
git -C "$APP_DIR" fetch origin stage
git -C "$APP_DIR" reset --hard origin/stage

echo "Installing Stage dependencies..."
"$VENV/bin/pip" install -r "$APP_PATH/requirements.txt"

echo "Restarting Stage service..."
sudo systemctl restart hemocare-stage

sleep 3

echo "Checking Stage service..."
sudo systemctl is-active --quiet hemocare-stage

echo "Checking Stage application..."
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:8001/)

if [[ "$HTTP_CODE" != "302" && "$HTTP_CODE" != "200" ]]; then
    echo "Stage health check failed: HTTP $HTTP_CODE"
    exit 1
fi

trap - ERR

echo "Stage deployment successful."
echo "Previous commit: $OLD_COMMIT"
echo "Database backup: $BACKUP"