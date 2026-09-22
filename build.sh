#!/usr/bin/env bash
# Build step for Render / Railway / any container platform.
# Exit on the first error so a bad deploy never reaches "live".
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Load the demo catalogue on first deploy only.
# Set SEED_DEMO_DATA=True in the dashboard to switch this on, then remove it.
if [ "$SEED_DEMO_DATA" = "True" ]; then
  python manage.py seed_data
fi
