from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from .models import Category, Book, Feedback, Review, Comment, ReadingList, Notification
from .serializers import (
    CategorySerializer, BookListSerializer, BookDetailSerializer,
    BookCreateSerializer, FeedbackSerializer,
    ReviewSerializer, CommentSerializer, ReadingListSerializer, NotificationSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.annotate(book_count=Count('books', filter=Q(books__status='published')))
    serializer_class = CategorySerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('category', 'language').all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'title_hausa', 'author', 'description']
    ordering_fields = ['created_at', 'view_count', 'year']

    def get_serializer_class(self):
        if self.action == 'list':
            return BookListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return BookCreateSerializer
        return BookDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        language = self.request.query_params.get('language')
        book_status = self.request.query_params.get('status')

        if category:
            qs = qs.filter(category__slug=category)
        if language:
            qs = qs.filter(language__code=language)
        if book_status:
            qs = qs.filter(status=book_status)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Book.objects.filter(pk=instance.pk).update(view_count=instance.view_count + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        book = self.get_object()
        Book.objects.filter(pk=book.pk).update(download_count=book.download_count + 1)
        return Response({'file_url': book.file.url if book.file else None})

    @action(detail=True, methods=['post'])
    def generate_ai(self, request, pk=None):
        """Generate AI metadata for a specific book"""
        book = self.get_object()
        field = request.data.get('field', 'all')  # all, description, toc, tags, seo

        try:
            from .ai_service import (
                generate_all, generate_book_description,
                generate_table_of_contents, generate_tags,
                generate_seo, extract_text_from_pdf
            )
        except Exception as e:
            return Response({'error': f'AI service error: {str(e)}'}, status=500)

        # Extract text from PDF if available
        text_content = ""
        if book.file:
            text_content = extract_text_from_pdf(book.file.path)

        category_name = book.category.name_hausa if book.category else ""
        lang_code = book.language_code or 'ha'

        try:
            if field == 'all':
                result = generate_all(
                    book.title, book.title_hausa or "", book.author,
                    category_name, lang_code, text_content
                )
                book.description = result.get('description', book.description)
                book.table_of_contents = result.get('chapters', book.table_of_contents)
                book.tags = result.get('tags', book.tags)
                book.seo_title = result.get('seo_title', book.seo_title)
                book.seo_description = result.get('seo_description', book.seo_description)
                if not book.seo_slug:
                    book.seo_slug = result.get('slug') or result.get('seo_slug')
                book.save()
                return Response({'message': 'All AI metadata generated', 'data': result})

            elif field == 'description':
                desc = generate_book_description(
                    book.title, book.title_hausa or "", book.author,
                    category_name, text_content
                )
                book.description = desc
                book.save(update_fields=['description', 'updated_at'])
                return Response({'description': desc})

            elif field == 'toc':
                chapters = generate_table_of_contents(
                    book.title, book.title_hausa or "", book.author, text_content
                )
                book.table_of_contents = chapters
                book.save(update_fields=['table_of_contents', 'updated_at'])
                return Response({'chapters': chapters})

            elif field == 'tags':
                tags = generate_tags(
                    book.title, book.title_hausa or "", book.author,
                    book.description or "", category_name
                )
                book.tags = tags
                book.save(update_fields=['tags', 'updated_at'])
                return Response({'tags': tags})

            elif field == 'seo':
                seo = generate_seo(book.title, book.title_hausa or "", book.description or "")
                book.seo_title = seo.get('seo_title')
                book.seo_description = seo.get('seo_description')
                if not book.seo_slug:
                    book.seo_slug = seo.get('seo_slug')
                book.save(update_fields=['seo_title', 'seo_description', 'seo_slug', 'updated_at'])
                return Response(seo)

            else:
                return Response({'error': 'Invalid field. Use: all, description, toc, tags, seo'}, status=400)

        except Exception as e:
            return Response({'error': str(e)}, status=500)


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('book').all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related('user', 'book').all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        book_id = self.request.query_params.get('book')
        if book_id:
            qs = qs.filter(book_id=book_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('user', 'book').all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        book_id = self.request.query_params.get('book')
        if book_id:
            qs = qs.filter(book_id=book_id, parent__isnull=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReadingListViewSet(viewsets.ModelViewSet):
    serializer_class = ReadingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReadingList.objects.filter(user=self.request.user).prefetch_related('books')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_book(self, request, pk=None):
        reading_list = self.get_object()
        book_id = request.data.get('book_id')
        try:
            book = Book.objects.get(pk=book_id)
            reading_list.books.add(book)
            return Response({'success': True})
        except Book.DoesNotExist:
            return Response({'error': 'Book not found'}, status=404)

    @action(detail=True, methods=['post'])
    def remove_book(self, request, pk=None):
        reading_list = self.get_object()
        book_id = request.data.get('book_id')
        reading_list.books.remove(book_id)
        return Response({'success': True})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'success': True})


@api_view(['GET'])
def stats_view(request):
    books = Book.objects.all()
    data = {
        'total_books': books.count(),
        'published': books.filter(status='published').count(),
        'drafts': books.filter(status='draft').count(),
        'processing': books.filter(status='processing').count(),
        'total_views': books.aggregate(s=Sum('view_count'))['s'] or 0,
        'total_downloads': books.aggregate(s=Sum('download_count'))['s'] or 0,
        'total_authors': books.values('author').distinct().count(),
        'top_books': list(
            books.filter(status='published')
            .order_by('-view_count')[:10]
            .values('id', 'title', 'title_hausa', 'author', 'view_count')
        ),
        'by_category': list(
            Category.objects.annotate(count=Count('books'))
            .order_by('-count')
            .values('name_hausa', 'count')
        ),
    }
    return Response(data)


@api_view(['POST'])
def ai_generate_view(request):
    """Standalone AI generation (without saving to a book)"""
    try:
        from .ai_service import generate_all, get_ai_provider
    except Exception as e:
        return Response({'error': f'AI import error: {str(e)}'}, status=500)

    provider = get_ai_provider()
    if not provider:
        return Response({
            'error': 'No AI provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY in .env'
        }, status=400)

    title = request.data.get('title', '')
    title_hausa = request.data.get('title_hausa', '')
    author = request.data.get('author', '')
    category = request.data.get('category', '')
    language_code = request.data.get('language_code', 'ha')

    if not title and not title_hausa:
        return Response({'error': 'title or title_hausa is required'}, status=400)

    try:
        result = generate_all(title, title_hausa, author, category, language_code)
        result['ai_provider'] = provider
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
