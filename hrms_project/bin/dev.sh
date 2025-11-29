#!/usr/bin/env bash
# Simple development helper: apply migrations then run the Django dev server
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Applying migrations..."
python3 manage.py migrate

echo "Running development server on 127.0.0.1:8000"
python3 manage.py runserver 127.0.0.1:8000
