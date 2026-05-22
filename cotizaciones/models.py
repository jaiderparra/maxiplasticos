from django.db import models
from productos.models import Producto


class Cotizacion(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada al cliente'),
        ('aceptada', 'Aceptada'),
        ('cancelada', 'Cancelada'),
    ]
    numero = models.CharField(max_length=20, unique=True, editable=False)
    cliente_nombre = models.CharField(max_length=200, blank=True, default='Cliente')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ganancia_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.utils import timezone
            ts = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero = f"COT-{ts}"
        super().save(*args, **kwargs)

    def recalcular_totales(self):
        totales = self.items.aggregate(
            total=models.Sum('subtotal'),
            ganancia=models.Sum('ganancia')
        )
        self.total = totales['total'] or 0
        self.ganancia_total = totales['ganancia'] or 0
        self.save()

    def __str__(self):
        return f"Cotización {self.numero} — {self.cliente_nombre}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"


class ItemCotizacion(models.Model):
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.CASCADE, related_name='items'
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
        verbose_name = "Item de Cotización"
        verbose_name_plural = "Items de Cotización"
