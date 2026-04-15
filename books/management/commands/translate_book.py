"""Translate Arabic books to Hausa using AI with Sovereign Glossary"""
import os
import json
from django.core.management.base import BaseCommand
from books.models import Book, SovereignGlossary


class Command(BaseCommand):
    help = 'Translate Arabic book descriptions/content to Hausa using AI'

    def add_arguments(self, parser):
        parser.add_argument('--book-id', type=int, help='Specific book ID')

    def handle(self, *args, **options):
        try:
            from books.ai_service import call_ai, parse_json_response, get_ai_provider
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'AI service error: {e}'))
            return

        provider = get_ai_provider()
        if not provider:
            self.stdout.write(self.style.ERROR('Set OPENAI_API_KEY or GEMINI_API_KEY in .env'))
            return

        # Load sovereign glossary
        glossary_terms = list(
            SovereignGlossary.objects.values_list('term_arabic', 'term_hausa')
        )
        glossary_text = ""
        if glossary_terms:
            glossary_text = "SOVEREIGN GLOSSARY (must use these exact translations):\n"
            for ar, ha in glossary_terms[:50]:
                glossary_text += f"  {ar} → {ha}\n"

        book_id = options.get('book_id')
        if book_id:
            books = Book.objects.filter(id=book_id, language='ar')
        else:
            books = Book.objects.filter(
                language='ar', status='published', title_hausa__isnull=True
            )[:5]

        for book in books:
            self.stdout.write(f'Translating: {book.title}...')

            prompt = f"""Translate this Islamic book metadata from Arabic to Hausa language.
{glossary_text}

Book Title (Arabic): {book.title}
Author: {book.author}
Description (Arabic): {book.description or 'N/A'}
Table of Contents: {json.dumps(book.table_of_contents or [], ensure_ascii=False)}

IMPORTANT: Use the sovereign glossary terms exactly as specified. Do not change Islamic terminology.

Respond in JSON:
{{
    "title_hausa": "Hausa title",
    "description_hausa": "Full description in Hausa",
    "chapters_hausa": ["Babi na 1: ...", "..."],
    "tags_hausa": ["tag1", "tag2", "..."]
}}"""

            try:
                result = parse_json_response(call_ai(prompt))

                book.title_hausa = result.get('title_hausa', book.title_hausa)
                if result.get('description_hausa'):
                    book.description = result['description_hausa']
                if result.get('chapters_hausa'):
                    book.table_of_contents = result['chapters_hausa']
                if result.get('tags_hausa'):
                    book.tags = result['tags_hausa']
                if not book.seo_slug and book.title_hausa:
                    book.seo_slug = book.title_hausa.lower().replace(' ', '-')[:200]
                book.language = 'ha'
                book.save()

                self.stdout.write(self.style.SUCCESS(f'✅ Translated: {book.title} → {book.title_hausa}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Failed: {book.title} - {e}'))
