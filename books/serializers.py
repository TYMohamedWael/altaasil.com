from rest_framework import serializers
from .models import Category, Book, Feedback, AudioVersion, Review, Comment, ReadingList, Notification, Language


class CategorySerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = '__all__'


class BookListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_hausa', read_only=True, default=None)

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'title_hausa', 'author', 'translator',
            'category', 'category_name', 'category_specific',
            'description', 'tags', 'language', 'year',
            'status', 'approved', 'cover', 'view_count', 'created_at',
        ]


class BookDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name_hausa', read_only=True, default=None)
    category_slug = serializers.CharField(source='category.slug', read_only=True, default=None)
    related_books = BookListSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = '__all__'


class BookCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            'title', 'title_hausa', 'author', 'translator',
            'category', 'category_specific',
            'description', 'table_of_contents', 'tags',
            'language', 'year', 'file', 'cover', 'approved',
            'seo_title', 'seo_description', 'seo_slug',
        ]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = '__all__'


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user', 'username', 'book', 'rating', 'title', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user']


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'username', 'book', 'parent', 'content', 'created_at', 'replies']
        read_only_fields = ['user']

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []


class ReadingListSerializer(serializers.ModelSerializer):
    books = BookListSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ReadingList
        fields = ['id', 'user', 'username', 'name', 'description', 'books', 'is_public', 'created_at']
        read_only_fields = ['user']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'link', 'is_read', 'created_at']
