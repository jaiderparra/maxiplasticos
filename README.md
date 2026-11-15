# 🏭 Maxi Plásticos · Cotizador de precios escalados

Sistema web para **Maxi Plásticos (Bogotá)** que reemplaza las cotizaciones hechas a mano: el vendedor elige productos y cantidades, y el sistema aplica automáticamente el **precio de la escala que corresponde** (unidad, docena, caja…), calcula impuestos y muestra la **ganancia** de cada cotización.

## ✨ Funcionalidades

- **Catálogo de productos** con código, costo, precio base, IVA, unidades por paquete y categoría.
- **Escalas de precio por producto**: rangos de cantidad mínima/máxima con precio unitario o % de descuento propio.
- **Cálculo de precio en vivo** (endpoint AJAX) mientras se arma la cotización.
- **Cotizaciones** con consecutivo `COT-AAAAMMDDhhmmss`, estados (borrador → enviada → aceptada / cancelada), total y ganancia recalculados automáticamente, e historial.
- **Importación masiva desde Excel** (`openpyxl`) que detecta las columnas por alias (`código`/`ref`/`sku`, `costo`, `precio`, `iva`…), para cargar el inventario real de la empresa sin reformatear el archivo.
- Panel de administración de Django y creación del admin por variables de entorno.

## 🛠️ Stack

`Python 3.12` · `Django 6` · `openpyxl` · `Gunicorn` · `WhiteNoise` · `Docker`

## 🧱 Estructura

```
mysite/         configuración (settings por variables de entorno)
productos/      catálogo, escalas de precio, importación Excel, cálculo de precio
cotizaciones/   cotizaciones, ítems e historial
startup.sh      migraciones + admin + gunicorn
```

## 🚀 Cómo correrlo

**Local**

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Docker**

```bash
docker build -t maxiplasticos .
docker run -p 8000:8000 -e SECRET_KEY=cambia-esto -e ADMIN_PASSWORD=cambia-esto maxiplasticos
```

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave de Django (obligatoria en producción) |
| `DEBUG` | `True` solo en desarrollo |
| `ALLOWED_HOSTS` | Dominios permitidos (también arma `CSRF_TRUSTED_ORIGINS`) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Usuario administrador que se crea al arrancar |
| `PORT` | Puerto de gunicorn (por defecto 8000) |

---
Desarrollado por [Jaider Parra](https://github.com/jaiderparra).
