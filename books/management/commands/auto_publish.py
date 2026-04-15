"""Auto-publish new books to Telegram"""
import os
import logging
from django.core.management.base import BaseCommand
from books.models import Book, SocialPost

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Auto-publish new books to Telegram'

    def handle(self, *args, **options):
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        if not bot_token or not chat_id:
            self.stdout.write(self.style.WARNING(
                'Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env'
            ))
            return

        # Find published books not yet posted to Telegram
        posted_ids = SocialPost.objects.filter(
            platform='telegram', success=True
        ).values_list('book_id', flat=True)

        new_books = Book.objects.filter(
            status='published'
        ).exclude(id__in=posted_ids)

        if not new_books.exists():
            self.stdout.write('No new books to publish.')
            return

        import urllib.request
        import json

        for book in new_books:
            text = f"""📚 *{book.title_hausa or book.title}*

✍️ {book.author}
📂 {book.category.name_hausa if book.category else 'Gabaɗaya'}

{(book.description or '')[:300]}

🏷️ {' '.join('#' + t.replace(' ', '_') for t in (book.tags or [])[:5])}

🔗 Karanta: http://localhost:8000/books/{book.seo_slug}/"""

            try:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                data = json.dumps({
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'Markdown'
                }).encode()
                req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req)

                SocialPost.objects.create(book=book, platform='telegram', success=True)
                self.stdout.write(self.style.SUCCESS(f'✅ Published: {book.title_hausa}'))

            except Exception as e:
                SocialPost.objects.create(book=book, platform='telegram', success=False, error_message=str(e))
                self.stdout.write(self.style.ERROR(f'❌ Failed: {book.title_hausa} - {e}'))
