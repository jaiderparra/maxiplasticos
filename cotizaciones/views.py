import json
from decimal import Decimal
from django.views.generic import ListView, DetailView, DeleteView
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse
from .models import Cotizacion, ItemCotizacion
from .forms import CotizacionForm
from productos.models import Producto


def _cot_to_dict(cotizacion):
    return {
        'pk': cotizacion.pk,
        'numero': cotizacion.numero,
        'cliente': cotizacion.cliente_nombre,
        'total': float(cotizacion.total),
        'ganancia_total': float(cotizacion.ganancia_total),
        'items': [
            {
                'pk': i.pk,
                'producto_id': i.producto_id,
                'producto_nombre': i.producto.nombre,
                'cantidad': i.cantidad,
                'precio_unitario': float(i.precio_unitario_aplicado),
                'escala': i.escala_aplicada,
                'subtotal': float(i.subtotal),
                'ganancia': float(i.ganancia),
            }
            for i in cotizacion.items.select_related('producto').all()
        ],
    }


class HistorialCotizacionesView(ListView):
    model = Cotizacion
    template_name = 'cotizaciones/historial.html'
    context_object_name = 'cotizaciones'
    paginate_by = 20


class NuevaCotizacionView(View):
    template_name = 'cotizaciones/nueva_cotizacion.html'

    def _get_cotizacion(self, request):
        cot_id = request.session.get('cotizacion_activa')
        if not cot_id:
            return None
        return Cotizacion.objects.filter(pk=cot_id, estado='borrador').first()

    def get(self, request):
        form = CotizacionForm()
        cotizacion = self._get_cotizacion(request)

        productos_qs = Producto.objects.filter(activo=True).prefetch_related('escalas')
        productos_json = json.dumps([
            {
                'id': p.pk,
                'nombre': p.nombre,
                'categoria': p.categoria or '',
                'precio_base': float(p.precio_base),
                'precio_unitario': float(p.precio_por_unidad()),
                'unidad_paquete': p.unidad_paquete,
                'costo_unitario': float(Decimal(str(p.costo)) / p.unidad_paquete),
                'escalas': sorted(
                    [
                        {
                            'nombre': e.nombre_escala,
                            'min': e.cantidad_minima,
                            'max': e.cantidad_maxima,
                            'precio': float(e.precio_unitario),
                        }
                        for e in p.escalas.all()
                    ],
                    key=lambda x: x['min'],
                ),
            }
            for p in productos_qs
        ])

        cot_dict = _cot_to_dict(cotizacion) if cotizacion else None

        return render(request, self.template_name, {
            'form': form,
            'cotizacion': cotizacion,
            'cotizacion_json': json.dumps(cot_dict) if cot_dict else 'null',
            'productos_json': productos_json,
        })

    def post(self, request):
        action = request.POST.get('action', '')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if action == 'nueva':
            if is_ajax:
                nombre = request.POST.get('cliente_nombre', '').strip()
                notas = request.POST.get('notas', '').strip()
                if not nombre:
                    return JsonResponse({'error': 'El nombre del cliente es requerido.'}, status=400)
                cotizacion = Cotizacion.objects.create(cliente_nombre=nombre, notas=notas)
                request.session['cotizacion_activa'] = cotizacion.pk
                return JsonResponse({
                    'ok': True,
                    'pk': cotizacion.pk,
                    'numero': cotizacion.numero,
                    'cliente': cotizacion.cliente_nombre,
                    'cotizacion': _cot_to_dict(cotizacion),
                })
            form = CotizacionForm(request.POST)
            if form.is_valid():
                cotizacion = form.save()
                request.session['cotizacion_activa'] = cotizacion.pk
                messages.success(request, f'Cotización {cotizacion.numero} creada.')
            return redirect('nueva_cotizacion')

        elif action == 'agregar_item':
            cotizacion = self._get_cotizacion(request)
            if not cotizacion:
                if is_ajax:
                    return JsonResponse({'error': 'No hay cotización activa.'}, status=400)
                messages.error(request, 'Primero crea una cotización.')
                return redirect('nueva_cotizacion')

            producto_id = request.POST.get('producto_id')
            try:
                cantidad = int(request.POST.get('cantidad', 0))
                if cantidad < 1:
                    raise ValueError
            except (ValueError, TypeError):
                if is_ajax:
                    return JsonResponse({'error': 'Cantidad inválida.'}, status=400)
                messages.error(request, 'Cantidad inválida.')
                return redirect('nueva_cotizacion')

            producto = get_object_or_404(Producto, pk=producto_id, activo=True)
            costo_unit = Decimal(str(producto.costo)) / producto.unidad_paquete

            item_existente = ItemCotizacion.objects.filter(
                cotizacion=cotizacion, producto=producto
            ).first()

            if item_existente:
                nueva_cantidad = item_existente.cantidad + cantidad
                escala = producto.get_escala_para_cantidad(nueva_cantidad)
                precio_unit = escala.precio_unitario if escala else producto.precio_por_unidad()
                nombre_escala = escala.nombre_escala if escala else 'Precio base'
                item_existente.cantidad = nueva_cantidad
                item_existente.precio_unitario_aplicado = precio_unit
                item_existente.escala_aplicada = nombre_escala
                item_existente.subtotal = precio_unit * nueva_cantidad
                item_existente.ganancia = (precio_unit - costo_unit) * nueva_cantidad
                item_existente.save()
                msg = f'{producto.nombre}: cantidad actualizada a {nueva_cantidad}.'
            else:
                escala = producto.get_escala_para_cantidad(cantidad)
                precio_unit = escala.precio_unitario if escala else producto.precio_por_unidad()
                nombre_escala = escala.nombre_escala if escala else 'Precio base'
                ItemCotizacion.objects.create(
                    cotizacion=cotizacion,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario_aplicado=precio_unit,
                    escala_aplicada=nombre_escala,
                    subtotal=precio_unit * cantidad,
                    ganancia=(precio_unit - costo_unit) * cantidad,
                )
                msg = f'{cantidad}x {producto.nombre} agregado.'

            cotizacion.recalcular_totales()

            if is_ajax:
                return JsonResponse({'ok': True, 'mensaje': msg, 'cotizacion': _cot_to_dict(cotizacion)})
            messages.success(request, msg)
            return redirect('nueva_cotizacion')

        elif action == 'finalizar':
            cotizacion = self._get_cotizacion(request)
            if cotizacion:
                pk = cotizacion.pk
                del request.session['cotizacion_activa']
                if is_ajax:
                    return JsonResponse({'ok': True, 'redirect': reverse('detalle_cotizacion', kwargs={'pk': pk})})
                messages.success(request, 'Cotización guardada.')
                return redirect('detalle_cotizacion', pk=pk)

        return redirect('nueva_cotizacion')


class DetalleCotizacionView(DetailView):
    model = Cotizacion
    template_name = 'cotizaciones/ver_cotizacion.html'
    context_object_name = 'cotizacion'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('producto').all()
        return ctx


class EliminarCotizacionView(DeleteView):
    model = Cotizacion
    template_name = 'cotizaciones/confirmar_eliminar.html'
    success_url = reverse_lazy('historial_cotizaciones')


def eliminar_item_cotizacion(request, pk):
    item = get_object_or_404(ItemCotizacion, pk=pk)
    cotizacion = item.cotizacion
    item.delete()
    cotizacion.recalcular_totales()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return JsonResponse({'ok': True, 'cotizacion': _cot_to_dict(cotizacion)})

    messages.success(request, 'Item eliminado.')
    return redirect('nueva_cotizacion')
