import os
import re
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Sum, F, Case, When, Value, IntegerField
from django.core.paginator import Paginator
from django.utils import timezone, translation
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout, authenticate, get_user_model
from .forms import CustomUserCreationForm, ProfileEditForm
from django.contrib import messages
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import (
    Book, Category, Favorite, ReadingProgress, SearchLog, Feedback,
    Review, Comment, ReadingList, Notification,
)

# استخدام دالة جلب نموذج المستخدم لدعم النماذج المخصصة لاحقاً
User = get_user_model()


def _normalize_language(code: str | None) -> str:
    if not code:
        return 'ha'
    return code.split('-')[0]


def get_content_language(request, allow_all: bool = False) -> str:
    lang_param = request.GET.get('lang') or request.GET.get('language')
    if lang_param:
        lang_param = lang_param.strip().lower()
        if allow_all and lang_param == 'all':
            return 'all'
        return _normalize_language(lang_param)
    return _normalize_language(translation.get_language())


def _build_drive_embed_url(url: str | None) -> str:
    if not url:
        return ''

    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f'https://drive.google.com/file/d/{file_id}/preview'

    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f'https://drive.google.com/file/d/{file_id}/preview'

    return url


def home(request):
    content_language = get_content_language(request)
    category_filter = Q(language__code=content_language) | Q(language__isnull=True)
    categories = Category.objects.filter(category_filter).annotate(
        book_count=Count(
            'books',
            filter=Q(books__status='published', books__language__code=content_language)
        )
    )
    latest_books = (
        Book.objects.filter(
            status='published'
        ).filter(Q(language__code=content_language) | Q(language__isnull=True))
        .select_related('category', 'language', 'category__language')[:6]
    )
    stats = {
        'total_books': Book.objects.count(),
        'total_authors': Book.objects.values('author').distinct().count(),
        'total_published': Book.objects.filter(status='published', language__code=content_language).count(),
        'content_language': content_language,
    }
    return render(request, 'books/home.html', {
        'categories': categories,
        'latest_books': latest_books,
        'stats': stats,
        'content_language': content_language,
    })


def book_list(request):
    content_language = get_content_language(request, allow_all=True)
    books = Book.objects.filter(status='published').select_related('category', 'language', 'category__language')
    categories = Category.objects.all()

    if content_language != 'all':
        books = books.filter(Q(language__code=content_language) | Q(language__isnull=True))
        categories = categories.filter(Q(language__code=content_language) | Q(language__isnull=True))
        book_count_filter = Q(books__status='published', books__language__code=content_language)
    else:
        book_count_filter = Q(books__status='published')

    categories = categories.annotate(book_count=Count('books', filter=book_count_filter))

    category_slug = request.GET.get('category')
    q = request.GET.get('q')
    view_mode = request.GET.get('view', 'grid')

    if category_slug:
        books = books.filter(category__slug=category_slug)

    if q:
        title_exact = Q(title__iexact=q) | Q(title_hausa__iexact=q)
        title_match = Q(title__icontains=q) | Q(title_hausa__icontains=q)
        author_match = Q(author__icontains=q)
        desc_match = Q(description__icontains=q)
        tag_match = Q(tags__icontains=q)

        books = books.filter(title_match | author_match | desc_match | tag_match).annotate(
            search_rank=Case(
                When(title_exact, then=Value(4)),
                When(title_match, then=Value(3)),
                When(author_match, then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('-search_rank', '-created_at')

        SearchLog.objects.create(
            query=q, results_count=books.count(),
            user=request.user if request.user.is_authenticated else None
        )

    paginator = Paginator(books, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    favorite_ids = []
    if request.user.is_authenticated:
        favorite_ids = list(request.user.favorites.values_list('book_id', flat=True))

    sort_value = request.GET.get('sort', '')

    return render(request, 'books/book_list.html', {
        'books': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'current_category': category_slug,
        'search_query': q or '',
        'view_mode': view_mode,
        'favorite_ids': favorite_ids,
        'current_language_filter': content_language,
        'current_language': content_language,
        'sort': sort_value,
        'has_next': page_obj.has_next(),
    })


def book_detail(request, slug):
    book = get_object_or_404(
        Book.objects.select_related('language', 'category', 'category__language'),
        seo_slug=slug,
        status='published'
    )
    
    # تحديث العداد باستخدام F لحل مشكلة حالة التسابق (Race Condition)
    Book.objects.filter(pk=book.pk).update(view_count=F('view_count') + 1)
    
    related = book.related_books.filter(status='published')
    if book.language_code:
        related = related.filter(Q(language__code=book.language_code) | Q(language__isnull=True))
    related = related.select_related('language', 'category')[:4]

    is_favorite = False
    reading = None
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, book=book).exists()
        reading = ReadingProgress.objects.filter(user=request.user, book=book).first()

    reviews = book.reviews.select_related('user').order_by('-created_at')
    review_count = reviews.count()
    avg_rating = book.avg_rating
    comments = book.comments.filter(parent__isnull=True).select_related('user').prefetch_related('replies__user')
    user_review = None
    if request.user.is_authenticated:
        user_review = book.reviews.filter(user=request.user).first()

    return render(request, 'books/book_detail.html', {
        'book': book,
        'related': related,
        'is_favorite': is_favorite,
        'reading': reading,
        'reviews': reviews,
        'review_count': review_count,
        'avg_rating': avg_rating,
        'comments': comments,
        'user_review': user_review,
    })


def book_read(request, slug):
    """قارئ ملفات الـ PDF المدمج"""
    book = get_object_or_404(
        Book.objects.select_related('language', 'category', 'category__language'),
        seo_slug=slug,
        status='published'
    )
    if not book.file and not book.drive_url:
        messages.error(request, 'Wannan littafin ba shi da fayil na PDF ko Google Drive link.')
        return redirect('books:book_detail', slug=slug)

    reading = None
    if request.user.is_authenticated:
        reading, _ = ReadingProgress.objects.get_or_create(
            user=request.user, book=book
        )

    drive_embed_url = _build_drive_embed_url(book.drive_url)

    total_pages = reading.total_pages if reading and reading.total_pages else 0
    if total_pages == 0 and book.file and os.path.exists(book.file.path):
        try:
            import PyPDF2
            with open(book.file.path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
        except Exception:
            total_pages = 0

    return render(request, 'books/book_read.html', {
        'book': book,
        'reading': reading,
        'total_pages': total_pages,
        'drive_embed_url': drive_embed_url,
    })


@require_POST
def save_reading_progress(request, slug):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Dole ne a shiga (Login required)'}, status=401)
    book = get_object_or_404(Book, seo_slug=slug)
    page = int(request.POST.get('page', 1))
    total = int(request.POST.get('total', 0))
    progress, _ = ReadingProgress.objects.get_or_create(user=request.user, book=book)
    progress.current_page = page
    if total > 0:
        progress.total_pages = total
    progress.save()
    return JsonResponse({'success': True, 'page': page, 'percent': progress.progress_percent})


@require_POST
@login_required
def toggle_favorite(request, slug):
    book = get_object_or_404(Book, seo_slug=slug)
    fav, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if not created:
        fav.delete()
        return JsonResponse({'favorited': False})
    return JsonResponse({'favorited': True})


def category_list(request):
    content_language = get_content_language(request, allow_all=True)
    categories = Category.objects.all()
    if content_language != 'all':
        categories = categories.filter(Q(language__code=content_language) | Q(language__isnull=True))
        book_filter = Q(books__status='published', books__language__code=content_language)
    else:
        book_filter = Q(books__status='published')
    categories = categories.annotate(book_count=Count('books', filter=book_filter))
    return render(request, 'books/category_list.html', {
        'categories': categories,
        'content_language': content_language,
    })


def about(request):
    return render(request, 'books/about.html')


# ====== عروض المصادقة والتسجيل (AUTH VIEWS) ======

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'An ƙirƙiri asusu! Barka da zuwa.')
            return redirect('books:home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, 'Sunan mai amfani ko kalmar sirri ba daidai ba.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('books:home')


@login_required
def profile_view(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book', 'book__category')[:20]
    reading = ReadingProgress.objects.filter(user=request.user).select_related('book').order_by('-last_read')[:10]
    reading_lists = ReadingList.objects.filter(user=request.user).prefetch_related('books')
    return render(request, 'accounts/profile.html', {
        'favorites': favorites,
        'reading_list': reading,
        'reading_lists': reading_lists,
    })


# ====== التقييمات والتعليقات (REVIEWS & COMMENTS) ======

@require_POST
@login_required
def submit_review(request, slug):
    book = get_object_or_404(Book, seo_slug=slug, status='published')
    rating = int(request.POST.get('rating', 0))
    if rating < 1 or rating > 5:
        messages.error(request, 'Rating dole ne ya kasance tsakanin 1 zuwa 5.')
        return redirect('books:book_detail', slug=slug)

    review, created = Review.objects.update_or_create(
        user=request.user, book=book,
        defaults={
            'rating': rating,
            'title': request.POST.get('title', ''),
            'content': request.POST.get('content', ''),
        }
    )
    messages.success(request, 'An ajiye bitar ku!' if created else 'An sabunta bitar ku!')
    return redirect('books:book_detail', slug=slug)


@require_POST
@login_required
def add_comment(request, slug):
    book = get_object_or_404(Book, seo_slug=slug, status='published')
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')
    if not content:
        messages.error(request, 'Sharhi ba zai iya zama fanko ba.')
        return redirect('books:book_detail', slug=slug)

    parent = None
    if parent_id:
        parent = Comment.objects.filter(pk=parent_id, book=book).first()

    Comment.objects.create(
        user=request.user, book=book, parent=parent, content=content
    )

    if parent and parent.user != request.user:
        Notification.objects.create(
            user=parent.user,
            notification_type='comment_reply',
            title=f'{request.user.username} ya amsa sharhinku',
            message=content[:200],
            link=f'/books/{slug}/',
        )

    messages.success(request, 'An ƙara sharhi!')
    return redirect('books:book_detail', slug=slug)


# ====== قوائم القراءة (READING LISTS) ======

@login_required
def create_reading_list(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Suna yana da mahimmanci.')
            return redirect('books:profile')
        ReadingList.objects.create(
            user=request.user,
            name=name,
            description=request.POST.get('description', ''),
            is_public=request.POST.get('is_public') == 'on',
        )
        messages.success(request, 'An ƙirƙiri jerin karatu!')
    return redirect('books:profile')


@require_POST
@login_required
def add_to_reading_list(request, list_id, slug):
    reading_list = get_object_or_404(ReadingList, pk=list_id, user=request.user)
    book = get_object_or_404(Book, seo_slug=slug, status='published')
    reading_list.books.add(book)
    return JsonResponse({'success': True})


@require_POST
@login_required
def remove_from_reading_list(request, list_id, slug):
    reading_list = get_object_or_404(ReadingList, pk=list_id, user=request.user)
    book = get_object_or_404(Book, seo_slug=slug, status='published')
    reading_list.books.remove(book)
    return JsonResponse({'success': True})


@login_required
def reading_list_detail(request, list_id):
    reading_list = get_object_or_404(ReadingList, pk=list_id)
    if not reading_list.is_public and reading_list.user != request.user:
        return redirect('books:home')
    books = reading_list.books.filter(status='published').select_related('category')
    return render(request, 'accounts/reading_list_detail.html', {
        'reading_list': reading_list,
        'books': books,
        'is_owner': reading_list.user == request.user,
    })


# ====== الإشعارات (NOTIFICATIONS) ======

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    return render(request, 'books/notifications.html', {
        'notifications': notifications,
    })


@require_POST
@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('books:notifications')


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('books:notifications')


def unread_notification_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ====== لوحة الإحصائيات (ANALYTICS DASHBOARD) ======

@staff_member_required # استخدام مزخرف جانغو الأمني بدلاً من الفحص اليدوي
def analytics_dashboard(request):
    books = Book.objects.all()
    top_books = books.filter(status='published').order_by('-view_count')[:10]
    top_searches = (
        SearchLog.objects.values('query')
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )
    recent_feedback = Feedback.objects.select_related('book').order_by('-created_at')[:10]

    daily_views = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        count = SearchLog.objects.filter(created_at__date=day).count()
        daily_views.append({'date': day.strftime('%m/%d'), 'count': count})

    stats = {
        'total_books': books.count(),
        'published': books.filter(status='published').count(),
        'drafts': books.filter(status='draft').count(),
        'total_views': books.aggregate(s=Sum('view_count'))['s'] or 0,
        'total_users': User.objects.count(),
        'total_favorites': Favorite.objects.count(),
        'pending_feedback': Feedback.objects.filter(status='pending').count(),
    }

    return render(request, 'books/analytics.html', {
        'stats': stats,
        'top_books': top_books,
        'top_searches': top_searches,
        'recent_feedback': recent_feedback,
        'daily_views': daily_views,
    })


# ====== تحميل الكتب (BOOK DOWNLOAD) ======

def _find_file_path(file_field):
    if not file_field:
        return None

    file_name = str(file_field).replace('\\', '/')

    if os.path.isabs(file_name) or ':/' in file_name:
        file_name = os.path.basename(file_name)
        file_path = os.path.join(settings.MEDIA_ROOT, 'books', 'files', file_name)
    else:
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)

    # إضافة فحص أمان (Security Check) لمنع عبور الدليل (Path Traversal)
    file_path = os.path.abspath(file_path)
    safe_media_root = os.path.abspath(settings.MEDIA_ROOT)
    
    if not file_path.startswith(safe_media_root):
        return None

    if os.path.exists(file_path):
        return file_path

    directory = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)

    if not os.path.exists(directory):
        return None

    prefix = base_name[:40]
    candidates = [f for f in os.listdir(directory) if f.startswith(prefix)]

    if candidates:
        best = max(candidates, key=len)
        return os.path.join(directory, best)

    return None


def book_download(request, slug):
    book = get_object_or_404(Book, seo_slug=slug, status='published')

    if not book.file:
        raise Http404

    # تحديث العداد بطريقة آمنة باستخدام F لمنع تضارب البيانات
    Book.objects.filter(pk=book.pk).update(download_count=F('download_count') + 1)

    file_path = _find_file_path(book.file)

    if not file_path or not os.path.exists(file_path):
        messages.error(request, 'Fayil ɗin PDF ɗin ba a samu ba a cikin sabar.')
        return redirect('books:book_detail', slug=slug)

    correct_relative = os.path.relpath(file_path, settings.MEDIA_ROOT).replace('\\', '/')
    current_name = str(book.file).replace('\\', '/')
    if current_name != correct_relative:
        Book.objects.filter(pk=book.pk).update(file=correct_relative)

    safe_filename = f"{slug}.pdf"
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=safe_filename,
    )




    # ضع هذا الكود في views.py
# 1. أضف ProfileEditForm في الـ import الموجود:
#    from .forms import CustomUserCreationForm, ProfileEditForm

# 2. استبدل profile_view الحالي بالكود التالي:

@login_required
def profile_view(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book', 'book__category')[:20]
    reading = ReadingProgress.objects.filter(user=request.user).select_related('book').order_by('-last_read')[:10]
    reading_lists = ReadingList.objects.filter(user=request.user).prefetch_related('books')
    return render(request, 'accounts/profile.html', {
        'favorites': favorites,
        'reading_list': reading,
        'reading_lists': reading_lists,
    })


# في views.py:
# 1. أضف في الـ imports:
#    
# 2. استبدل profile_edit_view بالكود التالي:

@login_required
def profile_edit_view(request):
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        form = ProfileEditForm(request.user, request.POST, files=request.FILES)
        if form.is_valid():
            user = form.save(files=request.FILES)
            # لو غيّر كلمة المرور نحدث الـ session
            if form.cleaned_data.get('new_password'):
                update_session_auth_hash(request, user)
            messages.success(request, 'An sabunta bayananka da nasara! ✅')
            return redirect('books:profile_edit')
    else:
        form = ProfileEditForm(request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})



    # في views.py:
# 1. أضف في الـ imports:
#    from .forms import CustomUserCreationForm, ProfileEditForm
#    from .models import (..., UserProfile)

# 2. استبدل profile_edit_view بالكود التالي:

@login_required
def profile_edit_view(request):
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        form = ProfileEditForm(request.user, request.POST, files=request.FILES)
        if form.is_valid():
            user = form.save(files=request.FILES)
            # لو غيّر كلمة المرور نحدث الـ session
            if form.cleaned_data.get('new_password'):
                update_session_auth_hash(request, user)
            messages.success(request, 'An sabunta bayananka da nasara! ✅')
            return redirect('books:profile_edit')
    else:
        form = ProfileEditForm(request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})
