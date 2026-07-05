# books/services/cache.py
from django.core.cache import cache
from django.db.models import Q

TTL_SHORT = 60 * 5  # 5 minutes

def get_master_books(lang='ha'):
    """
    الكتب الأساسية (Master) المنشورة المخزنة مؤقتاً للصفحة الرئيسية.
    """
    key = f"books:master:{lang}"
    books = cache.get(key)
    if books is None:
        from ..models import Book
        books = list(
            Book.objects.filter(status='published', is_master=True)
            .filter(Q(language__code=lang) | Q(language__isnull=True))
            .select_related('category', 'language')
        )
        cache.set(key, books, TTL_SHORT)
    return books

def invalidate_book_caches(lang=None):
    """
    إبطال وحذف الكاش عند إضافة/تعديل/حذف كتاب.
    """
    langs = ['ha', 'ar', 'en', 'am', 'sw', 'all']
    for l in langs:
        # مسح كاش الكتب الأساسية للغة المعنية
        cache.delete(f"books:master:{l}")
