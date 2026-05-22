from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from productos.models import Producto, EscalaPrecios
from .models import Cotizacion, ItemCotizacion


class CotizacionModelTest(TestCase):

    def test_generacion_automatica_numero(self):
        cot = Cotizacion.objects.create(cliente_nombre='Juan')
        self.assertTrue(cot.numero.startswith('COT-'))
        self.assertEqual(len(cot.numero), 18)  # COT- + 14 dígitos

    def test_numero_unico(self):
        c1 = Cotizacion.objects.create(cliente_nombre='A')
        import time; time.sleep(1)
        c2 = Cotizacion.objects.create(cliente_nombre='B')
        self.assertNotEqual(c1.numero, c2.numero)

    def test_str_representation(self):
        cot = Cotizacion.objects.create(cliente_nombre='Pedro')
        self.assertIn('Pedro', str(cot))

    def test_recalcular_totales(self):
        producto = Producto.objects.create(
            nombre='Test', costo=Decimal('1000'), precio_base=Decimal('2000'), unidad_paquete=1
        )
        cot = Cotizacion.objects.create(cliente_nombre='Test')
        ItemCotizacion.objects.create(
            cotizacion=cot,
            producto=producto,
            cantidad=3,
            precio_unitario_aplicado=Decimal('2000'),
            subtotal=Decimal('6000'),
            ganancia=Decimal('3000'),
        )
        cot.recalcular_totales()
        self.assertEqual(cot.total, Decimal('6000'))
        self.assertEqual(cot.ganancia_total, Decimal('3000'))

    def test_estado_default_borrador(self):
        cot = Cotizacion.objects.create(cliente_nombre='Test')
        self.assertEqual(cot.estado, 'borrador')


class ItemCotizacionTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre='Vasos',
            costo=Decimal('8000'),
            precio_base=Decimal('12000'),
            unidad_paquete=100,
        )
        self.cotizacion = Cotizacion.objects.create(cliente_nombre='Cliente test')

    def test_str_item(self):
        item = ItemCotizacion.objects.create(
            cotizacion=self.cotizacion,
            producto=self.producto,
            cantidad=5,
            precio_unitario_aplicado=Decimal('150'),
            subtotal=Decimal('750'),
        )
        self.assertIn('5x', str(item))
        self.assertIn('Vasos', str(item))
