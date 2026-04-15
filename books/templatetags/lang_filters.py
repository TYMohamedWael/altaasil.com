from django import template
from django.utils import translation

register = template.Library()

@register.filter
def lang_field(obj, field_base):
    lang = translation.get_language()  # 'ha', 'ar', 'en'...
    field_name = f"{field_base}_{lang}"
    return getattr(obj, field_name, "")