from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from .models import Category, Book, Feedback, Favorite, ReadingProgress, AudioVersion, SocialPost, SearchLog, SovereignGlossary, Language, SiteText

admin.site.site_header = "إدارة الموقع"
admin.site.site_title = "إدارة الموقع"
admin.site.index_title = "الرئيسية"


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['label', 'code', 'direction', 'is_active', 'is_default', 'order']
    list_editable = ['is_active', 'is_default', 'order']
    search_fields = ['name_native', 'name_english', 'code']
    list_filter = ['direction', 'is_active']


@admin.register(SiteText)
class SiteTextAdmin(admin.ModelAdmin):
    list_display = ['key', 'language', 'short_content', 'updated_at']
    list_filter = ['language']
    search_fields = ['key', 'content']
    list_editable = []

    def short_content(self, obj):
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    short_content.short_description = 'المحتوى'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name_hausa', 'name_arabic', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'name_hausa', 'name_arabic']

# في admin.py أضف هذا الكلاس فوق BookAdmin
class LanguageFilter(admin.SimpleListFilter):
    title = 'اللغة'
    parameter_name = 'language'

    def lookups(self, request, model_admin):
        from .models import Language
        return [(l.code, l.name_native) for l in Language.objects.filter(is_active=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(language__code=self.value())
        return queryset



@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_filter = ['status', 'approved', LanguageFilter, 'category']    
    list_display = ['title_hausa', 'title', 'author', 'category', 'language', 'status', 'approved', 'ai_actions_list', 'view_count', 'created_at']
    search_fields = ['title', 'title_hausa', 'author', 'description']
    list_editable = ['status', 'approved']
    prepopulated_fields = {'seo_slug': ('title_hausa',)}
    readonly_fields = ['view_count', 'download_count', 'created_at', 'updated_at', 'ai_panel']
    
    fieldsets = (
        ('بيانات الكتاب', {
            'fields': ('title', 'title_hausa', 'author', 'translator', 'year', 'language')
        }),
        ('التصنيفات', {
            'fields': ('category', 'category_specific')
        }),
        ('🤖 أدوات الذكاء الاصطناعي', {
            'fields': ('ai_panel',),
            'description': 'استخدم الذكاء الاصطناعي لتوليد بيانات الكتاب',
        }),
        ('الوصف والفهرس', {
            'fields': ('description', 'table_of_contents', 'tags')
        }),
        ('الملفات', {
            'fields': ('file', 'drive_url', 'cover')
        }),
        ('السيو (SEO)', {
            'fields': ('seo_title', 'seo_description', 'seo_slug'),
            'classes': ('collapse',)
        }),
        ('الحالة', {
            'fields': ('status', 'approved', 'related_books')
        }),
        ('الإحصائيات', {
            'fields': ('view_count', 'download_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def ai_actions_list(self, obj):
        if obj.pk:
            return format_html(
                '<a class="button" style="padding:2px 8px;font-size:11px;background:#c8a84e;color:#1a5632;border-radius:4px;text-decoration:none" '
                'href="/admin/books/book/{}/ai/all/">🤖 AI</a>',
                obj.pk
            )
        return '-'
    ai_actions_list.short_description = 'الذكاء الاصطناعي'

    def ai_panel(self, obj):
        if not obj.pk:
            return "يجب حفظ الكتاب أولاً قبل استخدام أدوات الذكاء الاصطناعي."
        return format_html('''
            <div style="background:#faf8f0;padding:16px;border-radius:8px;border:1px solid #e0ead6">
                <p style="margin:0 0 12px 0;color:#1a5632;font-weight:bold;font-size:14px">🤖 مولد البيانات بالذكاء الاصطناعي</p>
                <p style="margin:0 0 12px 0;color:#666;font-size:12px">اضغط على الأزرار لتوليد البيانات تلقائياً باستخدام الذكاء الاصطناعي (ChatGPT أو Gemini)</p>
                <div style="display:flex;gap:8px;flex-wrap:wrap">
                    <a class="button" href="/admin/books/book/{id}/ai/all/" 
                       style="background:#1a5632;color:white;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:12px">
                       ✨ توليد الكل
                    </a>
                    <a class="button" href="/admin/books/book/{id}/ai/description/"
                       style="background:#2d7a4a;color:white;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:12px">
                       📝 الوصف
                    </a>
                    <a class="button" href="/admin/books/book/{id}/ai/toc/"
                       style="background:#2d7a4a;color:white;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:12px">
                       📑 الفهرس
                    </a>
                    <a class="button" href="/admin/books/book/{id}/ai/tags/"
                       style="background:#2d7a4a;color:white;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:12px">
                       🏷️ الكلمات الدلالية
                    </a>
                    <a class="button" href="/admin/books/book/{id}/ai/seo/"
                       style="background:#2d7a4a;color:white;padding:6px 16px;border-radius:6px;text-decoration:none;font-size:12px">
                       🔍 السيو (SEO)
                    </a>
                </div>
            </div>
        '''.format(id=obj.pk))
    ai_panel.short_description = 'أدوات الذكاء الاصطناعي'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:book_id>/ai/<str:field>/', self.admin_site.admin_view(self.ai_generate_view), name='book-ai-generate'),
        ]
        return custom_urls + urls

    def ai_generate_view(self, request, book_id, field):
        from django.shortcuts import redirect
        from django.contrib import messages

        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            messages.error(request, "الكتاب غير موجود")
            return redirect('/admin/books/book/')

        try:
            from .ai_service import (
                generate_all, generate_book_description,
                generate_table_of_contents, generate_tags,
                generate_seo, extract_text_from_pdf, get_ai_provider
            )

            provider = get_ai_provider()
            if not provider:
                messages.error(request, "❌ لم يتم إعداد مزود للذكاء الاصطناعي. يرجى ضبط المفاتيح في ملف .env")
                return redirect(f'/admin/books/book/{book_id}/change/')

            text_content = ""
            if book.file:
                text_content = extract_text_from_pdf(book.file.path)

            category_name = book.category.name_hausa if book.category else ""
            lang_code = book.language_code or 'ha'

            if field == 'all':
                result = generate_all(book.title, book.title_hausa or "", book.author, category_name, lang_code, text_content)
                book.description = result.get('description', book.description)
                book.table_of_contents = result.get('chapters', book.table_of_contents)
                book.tags = result.get('tags', book.tags)
                book.seo_title = result.get('seo_title', book.seo_title)
                book.seo_description = result.get('seo_description', book.seo_description)
                if not book.seo_slug:
                    book.seo_slug = result.get('slug') or result.get('seo_slug')
                book.save()
                messages.success(request, f"✅ تم توليد كافة البيانات بنجاح باستخدام {provider}!")

            elif field == 'description':
                book.description = generate_book_description(book.title, book.title_hausa or "", book.author, category_name, text_content)
                book.save(update_fields=['description', 'updated_at'])  # uses lang from generate_all
                messages.success(request, "✅ تم توليد الوصف بنجاح!")

            elif field == 'toc':
                book.table_of_contents = generate_table_of_contents(book.title, book.title_hausa or "", book.author, text_content)
                book.save(update_fields=['table_of_contents', 'updated_at'])
                messages.success(request, "✅ تم توليد الفهرس بنجاح!")

            elif field == 'tags':
                book.tags = generate_tags(book.title, book.title_hausa or "", book.author, book.description or "", category_name)
                book.save(update_fields=['tags', 'updated_at'])
                messages.success(request, "✅ تم توليد الكلمات الدلالية بنجاح!")

            elif field == 'seo':
                seo = generate_seo(book.title, book.title_hausa or "", book.description or "")
                book.seo_title = seo.get('seo_title')
                book.seo_description = seo.get('seo_description')
                if not book.seo_slug:
                    book.seo_slug = seo.get('seo_slug')
                book.save(update_fields=['seo_title', 'seo_description', 'seo_slug', 'updated_at'])
                messages.success(request, "✅ تم توليد وعناوين السيو بنجاح!")

        except Exception as e:
            messages.error(request, f"❌ AI Error: {str(e)}")

        return redirect(f'/admin/books/book/{book_id}/change/')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['book', 'feedback_type', 'reporter_name', 'status', 'created_at']
    list_filter = ['feedback_type', 'status']
    list_editable = ['status']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'created_at']
    list_filter = ['created_at']


@admin.register(ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'current_page', 'total_pages', 'progress_percent', 'last_read']


@admin.register(AudioVersion)
class AudioVersionAdmin(admin.ModelAdmin):
    list_display = ['book', 'language', 'duration_seconds', 'get_audio_source', 'created_at']

    def get_audio_source(self, obj):
        if obj.audio_file:
            return format_html('<span style="color:green">📁 ملف مرفوع</span>')
        elif obj.audio_url:
            return format_html('<a href="{}" target="_blank">🔗 رابط خارجي</a>', obj.audio_url)
        return '—'
    get_audio_source.short_description = 'مصدر الصوت'

@admin.register(SocialPost)
class SocialPostAdmin(admin.ModelAdmin):
    list_display = ['book', 'platform', 'success', 'posted_at']
    list_filter = ['platform', 'success']


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['query', 'results_count', 'user', 'created_at']
    list_filter = ['created_at']


@admin.register(SovereignGlossary)
class SovereignGlossaryAdmin(admin.ModelAdmin):
    list_display = ['term_arabic', 'term_hausa', 'term_english', 'category']
    search_fields = ['term_arabic', 'term_hausa', 'term_english']
    list_filter = ['category']
