#!/usr/bin/env python3
"""
setup_maxi_plasticos.py
Genera el proyecto Django base de Maxi Plásticos completo.
Ejecutar desde la carpeta donde quieres crear el proyecto:
    python setup_maxi_plasticos.py
"""

import os
import subprocess
import sys

BASE = os.getcwd()

# ─── helpers ──────────────────────────────────────────────────────────────────

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ {path}")


def run(cmd):
    print(f"  🔧 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=BASE)
    if result.returncode != 0:
        print(f"  ❌ Error ejecutando: {cmd}")
        sys.exit(1)


# ─── archivos de configuración ────────────────────────────────────────────────

REQUIREMENTS = """\
Django==4.2.11
gunicorn==21.2.0
whitenoise==6.6.0
"""

SETTINGS_EXTRA = """
# ── Maxi Plásticos extra settings ──────────────────────────────────────────
import os

INSTALLED_APPS += [
    'productos',
    'cotizaciones',
]

TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'django.template.context_processors.request',
]

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True
"""

# ─── modelos ──────────────────────────────────────────────────────────────────

PRODUCTOS_MODELS = '''\
from django.db import models


class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_paquete = models.PositiveIntegerField(
        default=1,
        help_text="Cuántas unidades trae el paquete (ej: 20, 100, 500)"
    )
    categoria = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def precio_por_unidad(self):
        if self.unidad_paquete > 0:
            return round(float(self.precio_base) / self.unidad_paquete, 2)
        return float(self.precio_base)

    def get_precio_para_cantidad(self, cantidad):
        """
        Retorna (precio_unitario, nombre_escala) para una cantidad dada.
        Si no hay escala definida, usa precio_por_unidad como fallback.
        """
        escalas = self.escalas.order_by('-cantidad_minima')
        for escala in escalas:
            if cantidad >= escala.cantidad_minima:
                if escala.cantidad_maxima is None or cantidad <= escala.cantidad_maxima:
                    return float(escala.precio_unitario), escala.nombre_escala
        # fallback
        return self.precio_por_unidad(), "Precio base"

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = [\'categoria\', \'nombre\']
        verbose_name = "Producto"
        verbose_name_plural = "Productos"


class EscalaPrecios(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name=\'escalas\'
    )
    nombre_escala = models.CharField(
        max_length=100,
        help_text="Ej: Unidad, Media docena, Docena, Media caja, Caja"
    )
    cantidad_minima = models.PositiveIntegerField(
        help_text="Cantidad mínima de unidades para este precio"
    )
    cantidad_maxima = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Cantidad máxima (dejar vacío = sin límite superior)"
    )
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Precio por unidad individual en esta escala"
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    def __str__(self):
        return f"{self.producto.nombre} — {self.nombre_escala} ({self.cantidad_minima}+)"

    class Meta:
        ordering = [\'producto\', \'cantidad_minima\']
        verbose_name = "Escala de Precios"
        verbose_name_plural = "Escalas de Precios"
'''

COTIZACIONES_MODELS = '''\
from django.db import models
from productos.models import Producto


class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        (\'borrador\', \'Borrador\'),
        (\'enviada\', \'Enviada al cliente\'),
        (\'aceptada\', \'Aceptada\'),
        (\'cancelada\', \'Cancelada\'),
    ]
    numero = models.CharField(max_length=20, unique=True, editable=False)
    cliente_nombre = models.CharField(max_length=200, blank=True, default=\'Cliente\')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=\'borrador\')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ganancia_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.utils import timezone
            ts = timezone.now().strftime(\'%Y%m%d%H%M%S\')
            self.numero = f"COT-{ts}"
        super().save(*args, **kwargs)

    def calcular_totales(self):
        total = sum(item.subtotal for item in self.items.all())
        ganancia = sum(item.ganancia for item in self.items.all())
        self.total = total
        self.ganancia_total = ganancia
        self.save()

    def __str__(self):
        return f"Cotización {self.numero} — {self.cliente_nombre}"

    class Meta:
        ordering = [\'-created_at\']
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"


class ItemCotizacion(models.Model):
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.CASCADE, related_name=\'items\'
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario_aplicado = models.DecimalField(max_digits=10, decimal_places=2)
    escala_aplicada = models.CharField(max_length=100, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    ganancia = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"

    class Meta:
        verbose_name = "Ítem de Cotización"
        verbose_name_plural = "Ítems de Cotización"
'''

# ─── vistas ───────────────────────────────────────────────────────────────────

PRODUCTOS_VIEWS = '''\
import json
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from .models import Producto, EscalaPrecios
from .forms import ProductoForm, EscalaPreciosFormSet


class ListaProductosView(ListView):
    model = Producto
    template_name = \'productos/lista_productos.html\'
    context_object_name = \'productos\'
    paginate_by = 20

    def get_queryset(self):
        qs = Producto.objects.filter(activo=True)
        q = self.request.GET.get(\'q\', \'\')
        if q:
            qs = qs.filter(nombre__icontains=q)
        cat = self.request.GET.get(\'categoria\', \'\')
        if cat:
            qs = qs.filter(categoria=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx[\'categorias\'] = Producto.objects.values_list(\'categoria\', flat=True).distinct()
        return ctx


class DetalleProductoView(DetailView):
    model = Producto
    template_name = \'productos/detalle_producto.html\'
    context_object_name = \'producto\'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx[\'escalas\'] = self.object.escalas.order_by(\'cantidad_minima\')
        return ctx


class CrearProductoView(CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = \'productos/form_producto.html\'
    success_url = reverse_lazy(\'lista_productos\')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx[\'titulo\'] = \'Agregar Producto\'
        return ctx


class EditarProductoView(UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = \'productos/form_producto.html\'
    success_url = reverse_lazy(\'lista_productos\')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx[\'titulo\'] = \'Editar Producto\'
        return ctx


class EliminarProductoView(DeleteView):
    model = Producto
    template_name = \'productos/confirmar_eliminar.html\'
    success_url = reverse_lazy(\'lista_productos\')


@require_GET
def calcular_precio_ajax(request):
    """
    AJAX: recibe producto_id y cantidad, devuelve precio, escala y ganancia.
    GET /api/calcular-precio/?producto_id=1&cantidad=37
    """
    try:
        producto_id = int(request.GET.get(\'producto_id\', 0))
        cantidad = int(request.GET.get(\'cantidad\', 0))
        if cantidad <= 0:
            return JsonResponse({\'error\': \'Cantidad debe ser mayor a 0\'}, status=400)

        producto = Producto.objects.get(pk=producto_id, activo=True)
        precio_unit, escala = producto.get_precio_para_cantidad(cantidad)
        subtotal = round(precio_unit * cantidad, 2)
        ganancia_unit = precio_unit - float(producto.costo) / producto.unidad_paquete
        ganancia_total = round(ganancia_unit * cantidad, 2)

        return JsonResponse({
            \'producto\': producto.nombre,
            \'cantidad\': cantidad,
            \'precio_unitario\': precio_unit,
            \'escala_aplicada\': escala,
            \'subtotal\': subtotal,
            \'ganancia_total\': ganancia_total,
            \'margen_porcentaje\': round((ganancia_total / subtotal) * 100, 1) if subtotal > 0 else 0,
        })
    except Producto.DoesNotExist:
        return JsonResponse({\'error\': \'Producto no encontrado\'}, status=404)
    except (ValueError, TypeError) as e:
        return JsonResponse({\'error\': str(e)}, status=400)
'''

COTIZACIONES_VIEWS = '''\
from django.views.generic import ListView, DetailView, CreateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views import View
from .models import Cotizacion, ItemCotizacion
from productos.models import Producto
import json


class HistorialCotizacionesView(ListView):
    model = Cotizacion
    template_name = \'cotizaciones/historial.html\'
    context_object_name = \'cotizaciones\'
    paginate_by = 15


class NuevaCotizacionView(View):
    template_name = \'cotizaciones/nueva_cotizacion.html\'

    def get(self, request):
        from django.shortcuts import render
        productos = Producto.objects.filter(activo=True).prefetch_related(\'escalas\')
        return render(request, self.template_name, {\'productos\': productos})

    def post(self, request):
        data = json.loads(request.body)
        cotizacion = Cotizacion.objects.create(
            cliente_nombre=data.get(\'cliente\', \'Cliente\'),
            notas=data.get(\'notas\', \'\'),
        )
        total = 0
        ganancia = 0
        for item_data in data.get(\'items\', []):
            producto = get_object_or_404(Producto, pk=item_data[\'producto_id\'])
            cantidad = int(item_data[\'cantidad\'])
            precio_unit, escala = producto.get_precio_para_cantidad(cantidad)
            subtotal = round(precio_unit * cantidad, 2)
            gan_unit = precio_unit - float(producto.costo) / producto.unidad_paquete
            gan_total = round(gan_unit * cantidad, 2)

            ItemCotizacion.objects.create(
                cotizacion=cotizacion,
                producto=producto,
                cantidad=cantidad,
                precio_unitario_aplicado=precio_unit,
                escala_aplicada=escala,
                subtotal=subtotal,
                ganancia=gan_total,
            )
            total += subtotal
            ganancia += gan_total

        cotizacion.total = total
        cotizacion.ganancia_total = ganancia
        cotizacion.save()
        return JsonResponse({\'cotizacion_id\': cotizacion.pk, \'numero\': cotizacion.numero})


class DetalleCotizacionView(DetailView):
    model = Cotizacion
    template_name = \'cotizaciones/ver_cotizacion.html\'
    context_object_name = \'cotizacion\'


class EliminarCotizacionView(DeleteView):
    model = Cotizacion
    template_name = \'cotizaciones/confirmar_eliminar.html\'
    success_url = reverse_lazy(\'historial_cotizaciones\')
'''

# ─── URLs ─────────────────────────────────────────────────────────────────────

PRODUCTOS_URLS = '''\
from django.urls import path
from . import views

urlpatterns = [
    path(\'\', views.ListaProductosView.as_view(), name=\'lista_productos\'),
    path(\'producto/<int:pk>/\', views.DetalleProductoView.as_view(), name=\'detalle_producto\'),
    path(\'producto/crear/\', views.CrearProductoView.as_view(), name=\'crear_producto\'),
    path(\'producto/<int:pk>/editar/\', views.EditarProductoView.as_view(), name=\'editar_producto\'),
    path(\'producto/<int:pk>/eliminar/\', views.EliminarProductoView.as_view(), name=\'eliminar_producto\'),
    path(\'api/calcular-precio/\', views.calcular_precio_ajax, name=\'calcular_precio\'),
]
'''

COTIZACIONES_URLS = '''\
from django.urls import path
from . import views

urlpatterns = [
    path(\'\', views.HistorialCotizacionesView.as_view(), name=\'historial_cotizaciones\'),
    path(\'nueva/\', views.NuevaCotizacionView.as_view(), name=\'nueva_cotizacion\'),
    path(\'<int:pk>/\', views.DetalleCotizacionView.as_view(), name=\'detalle_cotizacion\'),
    path(\'<int:pk>/eliminar/\', views.EliminarCotizacionView.as_view(), name=\'eliminar_cotizacion\'),
]
'''

# ─── forms ────────────────────────────────────────────────────────────────────

PRODUCTOS_FORMS = '''\
from django import forms
from django.forms import inlineformset_factory
from .models import Producto, EscalaPrecios


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [\'nombre\', \'descripcion\', \'costo\', \'precio_base\', \'unidad_paquete\', \'categoria\', \'activo\']
        widgets = {
            \'nombre\': forms.TextInput(attrs={\'class\': \'form-control\', \'placeholder\': \'Ej: VASO 9 ONZAS CHAMPION\'}),
            \'descripcion\': forms.Textarea(attrs={\'class\': \'form-control\', \'rows\': 2}),
            \'costo\': forms.NumberInput(attrs={\'class\': \'form-control\', \'step\': \'0.01\'}),
            \'precio_base\': forms.NumberInput(attrs={\'class\': \'form-control\', \'step\': \'0.01\'}),
            \'unidad_paquete\': forms.NumberInput(attrs={\'class\': \'form-control\', \'min\': \'1\'}),
            \'categoria\': forms.TextInput(attrs={\'class\': \'form-control\', \'placeholder\': \'Ej: Vasos, Bolsas, Cubiertos\'}),
            \'activo\': forms.CheckboxInput(attrs={\'class\': \'form-check-input\'}),
        }
        labels = {
            \'costo\': \'Costo (COP)\',
            \'precio_base\': \'Precio base por paquete (COP)\',
            \'unidad_paquete\': \'Unidades por paquete\',
        }


EscalaPreciosFormSet = inlineformset_factory(
    Producto, EscalaPrecios,
    fields=[\'nombre_escala\', \'cantidad_minima\', \'cantidad_maxima\', \'precio_unitario\', \'descuento_porcentaje\'],
    extra=3,
    can_delete=True,
)
'''

# ─── admin ────────────────────────────────────────────────────────────────────

PRODUCTOS_ADMIN = '''\
from django.contrib import admin
from .models import Producto, EscalaPrecios


class EscalaPreciosInline(admin.TabularInline):
    model = EscalaPrecios
    extra = 3
    fields = [\'nombre_escala\', \'cantidad_minima\', \'cantidad_maxima\', \'precio_unitario\', \'descuento_porcentaje\']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [\'nombre\', \'categoria\', \'costo\', \'precio_base\', \'unidad_paquete\', \'activo\']
    list_filter = [\'categoria\', \'activo\']
    search_fields = [\'nombre\']
    list_editable = [\'activo\']
    inlines = [EscalaPreciosInline]


@admin.register(EscalaPrecios)
class EscalaPreciosAdmin(admin.ModelAdmin):
    list_display = [\'producto\', \'nombre_escala\', \'cantidad_minima\', \'cantidad_maxima\', \'precio_unitario\']
    list_filter = [\'producto__categoria\']
    search_fields = [\'producto__nombre\', \'nombre_escala\']
'''

COTIZACIONES_ADMIN = '''\
from django.contrib import admin
from .models import Cotizacion, ItemCotizacion


class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 0
    readonly_fields = [\'subtotal\', \'ganancia\', \'escala_aplicada\']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = [\'numero\', \'cliente_nombre\', \'estado\', \'total\', \'ganancia_total\', \'created_at\']
    list_filter = [\'estado\']
    readonly_fields = [\'numero\', \'total\', \'ganancia_total\']
    inlines = [ItemCotizacionInline]
'''

# ─── tests ────────────────────────────────────────────────────────────────────

PRODUCTOS_TESTS = '''\
from django.test import TestCase, Client
from django.urls import reverse
from .models import Producto, EscalaPrecios
import json


class ProductoModelTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre=\'VASO 9 ONZAS CHAMPION\',
            costo=2200.00,
            precio_base=2800.00,
            unidad_paquete=20,
            categoria=\'Vasos\',
        )

    def test_str_producto(self):
        self.assertEqual(str(self.producto), \'VASO 9 ONZAS CHAMPION\')

    def test_precio_por_unidad(self):
        # 2800 / 20 = 140
        self.assertEqual(self.producto.precio_por_unidad(), 140.0)

    def test_precio_sin_escala_usa_fallback(self):
        precio, escala = self.producto.get_precio_para_cantidad(5)
        self.assertEqual(precio, 140.0)
        self.assertEqual(escala, \'Precio base\')


class EscalaPreciosTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre=\'VASO TEST\',
            costo=2200.00,
            precio_base=2800.00,
            unidad_paquete=20,
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala=\'Unidad\',
            cantidad_minima=1,
            cantidad_maxima=11,
            precio_unitario=160.00,
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala=\'Docena\',
            cantidad_minima=12,
            cantidad_maxima=23,
            precio_unitario=140.00,
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala=\'Mayorista\',
            cantidad_minima=24,
            cantidad_maxima=None,
            precio_unitario=120.00,
        )

    def test_escala_unidad(self):
        precio, escala = self.producto.get_precio_para_cantidad(1)
        self.assertEqual(precio, 160.0)
        self.assertEqual(escala, \'Unidad\')

    def test_escala_docena(self):
        precio, escala = self.producto.get_precio_para_cantidad(12)
        self.assertEqual(precio, 140.0)
        self.assertEqual(escala, \'Docena\')

    def test_escala_mayorista_sin_limite(self):
        precio, escala = self.producto.get_precio_para_cantidad(100)
        self.assertEqual(precio, 120.0)
        self.assertEqual(escala, \'Mayorista\')

    def test_cantidad_irregular(self):
        """37 unidades debe aplicar escala Mayorista (>=24)"""
        precio, escala = self.producto.get_precio_para_cantidad(37)
        self.assertEqual(precio, 120.0)


class CalcularPrecioAjaxTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.producto = Producto.objects.create(
            nombre=\'VASO AJAX TEST\',
            costo=2200.00,
            precio_base=2800.00,
            unidad_paquete=20,
            activo=True,
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala=\'Docena\',
            cantidad_minima=12,
            precio_unitario=140.00,
        )

    def test_calcular_precio_valido(self):
        url = reverse(\'calcular_precio\')
        response = self.client.get(url, {\'producto_id\': self.producto.pk, \'cantidad\': 12})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data[\'escala_aplicada\'], \'Docena\')
        self.assertEqual(data[\'subtotal\'], 1680.0)

    def test_producto_inexistente(self):
        url = reverse(\'calcular_precio\')
        response = self.client.get(url, {\'producto_id\': 9999, \'cantidad\': 10})
        self.assertEqual(response.status_code, 404)

    def test_cantidad_invalida(self):
        url = reverse(\'calcular_precio\')
        response = self.client.get(url, {\'producto_id\': self.producto.pk, \'cantidad\': 0})
        self.assertEqual(response.status_code, 400)


class ListaProductosViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        Producto.objects.create(nombre=\'P1\', costo=1000, precio_base=1500, unidad_paquete=1)
        Producto.objects.create(nombre=\'P2\', costo=2000, precio_base=2500, unidad_paquete=1)

    def test_lista_carga_ok(self):
        response = self.client.get(reverse(\'lista_productos\'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, \'P1\')
        self.assertContains(response, \'P2\')
'''

# ─── template base ────────────────────────────────────────────────────────────

BASE_HTML = '''\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Maxi Plásticos{% endblock %}</title>
  <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --maxi-lima:         #D8EE75;
      --maxi-verde-bosque: #1C542D;
      --maxi-verde-marca:  #68C151;
      --maxi-teal:         #73C2B6;
      --maxi-rojo-cta:     #E34A60;
      --maxi-blanco:       #FFFFFF;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: \'Nunito\', sans-serif;
      background: var(--maxi-lima);
      color: var(--maxi-verde-bosque);
      min-height: 100vh;
    }
    /* Navbar */
    nav {
      background: var(--maxi-verde-bosque);
      padding: 0.8rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 8px rgba(28,84,45,0.3);
    }
    .nav-brand {
      color: var(--maxi-lima);
      font-size: 1.4rem;
      font-weight: 800;
      text-decoration: none;
      letter-spacing: 0.5px;
    }
    .nav-brand span { color: var(--maxi-verde-marca); }
    .nav-links { display: flex; gap: 1.5rem; list-style: none; }
    .nav-links a {
      color: var(--maxi-blanco);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.95rem;
      padding: 0.3rem 0.6rem;
      border-radius: 6px;
      transition: background 0.2s;
    }
    .nav-links a:hover { background: var(--maxi-teal); color: var(--maxi-verde-bosque); }
    /* Main container */
    .container {
      max-width: 1200px;
      margin: 2rem auto;
      padding: 0 1.5rem;
    }
    /* Cards */
    .card {
      background: var(--maxi-blanco);
      border-radius: 16px;
      padding: 1.5rem;
      box-shadow: 0 4px 16px rgba(28,84,45,0.1);
      border: 1.5px solid var(--maxi-teal);
    }
    /* Botones */
    .btn {
      display: inline-block;
      padding: 0.55rem 1.3rem;
      border-radius: 10px;
      font-family: \'Nunito\', sans-serif;
      font-weight: 700;
      font-size: 0.95rem;
      border: none;
      cursor: pointer;
      text-decoration: none;
      transition: opacity 0.2s, transform 0.1s;
    }
    .btn:hover { opacity: 0.87; transform: translateY(-1px); }
    .btn-primary   { background: var(--maxi-rojo-cta);     color: var(--maxi-blanco); }
    .btn-secondary { background: var(--maxi-verde-marca);  color: var(--maxi-blanco); }
    .btn-outline   { background: transparent; color: var(--maxi-verde-bosque); border: 2px solid var(--maxi-verde-bosque); }
    /* Badge de escala */
    .badge-escala {
      background: var(--maxi-teal);
      color: var(--maxi-verde-bosque);
      padding: 0.2rem 0.7rem;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 700;
    }
    /* Forms */
    .form-control {
      width: 100%;
      padding: 0.55rem 0.9rem;
      border: 1.5px solid var(--maxi-teal);
      border-radius: 10px;
      font-family: \'Nunito\', sans-serif;
      font-size: 0.95rem;
      background: var(--maxi-blanco);
      color: var(--maxi-verde-bosque);
      outline: none;
    }
    .form-control:focus { border-color: var(--maxi-verde-bosque); box-shadow: 0 0 0 3px rgba(28,84,45,0.1); }
    .form-label { font-weight: 700; margin-bottom: 0.3rem; display: block; }
    .form-group { margin-bottom: 1.1rem; }
    /* Alerts */
    .alert-success { background: #e8f8e8; border-left: 4px solid var(--maxi-verde-marca); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
    .alert-error   { background: #fde8ec; border-left: 4px solid var(--maxi-rojo-cta); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
    /* Footer */
    footer {
      background: var(--maxi-verde-bosque);
      color: var(--maxi-lima);
      text-align: center;
      padding: 1.2rem;
      margin-top: 3rem;
      font-size: 0.9rem;
    }
    /* Tabla */
    table { width: 100%; border-collapse: collapse; }
    th { background: var(--maxi-verde-bosque); color: var(--maxi-lima); padding: 0.75rem 1rem; text-align: left; }
    td { padding: 0.65rem 1rem; border-bottom: 1px solid rgba(115,194,182,0.3); }
    tr:hover td { background: rgba(216,238,117,0.4); }
    h1, h2, h3 { color: var(--maxi-verde-bosque); margin-bottom: 1rem; }
  </style>
  {% block extra_head %}{% endblock %}
</head>
<body>
  <nav>
    <a href="{% url \'lista_productos\' %}" class="nav-brand">MAXI <span>PLÁSTICOS</span></a>
    <ul class="nav-links">
      <li><a href="{% url \'lista_productos\' %}">📦 Productos</a></li>
      <li><a href="{% url \'crear_producto\' %}">➕ Agregar</a></li>
      <li><a href="{% url \'historial_cotizaciones\' %}">🧾 Cotizaciones</a></li>
      <li><a href="{% url \'nueva_cotizacion\' %}">🛒 Nueva Cot.</a></li>
      <li><a href="/admin/">⚙️ Admin</a></li>
    </ul>
  </nav>

  <div class="container">
    {% if messages %}
      {% for message in messages %}
        <div class="alert-{% if message.tags == \'error\' %}error{% else %}success{% endif %}">
          {{ message }}
        </div>
      {% endfor %}
    {% endif %}
    {% block content %}{% endblock %}
  </div>

  <footer>
    <strong>Maxi Plásticos</strong> — Desechables de confianza &nbsp;|&nbsp;
    📞 3227951052 / 3006952453 &nbsp;|&nbsp; Cra 88C #50a 22 sur, Bogotá
  </footer>
  {% block extra_scripts %}{% endblock %}
</body>
</html>
'''

LISTA_PRODUCTOS_HTML = '''\
{% extends "base.html" %}
{% block title %}Productos — Maxi Plásticos{% endblock %}
{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
  <h1>📦 Catálogo de Productos</h1>
  <a href="{% url \'crear_producto\' %}" class="btn btn-primary">+ Agregar producto</a>
</div>

<!-- Filtros -->
<div class="card" style="margin-bottom:1.5rem; padding:1rem;">
  <form method="get" style="display:flex; gap:1rem; flex-wrap:wrap; align-items:flex-end;">
    <div class="form-group" style="margin:0; flex:1; min-width:200px;">
      <input type="text" name="q" value="{{ request.GET.q }}" class="form-control" placeholder="🔍 Buscar producto...">
    </div>
    <div class="form-group" style="margin:0;">
      <select name="categoria" class="form-control">
        <option value="">Todas las categorías</option>
        {% for cat in categorias %}
          <option value="{{ cat }}" {% if request.GET.categoria == cat %}selected{% endif %}>{{ cat }}</option>
        {% endfor %}
      </select>
    </div>
    <button type="submit" class="btn btn-secondary">Filtrar</button>
    <a href="{% url \'lista_productos\' %}" class="btn btn-outline">Limpiar</a>
  </form>
</div>

<div class="card">
  {% if productos %}
    <table>
      <thead>
        <tr>
          <th>Producto</th>
          <th>Categoría</th>
          <th>Precio paquete</th>
          <th>Und/paquete</th>
          <th>Precio/unidad</th>
          <th>Escalas</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {% for p in productos %}
        <tr>
          <td><strong>{{ p.nombre }}</strong></td>
          <td>{{ p.categoria|default:"-" }}</td>
          <td>${{ p.precio_base|floatformat:0 }}</td>
          <td style="text-align:center;">{{ p.unidad_paquete }}</td>
          <td>${{ p.precio_por_unidad|floatformat:0 }}</td>
          <td>
            {% with escalas_count=p.escalas.count %}
              {% if escalas_count > 0 %}
                <span class="badge-escala">{{ escalas_count }} escala{{ escalas_count|pluralize:"s" }}</span>
              {% else %}
                <span style="color:#aaa; font-size:0.85rem;">Sin escalas</span>
              {% endif %}
            {% endwith %}
          </td>
          <td style="display:flex; gap:0.5rem;">
            <a href="{% url \'detalle_producto\' p.pk %}" class="btn btn-secondary" style="padding:0.3rem 0.7rem; font-size:0.85rem;">Ver</a>
            <a href="{% url \'editar_producto\' p.pk %}" class="btn btn-outline" style="padding:0.3rem 0.7rem; font-size:0.85rem;">Editar</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <!-- Paginación -->
    {% if is_paginated %}
    <div style="margin-top:1rem; display:flex; gap:0.5rem;">
      {% if page_obj.has_previous %}
        <a href="?page={{ page_obj.previous_page_number }}" class="btn btn-outline">← Anterior</a>
      {% endif %}
      <span style="padding:0.5rem; font-weight:700;">Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}</span>
      {% if page_obj.has_next %}
        <a href="?page={{ page_obj.next_page_number }}" class="btn btn-outline">Siguiente →</a>
      {% endif %}
    </div>
    {% endif %}
  {% else %}
    <p style="text-align:center; color:#888; padding:2rem;">No hay productos. <a href="{% url \'crear_producto\' %}">Agrega el primero</a>.</p>
  {% endif %}
</div>
{% endblock %}
'''

DETALLE_PRODUCTO_HTML = '''\
{% extends "base.html" %}
{% block title %}{{ producto.nombre }} — Maxi Plásticos{% endblock %}
{% block content %}
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
  <div>
    <a href="{% url \'lista_productos\' %}" style="color:var(--maxi-verde-bosque); font-weight:600;">← Volver</a>
    <h1 style="margin-top:0.3rem;">{{ producto.nombre }}</h1>
    {% if producto.categoria %}<span class="badge-escala">{{ producto.categoria }}</span>{% endif %}
  </div>
  <div style="display:flex; gap:0.7rem;">
    <a href="{% url \'editar_producto\' producto.pk %}" class="btn btn-secondary">Editar</a>
    <a href="{% url \'eliminar_producto\' producto.pk %}" class="btn btn-outline" style="color:var(--maxi-rojo-cta); border-color:var(--maxi-rojo-cta);">Eliminar</a>
  </div>
</div>

<div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem;">
  <!-- Info del producto -->
  <div class="card">
    <h2>💰 Información de Precios</h2>
    <table>
      <tr><td><strong>Costo</strong></td><td>${{ producto.costo|floatformat:0 }}</td></tr>
      <tr><td><strong>Precio paquete</strong></td><td>${{ producto.precio_base|floatformat:0 }}</td></tr>
      <tr><td><strong>Unidades/paquete</strong></td><td>{{ producto.unidad_paquete }}</td></tr>
      <tr><td><strong>Precio/unidad base</strong></td><td>${{ producto.precio_por_unidad|floatformat:2 }}</td></tr>
    </table>
  </div>

  <!-- Calculadora -->
  <div class="card">
    <h2>🧮 Calculadora de Precio</h2>
    <p style="font-size:0.9rem; margin-bottom:1rem; color:#555;">Ingresa la cantidad que pide el cliente</p>
    <div class="form-group">
      <label class="form-label">Cantidad de unidades</label>
      <input type="number" id="calc-cantidad" class="form-control" min="1" value="1" placeholder="Ej: 37">
    </div>
    <button onclick="calcularPrecio()" class="btn btn-primary" style="width:100%;">Calcular precio</button>
    <div id="calc-resultado" style="margin-top:1rem; display:none;">
      <div style="background:var(--maxi-lima); border-radius:10px; padding:1rem;">
        <p style="font-size:0.85rem; margin-bottom:0.3rem;">Escala aplicada: <span id="calc-escala" class="badge-escala"></span></p>
        <p style="font-size:1.1rem;"><strong>Precio/unid:</strong> $<span id="calc-precio-unit"></span></p>
        <p style="font-size:1.4rem; font-weight:800; color:var(--maxi-rojo-cta);"><strong>Total: $<span id="calc-total"></span></strong></p>
        <p style="font-size:0.85rem; color:#2e7d32;">Ganancia estimada: $<span id="calc-ganancia"></span> (<span id="calc-margen"></span>%)</p>
      </div>
    </div>
  </div>
</div>

<!-- Escalas de precio -->
{% if escalas %}
<div class="card" style="margin-top:1.5rem;">
  <h2>📊 Escalas de Precio Configuradas</h2>
  <table>
    <thead>
      <tr>
        <th>Escala</th>
        <th>Desde</th>
        <th>Hasta</th>
        <th>Precio/unidad</th>
        <th>Descuento</th>
      </tr>
    </thead>
    <tbody>
      {% for escala in escalas %}
      <tr>
        <td><strong>{{ escala.nombre_escala }}</strong></td>
        <td>{{ escala.cantidad_minima }} unid.</td>
        <td>{{ escala.cantidad_maxima|default:"Sin límite" }} {% if escala.cantidad_maxima %}unid.{% endif %}</td>
        <td>${{ escala.precio_unitario|floatformat:2 }}</td>
        <td>{{ escala.descuento_porcentaje }}%</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% else %}
<div class="card" style="margin-top:1.5rem; text-align:center;">
  <p>Este producto no tiene escalas de precio configuradas. Se usa el precio base por unidad.</p>
  <a href="{% url \'editar_producto\' producto.pk %}" class="btn btn-secondary" style="margin-top:1rem;">Configurar escalas</a>
</div>
{% endif %}
{% endblock %}

{% block extra_scripts %}
<script>
async function calcularPrecio() {
  const cantidad = document.getElementById(\'calc-cantidad\').value;
  if (!cantidad || cantidad < 1) return alert(\'Ingresa una cantidad válida\');
  try {
    const resp = await fetch(`/api/calcular-precio/?producto_id={{ producto.pk }}&cantidad=${cantidad}`);
    const data = await resp.json();
    if (resp.ok) {
      document.getElementById(\'calc-escala\').textContent = data.escala_aplicada;
      document.getElementById(\'calc-precio-unit\').textContent = data.precio_unitario.toLocaleString(\'es-CO\');
      document.getElementById(\'calc-total\').textContent = data.subtotal.toLocaleString(\'es-CO\');
      document.getElementById(\'calc-ganancia\').textContent = data.ganancia_total.toLocaleString(\'es-CO\');
      document.getElementById(\'calc-margen\').textContent = data.margen_porcentaje;
      document.getElementById(\'calc-resultado\').style.display = \'block\';
    } else {
      alert(data.error || \'Error calculando precio\');
    }
  } catch(e) {
    alert(\'Error de conexión\');
  }
}
document.getElementById(\'calc-cantidad\').addEventListener(\'keypress\', function(e) {
  if (e.key === \'Enter\') calcularPrecio();
});
</script>
{% endblock %}
'''

ROOT_URLS = '''\
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path(\'admin/\', admin.site.urls),
    path(\'\', include(\'productos.urls\')),
    path(\'cotizaciones/\', include(\'cotizaciones.urls\')),
]
'''

# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    print("\\n🌿 Maxi Plásticos — Generador de proyecto Django")
    print("=" * 50)

    # 1. requirements
    write("requirements.txt", REQUIREMENTS)

    # 2. Crear proyecto Django si no existe
    if not os.path.exists("manage.py"):
        run("pip install django==4.2.11 gunicorn whitenoise --quiet")
        run("django-admin startproject maxiplasticos .")
    else:
        print("  ⚠️  manage.py ya existe — saltando creación del proyecto")

    # 3. Apps
    for app in ("productos", "cotizaciones"):
        if not os.path.exists(app):
            run(f"python manage.py startapp {app}")
        else:
            print(f"  ⚠️  App '{app}' ya existe — actualizando archivos")

    # 4. Patch settings.py
    settings_path = "maxiplasticos/settings.py"
    with open(settings_path, "r") as f:
        settings_content = f.read()
    if "maxi-plasticos-context" not in settings_content and "'productos'" not in settings_content:
        with open(settings_path, "a") as f:
            f.write("\\n# maxi-plasticos-context\\n")
            f.write(SETTINGS_EXTRA)
        print(f"  ✅ {settings_path} (settings parcheado)")
    else:
        print(f"  ⚠️  {settings_path} ya tiene las apps registradas")

    # 5. URLs raíz
    write("maxiplasticos/urls.py", ROOT_URLS)

    # 6. Archivos de apps
    write("productos/models.py", PRODUCTOS_MODELS)
    write("productos/views.py", PRODUCTOS_VIEWS)
    write("productos/urls.py", PRODUCTOS_URLS)
    write("productos/forms.py", PRODUCTOS_FORMS)
    write("productos/admin.py", PRODUCTOS_ADMIN)
    write("productos/tests.py", PRODUCTOS_TESTS)

    write("cotizaciones/models.py", COTIZACIONES_MODELS)
    write("cotizaciones/views.py", COTIZACIONES_VIEWS)
    write("cotizaciones/urls.py", COTIZACIONES_URLS)
    write("cotizaciones/admin.py", COTIZACIONES_ADMIN)

    # 7. Templates
    write("templates/base.html", BASE_HTML)
    write("templates/productos/lista_productos.html", LISTA_PRODUCTOS_HTML)
    write("templates/productos/detalle_producto.html", DETALLE_PRODUCTO_HTML)

    # Placeholder para templates faltantes
    for tpl, titulo in [
        ("templates/productos/form_producto.html", "Formulario Producto"),
        ("templates/productos/confirmar_eliminar.html", "Confirmar eliminación"),
        ("templates/cotizaciones/historial.html", "Historial de Cotizaciones"),
        ("templates/cotizaciones/nueva_cotizacion.html", "Nueva Cotización"),
        ("templates/cotizaciones/ver_cotizacion.html", "Ver Cotización"),
        ("templates/cotizaciones/confirmar_eliminar.html", "Confirmar eliminación"),
    ]:
        if not os.path.exists(tpl):
            write(tpl, '{{% extends "base.html" %}}\n{{% block content %}}<h1>{titulo}</h1><p>Template pendiente de implementar.</p>{{% endblock %}}'.format(titulo=titulo))

    # 8. Directorio static
    os.makedirs("static", exist_ok=True)
    print("  ✅ static/ (creado)")

    # 9. Migraciones
    run("python manage.py makemigrations")
    run("python manage.py migrate")

    print("\\n" + "=" * 50)
    print("✅ Proyecto generado exitosamente.")
    print("\\n📋 Próximos pasos:")
    print("  1. python manage.py createsuperuser")
    print("  2. python manage.py runserver")
    print("  3. Abre http://127.0.0.1:8000/")
    print("  4. Panel admin: http://127.0.0.1:8000/admin/")
    print("\\n🧪 Para correr los tests:")
    print("  python manage.py test")
    print("=" * 50)


if __name__ == "__main__":
    main()
