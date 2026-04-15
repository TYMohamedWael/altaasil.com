"""Generate TTS audio for books using gTTS (free)"""
import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from books.models import Book, AudioVersion


class Command(BaseCommand):
    help = 'Generate audio (TTS) for books using gTTS'

    def add_arguments(self, parser):
        parser.add_argument('--book-id', type=int, help='Specific book ID')
        parser.add_argument('--language', default='ha', help='Language code (ha, ar, en)')

    def handle(self, *args, **options):
        try:
            from gtts import gTTS
        except ImportError:
            self.stdout.write(self.style.ERROR('Install gTTS: pip install gTTS'))
            return

        book_id = options.get('book_id')
        lang = options['language']

        if book_id:
            books = Book.objects.filter(id=book_id)
        else:
            # Books with descriptions but no audio
            existing = AudioVersion.objects.values_list('book_id', flat=True)
            books = Book.objects.filter(
                status='published', description__isnull=False
            ).exclude(id__in=existing)[:5]

        for book in books:
            text = f"{book.title_hausa or book.title}. {book.description or ''}"
            if not text.strip():
                continue

            self.stdout.write(f'Generating audio for: {book.title_hausa}...')

            try:
                # Map language codes
                tts_lang = {'ha': 'en', 'ar': 'ar', 'en': 'en', 'fr': 'fr'}.get(lang, 'en')
                tts = gTTS(text=text[:5000], lang=tts_lang, slow=False)

                # Save to bytes
                import io
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)

                audio = AudioVersion(book=book, language=lang)
                filename = f"{book.seo_slug or book.id}_{lang}.mp3"
                audio.audio_file.save(filename, ContentFile(audio_buffer.read()))
                audio.save()

                self.stdout.write(self.style.SUCCESS(f'✅ Audio created: {filename}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Failed: {book.title_hausa} - {e}'))
