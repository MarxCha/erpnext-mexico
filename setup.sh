#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ERPNext Mexico — Development Environment Setup
# ═══════════════════════════════════════════════════════════
set -euo pipefail

# Load env
source .env 2>/dev/null || true
SITE_NAME="${SITE_NAME:-erpnext-mexico.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-frappe_root_2024}"
CONTAINER="erpnext-mx-frappe"

echo "╔══════════════════════════════════════════════╗"
echo "║  ERPNext Mexico — Setup Development Env      ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Step 1: Build & Start Services ──────────────────────
echo "[1/6] Building Docker image (this takes 5-10 min first time)..."
docker compose build --no-cache

echo "[2/6] Starting services..."
docker compose up -d mariadb redis-cache redis-queue
echo "  Waiting for MariaDB to be healthy..."
sleep 10

# Start frappe container but override command to keep it alive without bench start
docker compose run -d --name ${CONTAINER}-setup \
    --service-ports \
    -e SHELL=/bin/bash \
    frappe bash -c "tail -f /dev/null"

SETUP_CONTAINER="${CONTAINER}-setup"

echo "[3/6] Creating site: ${SITE_NAME}..."
docker exec ${SETUP_CONTAINER} bash -c "
    cd /home/frappe/frappe-bench &&
    bench new-site ${SITE_NAME} \
        --mariadb-root-password ${DB_ROOT_PASSWORD} \
        --admin-password ${ADMIN_PASSWORD} \
        --install-app erpnext \
        --set-default
"

echo "[4/6] Installing erpnext_mexico app..."
docker exec ${SETUP_CONTAINER} bash -c "
    cd /home/frappe/frappe-bench &&
    bench get-app /home/frappe/frappe-bench/apps/erpnext_mexico &&
    bench --site ${SITE_NAME} install-app erpnext_mexico
"

echo "[5/6] Running migrations..."
docker exec ${SETUP_CONTAINER} bash -c "
    cd /home/frappe/frappe-bench &&
    bench --site ${SITE_NAME} migrate
"

echo "[6/6] Cleaning up setup container and starting services..."
docker stop ${SETUP_CONTAINER} && docker rm ${SETUP_CONTAINER}
docker compose up -d

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Setup Complete!                              ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  URL:      http://localhost:8080              ║"
echo "║  Site:     ${SITE_NAME}                       ║"
echo "║  User:     Administrator                      ║"
echo "║  Password: ${ADMIN_PASSWORD}                  ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Add to /etc/hosts:                           ║"
echo "║  127.0.0.1  ${SITE_NAME}                     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Commands:"
echo "  docker compose up -d          # Start all services"
echo "  docker compose logs -f frappe # View logs"
echo "  docker compose down           # Stop all"
echo "  docker exec -it ${CONTAINER} bash  # Shell into container"
echo "  # Inside container:"
echo "  bench --site ${SITE_NAME} console    # Python console"
echo "  bench --site ${SITE_NAME} run-tests --app erpnext_mexico  # Run tests"
