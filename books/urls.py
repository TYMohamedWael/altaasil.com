from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('', views.home, name='home'),
    path('books/', views.book_list, name='book_list'),
    path('books/<slug:slug>/', views.book_detail, name='book_detail'),
    path('books/<slug:slug>/read/', views.book_read, name='book_read'),
    path('books/<slug:slug>/progress/', views.save_reading_progress, name='save_progress'),
    path('books/<slug:slug>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('categories/', views.category_list, name='category_list'),
    path('about/', views.about, name='about'),
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    # Reviews & Comments
    path('books/<slug:slug>/review/', views.submit_review, name='submit_review'),
    path('books/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    # Reading Lists
    path('reading-lists/create/', views.create_reading_list, name='create_reading_list'),
    path('reading-lists/<int:list_id>/add/<slug:slug>/', views.add_to_reading_list, name='add_to_reading_list'),
    path('reading-lists/<int:list_id>/remove/<slug:slug>/', views.remove_from_reading_list, name='remove_from_reading_list'),
    path('reading-lists/<int:list_id>/', views.reading_list_detail, name='reading_list_detail'),
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
    # Analytics
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('books/<slug:slug>/download/', views.book_download, name='book_download'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

]
