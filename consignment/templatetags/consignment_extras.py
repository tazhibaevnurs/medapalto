from django import template

register = template.Library()


@register.filter
def som(value):
    """Форматирует число в стиле «1 100» (разделитель тысяч — пробел)."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    s = f"{value:,.0f}"
    return s.replace(",", " ")
