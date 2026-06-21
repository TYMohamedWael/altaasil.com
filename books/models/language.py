"""
books/models/language.py
نموذج اللغة — Language model for multilingual support.

Stores supported languages with their direction, flag, and display order.
"""

from django.db import models

from ..constants import DIRECTION_CHOICES, FALLBACK_LANGUAGES


# ═══════════════════════════════════════════════════════════════════════════════
# Language / اللغة
# ═══════════════════════════════════════════════════════════════════════════════

class Language(models.Model):
    """
    Represents a supported language on the platform.
    يمثل لغة مدعومة في المنصة.
    """

    code = models.CharField(max_length=10, unique=True, help_text='ISO code e.g. ha, ar, en', verbose_name='الرمز')
    name_native = models.CharField(max_length=100, verbose_name='الاسم (أصلي)')
    name_english = models.CharField(max_length=100, verbose_name='الاسم (إنجليزي)')
    flag_emoji = models.CharField(max_length=8, blank=True, null=True, verbose_name='العلم')
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, default='ltr', verbose_name='الاتجاه')
    is_active = models.BooleanField(default=True, verbose_name='نشطة')
    is_default = models.BooleanField(default=False, verbose_name='افتراضية')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='الترتيب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'لغة'
        verbose_name_plural = 'اللغات'
        ordering = ['order', 'name_native']

    def __str__(self):
        return f"{self.name_native} ({self.code})"

    def save(self, *args, **kwargs):
        """Ensure only one language can be the default at a time."""
        if self.is_default:
            Language.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def default(cls):
        """Return the default Language instance, falling back to the first one."""
        lang = cls.objects.filter(is_default=True).first()
        if not lang:
            lang = cls.objects.first()
        return lang

    @property
    def label(self):
        """Display label with optional flag emoji."""
        flag = f"{self.flag_emoji} " if self.flag_emoji else ''
        return f"{flag}{self.name_native}"

    @staticmethod
    def fallback_languages():
        """Hard-coded language list used when the DB table is empty."""
        return FALLBACK_LANGUAGES
