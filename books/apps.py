from django.apps import AppConfig
from django.db.models.signals import post_migrate


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'books'
    verbose_name = 'إدارة المحتوى'

    def ready(self):
        import books.signals  # noqa: F401 – register signal handlers
        post_migrate.connect(sync_languages_from_db, sender=self)


def sync_languages_from_db(sender, **kwargs):
    """
    After migrations, load all active languages from the database,
    register them in django's locale info, and clear caches to ensure
    they are ready immediately.
    """
    try:
        from django.conf import settings
        from books.models import Language
        import django.conf.locale

        db_langs = Language.objects.filter(is_active=True)

        for lang in db_langs:
            code = lang.code.strip().lower()
            if code not in django.conf.locale.LANG_INFO:
                django.conf.locale.LANG_INFO[code] = {
                    'bidi': lang.direction == 'rtl',
                    'code': code,
                    'name': lang.name_english or lang.name_native,
                    'name_local': lang.name_native,
                }

        # Clear translation cache
        from django.utils.translation import trans_real
        trans_real._translations = {}
        from django.utils import translation
        translation.deactivate_all()

        # Clear URL resolver cache
        from django.urls import clear_url_caches
        clear_url_caches()
    except Exception:
        pass
