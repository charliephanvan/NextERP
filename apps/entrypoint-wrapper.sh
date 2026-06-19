#!/bin/bash
# Wrapper entrypoint: cài custom apps vào virtualenv trước khi start service
set -e

APP_PATH="/home/frappe/frappe-bench/apps/item_master"
PYTHON="/home/frappe/frappe-bench/env/bin/python"
UV="/home/frappe/frappe-bench/env/bin/uv"

if [ -d "$APP_PATH" ]; then
    if $PYTHON -c "import item_master" 2>/dev/null; then
        echo "[wrapper] item_master already installed, skipping."
    else
        echo "[wrapper] Installing item_master into virtualenv..."
        if [ -f "$UV" ]; then
            $UV pip install -q -e "$APP_PATH" --python "$PYTHON"
        else
            $PYTHON -m pip install -q -e "$APP_PATH"
        fi
        echo "[wrapper] item_master installed."
    fi
fi

exec "$@"
