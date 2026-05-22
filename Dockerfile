FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Estáticos y migraciones en tiempo de BUILD (quedan en la imagen)
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

EXPOSE 8000

# Startup: migrate (por si acaso), crear admin, arrancar gunicorn
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && python manage.py create_admin && gunicorn mysite.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --log-file -"]
