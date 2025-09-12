#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
django.setup()
from django.db import connection
import time
while True:
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        print('Database is ready!')
        break
    except Exception as e:
        print('Database is unavailable - sleeping')
        time.sleep(1)
"

# Run Django commands
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Running migrations..."
python manage.py migrate

echo "Starting Django server..."
# Execute the main command
exec "$@"