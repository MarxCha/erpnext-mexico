#!/bin/bash
# ERPNext Mexico — Container Entrypoint
set -e

cd /home/frappe/frappe-bench

# Ensure erpnext_mexico is in apps.txt
if ! grep -q "erpnext_mexico" sites/apps.txt 2>/dev/null; then
    echo "erpnext_mexico" >> sites/apps.txt
fi

# Install erpnext_mexico in development mode if mounted
if [ -d "apps/erpnext_mexico" ] && [ -f "apps/erpnext_mexico/pyproject.toml" ]; then
    echo "[entrypoint] Installing erpnext_mexico in dev mode..."
    ./env/bin/pip install -e apps/erpnext_mexico --quiet 2>&1
fi

echo "[entrypoint] Starting bench..."
exec bench start
