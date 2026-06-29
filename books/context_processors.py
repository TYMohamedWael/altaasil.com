
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

    SITE_NAMES = {
        'ha': 'Laburaren Ilmin Musulunci',
        'en': 'Islamic Knowledge Library',
        'ar': 'مكتبة المعرفة الإسلامية',
        'am': 'የእስልምና እውቀት ቤተ መጻሕፍት',
        'sw': 'Maktaba ya Maarifa ya Kiislamu',
        'bn': 'ইসলামিক নলেজ লাইব্রেরি',
        'fa': 'کتابخانه دانش اسلامی',
        'fr': 'Bibliothèque des Connaissances Islamiques',
        'de': 'Islamische Wissensbibliothek',
        'es': 'Biblioteca de Conocimiento Islámico',
        'ru': 'Библиотека исламских знаний',
        'pt': 'Biblioteca de Conhecimento Islâmico',
    }

    LANG_SUFFIXES = {
        'ha': 'hausa',
        'en': 'english',
        'ar': 'arabic',
        'am': 'amharic',
        'sw': 'swahili',
        'bn': 'bengali',
        'fa': 'persian',
        'fr': 'french',
        'de': 'german',
        'es': 'spanish',
        'ru': 'russian',
        'pt': 'portuguese',
    }

    active_lang_name = 'english'
    for lang in lang_data:
        if lang['code'] == current_code:
            active_lang_name = lang['name_english'].lower()
            break

    site_name_base = SITE_NAMES.get(current_code, 'Islamic Knowledge Library')
    lang_suffix = LANG_SUFFIXES.get(current_code, active_lang_name)
    site_name = f"{site_name_base} - {lang_suffix}"

    return {
        'language_menu': lang_data,
        'active_language_code': current_code,
        'active_language_direction': default_direction,
        'site_name': site_name,
        'site_name_base': site_name_base,
    }


def menus(request):
    """
    Inject navigation menus into all templates.
    حقن قوائم التنقل في جميع القوالب تلقائياً.

    Available in templates as:
      {{ header_menu }}  — header navigation items
      {{ footer_menu }}  — footer navigation items
      {{ footer_pages }} — published pages marked for footer
    """
    from django.core.cache import cache

    cache_key = 'ctx:menus:all'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from .models import Menu, Page

        result = {}

        # Load menus by location
        for location in ['header', 'footer', 'sidebar', 'mobile_bottom']:
            menu = Menu.objects.filter(location=location, is_active=True).first()
            if menu:
                items = list(
                    menu.items
                    .filter(is_visible=True, parent__isnull=True)
                    .select_related('page', 'category')
                    .prefetch_related('children')
                    .order_by('order')
                )
                result[f'{location}_menu'] = items
            else:
                result[f'{location}_menu'] = []

        # Footer pages (from Page model)
        result['footer_pages'] = list(
            Page.objects.filter(status='published', show_in_footer=True)
            .only('title', 'title_hausa', 'slug', 'icon')
            .order_by('order')
        )

        # Header pages
        result['header_pages'] = list(
            Page.objects.filter(status='published', show_in_header=True)
            .only('title', 'title_hausa', 'slug', 'icon')
            .order_by('order')
        )

        cache.set(cache_key, result, 300)  # 5 minutes
        return result

    except Exception:
        return {
            'header_menu': [],
            'footer_menu': [],
            'sidebar_menu': [],
            'mobile_bottom_menu': [],
            'footer_pages': [],
            'header_pages': [],
        }
