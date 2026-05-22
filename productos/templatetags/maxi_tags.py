from django import template

register = template.Library()


@register.filter
def cop(value):
    """Formatea un número como pesos colombianos: $1.200 o $127.500"""
    try:
        n = round(float(value))
        # Formato colombiano: punto como separador de miles, sin decimales
        formatted = f"{n:,}".replace(",", ".")
        return f"${formatted}"
    except (TypeError, ValueError):
        return f"${value}"
