from django.utils import translation

try:
    from .models import Language
except Exception:  # pragma: no cover - during migrations
    Language = None


def languages(request):
    current_code = translation.get_language() or 'ha'
    current_code = current_code.split('-')[0]
    lang_data = []

    if Language is not None:
        try:
            qs = Language.objects.filter(is_active=True).order_by('order', 'name_native')
            lang_data = [
                {
                    'code': lang.code,
                    'name_native': lang.name_native,
                    'name_english': lang.name_english,
                    'flag_emoji': lang.flag_emoji,
                    'direction': lang.direction,
                    'is_default': lang.is_default,
                }
                for lang in qs
            ]
        except Exception:
            lang_data = []

    if not lang_data:
        from .models import Language as LanguageModel  # local import to access fallback list
        lang_data = LanguageModel.fallback_languages()

    default_direction = next(
        (lang['direction'] for lang in lang_data if lang.get('code') == current_code),
        'rtl' if current_code == 'ar' else 'ltr'
    )

    return {
        'language_menu': lang_data,
        'active_language_code': current_code,
        'active_language_direction': default_direction,
    }
