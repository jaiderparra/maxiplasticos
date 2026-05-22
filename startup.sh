#!/bin/sh
set -e

echo "=== Migraciones ==="
python manage.py migrate

echo "=== Creando/actualizando admin ==="
echo "ADMIN_USERNAME=${ADMIN_USERNAME:-admin}"
echo "ADMIN_PASSWORD configurada: $([ -n "$ADMIN_PASSWORD" ] && echo SI || echo NO)"
python manage.py create_admin

echo "=== Iniciando gunicorn en puerto ${PORT:-8000} ==="
exec gunicorn mysite.wsgi \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --log-file -
