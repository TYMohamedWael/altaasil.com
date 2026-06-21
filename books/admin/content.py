"""
books/admin/content.py
إدارة المحتوى — Admin classes for Language, SiteText, and Category.
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from ..models import Language, SiteText, Category, SovereignGlossary, AudioVersion


# ═══════════════════════════════════════════════════════════════════════════════
# LanguageAdmin / إدارة اللغات
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    """
    Admin for the Language model — manage supported languages.

    إضافات:
      • action  «provision_languages»: يُنشئ ملفات locale/.po/.mo وينشّط اللغة في Rosetta
      • save_model override: يستدعي provision_language مباشرةً عند إنشاء سجل جديد
        ويعرض رسالة فورية في الواجهة.
    """

    list_display  = ['label', 'code', 'direction', 'is_active', 'is_default', 'order', 'locale_status']
    list_editable = ['is_active', 'is_default', 'order']
    search_fields = ['name_native', 'name_english', 'code']
    list_filter   = ['direction', 'is_active']
    actions       = ['provision_languages']

    # ── display: locale file status ──────────────────────────────────────────

    @admin.display(description='ملف الترجمة')
    def locale_status(self, obj):
        """Show whether the .po and .mo files exist for this language code."""
        from pathlib import Path
        from django.conf import settings

        locale_paths = getattr(settings, 'LOCALE_PATHS', [])
        locale_root  = Path(locale_paths[0]) if locale_paths else Path(settings.BASE_DIR) / 'locale'
        lc_dir = locale_root / obj.code / 'LC_MESSAGES'
        po_ok  = (lc_dir / 'django.po').exists()
        mo_ok  = (lc_dir / 'django.mo').exists()

        po_icon = '✅' if po_ok else '❌'
        mo_icon = '✅' if mo_ok else '❌'
        return format_html(
            '<span title="{}">.po {} &nbsp; .mo {}</span>',
            str(lc_dir), po_icon, mo_icon,
        )

    # ── save_model: auto-provision on first create ────────────────────────────

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new:
            # Initialize cache status so that the progress page is populated immediately
            from django.core.cache import cache
            cache.set(f"provision_progress_{obj.code.strip().lower()}", {
                'status': 'pending',
                'progress': 0,
                'message': 'بدء إعداد اللغة...',
                'log': ['بدء العملية...'],
                'errors': []
            }, 3600)

    def response_add(self, request, obj, post_url_continue=None):
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse('admin:books_language_provision_progress', args=[obj.code]))

    # ── action: manually provision one or more languages ─────────────────────

    @admin.action(description='🔧 إعداد ملفات الترجمة (provision locale files)')
    def provision_languages(self, request, queryset):
        """
        تشغيل إعداد اللغة في الخلفية والتوجيه لصفحة شريط تقدم الترجمة.
        """
        import threading
        from django.core.cache import cache
        from django.shortcuts import redirect
        from django.urls import reverse

        first_code = None
        for lang in queryset:
            code = lang.code.strip().lower()
            if not first_code:
                first_code = code

            # تهيئة الكاش لهذه اللغة
            cache.set(f"provision_progress_{code}", {
                'status': 'pending',
                'progress': 0,
                'message': 'بدء إعداد اللغة (يدوياً)...',
                'log': ['بدء العملية يدوياً من قائمة التحكم...'],
                'errors': []
            }, 3600)

            # تشغيل العملية في thread خلفي
            def run_provision(l=lang, lcode=code):
                from django.db import close_old_connections
                close_old_connections()
                try:
                    from ..services.language_setup import provision_language
                    provision_language(l)
                except Exception as exc:
                    import logging
                    logging.getLogger(__name__).exception("Error in provision action background thread: %s", exc)
                    # Update cache so progress page shows error instead of hanging
                    try:
                        from ..services.language_setup import update_provision_progress
                        update_provision_progress(
                            lcode, 0,
                            "خطأ غير متوقع في الخيط الخلفي",
                            log_line=f"❌ {exc}",
                            status='failed',
                            error_msg=str(exc)
                        )
                    except Exception:
                        pass
                finally:
                    close_old_connections()

            thread = threading.Thread(target=run_provision, name=f"provision_action_{code}")
            thread.daemon = True
            thread.start()

        if first_code:
            return redirect(reverse('admin:books_language_provision_progress', args=[first_code]))

    # ── Custom URL configuration ────────────────────────────────────────────

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'provision-progress/<str:code>/',
                self.admin_site.admin_view(self.provision_progress_page_view),
                name='books_language_provision_progress',
            ),
            path(
                'provision-progress/<str:code>/json/',
                self.admin_site.admin_view(self.provision_progress_json_view),
                name='books_language_provision_progress_json',
            ),
        ]
        return custom_urls + urls

    def provision_progress_page_view(self, request, code):
        from django.template.response import TemplateResponse
        from books.models import Language
        lang = Language.objects.filter(code=code).first()
        lang_name = lang.name_native if lang else code
        context = {
            **self.admin_site.each_context(request),
            'code': code,
            'lang_name': lang_name,
            'title': f'متابعة إعداد اللغة ({lang_name})',
        }
        return TemplateResponse(request, 'admin/books/language/provision_progress.html', context)

    def provision_progress_json_view(self, request, code):
        from django.http import JsonResponse
        from django.core.cache import cache
        data = cache.get(f"provision_progress_{code.strip().lower()}")
        if not data:
            data = {
                'status': 'pending',
                'progress': 0,
                'message': 'قيد الانتظار...',
                'log': ['في انتظار بدء العملية...'],
                'errors': []
            }
        return JsonResponse(data)


# ═══════════════════════════════════════════════════════════════════════════════
# SiteTextAdmin / إدارة نصوص الموقع
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(SiteText)
class SiteTextAdmin(admin.ModelAdmin):
    """Admin for translatable site-wide text snippets."""

    list_display = ['key', 'language', 'short_content', 'updated_at']
    list_filter = ['language']
    search_fields = ['key', 'content']
    list_editable = []

    def short_content(self, obj):
        """Truncate content for the list view."""
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    short_content.short_description = 'المحتوى'


# ═══════════════════════════════════════════════════════════════════════════════
# CategoryAdmin / إدارة التصنيفات
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for book categories with auto-slug."""

    list_display = ['name_hausa', 'name_arabic', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'name_hausa', 'name_arabic']


# ═══════════════════════════════════════════════════════════════════════════════
# SovereignGlossaryAdmin / إدارة المعجم
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(SovereignGlossary)
class SovereignGlossaryAdmin(ModelAdmin):
    list_display = ['term_arabic', 'term_hausa', 'term_english', 'category']
    search_fields = ['term_arabic', 'term_hausa', 'term_english']


# ═══════════════════════════════════════════════════════════════════════════════
# AudioVersionAdmin / إدارة النسخ الصوتية
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(AudioVersion)
class AudioVersionAdmin(ModelAdmin):
    list_display = ['book', 'language', 'duration_seconds', 'get_audio_source', 'created_at']

    def get_audio_source(self, obj):
        if obj.audio_file:
            return format_html('<span style="color:green">📁 ملف مرفوع</span>')
        elif hasattr(obj, 'audio_url') and obj.audio_url:
            return format_html('<a href="{}" target="_blank">🔗 رابط خارجي</a>', obj.audio_url)
        return '—'
    get_audio_source.short_description = 'مصدر الصوت'
