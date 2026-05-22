FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Colectar estáticos en tiempo de BUILD (quedan dentro de la imagen)
RUN python manage.py collectstatic --noinput

# Crear y migrar la BD SQLite en tiempo de BUILD
RUN python manage.py migrate

# Puerto que Railway asigna dinámicamente
EXPOSE 8000

# Arranque: crear admin (si no existe) y servir con gunicorn
CMD python manage.py create_admin && \
    gunicorn mysite.wsgi \
      --bind 0.0.0.0:${PORT:-8000} \
      --workers 2 \
      --log-file -
