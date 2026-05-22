"""
Utilidad para importar productos desde un archivo Excel (.xlsx).

Columnas del Excel de Maxi Plásticos:
  0000000 / codigo / referencia / ref / cod     → código del producto
  nombre del producto / nombre / producto       → nombre
  costo / cost                                  → costo de compra
  markup / margen / margin                      → % markup (se almacena para info)
  precio / precio_base / price / precio venta   → precio de venta
  impuesto / iva / tax                          → % de impuesto
  categoria / tipo / linea / grupo              → categoría (si existe)
  paquete / unidades / und / contenido          → unidades por paquete (si existe)
"""

import re
from decimal import Decimal, InvalidOperation


# ---------- normalización ----------

def _norm(s):
    return re.sub(r'\s+', ' ', str(s).strip().lower())


# Alias por campo — orden de prioridad: primero los más específicos
_ALIAS_CODIGO  = {'0000000', 'codigo', 'código', 'referencia', 'ref', 'cod', 'code', 'sku', 'id'}
_ALIAS_NOMBRE  = {'nombre del producto', 'nombre', 'name', 'producto', 'articulo', 'artículo', 'item', 'descripcion corta'}
_ALIAS_COSTO   = {'costo', 'cost', 'costo paquete', 'precio costo', 'precio compra', 'costo total'}
_ALIAS_MARKUP  = {'markup', 'margen', 'margin', 'mark up', 'mark-up'}
_ALIAS_PRECIO  = {'precio', 'precio_base', 'price', 'precio venta', 'precio paquete', 'valor', 'pvp', 'precio base'}
_ALIAS_IMP     = {'impuesto', 'iva', 'tax', 'impuestos', '% impuesto', 'imp'}
_ALIAS_DESC    = {'descripcion', 'descripción', 'description', 'detalle', 'obs', 'observacion', 'nota'}
_ALIAS_CAT     = {'categoria', 'categoría', 'category', 'tipo', 'linea', 'línea', 'grupo', 'family'}
_ALIAS_UNIDAD  = {'unidad_paquete', 'paquete', 'unidades', 'und paquete', 'unid', 'cant paquete',
                  'contenido', 'unidades por paquete', 'und/paquete', 'cantidad paquete', 'und'}


def _detect_columns(headers):
    mapping = {}
    for idx, raw in enumerate(headers):
        h = _norm(raw)
        # Orden importa: nombre del producto debe detectarse antes que nombre genérico
        if h in _ALIAS_CODIGO  and 'codigo'        not in mapping: mapping['codigo']        = idx
        elif h in _ALIAS_NOMBRE  and 'nombre'       not in mapping: mapping['nombre']        = idx
        elif h in _ALIAS_COSTO   and 'costo'        not in mapping: mapping['costo']         = idx
        elif h in _ALIAS_MARKUP  and 'markup'       not in mapping: mapping['markup']        = idx
        elif h in _ALIAS_PRECIO  and 'precio_base'  not in mapping: mapping['precio_base']   = idx
        elif h in _ALIAS_IMP     and 'impuesto'     not in mapping: mapping['impuesto']      = idx
        elif h in _ALIAS_DESC    and 'descripcion'  not in mapping: mapping['descripcion']   = idx
        elif h in _ALIAS_CAT     and 'categoria'    not in mapping: mapping['categoria']     = idx
        elif h in _ALIAS_UNIDAD  and 'unidad_paquete' not in mapping: mapping['unidad_paquete'] = idx
        else:
            # Escalas opcionales: escala1_nombre, min1, max1, precio1 … hasta 5
            for i in range(1, 6):
                patterns = {
                    f'escala{i}_nombre': {f'escala{i}', f'escala {i}', f'escala{i}_nombre', f'escala {i} nombre', f'nombre escala {i}'},
                    f'escala{i}_min':    {f'escala{i}_min', f'min{i}', f'desde{i}', f'escala {i} min', f'cant min {i}'},
                    f'escala{i}_max':    {f'escala{i}_max', f'max{i}', f'hasta{i}', f'escala {i} max', f'cant max {i}'},
                    f'escala{i}_precio': {f'escala{i}_precio', f'precio{i}', f'precio escala {i}', f'escala {i} precio', f'p{i}', f'pvta{i}'},
                }
                for campo, aliases in patterns.items():
                    if h in aliases and campo not in mapping:
                        mapping[campo] = idx
    return mapping


# ---------- conversión segura ----------

def _to_decimal(val, default=Decimal('0')):
    if val is None or str(val).strip() in ('', 'None', 'nan'):
        return default
    try:
        cleaned = str(val).replace(',', '.').replace('$', '').replace(' ', '').replace('%', '')
        return Decimal(cleaned)
    except InvalidOperation:
        return default


def _to_int(val, default=1):
    if val is None or str(val).strip() in ('', 'None', 'nan'):
        return default
    try:
        return max(1, int(float(str(val).replace(',', '.'))))
    except (ValueError, TypeError):
        return default


def _get(row, col_map, campo):
    """Obtiene el valor de una fila dado el nombre de campo interno."""
    idx = col_map.get(campo)
    if idx is None:
        return None
    return row[idx] if idx < len(row) else None


# ---------- función principal ----------

def parse_excel(file_obj):
    """
    Recibe un file-like object de un .xlsx.
    Retorna (filas_ok, errores, columnas_detectadas).
    """
    import openpyxl
    wb = openpyxl.load_workbook(file_obj, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ['El archivo está vacío.'], {}

    headers = [str(c) if c is not None else '' for c in rows[0]]
    col_map = _detect_columns(headers)

    if 'nombre' not in col_map:
        return [], [
            f'No se encontró columna de nombre. '
            f'Encabezados detectados: {headers}. '
            f'Asegúrate de tener una columna "Nombre del producto" o "nombre".'
        ], col_map

    if 'precio_base' not in col_map and 'costo' not in col_map:
        return [], [
            f'No se encontró columna de precio ni costo. '
            f'Encabezados detectados: {headers}.'
        ], col_map

    filas_ok = []
    errores  = []

    for row_num, row in enumerate(rows[1:], start=2):
        nombre_val = _get(row, col_map, 'nombre')
        nombre = str(nombre_val).strip() if nombre_val else ''
        if not nombre or nombre.lower() in ('none', 'nan', ''):
            continue

        precio_base = _to_decimal(_get(row, col_map, 'precio_base'))
        costo       = _to_decimal(_get(row, col_map, 'costo'))
        markup      = _to_decimal(_get(row, col_map, 'markup'))   # solo para info/cálculo
        impuesto    = _to_decimal(_get(row, col_map, 'impuesto'))

        # Si el precio está en 0 pero hay costo y markup, calcularlo
        if precio_base == 0 and costo > 0 and markup > 0:
            precio_base = costo * (1 + markup / 100)
            errores.append(
                f'Fila {row_num} ({nombre}): precio calculado desde costo + markup ({markup}%) = ${precio_base:.0f}.'
            )

        # Si sigue en 0, usar costo
        if precio_base == 0 and costo > 0:
            precio_base = costo
            errores.append(f'Fila {row_num} ({nombre}): sin precio, se usó el costo como precio base.')

        if precio_base == 0:
            errores.append(f'Fila {row_num} ({nombre}): sin precio ni costo — omitido.')
            continue

        codigo         = str(_get(row, col_map, 'codigo')     or '').strip()
        descripcion    = str(_get(row, col_map, 'descripcion') or '').strip()
        categoria      = str(_get(row, col_map, 'categoria')   or '').strip()
        unidad_paquete = _to_int(_get(row, col_map, 'unidad_paquete'), default=1)

        # Limpiar "None" literal
        if codigo      == 'None': codigo = ''
        if descripcion == 'None': descripcion = ''
        if categoria   == 'None': categoria = ''

        # Escalas opcionales
        escalas = []
        for i in range(1, 6):
            if f'escala{i}_nombre' not in col_map and f'escala{i}_precio' not in col_map:
                continue
            nombre_escala = str(_get(row, col_map, f'escala{i}_nombre') or f'Escala {i}').strip()
            min_cant      = _to_int(_get(row, col_map, f'escala{i}_min'), default=1)
            max_raw       = _get(row, col_map, f'escala{i}_max')
            max_cant      = _to_int(max_raw) if max_raw not in (None, '', 0) else None
            p_escala      = _to_decimal(_get(row, col_map, f'escala{i}_precio'))
            if p_escala > 0:
                escalas.append({
                    'nombre_escala':   nombre_escala,
                    'cantidad_minima': min_cant,
                    'cantidad_maxima': max_cant,
                    'precio_unitario': p_escala,
                })

        filas_ok.append({
            'codigo':         codigo,
            'nombre':         nombre,
            'descripcion':    descripcion,
            'costo':          costo,
            'precio_base':    precio_base,
            'impuesto':       impuesto,
            'unidad_paquete': unidad_paquete,
            'categoria':      categoria,
            'escalas':        escalas,
        })

    return filas_ok, errores, col_map


def importar_productos(filas, actualizar_existentes=False):
    """
    Guarda los productos. Busca existentes por código (si hay) o por nombre.
    Retorna (creados, actualizados, omitidos).
    """
    from .models import Producto, EscalaPrecios

    creados = actualizados = omitidos = 0

    for fila in filas:
        escalas_data = fila.pop('escalas', [])
        codigo  = fila.get('codigo', '')
        nombre  = fila['nombre']

        # Buscar existente por código primero, luego por nombre
        existente = None
        if codigo:
            existente = Producto.objects.filter(codigo=codigo).first()
        if not existente:
            existente = Producto.objects.filter(nombre__iexact=nombre).first()

        if existente and not actualizar_existentes:
            omitidos += 1
            fila['escalas'] = escalas_data
            continue

        if existente and actualizar_existentes:
            for campo, valor in fila.items():
                setattr(existente, campo, valor)
            existente.save()
            existente.escalas.all().delete()
            producto = existente
            actualizados += 1
        else:
            producto = Producto.objects.create(**fila)
            creados += 1

        for e in escalas_data:
            EscalaPrecios.objects.create(producto=producto, **e)

        fila['escalas'] = escalas_data

    return creados, actualizados, omitidos
