from django import template

register = template.Library()


@register.filter
def toman(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value
