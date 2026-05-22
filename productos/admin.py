from django.contrib import admin
from .models import Producto, EscalaPrecios


class EscalaPreciosInline(admin.TabularInline):
    model = EscalaPrecios
    extra = 1
    fields = ['nombre_escala', 'cantidad_minima', 'cantidad_maxima', 'precio_unitario', 'descuento_porcentaje']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'categoria', 'costo', 'precio_base', 'impuesto', 'unidad_paquete', 'activo']
    list_filter = ['categoria', 'activo']
    search_fields = ['codigo', 'nombre', 'descripcion']
    inlines = [EscalaPreciosInline]
    list_editable = ['activo']


@admin.register(EscalaPrecios)
class EscalaPreciosAdmin(admin.ModelAdmin):
    list_display = ['producto', 'nombre_escala', 'cantidad_minima', 'cantidad_maxima', 'precio_unitario']
    list_filter = ['producto']
