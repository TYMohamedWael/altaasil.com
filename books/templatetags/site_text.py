import json
import os
from django import template
from django.conf import settings
from django.utils import translation
from ..models import SiteText

register = template.Library()

# Cache for loaded translations
_translations = {}

def load_translations(language_code):
    """Load translation JSON file for the given language."""
    if language_code in _translations:
        return _translations[language_code]
        
    locale_dir = os.path.join(settings.BASE_DIR, 'locale')
    json_path = os.path.join(locale_dir, f"{language_code}.json")
    
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                _translations[language_code] = json.load(f)
            except (json.JSONDecodeError, IOError):
                _translations[language_code] = {}
    else:
        _translations[language_code] = {}
        
    return _translations[language_code]

@register.simple_tag(takes_context=True)
def jtrans(context, key):
    """
    Template tag to translate strings using JSON files.
    Usage: {% jtrans "Greeting message" %}
    """
    language_code = translation.get_language() or 'en'
    
    # Optional: fallback to generic prefix. 'en-us' -> 'en'
    if language_code not in ['en', 'ar', 'ha', 'sw', 'am']:
        language_code = get_language().split('-')[0] # سيحول en-us إلى en و ar-eg إلى ar
        
    translations = load_translations(language_code)
    
    # Return translated string or the original key if missing
    return translations.get(key, key)


@register.simple_tag(takes_context=True)
def site_text(context, key, default="", **kwargs):
    request = context.get('request')
    lang_code = None
    if request and hasattr(request, 'LANGUAGE_CODE'):
        lang_code = request.LANGUAGE_CODE
    if not lang_code:
        lang_code = translation.get_language()
    if lang_code:
        lang_code = lang_code.split('-')[0]

    value = SiteText.get_text(key, lang_code, default)
    if kwargs and isinstance(value, str):
        try:
            value = value.format(**kwargs)
        except Exception:
            pass
    return value
