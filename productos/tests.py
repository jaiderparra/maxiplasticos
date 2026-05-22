from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from .models import Producto, EscalaPrecios


class ProductoModelTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre='Vasos 7oz',
            costo=Decimal('8000'),
            precio_base=Decimal('12000'),
            unidad_paquete=100,
            categoria='Vasos',
        )

    def test_creacion_producto(self):
        self.assertEqual(self.producto.nombre, 'Vasos 7oz')
        self.assertTrue(self.producto.activo)

    def test_precio_por_unidad(self):
        self.assertEqual(self.producto.precio_por_unidad(), Decimal('120'))

    def test_precio_por_unidad_sin_paquete(self):
        p = Producto(precio_base=Decimal('5000'), unidad_paquete=0, costo=Decimal('3000'))
        self.assertEqual(p.precio_por_unidad(), Decimal('5000'))

    def test_str_representation(self):
        self.assertEqual(str(self.producto), 'Vasos 7oz')


class EscalaPreciosTest(TestCase):

    def setUp(self):
        self.producto = Producto.objects.create(
            nombre='Platos desechables',
            costo=Decimal('5000'),
            precio_base=Decimal('8000'),
            unidad_paquete=25,
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala='Unidad',
            cantidad_minima=1,
            cantidad_maxima=11,
            precio_unitario=Decimal('400'),
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala='Docena',
            cantidad_minima=12,
            cantidad_maxima=23,
            precio_unitario=Decimal('350'),
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala='Mayorista',
            cantidad_minima=24,
            cantidad_maxima=None,
            precio_unitario=Decimal('300'),
        )

    def test_escala_unidad(self):
        escala = self.producto.get_escala_para_cantidad(5)
        self.assertIsNotNone(escala)
        self.assertEqual(escala.nombre_escala, 'Unidad')

    def test_escala_docena(self):
        escala = self.producto.get_escala_para_cantidad(12)
        self.assertEqual(escala.nombre_escala, 'Docena')

    def test_escala_mayorista_sin_limite(self):
        escala = self.producto.get_escala_para_cantidad(100)
        self.assertEqual(escala.nombre_escala, 'Mayorista')

    def test_sin_escala_retorna_none(self):
        producto_sin_escalas = Producto.objects.create(
            nombre='Sin escalas', costo=Decimal('1000'), precio_base=Decimal('2000'), unidad_paquete=1
        )
        self.assertIsNone(producto_sin_escalas.get_escala_para_cantidad(5))

    def test_str_escala(self):
        escala = EscalaPrecios.objects.filter(producto=self.producto, nombre_escala='Docena').first()
        self.assertIn('Docena', str(escala))


class CalcularPrecioViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.producto = Producto.objects.create(
            nombre='Vasos',
            costo=Decimal('8000'),
            precio_base=Decimal('12000'),
            unidad_paquete=100,
        )
        EscalaPrecios.objects.create(
            producto=self.producto,
            nombre_escala='Docena',
            cantidad_minima=12,
            cantidad_maxima=None,
            precio_unitario=Decimal('100'),
        )
        self.url = reverse('calcular_precio')

    def test_con_escala(self):
        resp = self.client.get(self.url, {'producto_id': self.producto.pk, 'cantidad': 12})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['escala'], 'Docena')
        self.assertAlmostEqual(data['precio_unitario'], 100.0)

    def test_fallback_precio_base(self):
        resp = self.client.get(self.url, {'producto_id': self.producto.pk, 'cantidad': 1})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['escala'], 'Precio base')

    def test_producto_inexistente(self):
        resp = self.client.get(self.url, {'producto_id': 9999, 'cantidad': 1})
        self.assertEqual(resp.status_code, 404)

    def test_cantidad_invalida(self):
        resp = self.client.get(self.url, {'producto_id': self.producto.pk, 'cantidad': 'abc'})
        self.assertEqual(resp.status_code, 400)
