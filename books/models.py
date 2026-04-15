from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import translation
import uuid
from django.core.cache import cache
import os   



def _active_lang():
    lang = translation.get_language() or 'ha'
    return lang.split('-')[0]


def book_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'books/files/{uuid.uuid4().hex}{ext}'


class Language(models.Model):
    DIRECTION_CHOICES = (
        ('ltr', 'من اليسار إلى اليمين (LTR)'),
        ('rtl', 'من اليمين إلى اليسار (RTL)'),
    )

    code = models.CharField(max_length=10, unique=True, verbose_name='كود اللغة (ISO)')
    name_native = models.CharField(max_length=100, verbose_name='الاسم الأصلي')
    name_english = models.CharField(max_length=100, verbose_name='الاسم بالإنجليزية')
    flag_emoji = models.CharField(max_length=8, blank=True, null=True, verbose_name='رمز العلم (Emoji)')
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default='ltr', verbose_name='اتجاه النص')
    is_active = models.BooleanField(default=True, verbose_name='مفعل')
    is_default = models.BooleanField(default=False, verbose_name='لغة افتراضية')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='الترتيب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'اللغة'
        verbose_name_plural = 'اللغات'
        ordering = ['order', 'name_native']

    def __str__(self):
        return f"{self.name_native} ({self.code})"

    def save(self, *args, **kwargs):
        if self.is_default:
            Language.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def default(cls):
        lang = cls.objects.filter(is_default=True).first()
        if not lang:
            lang = cls.objects.first()
        return lang

    @property
    def label(self):
        flag = f"{self.flag_emoji} " if self.flag_emoji else ''
        return f"{flag}{self.name_native}"

    @staticmethod
    def fallback_languages():
        return [
            {
                'code': 'ha',
                'name_native': 'Hausa',
                'name_english': 'Hausa',
                'flag_emoji': '🇳🇬',
                'direction': 'ltr',
            },
            {
                'code': 'ar',
                'name_native': 'العربية',
                'name_english': 'Arabic',
                'flag_emoji': '🇸🇦',
                'direction': 'rtl',
            },
            {
                'code': 'en',
                'name_native': 'English',
                'name_english': 'English',
                'flag_emoji': '🇬🇧',
                'direction': 'ltr',
            },
            {
                'code': 'am',
                'name_native': 'አማርኛ',
                'name_english': 'Amharic',
                'flag_emoji': '🇪🇹',
                'direction': 'ltr',
            },
            {
                'code': 'hr',
                'name_native': 'الأمهرية',
                'name_english': 'Amharic (legacy)',
                'flag_emoji': '',
                'direction': 'ltr',
            },
        ]


def book_cover_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'books/covers/{uuid.uuid4().hex}{ext}'


def audio_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'books/audio/{uuid.uuid4().hex}{ext}'


def scraped_file_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'books/scraped/{uuid.uuid4().hex}{ext}'


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='الاسم الأساسي')
    name_hausa = models.CharField(max_length=100, verbose_name='الاسم بلغة الهوسا')
    name_arabic = models.CharField(max_length=100, verbose_name='الاسم بالعربية')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='الرابط (Slug)')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    language = models.ForeignKey(
        'Language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categories',
        verbose_name='اللغة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'التصنيف'
        verbose_name_plural = 'التصنيفات'
        ordering = ['name_hausa']

    def __str__(self):
        base = self.name_hausa or self.name
        if self.language:
            return f"{base} [{self.language.code}]"
        return base

    @property
    def localized_name(self):
        lang = _active_lang()
        if lang == 'ar' and self.name_arabic:
            return self.name_arabic
        if lang == 'ha' and self.name_hausa:
            return self.name_hausa
        if lang in ('en', 'am') and self.name:
            return self.name
        return self.name_hausa or self.name_arabic or self.name

    @property
    def alternate_name(self):
        lang = _active_lang()
        if lang == 'ar':
            return self.name_hausa or self.name
        if self.name_arabic:
            return self.name_arabic
        return None

    @property
    def language_label(self):
        if self.language:
            return self.language.name_native
        return None


class SiteText(models.Model):
    key = models.CharField(max_length=191, verbose_name='مفتاح النص (Key)')
    language = models.ForeignKey(
        Language,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='site_texts',
        verbose_name='اللغة'
    )
    content = models.TextField(verbose_name='المحتوى')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='وصف داخلي')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'النص الثابت'
        verbose_name_plural = 'النصوص الثابتة'
        unique_together = ('key', 'language')
        ordering = ['key']

    def __str__(self):
        label = self.language.code if self.language else 'default'
        return f"{self.key} ({label})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        self._invalidate_cache()
        super().delete(*args, **kwargs)

    def _invalidate_cache(self):
        cache.delete(f"site_text:None:{self.key}")
        for code in Language.objects.values_list('code', flat=True):
            cache.delete(f"site_text:{code}:{self.key}")

    @staticmethod
    def get_text(key, language_code=None, default=""):
        cache_key = f"site_text:{language_code}:{key}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        lang = None
        if language_code:
            lang = Language.objects.filter(code=language_code).first()

        queryset = SiteText.objects.filter(key=key)
        if lang:
            text_obj = queryset.filter(language=lang).first()
            if text_obj:
                cache.set(cache_key, text_obj.content, 3600)
                return text_obj.content

        default_obj = queryset.filter(language__isnull=True).first()
        if default_obj:
            cache.set(cache_key, default_obj.content, 3600)
            return default_obj.content

        default_language = Language.default()
        if default_language:
            fallback_obj = queryset.filter(language=default_language).first()
            if fallback_obj:
                cache.set(cache_key, fallback_obj.content, 3600)
                return fallback_obj.content

        return default


class Book(models.Model):
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('processing', 'جاري المعالجة'),
        ('published', 'تم النشر'),
    ]

    title = models.CharField(max_length=500, verbose_name='اسم الكتاب (العربية)')
    title_hausa = models.CharField(max_length=500, blank=True, null=True, verbose_name='اسم الكتاب (الهوسا)')
    author = models.CharField(max_length=300, verbose_name='المؤلف')
    translator = models.CharField(max_length=300, blank=True, null=True, verbose_name='المترجم')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='books', verbose_name='التصنيف')
    category_specific = models.CharField(max_length=200, blank=True, null=True, verbose_name='التصنيف الفرعي')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    table_of_contents = models.JSONField(default=list, blank=True, verbose_name='الفهرس')
    tags = models.JSONField(default=list, blank=True, verbose_name='الكلمات الدلالية')
    related_books = models.ManyToManyField('self', blank=True, verbose_name='كتب ذات صلة')
    language = models.ForeignKey(
        Language,
        to_field='code',
        db_column='language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books',
        verbose_name='لغة الكتاب'
    )
    year = models.IntegerField(blank=True, null=True, verbose_name='سنة النشر')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='الحالة')
    approved = models.BooleanField(default=False, verbose_name='موافق عليه علمياً')
    file = models.FileField(upload_to=book_file_path, blank=True, null=True, verbose_name='ملف الكتاب')
    drive_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='رابط Google Drive (PDF)'
    )
    cover = models.ImageField(upload_to=book_cover_path, blank=True, null=True, verbose_name='صورة الغلاف')
    seo_title = models.CharField(max_length=200, blank=True, null=True, verbose_name='عنوان السيو (SEO)')
    seo_description = models.CharField(max_length=500, blank=True, null=True, verbose_name='وصف السيو (SEO)')
    seo_slug = models.SlugField(max_length=191, unique=True, blank=True, null=True, verbose_name='الرابط الدائم (Slug)')
    view_count = models.IntegerField(default=0, verbose_name='عدد المشاهدات')
    download_count = models.IntegerField(default=0, verbose_name='عدد التحميلات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ آخر تحديث')

    class Meta:
        verbose_name = 'الكتاب'
        verbose_name_plural = 'الكتب'
        ordering = ['-created_at']

    def __str__(self):
        return self.title_hausa or self.title

    @property
    def localized_title(self):
        lang = _active_lang()
        if lang == 'ar' and self.title:
            return self.title
        if lang == 'ha' and self.title_hausa:
            return self.title_hausa
        if lang in ('en', 'am') and self.title_hausa:
            return self.title_hausa
        return self.title_hausa or self.title

    @property
    def alternate_title(self):
        lang = _active_lang()
        if lang == 'ar':
            return self.title_hausa or None
        if self.title:
            return self.title
        return None

    @property
    def language_code(self):
        if self.language:
            return self.language.code
        return None

    @property
    def language_label(self):
        if self.language:
            return self.language.name_native
        return None

    @property
    def language_direction(self):
        if self.language:
            return self.language.direction
        return 'ltr'

    @property
    def language_flag(self):
        if self.language and self.language.flag_emoji:
            return self.language.flag_emoji
        return ''

    @property
    def avg_rating(self):
        result = self.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(result, 1) if result else None

    def save(self, *args, **kwargs):
        if not self.language:
            self.language = Language.default()
        if not self.seo_slug and self.title_hausa:
            self.seo_slug = self.title_hausa.lower().replace(' ', '-')
        if not self.seo_title:
            self.seo_title = f"{self.title_hausa or self.title} - Littattafan Hausa"
        if not self.seo_description and self.description:
            self.seo_description = self.description[:200]
        super().save(*args, **kwargs)


class Feedback(models.Model):
    TYPE_CHOICES = [
        ('error', 'خطأ'),
        ('suggestion', 'اقتراح'),
        ('translation', 'ترجمة'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('reviewed', 'تمت المراجعة'),
        ('resolved', 'تم الحل'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='feedbacks', verbose_name='الكتاب')
    reporter_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='اسم المبلّغ')
    reporter_email = models.EmailField(blank=True, null=True, verbose_name='البريد الإلكتروني للمبلّغ')
    feedback_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='error', verbose_name='نوع الملاحظة')
    message = models.TextField(verbose_name='الرسالة')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='الحالة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'التقرير / الملاحظة'
        verbose_name_plural = 'التقارير والملاحظات'

    def __str__(self):
        return f"{self.feedback_type}: {self.book} - {self.message[:50]}"


# ====== NEW MODELS ======

class Favorite(models.Model):
    """User's favorite books"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='المستخدم')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='الكتاب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'المفضلة'
        verbose_name_plural = 'المفضلات'
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} → {self.book}"


class ReadingProgress(models.Model):
    """Track user's reading progress"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_progress', verbose_name='المستخدم')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='readers', verbose_name='الكتاب')
    current_page = models.IntegerField(default=1, verbose_name='الصفحة الحالية')
    total_pages = models.IntegerField(default=0, verbose_name='إجمالي الصفحات')
    last_read = models.DateTimeField(auto_now=True, verbose_name='آخر قراءة')

    class Meta:
        verbose_name = 'تقدم القراءة'
        verbose_name_plural = 'تقدم القراءة'
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book} (p.{self.current_page})"

    @property
    def progress_percent(self):
        if self.total_pages > 0:
            return int((self.current_page / self.total_pages) * 100)
        return 0


class AudioVersion(models.Model):
    """TTS audio version of a book"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='audio_versions', verbose_name='الكتاب')
    language = models.ForeignKey(
        Language,
        to_field='code',
        db_column='language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audio_versions',
        verbose_name='اللغة'
    )
    audio_file = models.FileField(upload_to=audio_file_path, blank=True, null=True, verbose_name='ملف الصوت')
    audio_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='رابط خارجي (Google Drive)')
    duration_seconds = models.IntegerField(default=0, verbose_name='المدة بالثواني')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'النسخة الصوتية'
        verbose_name_plural = 'النسخ الصوتية'

    def __str__(self):
        lang = self.language.code if self.language else 'N/A'
        return f"Audio: {self.book} ({lang})"

    @property
    def language_label(self):
        if self.language:
            return self.language.name_native
        return None

    @property
    def direct_audio_url(self):
        if self.audio_file:
            try:
                return self.audio_file.url
            except ValueError:
                pass
        if self.audio_url:
            if 'drive.google.com/file/d/' in self.audio_url:
                import re
                match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', self.audio_url)
                if match:
                    file_id = match.group(1)
                    return f'https://drive.google.com/uc?export=download&id={file_id}'
            return self.audio_url
        return None


class SocialPost(models.Model):
    """Track auto-published social media posts"""
    PLATFORM_CHOICES = [
        ('telegram', 'تيليجرام'),
        ('twitter', 'تويتر (X)'),
        ('facebook', 'فيسبوك'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='social_posts', verbose_name='الكتاب')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='المنصة')
    post_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='معرف المنشور')
    posted_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ النشر')
    success = models.BooleanField(default=True, verbose_name='تم بنجاح')
    error_message = models.TextField(blank=True, null=True, verbose_name='رسالة الخطأ')

    class Meta:
        verbose_name = 'منشور التواصل الاجتماعي'
        verbose_name_plural = 'منشورات التواصل الاجتماعي'

    def __str__(self):
        return f"{self.platform}: {self.book} ({'✅' if self.success else '❌'})"


class SearchLog(models.Model):
    """Track search queries for analytics"""
    query = models.CharField(max_length=500, verbose_name='نص البحث')
    results_count = models.IntegerField(default=0, verbose_name='عدد النتائج')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='المستخدم')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ البحث')

    class Meta:
        verbose_name = 'سجل البحث'
        verbose_name_plural = 'سجلات البحث'

    def __str__(self):
        return f"{self.query} ({self.results_count} results)"


class ScrapedBook(models.Model):
    """Books discovered by the smart scraper"""
    STATUS_CHOICES = [
        ('discovered', 'مكتشف'),
        ('verified', 'مؤكد'),
        ('rejected', 'مرفوض'),
        ('imported', 'تم الاستيراد'),
        ('failed', 'فشل'),
    ]

    source_url = models.URLField(max_length=191, unique=True, verbose_name='رابط المصدر')
    source_site = models.CharField(max_length=200, verbose_name='موقع المصدر')
    title = models.CharField(max_length=500, verbose_name='العنوان')
    author = models.CharField(max_length=300, blank=True, null=True, verbose_name='المؤلف')
    language = models.CharField(max_length=50, blank=True, null=True, verbose_name='اللغة')
    file_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name='رابط الملف')
    file_path = models.FileField(upload_to=scraped_file_path, blank=True, null=True, verbose_name='اسم الملف المحلي')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    ai_analysis = models.JSONField(default=dict, blank=True, verbose_name='تحليل الذكاء الاصطناعي')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='discovered', verbose_name='الحالة')
    imported_book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name='scraped_source', verbose_name='الكتاب المستورد')
    scraped_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ السحب')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'كتاب مسحوب'
        verbose_name_plural = 'الكتب المسحوبة'
        ordering = ['-scraped_at']

    def __str__(self):
        return f"[{self.status}] {self.title} ({self.source_site})"


class SovereignGlossary(models.Model):
    """Islamic terms translation glossary"""
    term_arabic = models.CharField(max_length=200, verbose_name='المصطلح بالعربي')
    term_hausa = models.CharField(max_length=200, verbose_name='المصطلح بالهوسا')
    term_english = models.CharField(max_length=200, blank=True, null=True, verbose_name='المصطلح بالإنجليزي')
    definition = models.TextField(blank=True, null=True, verbose_name='التعريف')
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name='التصنيف')

    class Meta:
        verbose_name = 'مصطلح ديني'
        verbose_name_plural = 'المصطلحات الدينية (Glossary)'
        unique_together = ('term_arabic', 'term_hausa')

    def __str__(self):
        return f"{self.term_arabic} → {self.term_hausa}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name='المستخدم')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews', verbose_name='الكتاب')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='التقييم')
    title = models.CharField(max_length=200, blank=True, verbose_name='عنوان التقييم')
    content = models.TextField(blank=True, verbose_name='محتوى التقييم')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'التقييم'
        verbose_name_plural = 'التقييمات'
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book} ({self.rating}★)"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name='المستخدم')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='comments', verbose_name='الكتاب')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies', verbose_name='الرد على')
    content = models.TextField(verbose_name='محتوى التعليق')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'التعليق'
        verbose_name_plural = 'التعليقات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} في {self.book} - {self.content[:50]}"


class ReadingList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_lists', verbose_name='المستخدم')
    name = models.CharField(max_length=200, verbose_name='اسم القائمة')
    description = models.TextField(blank=True, verbose_name='الوصف')
    books = models.ManyToManyField(Book, blank=True, related_name='in_lists', verbose_name='الكتب')
    is_public = models.BooleanField(default=False, verbose_name='عامة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'قائمة القراءة'
        verbose_name_plural = 'قوائم القراءة'

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_book', 'كتاب جديد'),
        ('review_reply', 'رد على تقييم'),
        ('comment_reply', 'رد على تعليق'),
        ('feedback_update', 'تحديث ملاحظة'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='المستخدم')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='نوع الإشعار')
    title = models.CharField(max_length=200, verbose_name='العنوان')
    message = models.TextField(verbose_name='الرسالة')
    link = models.CharField(max_length=500, blank=True, verbose_name='الرابط')
    is_read = models.BooleanField(default=False, verbose_name='تمت القراءة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'الإشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


@receiver(post_save, sender=SocialPost)
def auto_send_social_post(sender, instance, created, **kwargs):
    if not created or instance.platform != 'telegram':
        return

    import os
    import json
    import urllib.request

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        return

    book = instance.book
    title = book.title_hausa or book.title or ''
    author = book.author or ''
    category = book.category.name_arabic if book.category else 'عام'
    description = (book.description or '')[:300]
    tags = ' '.join('#' + t.replace(' ', '_') for t in (book.tags or [])[:5])
    slug = book.seo_slug or ''

    text = (
        f"📚 <b>{title}</b>\n\n"
        f"✍️ {author}\n"
        f"📂 {category}\n\n"
        f"{description}\n\n"
        f"🏷 {tags}\n\n"
        f"🔗 اقرأ المزيد: https://dj.mohamedwael.site/books/{slug}/"
    )

    try:
        api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }).encode()
        req = urllib.request.Request(api_url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
        SocialPost.objects.filter(pk=instance.pk).update(success=True)
    except Exception as e:
        SocialPost.objects.filter(pk=instance.pk).update(success=False, error_message=str(e))

# أضف هذا الكود في نهاية models.py (قبل أي شيء تاني)
# وأضف في أعلى الملف: import os  (إن لم يكن موجوداً)

def profile_avatar_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'profiles/avatars/{uuid.uuid4().hex}{ext}'


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ImageField(
        upload_to=profile_avatar_path,
        blank=True,
        null=True,
        verbose_name='الصورة الشخصية'
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='الدولة'
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='تاريخ الميلاد'
    )

    class Meta:
        verbose_name = 'الملف الشخصي للمستخدم'
        verbose_name_plural = 'الملفات الشخصية للمستخدمين'

    def __str__(self):
        return f"ملف: {self.user.username}"

    @property
    def avatar_url(self):
        if self.avatar:
            try:
                return self.avatar.url
            except ValueError:
                pass
        return None


# Signal: ƙirƙiri profile atomatik lokacin ƙirƙirar user
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)
