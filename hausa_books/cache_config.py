"""
Cache configuration for production.
Add to settings.py:
    from hausa_books.cache_config import CACHES, CACHE_MIDDLEWARE_SECONDS
"""

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'TIMEOUT': 300,
        'OPTIONS': {
            'db': '1',
        }
    },
    'pages': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'TIMEOUT': 600,
    }
}

CACHE_MIDDLEWARE_SECONDS = 300

# View-level cache decorators to use:
# from django.views.decorators.cache import cache_page
# @cache_page(60 * 15)  # 15 minutes
# def book_list(request): ...

# Template fragment caching:
# {% load cache %}
# {% cache 600 book_card book.pk %}
#   ... book card HTML ...
# {% endcache %}
