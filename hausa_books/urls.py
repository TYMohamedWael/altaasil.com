from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from rest_framework.routers import DefaultRouter
from books.views_api import (
    CategoryViewSet, BookViewSet, FeedbackViewSet, stats_view, ai_generate_view,
    ReviewViewSet, CommentViewSet, ReadingListViewSet, NotificationViewSet,
)




router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'books', BookViewSet)
router.register(r'feedback', FeedbackViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'reading-lists', ReadingListViewSet, basename='readinglist')
router.register(r'notifications', NotificationViewSet, basename='notification')

# Non-i18n URLs (API, admin, language switching)
urlpatterns = [
    path('api/', include(router.urls)),
    path('api/stats/', stats_view, name='api-stats'),
    path('api/ai/generate/', ai_generate_view, name='api-ai-generate'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
]

# i18n URLs (user-facing pages)
urlpatterns += i18n_patterns(
    path('admin/rosetta/', include('rosetta.urls')),
    path('admin/', admin.site.urls),
    path('', include('books.urls')),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
