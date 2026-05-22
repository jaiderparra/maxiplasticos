from django.db import models


class Producto(models.Model):
    codigo = models.CharField(max_length=50, blank=True, help_text="Código o referencia del producto")
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="% de impuesto (IVA)")
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
            return self.precio_base / self.unidad_paquete
        return self.precio_base

    def get_escala_para_cantidad(self, cantidad):
        """Retorna la EscalaPrecios que aplica para la cantidad dada, o None."""
        escala = (
            self.escalas
            .filter(cantidad_minima__lte=cantidad)
            .filter(models.Q(cantidad_maxima__gte=cantidad) | models.Q(cantidad_maxima__isnull=True))
            .order_by('-cantidad_minima')
            .first()
        )
        return escala

    def __str__(self):
        return self.nombre

    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = "Producto"
        verbose_name_plural = "Productos"


class EscalaPrecios(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='escalas'
    )
    nombre_escala = models.CharField(
        max_length=100,
        help_text="Ej: Unidad, Media docena, Docena, Media caja, Caja"
    )
    cantidad_minima = models.PositiveIntegerField(
        help_text="Cantidad mínima para aplicar este precio"
    )
    cantidad_maxima = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Cantidad máxima (dejar vacío si no hay límite)"
    )
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Precio por unidad individual en esta escala"
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="% de descuento sobre precio base por unidad"
    )

    def __str__(self):
        return f"{self.producto.nombre} — {self.nombre_escala} ({self.cantidad_minima}+)"

    class Meta:
        ordering = ['producto', 'cantidad_minima']
        verbose_name = "Escala de Precios"
        verbose_name_plural = "Escalas de Precios"
