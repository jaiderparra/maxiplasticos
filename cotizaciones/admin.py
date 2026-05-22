from django.contrib import admin
from .models import Cotizacion, ItemCotizacion


class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 0
    readonly_fields = ['subtotal', 'ganancia', 'escala_aplicada']
    fields = ['producto', 'cantidad', 'precio_unitario_aplicado', 'escala_aplicada', 'subtotal', 'ganancia']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente_nombre', 'estado', 'total', 'ganancia_total', 'created_at']
    list_filter = ['estado']
    search_fields = ['numero', 'cliente_nombre']
    readonly_fields = ['numero', 'total', 'ganancia_total', 'created_at']
    inlines = [ItemCotizacionInline]


@admin.register(ItemCotizacion)
class ItemCotizacionAdmin(admin.ModelAdmin):
    list_display = ['cotizacion', 'producto', 'cantidad', 'precio_unitario_aplicado', 'subtotal']
