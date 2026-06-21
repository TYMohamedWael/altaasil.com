"""
إعدادات Django Unfold Admin
Littattafan Hausa — Islamic Library
"""

from django.conf.locale import LANG_INFO
from django.urls import reverse_lazy

LANG_INFO.update({
    "ha": {"bidi": False, "code": "ha", "name": "Hausa", "name_local": "Hausa"},
    "am": {"bidi": False, "code": "am", "name": "Amharic", "name_local": "አማርኛ"},
    "sw": {"bidi": False, "code": "sw", "name": "Swahili", "name_local": "Kiswahili"},
})


def _perm(perm):
    return lambda request: request.user.has_perm(perm)


def _staff(request):
    return request.user.is_staff


def _super(request):
    return request.user.is_superuser


SIDEBAR_NAVIGATION = [

    # ─── 📚 الكتب والمحتوى ──────────────────────────────────────────────────
    {
        "title": "📚 الكتب والمحتوى",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "الكتب", "icon": "menu_book",
             "link": "/admin/books/book/", "permission": _perm("books.view_book")},
            {"title": "التصنيفات", "icon": "category",
             "link": "/admin/books/category/", "permission": _perm("books.view_category")},
            {"title": "اللغات", "icon": "language",
             "link": "/admin/books/language/", "permission": _perm("books.view_language")},
            {"title": "النسخ الصوتية", "icon": "headphones",
             "link": "/admin/books/audioversion/", "permission": _perm("books.view_audioversion")},
            {"title": "نصوص الموقع", "icon": "text_fields",
             "link": "/admin/books/sitetext/", "permission": _perm("books.view_sitetext")},
            {"title": "المصطلحات", "icon": "translate",
             "link": "/admin/books/sovereignglossary/", "permission": _perm("books.view_sovereignglossary")},
            {"title": "مهمات التوليد", "icon": "smart_toy",
             "link": "/admin/books/bulkgenerationjob/", "permission": _staff},
        ],
    },

    # ─── 📄 الصفحات والقوائم ────────────────────────────────────────────────
    {
        "title": "📄 الصفحات والقوائم",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "الصفحات", "icon": "description",
             "link": "/admin/books/page/", "permission": _perm("books.view_page")},
            {"title": "القوائم", "icon": "menu",
             "link": "/admin/books/menu/", "permission": _perm("books.view_menu")},
            {"title": "عناصر القوائم", "icon": "list",
             "link": "/admin/books/menuitem/", "permission": _perm("books.view_menuitem")},
        ],
    },

    # ─── 👥 التفاعلات ──────────────────────────────────────────────────────
    {
        "title": "👥 التفاعلات",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "المفضلة", "icon": "favorite",
             "link": "/admin/books/favorite/", "permission": _perm("books.view_favorite")},
            {"title": "تقدم القراءة", "icon": "auto_stories",
             "link": "/admin/books/readingprogress/", "permission": _perm("books.view_readingprogress")},
            {"title": "التعليقات", "icon": "comment",
             "link": "/admin/books/comment/", "permission": _perm("books.view_comment")},
            {"title": "المراجعات", "icon": "rate_review",
             "link": "/admin/books/review/", "permission": _perm("books.view_review")},
            {"title": "قوائم القراءة", "icon": "bookmark",
             "link": "/admin/books/readinglist/", "permission": _perm("books.view_readinglist")},
            {"title": "الإشعارات", "icon": "notifications",
             "link": "/admin/books/notification/", "permission": _perm("books.view_notification")},
        ],
    },

    # ─── 📊 التحليلات والبيانات ────────────────────────────────────────────
    {
        "title": "📊 التحليلات والبيانات",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "سجل البحث", "icon": "search",
             "link": "/admin/books/searchlog/", "permission": _perm("books.view_searchlog")},
            {"title": "المنشورات الاجتماعية", "icon": "share",
             "link": "/admin/books/socialpost/", "permission": _perm("books.view_socialpost")},
        ],
    },

    # ─── 🔍 البحث والجلب ───────────────────────────────────────────────────
    {
        "title": "🔍 البحث والجلب",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "تخزين الكتب (جديد)", "icon": "cloud_download", "link": reverse_lazy("admin:search_books_crawljob_new_search"), "permission": _staff},
            {"title": "عملية البحث", "icon": "search", "link": reverse_lazy("admin:search_books_localsearchjob_new_search"), "permission": _staff},
            {"title": "تصنيفات المصادر", "icon": "category", "link": reverse_lazy("admin:search_books_sourcecategory_changelist"), "permission": _staff},
            {"title": "فهرس الكتب المجمعة", "icon": "library_books", "link": reverse_lazy("admin:search_books_bookindex_changelist"), "permission": _staff},
            {"title": "الكتب المكتشفة", "icon": "find_in_page", "link": reverse_lazy("admin:search_books_crawljobbook_changelist"), "permission": _staff},
            {"title": "سجلات عمليات التخزين", "icon": "history", "link": reverse_lazy("admin:search_books_crawljob_changelist"), "permission": _staff},
            {"title": "سجلات عمليات البحث", "icon": "history", "link": reverse_lazy("admin:search_books_localsearchjob_changelist"), "permission": _staff},
            {"title": "جدولة البحث", "icon": "schedule", "link": reverse_lazy("admin:search_books_scheduledsearch_changelist"), "badge": "search_books.context_processors.scheduled_search_count", "permission": _super},
        ],
    },

    # ─── 📄 استخراج النصوص ─────────────────────────────────────────────────
    {
        "title": "📄 استخراج النصوص",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "استخراج النص", "icon": "text_snippet",
             "link": "/admin/pdf-extractor-tool/", "permission": _staff},
            {"title": "مصحح الآيات القرآنية", "icon": "auto_fix_high",
             "link": "/admin/quran-corrector-tool/", "permission": _staff},
            {"title": "كتب PDF", "icon": "picture_as_pdf",
             "link": "/admin/pdf_extractor/book/", "permission": _staff},
            {"title": "أدوات الاستخراج", "icon": "build",
             "link": "/admin/pdf_extractor/extractiontool/", "permission": _super},
            {"title": "جداول الاستخراج", "icon": "event",
             "link": "/admin/pdf_extractor/extractionschedule/", "permission": _staff},
        ],
    },

    # ─── 🌍 فصل الترجمة ─────────────────────────────────────────
    {
        "title": "🌍 الترجمة",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "لوحة الترجمة", "icon": "translate",
             "link": "/ha/translation-separator/", "permission": _staff},
            {"title": "مهام الترجمة", "icon": "translate",
             "link": "/admin/book_translator/translationjob/", "permission": _staff},
            {"title": "أدوات الترجمة", "icon": "g_translate",
             "link": "/admin/book_translator/translationtool/", "permission": _super},
            {"title": "ذاكرة الترجمة", "icon": "memory",
             "link": "/admin/book_translator/translationmemory/", "permission": _super},
            {"title": "لوحة الفصل", "icon": "dashboard",
             "link": "/ha/translation-separator/separator/", "permission": _staff},
            {"title": "الملفات المترجمة", "icon": "translate",
             "link": "/admin/book_translator/translationfile/", "permission": _staff},
            {"title": "نتائج الفصل", "icon": "format_list_bulleted",
             "link": "/admin/book_translator/separationresult/", "permission": _staff},
            {"title": "نتائج الصفحات", "icon": "description",
             "link": "/admin/book_translator/pageresult/", "permission": _staff},
        ],
    },

    # ─── 🌐 اللغات والترجمات ──────────────────────────────────────────────
    {
        "title": "🌐 اللغات والترجمات",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "ترجمات الموقع (Rosetta)", "icon": "g_translate",
             "link": "/admin/rosetta/", "permission": _super},
        ],
    },

     {
        "title": "✅ المراجعة",
        "separator": True,
        "collapsible": True,
        "items": [
            {
                "title": "مراجعات الترجمة",
                "icon": "rate_review",
                "link": "/admin/books_review/translationreview/",
                "badge": "books_review.utils.pending_reviews_badge",
                "permission": _staff,
            },
            {
                "title": "مراجعة استخراج النصوص",
                "icon": "fact_check",
                "link": "/admin/pdf_extractor/extractedcontent/",
                "permission": _staff,
            },
            {
                "title": "مراجعة نتائج البحث",
                "icon": "spellcheck",
                "link": "/admin/search_books/pendingbook/",
                "badge": "search_books.context_processors.admin_pending_count",
                "permission": _staff,
            },
            {
                "title": "التعليقات",
                "icon": "comment",
                "link": "/admin/books_review/reviewcomment/",
                "permission": _staff,
            },
        ],
    },

    # ─── ⚙️ النظام ─────────────────────────────────────────────────────────
    {
        "title": "⚙️ النظام",
        "separator": True,
        "collapsible": True,
        "items": [
            {"title": "المستخدمين", "icon": "people",
             "link": "/admin/auth/user/", "permission": _perm("auth.view_user")},
            {"title": "المجموعات", "icon": "groups",
             "link": "/admin/auth/group/", "permission": _perm("auth.view_group")},
        ],
    },
]


UNFOLD = {
    "SITE_TITLE": "إدارة الموقع",
    "SITE_HEADER": "Littattafan Hausa",
    "SITE_SUBHEADER": "Dakin Karatu na Ilimi na Musulunci",
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": lambda request: "/static/images/logo.svg",
        "dark": lambda request: "/static/images/logo.svg",
    },
    "SITE_SYMBOL": "menu_book",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "ENVIRONMENT": "unfold.environment.default",
    "THEME": "light",
    "BORDER_RADIUS": "6px",

    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "31 41 55",
            "default-dark": "243 244 246",
            "important-light": "26 86 50",
            "important-dark": "200 168 78",
        },
        "primary": {
            "50": "240 253 244",
            "100": "220 252 231",
            "200": "187 247 208",
            "300": "134 239 172",
            "400": "74 222 128",
            "500": "26 86 50",
            "600": "22 73 42",
            "700": "15 61 34",
            "800": "12 48 27",
            "900": "8 36 20",
            "950": "4 24 13",
        },
    },

    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "ha": "🇳🇬",
                "ar": "🇸🇦",
                "en": "🇬🇧",
                "am": "🇪🇹",
                "sw": "🇰🇪",
            },
        },
    },

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": SIDEBAR_NAVIGATION,
    },
}
