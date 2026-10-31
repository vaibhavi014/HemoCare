
#!/bin/bash
set -Eeuo pipefail
umask 077

# ==========================================
# HemoCare - Stage Deployment Configuration
# ==========================================

APP_DIR="/home/ubuntu/HemoCare-stage"
APP_PATH="$APP_DIR/HemoCare"
VENV="$APP_DIR/venv"
DB="$APP_PATH/stage-bloodbank.db"
BACKUP_DIR="/home/ubuntu/hemocare-stage-backups"

# ==========================================
# Step 1: Validate Stage Environment
# ==========================================

echo "Validating Stage environment..."

if [[ ! -d "$APP_DIR" ]]; then
    echo "ERROR: Stage application directory not found."
    exit 1
fi

if [[ ! -d "$VENV" ]]; then
    echo "ERROR: Stage virtual environment not found."
    exit 1
fi

if [[ ! -f "$DB" ]]; then
    echo "ERROR: Stage database not found: $DB"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

OLD_COMMIT=$(git -C "$APP_DIR" rev-parse HEAD)

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="$BACKUP_DIR/stage-db-$TIMESTAMP.db"

# ==========================================
# Step 2: Backup Stage Database
# ==========================================

echo "Creating Stage database backup..."

"$VENV/bin/python" - "$DB" "$BACKUP" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
destination = sqlite3.connect(sys.argv[2])

try:
    source.backup(destination)

    result = destination.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if result != "ok":
        raise RuntimeError(
            f"Database backup integrity check failed: {result}"
        )

    print("SQLite backup and integrity check successful.")

finally:
    destination.close()
    source.close()
PY

chmod 600 "$BACKUP"

if [[ ! -s "$BACKUP" ]]; then
    echo "ERROR: Database backup is empty."
    exit 1
fi

echo "Database backup created: $BACKUP"

# ==========================================
# Step 3: Rollback Function
# ==========================================

rollback() {
    local DEPLOY_EXIT_CODE=$?

    trap - ERR
    set +e

    echo "=========================================="
    echo "Deployment failed. Starting rollback..."
    echo "=========================================="

    echo "Stopping Stage service..."
    sudo systemctl stop hemocare-stage

    echo "Restoring previous application code..."
    git -C "$APP_DIR" reset --hard "$OLD_COMMIT"
    local CODE_STATUS=$?

    echo "Restoring previous dependencies..."
    "$VENV/bin/pip" install -r "$APP_PATH/requirements.txt"
    local DEPENDENCY_STATUS=$?

    echo "Restoring Stage database backup..."
    cp "$BACKUP" "$DB"
    local DATABASE_STATUS=$?
    chmod 600 "$DB"

    echo "Starting Stage service..."
    sudo systemctl start hemocare-stage
    local SERVICE_STATUS=$?

    sleep 3

    echo "Verifying rollback..."
    sudo systemctl is-active --quiet hemocare-stage
    local ACTIVE_STATUS=$?

    if [[ $CODE_STATUS -eq 0 &&
          $DEPENDENCY_STATUS -eq 0 &&
          $DATABASE_STATUS -eq 0 &&
          $SERVICE_STATUS -eq 0 &&
          $ACTIVE_STATUS -eq 0 ]]; then

        echo "Rollback completed successfully."
    else
        echo "CRITICAL: Rollback encountered errors."
        echo "Manual Stage recovery is required."
    fi

    echo "Previous commit: $OLD_COMMIT"
    echo "Database backup: $BACKUP"

    exit "$DEPLOY_EXIT_CODE"
}

trap rollback ERR

# ==========================================
# Step 4: Fetch and Deploy Stage Code
# ==========================================

echo "Fetching latest Stage code..."

git -C "$APP_DIR" fetch origin stage
git -C "$APP_DIR" reset --hard origin/stage

# ==========================================
# Step 5: Install Dependencies
# ==========================================

echo "Installing Stage dependencies..."

"$VENV/bin/pip" install -r "$APP_PATH/requirements.txt"

# ==========================================
# Step 6: Restart Stage Service
# ==========================================

echo "Restarting Stage service..."

sudo systemctl restart hemocare-stage

sleep 3

# ==========================================
# Step 7: Verify Stage Service
# ==========================================

echo "Checking Stage service..."

sudo systemctl is-active --quiet hemocare-stage

# ==========================================
# Step 8: Application Health Check
# ==========================================

echo "Checking Stage application..."

HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:8001/)

if [[ "$HTTP_CODE" != "302" && "$HTTP_CODE" != "200" ]]; then
    echo "Stage health check failed: HTTP $HTTP_CODE"
    exit 1
fi

# ==========================================
# Step 9: Deployment Successful
# ==========================================

trap - ERR

echo "=========================================="
echo "STAGE DEPLOYMENT SUCCESSFUL"
echo "=========================================="

echo "Previous commit: $OLD_COMMIT"
echo "Deployed commit: $(git -C "$APP_DIR" rev-parse HEAD)"
echo "Database backup: $BACKUP"
echo "Stage URL: https://stage.hemocare.duckdns.org"
