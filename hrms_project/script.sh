#!/usr/bin/env bash
set -euo pipefail

# script.sh - simple helper to prepare and run the Django development server
# Usage:
#   ./script.sh                 # uses python3, starts runserver 0.0.0.0:8000
#   ADMIN_USERNAME=admin ./script.sh   # ensure superuser 'admin' exists (password printed)
#   PYTHON=/path/to/python ./script.sh
# Environment variables:
#   PYTHON - python executable to use (default: python3)
#   ADDRESS - bind address (default: 0.0.0.0)
#   PORT - port to run on (default: 8000)
#   ADMIN_USERNAME - if set, script will create that superuser if it doesn't exist
#   ADMIN_EMAIL - email to use when creating the superuser (default: admin@example.com)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Activate virtualenv if it exists
if [ -d ".venv" ]; then
  echo "Activating virtualenv..."
  source .venv/bin/activate
fi

PYTHON=${PYTHON:-python3}
ADDRESS=${ADDRESS:-0.0.0.0}
PORT=${PORT:-8000}
ADMIN_USERNAME=${ADMIN_USERNAME:-}
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}

echo "Using Python: $PYTHON"

# Run migrations
echo "[1/4] Applying database migrations..."
"$PYTHON" manage.py migrate --noinput

# Collect static files
echo "[2/4] Collecting static files..."
"$PYTHON" manage.py collectstatic --noinput

# Optionally create a superuser non-interactively when ADMIN_USERNAME provided
if [ -n "$ADMIN_USERNAME" ]; then
  echo "[3/4] Ensuring superuser '$ADMIN_USERNAME' exists (will print password if created)..."
  "$PYTHON" manage.py shell -c "from django.contrib.auth import get_user_model; import secrets; User=get_user_model(); u='$ADMIN_USERNAME'; e='$ADMIN_EMAIL'; pw=secrets.token_urlsafe(12);\
if not User.objects.filter(username=u).exists(): User.objects.create_superuser(u,e,pw); print('CREATED_SUPERUSER',u,e,pw);\
else: print('SUPERUSER_EXISTS', u)"
else
  echo "[3/4] Skipping superuser creation (set ADMIN_USERNAME to create one)"
fi

# Start development server
echo "[4/4] Starting Django development server on $ADDRESS:$PORT (Ctrl-C to stop)"
exec "$PYTHON" manage.py runserver "$ADDRESS:$PORT"
