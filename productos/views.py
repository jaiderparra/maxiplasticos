import json
from decimal import Decimal
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .models import Producto, EscalaPrecios
from .forms import ProductoForm, EscalaFormSet
from .import_utils import parse_excel, importar_productos


class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


class ListaProductosView(ListView):
    model = Producto
    template_name = 'productos/lista_productos.html'
    context_object_name = 'productos'
    paginate_by = 24

    def get_queryset(self):
        qs = Producto.objects.filter(activo=True).prefetch_related('escalas')
        categoria = self.request.GET.get('categoria', '')
        busqueda = self.request.GET.get('buscar', '')
        if categoria:
            qs = qs.filter(categoria__icontains=categoria)
        if busqueda:
            qs = qs.filter(nombre__icontains=busqueda)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categorias'] = Producto.objects.filter(activo=True).values_list('categoria', flat=True).distinct()
        ctx['categoria_actual'] = self.request.GET.get('categoria', '')
        ctx['busqueda'] = self.request.GET.get('buscar', '')
        ctx['total_productos'] = Producto.objects.filter(activo=True).count()
        # JSON liviano para búsqueda en tiempo real (solo id, nombre, categoría, precio)
        todos = Producto.objects.filter(activo=True).values('pk', 'nombre', 'categoria', 'precio_base', 'unidad_paquete')
        ctx['catalogo_json'] = json.dumps([
            {
                'id': p['pk'],
                'nombre': p['nombre'],
                'categoria': p['categoria'] or '',
                'precio_unitario': round(float(p['precio_base']) / max(p['unidad_paquete'], 1), 0),
            }
            for p in todos
        ])
        return ctx


class DetalleProductoView(DetailView):
    model = Producto
    template_name = 'productos/detalle_producto.html'
    context_object_name = 'producto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['escalas'] = self.object.escalas.all().order_by('cantidad_minima')
        return ctx


class CrearProductoView(CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/crear_producto.html'
    success_url = reverse_lazy('lista_productos')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['escala_formset'] = EscalaFormSet(self.request.POST)
        else:
            ctx['escala_formset'] = EscalaFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['escala_formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)


class EditarProductoView(UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/crear_producto.html'
    success_url = reverse_lazy('lista_productos')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['escala_formset'] = EscalaFormSet(self.request.POST, instance=self.object)
        else:
            ctx['escala_formset'] = EscalaFormSet(instance=self.object)
        ctx['editando'] = True
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['escala_formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        return self.form_invalid(form)


class EliminarProductoView(DeleteView):
    model = Producto
    template_name = 'productos/confirmar_eliminar.html'
    success_url = reverse_lazy('lista_productos')


@require_GET
def calcular_precio_ajax(request):
    producto_id = request.GET.get('producto_id')
    cantidad_str = request.GET.get('cantidad', '0')

    try:
        cantidad = int(cantidad_str)
    except ValueError:
        return JsonResponse({'error': 'Cantidad inválida'}, status=400)

    producto = get_object_or_404(Producto, pk=producto_id, activo=True)

    escala = producto.get_escala_para_cantidad(cantidad)

    if escala:
        precio_unit = escala.precio_unitario
        nombre_escala = escala.nombre_escala
    else:
        precio_unit = producto.precio_por_unidad()
        nombre_escala = 'Precio base'

    subtotal = precio_unit * cantidad
    costo_unit = producto.precio_por_unidad() if producto.unidad_paquete > 0 else producto.costo
    ganancia = (precio_unit - Decimal(str(producto.costo)) / producto.unidad_paquete) * cantidad

    return JsonResponse({
        'precio_unitario': float(precio_unit),
        'subtotal': float(subtotal),
        'ganancia': float(ganancia),
        'escala': nombre_escala,
        'producto_nombre': producto.nombre,
    })


class ImportarProductosView(View):
    template_name = 'productos/importar_excel.html'

    def get(self, request):
        request.session.pop('filas_importar', None)
        return render(request, self.template_name)

    def post(self, request):
        action = request.POST.get('action', 'preview')

        if action == 'preview':
            archivo = request.FILES.get('archivo_excel')
            if not archivo:
                messages.error(request, 'No se adjuntó ningún archivo.')
                return redirect('importar_productos')
            if not archivo.name.endswith(('.xlsx', '.xls')):
                messages.error(request, 'El archivo debe ser .xlsx o .xls')
                return redirect('importar_productos')
            try:
                filas, errores, col_map = parse_excel(archivo)
            except Exception as e:
                messages.error(request, f'Error al leer el archivo: {e}')
                return redirect('importar_productos')

            # Guardar en sesión (evita campo oculto gigante y problemas con Decimal)
            request.session['filas_importar'] = json.dumps(filas, cls=_DecimalEncoder)
            request.session['nombre_archivo'] = archivo.name

            return render(request, self.template_name, {
                'preview': True,
                'filas': filas[:20],
                'total_filas': len(filas),
                'errores': errores,
                'col_map': col_map,
                'nombre_archivo': archivo.name,
            })

        elif action == 'importar':
            filas_json = request.session.get('filas_importar', '[]')
            nombre_archivo = request.session.get('nombre_archivo', '')
            try:
                filas_guardadas = json.loads(filas_json)
                for f in filas_guardadas:
                    f['costo']          = Decimal(str(f['costo']))
                    f['precio_base']    = Decimal(str(f['precio_base']))
                    f['impuesto']       = Decimal(str(f.get('impuesto', '0')))
                    f['unidad_paquete'] = int(f.get('unidad_paquete', 1))
                    for e in f.get('escalas', []):
                        e['precio_unitario'] = Decimal(str(e['precio_unitario']))
                        e['cantidad_minima'] = int(e['cantidad_minima'])
                        e['cantidad_maxima'] = int(e['cantidad_maxima']) if e.get('cantidad_maxima') else None
            except Exception as ex:
                messages.error(request, f'Error procesando los datos: {ex}')
                return redirect('importar_productos')

            if not filas_guardadas:
                messages.error(request, 'No hay datos en sesión. Vuelve a subir el archivo.')
                return redirect('importar_productos')

            actualizar = request.POST.get('actualizar_existentes') == 'on'
            creados, actualizados, omitidos = importar_productos(filas_guardadas, actualizar)

            request.session.pop('filas_importar', None)
            request.session.pop('nombre_archivo', None)

            if omitidos > 0 and creados == 0 and actualizados == 0:
                messages.warning(
                    request,
                    f'Se omitieron los {omitidos} productos porque ya existen en la base de datos. '
                    f'Para actualizarlos, importa el archivo de nuevo y activa '
                    f'"Actualizar productos que ya existen".'
                )
            else:
                partes = []
                if creados:    partes.append(f'{creados} creados')
                if actualizados: partes.append(f'{actualizados} actualizados')
                if omitidos:   partes.append(f'{omitidos} omitidos (ya existían)')
                messages.success(request, f'Importación completa: {", ".join(partes)}.')

            return redirect('lista_productos')

        return redirect('importar_productos')
